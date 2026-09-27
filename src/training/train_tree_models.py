"""Train and compare RF, XGBoost, and CatBoost on the analysis dataset."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any
import sys

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.base import clone
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.models import catboost, random_forest, xgboost
DEFAULT_DATASET = ROOT / "artifacts" / "tables" / "analysis_dataset.csv"
DEFAULT_DICTIONARY = ROOT / "artifacts" / "tables" / "data_dictionary.csv"
DEFAULT_REPORT_DIR = ROOT / "artifacts" / "reports" / "tree_models"
RANDOM_STATE = 2026


def optional_import_xgboost() -> Any | None:
    try:
        from xgboost import XGBClassifier
    except Exception:
        return None
    return XGBClassifier


def optional_import_catboost() -> Any | None:
    try:
        from catboost import CatBoostClassifier
    except Exception:
        return None
    return CatBoostClassifier


def load_feature_groups(dictionary_path: Path) -> dict[str, str]:
    groups: dict[str, str] = {}
    with dictionary_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["role"] in {"feature", "missing_flag", "raw_categorical_feature"}:
                groups[row["variable"]] = row["secondary_indicator"]
    return groups


def specificity_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    tn, fp, _, _ = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return tn / (tn + fp) if (tn + fp) else 0.0


def predictions_at_threshold(estimator: Any, x_data: pd.DataFrame, threshold: float) -> np.ndarray:
    if hasattr(estimator, "predict_proba"):
        y_score = estimator.predict_proba(x_data)[:, 1]
        return (y_score >= threshold).astype(int)
    return estimator.predict(x_data)


def tune_threshold(
    estimator: Any,
    x_train: pd.DataFrame,
    y_train: pd.Series,
    objective: str = "accuracy",
    fit_params: dict[str, Any] | None = None,
) -> float:
    x_fit, x_val, y_fit, y_val = train_test_split(
        x_train,
        y_train,
        test_size=0.2,
        stratify=y_train,
        random_state=RANDOM_STATE,
    )
    threshold_model = clone(estimator)
    threshold_model.fit(x_fit, y_fit, **(fit_params or {}))
    if not hasattr(threshold_model, "predict_proba"):
        return 0.5

    y_score = threshold_model.predict_proba(x_val)[:, 1]
    best_threshold = 0.5
    best_score = -1.0
    for threshold in np.linspace(0.25, 0.75, 101):
        y_pred = (y_score >= threshold).astype(int)
        if objective == "balanced_accuracy":
            score = balanced_accuracy_score(y_val, y_pred)
        elif objective == "mcc":
            score = matthews_corrcoef(y_val, y_pred)
        else:
            score = accuracy_score(y_val, y_pred)
        if score > best_score:
            best_score = score
            best_threshold = float(threshold)
    return best_threshold


def evaluate_model(
    name: str,
    estimator: Any,
    x_test: pd.DataFrame,
    y_test: pd.Series,
    threshold: float = 0.5,
    threshold_objective: str = "fixed_0.5",
) -> dict[str, float | str]:
    y_pred = predictions_at_threshold(estimator, x_test, threshold)
    if hasattr(estimator, "predict_proba"):
        y_score = estimator.predict_proba(x_test)[:, 1]
    else:
        y_score = y_pred

    return {
        "model": name,
        "threshold": threshold,
        "threshold_objective": threshold_objective,
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "specificity": specificity_score(y_test.to_numpy(), y_pred),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_test, y_score),
        "pr_auc": average_precision_score(y_test, y_score),
        "balanced_accuracy": balanced_accuracy_score(y_test, y_pred),
        "mcc": matthews_corrcoef(y_test, y_pred),
    }


def write_confusion_matrix(path: Path, estimator: Any, x_test: pd.DataFrame, y_test: pd.Series, threshold: float = 0.5) -> None:
    y_pred = predictions_at_threshold(estimator, x_test, threshold)
    matrix = confusion_matrix(y_test, y_pred, labels=[1, 0])
    rows = [
        ["", "pred_positive", "pred_negative"],
        ["true_positive", int(matrix[0, 0]), int(matrix[0, 1])],
        ["true_negative", int(matrix[1, 0]), int(matrix[1, 1])],
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)


def save_permutation_importance(path: Path, estimator: Any, x_test: pd.DataFrame, y_test: pd.Series, groups: dict[str, str]) -> None:
    result = permutation_importance(
        estimator,
        x_test,
        y_test,
        scoring="roc_auc",
        n_repeats=10,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    rows = []
    for feature, mean_value, std_value in zip(x_test.columns, result.importances_mean, result.importances_std):
        rows.append(
            {
                "feature": feature,
                "secondary_indicator": groups.get(feature, ""),
                "importance_mean_auc_drop": mean_value,
                "importance_std": std_value,
            }
        )
    pd.DataFrame(rows).sort_values("importance_mean_auc_drop", ascending=False).to_csv(
        path, index=False, encoding="utf-8-sig"
    )


def save_shap_importance(path: Path, aggregate_path: Path, estimator: Any, x_test: pd.DataFrame, groups: dict[str, str]) -> None:
    try:
        import shap
    except Exception as exc:
        print(f"skip SHAP: {exc}")
        return

    if hasattr(estimator, "named_steps"):
        imputer = estimator.named_steps["imputer"]
        model = estimator.named_steps["model"]
        x_imputed = pd.DataFrame(imputer.transform(x_test), columns=x_test.columns, index=x_test.index)
    else:
        model = estimator
        x_imputed = x_test
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(x_imputed)
    if isinstance(shap_values, list):
        shap_values = shap_values[-1]
    if getattr(shap_values, "ndim", 0) == 3:
        shap_values = shap_values[:, :, -1]

    values = np.abs(shap_values).mean(axis=0)
    rows = [
        {
            "feature": feature,
            "secondary_indicator": groups.get(feature, ""),
            "mean_abs_shap": value,
        }
        for feature, value in zip(x_test.columns, values)
    ]
    detail = pd.DataFrame(rows).sort_values("mean_abs_shap", ascending=False)
    detail.to_csv(path, index=False, encoding="utf-8-sig")
    detail.groupby("secondary_indicator", as_index=False)["mean_abs_shap"].sum().sort_values(
        "mean_abs_shap", ascending=False
    ).to_csv(aggregate_path, index=False, encoding="utf-8-sig")



def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--quick", action="store_true", help="Use a small parameter search for smoke testing.")
    parser.add_argument("--skip-importance", action="store_true", help="Skip permutation and SHAP importance outputs.")
    args = parser.parse_args()

    df = pd.read_csv(args.dataset, encoding="utf-8-sig")
    y = df["y_enlist_positive"].astype(int)
    x = df.drop(columns=["record_id", "y_enlist_positive", "enlist_willingness_raw"])
    cat_features = [column for column in x.columns if column.startswith("raw_cat_")]
    numeric_features = [column for column in x.columns if column not in cat_features]
    groups = load_feature_groups(args.dictionary)

    x_train_all, x_test_all, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        stratify=y,
        random_state=RANDOM_STATE,
    )
    x_train_numeric = x_train_all[numeric_features]
    x_test_numeric = x_test_all[numeric_features]
    cv = StratifiedKFold(n_splits=3 if args.quick else 5, shuffle=True, random_state=RANDOM_STATE)

    args.report_dir.mkdir(parents=True, exist_ok=True)
    split_summary = {
        "random_state": RANDOM_STATE,
        "train_rows": int(len(x_train_all)),
        "test_rows": int(len(x_test_all)),
        "train_positive": int(y_train.sum()),
        "train_negative": int(len(y_train) - y_train.sum()),
        "test_positive": int(y_test.sum()),
        "test_negative": int(len(y_test) - y_test.sum()),
        "numeric_features": numeric_features,
        "catboost_categorical_features": cat_features,
        "catboost_features": list(x.columns),
    }
    (args.report_dir / "split_summary.json").write_text(
        json.dumps(split_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    searches: list[tuple[str, RandomizedSearchCV | None, str]] = [
        ("RandomForest", random_forest.build_search(cv, args.quick, RANDOM_STATE), "numeric"),
        ("XGBoost", xgboost.build_search(cv, args.quick, RANDOM_STATE), "numeric"),
        ("CatBoostAccuracy", catboost.build_search(cv, args.quick, RANDOM_STATE, balanced=False), "all"),
        ("CatBoostBalanced", catboost.build_search(cv, args.quick, RANDOM_STATE, balanced=True), "all"),
    ]

    metrics: list[dict[str, float | str]] = []
    best_params: dict[str, Any] = {}
    skipped: list[str] = []

    for name, search, feature_mode in searches:
        if search is None:
            skipped.append(name)
            print(f"skip {name}: package is not available")
            continue

        x_train = x_train_all if feature_mode == "all" else x_train_numeric
        x_test = x_test_all if feature_mode == "all" else x_test_numeric
        fit_params = {"cat_features": cat_features} if feature_mode == "all" else {}
        print(f"training {name}")
        search.fit(x_train, y_train, **fit_params)
        estimator = search.best_estimator_
        threshold_objective = "accuracy" if name == "CatBoostAccuracy" else "fixed_0.5"
        threshold = (
            tune_threshold(estimator, x_train, y_train, objective=threshold_objective, fit_params=fit_params)
            if name == "CatBoostAccuracy"
            else 0.5
        )
        metrics.append(evaluate_model(name, estimator, x_test, y_test, threshold, threshold_objective))
        best_params[name] = search.best_params_
        best_params[name]["classification_threshold"] = threshold
        best_params[name]["threshold_objective"] = threshold_objective
        write_confusion_matrix(args.report_dir / f"{name}_confusion_matrix.csv", estimator, x_test, y_test, threshold)
        if not args.skip_importance:
            save_permutation_importance(
                args.report_dir / f"{name}_permutation_importance.csv",
                estimator,
                x_test,
                y_test,
                groups,
            )
            if name in {"XGBoost", "CatBoostAccuracy", "CatBoostBalanced"}:
                save_shap_importance(
                    args.report_dir / f"{name}_shap_importance.csv",
                    args.report_dir / f"{name}_shap_secondary_importance.csv",
                    estimator,
                    x_test,
                    groups,
                )

    pd.DataFrame(metrics).to_csv(args.report_dir / "model_metrics.csv", index=False, encoding="utf-8-sig")
    (args.report_dir / "best_params.json").write_text(
        json.dumps(best_params, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if skipped:
        (args.report_dir / "skipped_models.txt").write_text("\n".join(skipped), encoding="utf-8")
    else:
        skipped_path = args.report_dir / "skipped_models.txt"
        if skipped_path.exists():
            skipped_path.unlink()

    print(f"wrote reports to {args.report_dir}")


if __name__ == "__main__":
    main()
