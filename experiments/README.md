# 实验

`experiments/` 记录分析和算法运行是如何执行的。

## 建议结构

```text
experiments/
|-- notebooks/
|-- configs/
|-- runs/
`-- README.md
```

## 运行规则

每个实质性实验都应有一个稳定的运行目录：

```text
experiments/runs/EXP-001/
|-- config.yaml
|-- run.log
|-- metrics.json
|-- environment.txt
`-- outputs/
```

重要运行结果应链接回 `thesis-map.yml`。
