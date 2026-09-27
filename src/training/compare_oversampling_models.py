"""Compare baseline and random oversampling for tree models."""

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
from xgboost import XGBClassifier


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "artifacts" / "tables" / "analysis_dataset.csv"
REPORT_DIR = ROOT / "artifacts" / "reports" / "oversampling_models"
RANDOM_STATE = 2026


def specificity_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    tn, fp, _, _ = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return tn / (tn + fp) if (tn + fp) else 0.0


def evaluate(model_name: str, sampling: str, estimator, x_test: pd.DataFrame, y_test: pd.Series) -> dict[str, float | str]:
    y_pred = estimator.predict(x_test)
    y_score = estimator.predict_proba(x_test)[:, 1]
    return {
        "model": model_name,
        "sampling": sampling,
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


def random_oversample(x: pd.DataFrame, y: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(RANDOM_STATE)
    counts = y.value_counts()
    max_count = counts.max()
    parts_x = [x]
    parts_y = [y]
    for klass, count in counts.items():
        if count == max_count:
            continue
        need = max_count - count
        class_index = y[y == klass].index.to_numpy()
        sampled = rng.choice(class_index, size=need, replace=True)
        parts_x.append(x.loc[sampled])
        parts_y.append(y.loc[sampled])
    x_new = pd.concat(parts_x, axis=0).reset_index(drop=True)
    y_new = pd.concat(parts_y, axis=0).reset_index(drop=True)
    order = rng.permutation(len(y_new))
    return x_new.iloc[order].reset_index(drop=True), y_new.iloc[order].reset_index(drop=True)



def make_models() -> list[tuple[str, Pipeline]]:
    return [
        (
            "RandomForest",
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
        ),
        (
            "XGBoost",
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
        ),
        (
            "CatBoost",
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
        ),
    ]


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

    sampling_sets = [("none", x_train, y_train), ("random_oversampling", *random_oversample(x_train, y_train))]

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    sampling_summary = {}
    for sampling, sampled_x, sampled_y in sampling_sets:
        sampling_summary[sampling] = {
            "rows": int(len(sampled_y)),
            "positive": int(sampled_y.sum()),
            "negative": int(len(sampled_y) - sampled_y.sum()),
        }
        for model_name, estimator in make_models():
            print(f"training {model_name} {sampling}")
            estimator.fit(sampled_x, sampled_y)
            rows.append(evaluate(model_name, sampling, estimator, x_test, y_test))
            write_confusion_matrix(REPORT_DIR / f"{model_name}_{sampling}_confusion_matrix.csv", estimator, x_test, y_test)

    pd.DataFrame(rows).to_csv(REPORT_DIR / "model_metrics.csv", index=False, encoding="utf-8-sig")
    summary = {
        "random_state": RANDOM_STATE,
        "train_rows_before_sampling": int(len(y_train)),
        "test_rows": int(len(y_test)),
        "test_positive": int(y_test.sum()),
        "test_negative": int(len(y_test) - y_test.sum()),
        "sampling": sampling_summary,
    }
    (REPORT_DIR / "split_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote reports to {REPORT_DIR}")


if __name__ == "__main__":
    main()
