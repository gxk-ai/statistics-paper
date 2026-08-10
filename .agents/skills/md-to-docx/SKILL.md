---
name: md-to-docx
description: 将 Markdown 论文文件转换为 DOCX 格式，LaTeX 公式保持原文不转换。当用户提到"转docx"、"生成word"、"转word"、"导出docx"、"转换格式"、"md转docx"时触发。也可用于论文排版、格式转换、生成最终提交文档等场景。使用 pandoc 配合学校论文模板确保格式符合学位论文规范。
allowed-tools: Bash Read Write Glob
---

# Markdown 转 DOCX 技能

将 Markdown 论文转换为符合湘潭大学学位论文格式规范的 DOCX 文件。LaTeX 公式（`$...$`、`$$...$$`）保持原文，不做任何转换。

## 前置条件

- pandoc >= 3.0 已安装
- 学校论文模板：`data/研究生学位论文写作指南.docx`

## 工作流程

```
用户请求：转 docx / 生成 word
       │
       ▼
【第一步】确认输入
├── 确认要转换的 .md 文件路径
├── 若用户未指定，扫描 lunwen/lunwen_md/ 目录
├── 若有多个文件，询问是合并转换还是逐个转换
└── 确认输出文件名（默认与输入同名，扩展名改为 .docx）

【第二步】执行转换
├── 调用转换脚本
├── 使用学校模板作为 reference-doc
├── LaTeX 公式保持原文
└── 输出到 lunwen/lunwen_docx/

【第三步】验证结果
├── 确认文件已生成
├── 检查文件大小是否合理（非空文件）
└── 告知用户输出路径
```

## 转换命令

核心命令如下，通过脚本 `scripts/convert.sh` 封装：

```bash
pandoc <input.md> \
  -o <output.docx> \
  --reference-doc=data/研究生学位论文写作指南.docx \
  --standalone \
  --wrap=preserve
```

**关键说明：**
- **不加 `--mathml`、`--mathjax` 等数学选项**：这确保 LaTeX 公式保持原文状态，不会被转换
- `--reference-doc`：继承学校模板的样式定义（标题层级、字体、页边距等）
- `--standalone`：生成完整文档
- `--wrap=preserve`：保留原始换行

## 多文件处理

当需要将多个章节文件合并为一个 DOCX 时：

```bash
pandoc chapter-1.md chapter-2.md chapter-3.md \
  -o full-paper.docx \
  --reference-doc=data/研究生学位论文写作指南.docx \
  --standalone \
  --wrap=preserve
```

按章节顺序依次列出文件，pandoc 会按顺序合并。

## 默认路径约定

| 项目 | 路径 |
|------|------|
| 输入目录 | `lunwen/lunwen_md/` |
| 输出目录 | `lunwen/lunwen_docx/` |
| 学校模板 | `data/研究生学位论文写作指南.docx` |
| 转换脚本 | `skills/md-to-docx/scripts/convert.sh` |

所有路径相对于项目根目录（`D:/github/lunwen-writting/`）。

## 参考文档

- `references/thesis-format-guide.md`：湘潭大学研究生学位论文写作指南全文，包含页面设置、字体字号、标题层级、参考文献格式等详细规范。当需要检查或调整输出格式时读取此文件。

## 注意事项

- 转换前确认输出目录存在，不存在则创建
- 如果用户提供了自定义模板路径，优先使用用户指定的模板
- 如果输入 md 中包含图片引用（`![](path)`），确保图片路径在转换后仍然可访问
- 合并多文件时，按论文章节顺序排列：摘要 → Abstract → 各章 → 参考文献 → 致谢 → 附录
