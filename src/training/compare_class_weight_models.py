"""Compare unweighted vs class-weighted tree models."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
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
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "artifacts" / "tables" / "analysis_dataset.csv"
REPORT_DIR = ROOT / "artifacts" / "reports" / "class_weight_models"
RANDOM_STATE = 2026


def specificity_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    tn, fp, _, _ = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return tn / (tn + fp) if (tn + fp) else 0.0


def evaluate(model_name: str, weight_mode: str, estimator, x_test: pd.DataFrame, y_test: pd.Series) -> dict[str, float | str]:
    y_pred = estimator.predict(x_test)
    y_score = estimator.predict_proba(x_test)[:, 1]
    return {
        "model": model_name,
        "weight_mode": weight_mode,
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall_positive": recall_score(y_test, y_pred, zero_division=0),
        "specificity_negative": specificity_score(y_test.to_numpy(), y_pred),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_test, y_score),
        "pr_auc": average_precision_score(y_test, y_score),
        "balanced_accuracy": balanced_accuracy_score(y_test, y_pred),
        "mcc": matthews_corrcoef(y_test, y_pred),
    }


def write_confusion_matrix(path: Path, estimator, x_test: pd.DataFrame, y_test: pd.Series) -> None:
    y_pred = estimator.predict(x_test)
    matrix = confusion_matrix(y_test, y_pred, labels=[1, 0])
    rows = [
        ["", "pred_positive", "pred_negative"],
        ["true_positive", int(matrix[0, 0]), int(matrix[0, 1])],
        ["true_negative", int(matrix[1, 0]), int(matrix[1, 1])],
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)


def main() -> None:
    df = pd.read_csv(DATASET, encoding="utf-8-sig")
    y = df["y_enlist_positive"].astype(int)
    x = df.drop(columns=["record_id", "y_enlist_positive", "enlist_willingness_raw"])
    x = x[[column for column in x.columns if not column.startswith("raw_cat_")]]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        stratify=y,
        random_state=RANDOM_STATE,
    )
    sample_weight = compute_sample_weight(class_weight="balanced", y=y_train)

    models = [
        (
            "RandomForest",
            "none",
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        RandomForestClassifier(
                            n_estimators=500,
                            max_depth=12,
                            max_features="log2",
                            min_samples_split=5,
                            min_samples_leaf=10,
                            class_weight=None,
                            random_state=RANDOM_STATE,
                            n_jobs=-1,
                        ),
                    ),
                ]
            ),
            {},
        ),
        (
            "RandomForest",
            "class_weight_balanced",
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        RandomForestClassifier(
                            n_estimators=500,
                            max_depth=12,
                            max_features="log2",
                            min_samples_split=5,
                            min_samples_leaf=10,
                            class_weight="balanced",
                            random_state=RANDOM_STATE,
                            n_jobs=-1,
                        ),
                    ),
                ]
            ),
            {},
        ),
        (
            "XGBoost",
            "none",
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        XGBClassifier(
                            objective="binary:logistic",
                            eval_metric="auc",
                            n_estimators=400,
                            learning_rate=0.03,
                            max_depth=3,
                            subsample=0.85,
                            colsample_bytree=0.7,
                            reg_alpha=0,
                            reg_lambda=1,
                            min_child_weight=1,
                            gamma=0,
                            tree_method="hist",
                            random_state=RANDOM_STATE,
                            n_jobs=-1,
                        ),
                    ),
                ]
            ),
            {},
        ),
        (
            "XGBoost",
            "sample_weight_balanced",
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        XGBClassifier(
                            objective="binary:logistic",
                            eval_metric="auc",
                            n_estimators=400,
                            learning_rate=0.03,
                            max_depth=3,
                            subsample=0.85,
                            colsample_bytree=0.7,
                            reg_alpha=0,
                            reg_lambda=1,
                            min_child_weight=1,
                            gamma=0,
                            tree_method="hist",
                            random_state=RANDOM_STATE,
                            n_jobs=-1,
                        ),
                    ),
                ]
            ),
            {"model__sample_weight": sample_weight},
        ),
        (
            "CatBoost",
            "none",
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        CatBoostClassifier(
                            iterations=300,
                            depth=4,
                            learning_rate=0.03,
                            l2_leaf_reg=10,
                            random_strength=1,
                            bagging_temperature=0,
                            border_count=64,
                            loss_function="Logloss",
                            eval_metric="AUC",
                            random_seed=RANDOM_STATE,
                            verbose=False,
                            allow_writing_files=False,
                        ),
                    ),
                ]
            ),
            {},
        ),
        (
            "CatBoost",
            "auto_class_weights_balanced",
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        CatBoostClassifier(
                            iterations=300,
                            depth=4,
                            learning_rate=0.03,
                            l2_leaf_reg=1,
                            random_strength=1,
                            bagging_temperature=1,
                            border_count=64,
                            loss_function="Logloss",
                            eval_metric="AUC",
                            auto_class_weights="Balanced",
                            random_seed=RANDOM_STATE,
                            verbose=False,
                            allow_writing_files=False,
                        ),
                    ),
                ]
            ),
            {},
        ),
    ]

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for model_name, weight_mode, estimator, fit_params in models:
        print(f"training {model_name} {weight_mode}")
        estimator.fit(x_train, y_train, **fit_params)
        rows.append(evaluate(model_name, weight_mode, estimator, x_test, y_test))
        write_confusion_matrix(REPORT_DIR / f"{model_name}_{weight_mode}_confusion_matrix.csv", estimator, x_test, y_test)

    pd.DataFrame(rows).to_csv(REPORT_DIR / "model_metrics.csv", index=False, encoding="utf-8-sig")
    summary = {
        "random_state": RANDOM_STATE,
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "train_positive": int(y_train.sum()),
        "train_negative": int(len(y_train) - y_train.sum()),
        "test_positive": int(y_test.sum()),
        "test_negative": int(len(y_test) - y_test.sum()),
        "balanced_sample_weight_min": float(np.min(sample_weight)),
        "balanced_sample_weight_max": float(np.max(sample_weight)),
    }
    (REPORT_DIR / "split_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote reports to {REPORT_DIR}")


if __name__ == "__main__":
    main()
