# DOCX → Markdown 转换常见问题排查

## 环境问题

### pandoc 未安装

**现象**：`[ERROR] pandoc 失败: 'pandoc' 不是内部或外部命令`

**解决**：
```bash
# Windows (winget)
winget install JohnMacFarlane.Pandoc

# 或从 https://pandoc.org/installing.html 下载安装
```

## 转换问题

### 图片路径错误

**现象**：Markdown 中 `![](media/imageN.png)` 引用的文件不存在

**原因**：pandoc 使用 `--extract-media` 提取图片时路径嵌套

**处理**：脚本会自动修复路径并将文件提升到 `media/` 目录。如果仍有问题：
1. 检查 `media/media/` 子目录是否有文件
2. 手动将 `media/media/` 中的文件移到 `media/`

### 表格格式混乱

**现象**：Markdown 表格列对齐不正确

**原因**：复杂 Word 表格（合并单元格）无法完美转为 Markdown 表格

**处理**：手动调整表格格式，或使用 HTML 表格语法

## 格式兼容性

### 支持的 DOCX 特性

| 特性 | 支持程度 | 说明 |
|------|----------|------|
| 标题层级 | 完整 | h1-h6 正确转换 |
| 段落文本 | 完整 | 含粗体、斜体 |
| OMML 公式 | 完整 | pandoc 原生支持 |
| 图片 | 完整 | 提取到 media/ |
| 表格 | 良好 | 简单表格完美，复杂表格需调整 |
| 批注 | 不支持 | 使用 --track-changes=accept |
| 修订 | 接受 | 所有修订自动接受 |
| 页眉页脚 | 不支持 | pandoc 默认不提取 |
| 目录 | 不支持 | pandoc 输出为空 |
| 文本框 | 部分 | 可能丢失 |
| 艺术字 | 不支持 | 丢失 |
