#!/usr/bin/env python
"""DOCX → Markdown 转换脚本

3步流水线:
  Step 0: 预处理 DOCX（提取纯文本中的 LaTeX 公式为占位符）
  Step 1: pandoc 转换 DOCX → Markdown（接受所有修订）
  Step 2: 后处理（图片路径修复、清理标记、修复公式、还原占位符、转三线表）

  LaTeX 公式占位符保护：DOCX 中的纯文本 LaTeX 公式（$...$、$$...$$、\[...\]）
  在 pandoc 转换前被替换为占位符，转换后原样还原，避免 pandoc 转义改动。

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
        "-t", "markdown",
        "--wrap=none",
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


def postprocess(md_content, media_dir, formula_map):
    # 1. 修复图片路径
    md_content = _fix_image_paths(md_content)
    _flatten_media_dir(media_dir)

    # 2. 清理 pandoc 多余标记
    md_content = _cleanup(md_content)

    # 3. 还原 LaTeX 公式占位符
    md_content = _restore_formulas(md_content, formula_map)

    # 4. 还原 HTML 实体
    md_content = _fix_html_entities(md_content)

    # 5. 修复 pandoc 对行间公式的错误转义
    md_content = _fix_escaped_display_math(md_content)

    # 6. 三线表 simple table → pipe table
    md_content = _convert_simple_tables(md_content)

    return md_content


def _fix_image_paths(content):
    content = re.sub(r"\((?:[^\)]*?)media[/\\]media[/\\]", "(media/", content)
    content = re.sub(r"!\[\]\s*\|\s*[^\)]*?media[/\\]media[/\\]", r"!\](media/", content)
    content = re.sub(r"\(\./media/", "(media/", content)
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


def _convert_simple_tables(content):
    """将 pandoc simple table 格式转为 markdown pipe table。

    在列切割前先保护 $...$ 公式为占位符，切割后还原，避免公式被截断。
    """
    all_placeholders = {}
    tbl_counter = [0]

    def _parse_block(block_text):
        lines = block_text.split("\n")
        if len(lines) < 3:
            return block_text

        if not re.match(r"^\s*-{10,}\s*$", lines[0]):
            return block_text
        if not re.match(r"^\s*-{10,}\s*$", lines[-1]):
            return block_text

        sep_idx = None
        for i in range(1, len(lines) - 1):
            stripped = lines[i].strip()
            if not stripped:
                continue
            if re.match(r"^[-\s]+$", stripped) and " " in stripped and "-" in stripped:
                sep_idx = i
                break
        if sep_idx is None:
            return block_text

        # 列边界
        sep_line = lines[sep_idx]
        columns = []
        i = 0
        while i < len(sep_line):
            if sep_line[i] == "-":
                start = i
                while i < len(sep_line) and sep_line[i] == "-":
                    i += 1
                columns.append((start, i))
            else:
                i += 1
        if not columns:
            return block_text

        # 保护公式为占位符
        tid = tbl_counter[0]
        tbl_counter[0] += 1
        cell_counter = [0]

        def _protect(s):
            key = f"@@TBL_{tid}_{cell_counter[0]}@@"
            all_placeholders[key] = s.group(0)
            cell_counter[0] += 1
            return key

        protected = []
        for line in lines:
            protected.append(re.sub(r"\$[^$]+?\$", _protect, line))

        # 定位 header / data
        header_idx = sep_idx - 1
        while header_idx > 0 and not protected[header_idx].strip():
            header_idx -= 1
        header_line = protected[header_idx] if header_idx > 0 else None

        data_lines = []
        for i in range(sep_idx + 1, len(protected) - 1):
            stripped = protected[i].strip()
            if stripped and not re.match(r"^-+$", stripped):
                data_lines.append(protected[i])

        def _split_row(line):
            cells = []
            for start, end in columns:
                cell = line[start:end].strip() if len(line) >= start else ""
                cells.append(cell)
            return cells

        col_count = len(columns)
        result = []

        if header_line:
            headers = _split_row(header_line)
            result.append("| " + " | ".join(headers) + " |")
            result.append("|" + "|".join(["-" * max(len(h) + 2, 5) for h in headers]) + "|")

        for dl in data_lines:
            cells = _split_row(dl)
            while len(cells) < col_count:
                cells.append("")
            result.append("| " + " | ".join(cells) + " |")

        return "\n".join(result)

    # 匹配 simple table 块
    content = re.sub(
        r"(^[ \t]*-{10,}[ \t]*$\n)((?:^.*$\n)+?)(^[ \t]*-{10,}[ \t]*$)",
        lambda m: _parse_block(m.group(0)),
        content,
        flags=re.MULTILINE,
    )

    # 还原表格中的公式占位符
    for ph, orig in all_placeholders.items():
        content = content.replace(ph, orig)

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
        md_content = postprocess(md_content, media_dir, formula_map)

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
