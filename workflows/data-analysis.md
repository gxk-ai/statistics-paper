# 数据分析与算法工作流

用于数据准备、算法代码、模型训练、评估和可复现性记录。

## 先读

- `project-state.yml`
- `research/variables.md`
- `research/methodology.md`
- `data/metadata/`
- `experiments/configs/`

## 代码布局

- 可复用代码：`src/`
- 实验配置：`experiments/configs/`
- 运行日志和指标：`experiments/runs/`
- 最终图件、表格和模型：`artifacts/`

## 步骤

1. 确认数据来源、字段定义和数据切分策略。
2. 将可复用的数据、特征、模型、训练、评估和可视化代码放到 `src/`。
3. 将每个实验设置放到 `experiments/configs/`。
4. 将每次运行保存到 `experiments/runs/EXP-XXX/`。
5. 只有可直接用于论文的输出才提升到 `artifacts/`。
6. 在 `thesis-map.yml` 中链接重要运行、图件、表格和发现。

## 输出

- `src/`
- `experiments/configs/`
- `experiments/runs/`
- `artifacts/figures/`
- `artifacts/tables/`
- `artifacts/models/`
- `research/findings/`
- `thesis-map.yml`
