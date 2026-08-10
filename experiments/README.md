# Experiments

`experiments/` records how analysis and algorithm runs were executed.

## Suggested Layout

```text
experiments/
├── notebooks/
├── configs/
├── runs/
└── README.md
```

## Run Rule

Each substantial run should get a stable run directory:

```text
experiments/runs/EXP-001/
├── config.yaml
├── run.log
├── metrics.json
├── environment.txt
└── outputs/
```

Link important runs back into `thesis-map.yml`.
