# Tree Model Experiment Plan

## Data Artifacts

- Input survey export: `paper-materials/data/raw/survey/*.csv`
- Built analysis dataset: `artifacts/tables/analysis_dataset.csv`
- Data dictionary: `artifacts/tables/data_dictionary.csv`
- Model reports: `artifacts/reports/tree_models/`

## Reproduce

Build the tertiary-indicator dataset:

```powershell
python src/features/build_analysis_dataset.py
```

Run a quick smoke test:

```powershell
python src/training/train_tree_models.py --quick
```

Run the full parameter search after dependencies are available:

```powershell
python src/training/train_tree_models.py
```

Optional model dependencies:

```powershell
python -m pip install xgboost catboost shap
```

## Notes

- The source files under `paper-materials/` are treated as read-only.
- The target is `y_enlist_positive`: question 13 values `1` and `2` are positive; values `3`, `4`, and `5` are non-positive.
- Train/test split uses stratified 80/20 sampling with `random_state=2026`.
- Structural missing flags are added for skipped military-training, textbook, and equipment-attention questions.
- The training report includes two CatBoost variants:
  - `CatBoostAccuracy`: no class balancing; selected for overall Accuracy/F1 comparison.
  - `CatBoostBalanced`: balanced class weights; selected for Specificity, Balanced Accuracy, and MCC comparison.
- `CatBoostAccuracy` tunes the classification threshold on an internal validation split from the training set only; the test set remains held out for final evaluation.
