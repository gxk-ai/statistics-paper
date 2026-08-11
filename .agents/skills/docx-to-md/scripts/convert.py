#!/usr/bin/env python
r"""DOCX → Markdown 转换脚本

4步流水线:
  Step 0: 预处理 DOCX（提取纯文本中的 LaTeX 公式为占位符）
  Step 1: pandoc 转换 DOCX → Markdown（接受所有修订）
  Step 2: 后处理（图片路径修复、清理标记、修复公式、还原占位符）
  Step 3: 将 WPS/MathType 等 OLE 公式导出的 WMF 预览图转为 PNG
  Step 4: 按 formula-map.tsv 将公式预览图替换为 LaTeX

  LaTeX 公式占位符保护：DOCX 中的纯文本 LaTeX 公式（$...$、$$...$$、\[...\]）
  在 pandoc 转换前被替换为占位符，转换后原样还原，避免 pandoc 转义改动。

  注意：WPS/金山公式（Equation.KSEE3）和部分 MathType 公式在 DOCX 中不是 OMML，
  pandoc 只能读取到 WMF 预览图。脚本会自动把这些 WMF 转为 PNG 并修正引用。
  若输出目录存在 formula-map.tsv，则会进一步把已校正的公式图片替换为 LaTeX。

用法:
  python convert.py <input.docx> [-o output_dir]
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

_PLACEHOLDER_PREFIX = "@@LATEX_FORMULA_"
_PLACEHOLDER_SUFFIX = "@@@"


# ── Step 0: 预处理 DOCX ───────────────────────────────────


def _protect_formulas_in_docx(docx_path, tmp_dir):
    """提取 DOCX 中纯文本里的 LaTeX 公式，替换为占位符。

    返回:
        modified_docx_path: 替换后的临时 DOCX 路径
        formula_map: {占位符: 原公式文本}
    """
    formula_map = {}
    counter = [0]

    def _replace(match):
        key = f"{_PLACEHOLDER_PREFIX}{counter[0]}{_PLACEHOLDER_SUFFIX}"
        formula_map[key] = match.group(0)
        counter[0] += 1
        return key

    with zipfile.ZipFile(docx_path, "r") as zin:
        document_xml = zin.read("word/document.xml").decode("utf-8")

    def _process_text(text):
        text = re.sub(r"\$\$.*?\$\$", _replace, text, flags=re.DOTALL)
        text = re.sub(r"\\\[.*?\\\]", _replace, text, flags=re.DOTALL)
        text = re.sub(r"(?<!@)\$[^$@\n]+?\$", _replace, text)
        return text

    new_xml = re.sub(
        r"(<w:t[^>]*>)(.*?)(</w:t>)",
        lambda m: m.group(1) + _process_text(m.group(2)) + m.group(3),
        document_xml,
        flags=re.DOTALL,
    )

    if not formula_map:
        return docx_path, formula_map

    modified_path = os.path.join(tmp_dir, "protected.docx")
    with zipfile.ZipFile(docx_path, "r") as zin:
        with zipfile.ZipFile(modified_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "word/document.xml":
                    zout.writestr(item, new_xml.encode("utf-8"))
                else:
                    zout.writestr(item, zin.read(item.filename))

    print(f"[INFO] 保护了 {len(formula_map)} 个 LaTeX 公式")
    return modified_path, formula_map


# ── Step 1: pandoc 转换 ──────────────────────────────────


def _pandoc_convert(docx_path, output_dir, tmp_dir):
    raw_md = os.path.join(tmp_dir, "raw.md")
    media_dir = os.path.join(output_dir, "media")

    cmd = [
        "pandoc",
        os.path.abspath(docx_path),
        "-f", "docx",
        "-t", "gfm+tex_math_dollars",
        "--wrap=none",
        "--markdown-headings=atx",
        f"--extract-media={os.path.abspath(media_dir)}",
        "--track-changes=accept",
        "-o", os.path.abspath(raw_md),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        print(f"[ERROR] pandoc 失败: {proc.stderr}")
        sys.exit(1)

    with open(raw_md, "r", encoding="utf-8") as f:
        content = f.read()

    return content, media_dir


# ── Step 2: 后处理 ──────────────────────────────────────


def postprocess(md_content, media_dir, formula_map, image_formula_map=None):
    # 1. 先整理图片目录，再把 WMF 公式预览图转成 Markdown 可渲染的 PNG
    _flatten_media_dir(media_dir)
    wmf_map = _convert_wmf_media_to_png(media_dir)
    md_content = _replace_media_extensions(md_content, wmf_map)

    # 2. 修复图片路径
    md_content = _fix_image_paths(md_content)

    # 3. 清理 pandoc 多余标记
    md_content = _cleanup(md_content)

    # 4. 还原 LaTeX 公式占位符
    md_content = _restore_formulas(md_content, formula_map)

    # 5. 还原 HTML 实体
    md_content = _fix_html_entities(md_content)

    # 6. 修复 pandoc 对行间公式的错误转义
    md_content = _fix_escaped_display_math(md_content)

    # 7. 将 WPS/MathType 公式预览图替换为已校正 LaTeX
    md_content = _replace_formula_images_with_latex(md_content, image_formula_map or {})

    return md_content


def _fix_image_paths(content):
    content = re.sub(r"\((?:[^\)]*?)media[/\\]media[/\\]", "(media/", content)
    content = re.sub(r"!\[\]\s*\|\s*[^\)]*?media[/\\]media[/\\]", r"!\](media/", content)
    content = re.sub(r"\(\./media/", "(media/", content)
    content = re.sub(r'(<img\b[^>]*\bsrc=")[^"]*?media[/\\]media[/\\]', r"\1media/", content)
    content = re.sub(r'(<img\b[^>]*\bsrc=")\./media/', r"\1media/", content)
    return content


def _flatten_media_dir(media_dir):
    nested = os.path.join(media_dir, "media")
    if os.path.isdir(nested):
        for f in os.listdir(nested):
            src = os.path.join(nested, f)
            dst = os.path.join(media_dir, f)
            if os.path.isfile(src) and not os.path.exists(dst):
                shutil.move(src, dst)
        try:
            os.rmdir(nested)
        except OSError:
            pass


def _convert_wmf_media_to_png(media_dir):
    """Convert extracted WMF previews to PNG on Windows.

    WPS/Kingsoft equation objects are stored as OLE objects with WMF previews.
    Pandoc sees those previews as images, not as math. Most Markdown renderers
    cannot display WMF, so converting them to PNG preserves the visible formula.
    """
    media_path = Path(media_dir)
    wmf_files = sorted(media_path.glob("*.wmf"))
    if not wmf_files:
        return {}

    if os.name != "nt":
        print(f"[WARN] 检测到 {len(wmf_files)} 个 WMF 文件；当前系统无法自动转 PNG。")
        return {}

    ps_script = r'''
param(
    [Parameter(Mandatory=$true)][string]$MediaDir,
    [int]$Scale = 6
)
Add-Type -AssemblyName System.Drawing
$ErrorActionPreference = "Stop"
Get-ChildItem -LiteralPath $MediaDir -Filter *.wmf | ForEach-Object {
    $src = $_.FullName
    $dst = [System.IO.Path]::ChangeExtension($src, ".png")
    $img = [System.Drawing.Image]::FromFile($src)
    try {
        $width = [Math]::Max(1, [int]($img.Width * $Scale))
        $height = [Math]::Max(1, [int]($img.Height * $Scale))
        $bmp = New-Object System.Drawing.Bitmap $width, $height
        try {
            $bmp.SetResolution([Math]::Max(96, $img.HorizontalResolution * $Scale), [Math]::Max(96, $img.VerticalResolution * $Scale))
            $graphics = [System.Drawing.Graphics]::FromImage($bmp)
            try {
                $graphics.Clear([System.Drawing.Color]::White)
                $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
                $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
                $graphics.DrawImage($img, 0, 0, $width, $height)
            } finally {
                $graphics.Dispose()
            }
            $bmp.Save($dst, [System.Drawing.Imaging.ImageFormat]::Png)
        } finally {
            $bmp.Dispose()
        }
    } finally {
        $img.Dispose()
    }
}
'''
    import tempfile
    with tempfile.TemporaryDirectory(prefix="wmf2png_") as tmp_dir:
        script_path = Path(tmp_dir) / "convert-wmf.ps1"
        script_path.write_text(ps_script, encoding="utf-8")
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", str(script_path),
            "-MediaDir", str(media_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    converted = {}
    if proc.returncode != 0:
        print(f"[WARN] WMF 转 PNG 失败，将保留 WMF 引用: {proc.stderr.strip()}")
        return converted

    for wmf in wmf_files:
        png = wmf.with_suffix(".png")
        if png.exists():
            converted[wmf.name] = png.name

    print(f"[INFO] 已将 {len(converted)}/{len(wmf_files)} 个 WMF 文件转为 PNG")
    return converted


def _replace_media_extensions(content, filename_map):
    for old_name, new_name in filename_map.items():
        content = content.replace(f"media/{old_name}", f"media/{new_name}")
        content = content.replace(f"media\\{old_name}", f"media/{new_name}")
    return content


def _load_image_formula_map(map_path):
    """Load a tab-separated formula map: imageN.png<TAB>LaTeX body."""
    formulas = {}
    if not map_path or not os.path.exists(map_path):
        return formulas

    with open(map_path, "r", encoding="utf-8") as f:
        for lineno, raw_line in enumerate(f, 1):
            line = raw_line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if "\t" not in line:
                print(f"[WARN] formula-map 第 {lineno} 行缺少 Tab，已跳过")
                continue
            image_name, latex = line.split("\t", 1)
            image_name = image_name.strip()
            latex = latex.strip()
            if not image_name or not latex:
                print(f"[WARN] formula-map 第 {lineno} 行为空，已跳过")
                continue
            formulas[image_name] = latex

    print(f"[INFO] 载入 {len(formulas)} 条公式 LaTeX 映射: {map_path}")
    return formulas


def _replace_formula_images_with_latex(content, image_formula_map):
    if not image_formula_map:
        return content

    image_pattern = re.compile(r"!\[[^\]]*\]\(media/(image\d+\.png)\)")
    bare_pattern = re.compile(r"(?<!]\()\((media/(image\d+\.png))\)")

    def _display_or_inline(line):
        stripped = line.strip()
        match = image_pattern.fullmatch(stripped)
        if match and match.group(1) in image_formula_map:
            latex = image_formula_map[match.group(1)]
            return f"$$\n{latex}\n$$"
        return image_pattern.sub(
            lambda m: f"${image_formula_map[m.group(1)]}$"
            if m.group(1) in image_formula_map else m.group(0),
            line,
        )

    lines = [_display_or_inline(line) for line in content.splitlines()]
    content = "\n".join(lines)

    # Some malformed pandoc output can leave a bare "(media/imageN.png)" after
    # an inline formula. Replace only mapped formula images, not regular figures.
    content = bare_pattern.sub(
        lambda m: f"${image_formula_map[m.group(2)]}$"
        if m.group(2) in image_formula_map else m.group(0),
        content,
    )
    return content


def _cleanup(content):
    content = re.sub(r"\s*\{\.mark\}", "", content)
    content = re.sub(r"\n{4,}", "\n\n\n", content)
    content = re.sub(r":::\s*\{[^}]*\}\s*\n?", "", content)
    content = re.sub(r":::\s*\n?", "", content)
    content = re.sub(r"\[([^\]]*)\]\{\.[a-z][a-z0-9_-]*\}", r"\1", content)
    return content


def _restore_formulas(content, formula_map):
    if not formula_map:
        return content
    for placeholder, original in formula_map.items():
        content = content.replace(placeholder, original)
    return content


def _fix_html_entities(content):
    content = content.replace("&lt;", "<")
    content = content.replace("&gt;", ">")
    content = content.replace("&amp;", "&")
    return content


def _fix_escaped_display_math(content):
    r"""修复 pandoc 对多行公式的错误转义 \$...\$ → $$...$$。"""
    def _fix_one(match):
        body = match.group(1)
        body = re.sub(r"\\\\([a-zA-Z])", r"\\\1", body)
        body = body.replace("\\*", "*")
        body = body.replace("\\[", "[").replace("\\]", "]")
        body = body.replace("\\_", "_").replace("\\^", "^")
        return f"$${body}$$"

    content = re.sub(
        r"\\\$((?:[^$]|(?<!\\)\$(?!\$))*?)\\\$",
        _fix_one,
        content,
        flags=re.DOTALL,
    )
    return content


# ── 主流程 ────────────────────────────────────────────────


def convert(docx_path, output_dir=None):
    docx_path = os.path.abspath(docx_path)
    if not os.path.exists(docx_path):
        print(f"[ERROR] 文件不存在: {docx_path}")
        sys.exit(1)

    if output_dir is None:
        output_dir = os.path.dirname(docx_path)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    base_name = Path(docx_path).stem + ".md"
    output_path = os.path.join(output_dir, base_name)
    formula_map_path = os.path.join(output_dir, "formula-map.tsv")
    image_formula_map = _load_image_formula_map(formula_map_path)

    print(f"[INFO] 输入: {docx_path}")
    print(f"[INFO] 输出: {output_path}")

    import tempfile
    with tempfile.TemporaryDirectory(prefix="docx2md_") as tmp_dir:

        print("[STEP 0] 保护 LaTeX 公式...")
        safe_docx, formula_map = _protect_formulas_in_docx(docx_path, tmp_dir)

        print("[STEP 1] pandoc 转换...")
        md_content, media_dir = _pandoc_convert(safe_docx, output_dir, tmp_dir)
        print(f"[INFO] pandoc 输出 {len(md_content)} 字符")

        print("[STEP 2] 后处理...")
        md_content = postprocess(md_content, media_dir, formula_map, image_formula_map)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"[DONE] 输出: {output_path}")
    if formula_map:
        print(f"[INFO] 已还原 {len(formula_map)} 个 LaTeX 公式")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="DOCX → Markdown 转换")
    parser.add_argument("input", help="输入 DOCX 文件路径")
    parser.add_argument("-o", "--output", help="输出目录（默认与输入同目录）")
    args = parser.parse_args()
    convert(args.input, args.output)


if __name__ == "__main__":
    main()
