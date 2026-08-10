# 数据

`data/` 存放数据集和数据说明文档。

## 建议结构

```text
data/
|-- raw/
|-- interim/
|-- processed/
|-- external/
`-- metadata/
```

## 规则

- 不要直接修改 `data/raw/` 中的文件。
- 清洗后或可用于特征构造的数据放在 `data/processed/`。
- 字段、来源、许可证、刷新日期和已知质量问题记录在 `data/metadata/`。
