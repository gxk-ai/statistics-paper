# Data Analysis And Algorithm Workflow

Use this workflow for data preparation, algorithm code, model training, evaluation, and reproducibility.

## Read First

- `project-state.yml`
- `research/variables.md`
- `research/methodology.md`
- `data/metadata/`
- `experiments/configs/`

## Code Layout

- Reusable code: `src/`
- Experiment configs: `experiments/configs/`
- Run logs and metrics: `experiments/runs/`
- Final figures, tables, and models: `artifacts/`

## Steps

1. Confirm data source, field definitions, and split policy.
2. Put reusable data, feature, model, training, evaluation, and visualization code in `src/`.
3. Put each experiment setup in `experiments/configs/`.
4. Save each run under `experiments/runs/EXP-XXX/`.
5. Promote only thesis-ready outputs to `artifacts/`.
6. Link important runs, figures, tables, and findings in `thesis-map.yml`.

## Outputs

- `src/`
- `experiments/configs/`
- `experiments/runs/`
- `artifacts/figures/`
- `artifacts/tables/`
- `artifacts/models/`
- `research/findings/`
- `thesis-map.yml`
