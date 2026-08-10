# 源代码

`src/` 存放论文项目中可复用的算法和分析代码。

## 建议结构

```text
src/
|-- data/
|-- features/
|-- models/
|-- training/
|-- evaluation/
|-- visualization/
`-- utils/
```

## 边界

- 可复用代码放在这里。
- 一次性 notebook、运行配置、日志和实验输出放在 `experiments/`。
- 最终图件、表格、报告和模型产物放在 `artifacts/`。
