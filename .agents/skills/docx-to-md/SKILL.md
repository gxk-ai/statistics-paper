---
name: docx-to-md
description: DOCX 转 Markdown 技能。当用户需要将 Word/WPS 文档转为 Markdown、把 docx 转成 md、文档格式转换时触发。脚本负责 pandoc 转换和图片提取；三线表和公式由 AI 后处理为 LaTeX 格式。触发词包括：docx转md、word转markdown、文档转换、把文档转成md、转换格式、转md。
allowed-tools: Read, Write, Edit, Bash
---

# DOCX → Markdown 转换技能

将 WPS/Word 编辑的学术论文转为 Markdown 格式，便于后续编辑和版本管理。

## 适用场景

- 论文稿件需要转为 Markdown 进行版本管理
- 图片需要从 DOCX 中提取
- 三线表需要由 AI 转为 LaTeX 表格
- 公式需要由 AI 转为 LaTeX 格式

## 环境依赖

| 依赖 | 用途 | 是否必须 |
|------|------|----------|
| Python 3.10+ | 脚本运行 | 是 |
| pandoc | DOCX → Markdown 核心转换 | 是 |

## 工作流程

```
用户请求：转换 DOCX → Markdown
       │
       ▼
【Step 1】环境检查
└── 检查 pandoc 是否可用
       │
       ▼
【Step 2】执行转换脚本
├── 运行 convert.py
├── pandoc DOCX → GFM Markdown（OMML 公式自动转 LaTeX）
├── 最小后处理（图片路径修复、清理标记）
├── WPS/MathType OLE 公式预览图 WMF → PNG
├── formula-map.tsv 中已校正公式图片 → LaTeX
└── 输出 Markdown + media 目录
       │
       ▼
【Step 3】AI 后处理
├── 三线表 → LaTeX booktabs 表格
├── 公式图片 → LaTeX 正确格式，并写入 formula-map.tsv
├── 检查是否仍有 WMF 引用
└── 具体规则见下方"目标格式"
       │
       ▼
【Step 4】验证输出
├── 检查 Markdown 文件是否生成
├── 检查图片是否提取到 media/，且 Markdown 中不再引用 WMF
└── 检查公式/表格是否正确转换
       │
       ▼
【Step 5】报告结果
├── 输出文件路径
└── 转换统计（表格数、公式数）
```

## 使用方式

### 基本用法

```bash
python skills/docx-to-md/scripts/convert.py <input.docx>
```

### 指定输出目录

```bash
python skills/docx-to-md/scripts/convert.py <input.docx> -o <output_dir>
```

## 输出格式说明

### 文件结构

```
output_dir/
├── {文件名}.md          # 转换后的 Markdown
└── media/
    ├── image1.png       # 提取的图片
    ├── image2.png
    └── ...
```

### 公式对象处理

- Word 原生 OMML 公式：由 pandoc 尽量转为 LaTeX。
- 纯文本 LaTeX 公式：脚本会在转换前保护占位符，转换后原样还原。
- WPS/金山公式、部分 MathType 公式：在 DOCX 内通常是 OLE 对象（如 `Equation.KSEE3`），pandoc 只能读取 WMF 预览图，不能可靠直接还原 LaTeX。脚本会先将 WMF 转为 PNG 并修正 Markdown 引用；如果输出目录存在 `formula-map.tsv`，再将其中登记的公式图片替换为 LaTeX。

`formula-map.tsv` 格式：

```text
# image file<TAB>LaTeX body
image3.png	MSE=\frac{1}{n}\sum_{i=1}^{n}\omega_i(x_i-\hat{x}_i)^2
```

替换规则：
- 独占一行的公式图片替换为 `$$...$$` 行间公式。
- 夹在正文中的公式图片替换为 `$...$` 行内公式。
- 普通图表图片不要写入 `formula-map.tsv`。

### 表格处理策略

脚本使用 `gfm+tex_math_dollars` 输出，优先让 pandoc 生成 GFM 表格。复杂 Word 表格、合并单元格表格不再用正则硬切列，避免列错位。需要投稿/最终排版时，再由 AI 或人工将核心表格重写为 LaTeX booktabs 表格。

### AI 后处理目标格式

脚本仅执行 pandoc 转换 + 图片路径修复 + 标记清理。以下内容由 AI 后处理：

#### 三线表 → LaTeX booktabs 表格

pandoc 对 Word 三线表输出 simple table 格式：
```
---------------------------------------------------------
Header1   Header2
------    ------
Data1     Data2
---------------------------------------------------------
```

AI 需将其转为 LaTeX booktabs 表格：

```latex
\begin{table}[htbp]
    \centering
    \caption{表格标题}
    \label{tab:example}
    \begin{tabular}{lccc}
        \toprule
        方法 & 准确率 & 召回率 & F1值 \\
        \midrule
        方法A & 0.85 & 0.82 & 0.83 \\
        方法B & 0.88 & 0.86 & 0.87 \\
        本文方法 & \textbf{0.92} & \textbf{0.90} & \textbf{0.91} \\
        \bottomrule
    \end{tabular}
\end{table}
```

转换规则：
- 使用 `\toprule`、`\midrule`、`\bottomrule`（booktabs 宏包）实现三线表
- 表格标题写在 `\caption{}` 中，放在 `\begin{tabular}` 上方
- 列对齐方式根据内容判断：文字列用 `l`，数字列用 `c`
- 注意：数据行之间可能有空行，AI 需跳过空行收集所有数据行

#### 公式 → LaTeX 正确格式

pandoc 从 DOCX 转换时会对公式产生额外转义，AI 需还原为正确 LaTeX 格式：

| pandoc 输出 | 目标格式 | 说明 |
|-------------|----------|------|
| `\$...\$` | `$...$` | 行内公式 |
| `\\\[...\\\]` | `$$...$$` 或 `\begin{equation}` | 行间/独立公式 |

**目标格式规范：**

行内公式：
```latex
这是行内公式 $E=mc^2$。
```

带编号的独立公式：
```latex
\begin{equation}
    f(x) = \int_{-\infty}^{\infty} e^{-x^2} dx
    \label{eq:gaussian}
\end{equation}
```

多行公式：
```latex
\begin{align}
    a &= b + c \\
    d &= e + f
\end{align}
```

无编号公式：
```latex
\begin{equation*}
    y = ax + b
\end{equation*}
```

**转义修复规则：**

| pandoc 输出 | 修复后 | 说明 |
|-------------|--------|------|
| `\\frac` | `\frac` | 双重转义降级 |
| `\\sum` | `\sum` | 双重转义降级 |
| `\\left` | `\left` | 双重转义降级 |
| `\_` → `_`，`\^` → `^` | `_`，`^` | Markdown 特殊字符转义 |
| `\[` → `[`，`\]` → `]` | `[`，`]` | 方括号转义 |

**常见边界情况：**
- 行间公式 `\\\[...\\\]` 前可能出现孤立的 `$$`（pandoc 误生成），需删除
- 部分公式内容可能重复，需去重
- 公式编号如 `(4.1)` 出现在定界符外，需放入 `\label{}` 或保持原样

## 常见问题

详见 `references/troubleshooting.md`。

## 注意事项

1. **WPS 必须关闭文档**：转换前确保目标 DOCX 未在 WPS 中打开
2. **编码**：输出文件统一 UTF-8 编码
3. **修订**：转换自动接受所有修订（`--track-changes=accept`）
