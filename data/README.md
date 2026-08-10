# Data

`data/` stores datasets and data documentation.

## Suggested Layout

```text
data/
├── raw/
├── interim/
├── processed/
├── external/
└── metadata/
```

## Rule

- Never modify files in `data/raw/` directly.
- Store cleaned or feature-ready data in `data/processed/`.
- Document fields, source, license, refresh date, and known quality issues in `data/metadata/`.
