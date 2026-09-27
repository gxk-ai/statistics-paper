"""Train a two-layer OOF stacking classifier for enlistment willingness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.base import clone
from sklearn.ensemble import AdaBoostClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_DATASET = ROOT / "artifacts" / "tables" / "analysis_dataset.csv"
DEFAULT_REPORT_DIR = ROOT / "artifacts" / "reports" / "stacking"
RANDOM_STATE = 2026
BASE_MODEL_NAMES = ["LogisticRegression", "RandomForest", "XGBoost", "CatBoostBalanced", "AdaBoost"]


def make_models(quick: bool) -> dict[str, tuple[Any, str]]:
    """Return fixed base estimators and the feature subset each uses."""
    tree_size = 100 if quick else 500
    boost_size = 100 if quick else 400
    ada_size = 50 if quick else 200
    return {
        "LogisticRegression": (
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                    ("model", LogisticRegression(max_iter=2000, random_state=RANDOM_STATE)),
                ]
            ),
            "numeric",
        ),
        "RandomForest": (
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        RandomForestClassifier(
                            n_estimators=tree_size,
                            max_depth=12,
                            max_features="log2",
                            min_samples_split=5,
                            min_samples_leaf=10,
                            random_state=RANDOM_STATE,
                            n_jobs=-1,
                        ),
                    ),
                ]
            ),
            "numeric",
        ),
        "XGBoost": (
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        XGBClassifier(
                            objective="binary:logistic",
                            eval_metric="auc",
                            n_estimators=boost_size,
                            learning_rate=0.03,
                            max_depth=3,
                            min_child_weight=1,
                            subsample=0.85,
                            colsample_bytree=0.7,
                            reg_alpha=0,
                            reg_lambda=1,
                            gamma=0,
                            tree_method="hist",
                            random_state=RANDOM_STATE,
                            n_jobs=-1,
                        ),
                    ),
                ]
            ),
            "numeric",
        ),
        "CatBoostBalanced": (
            CatBoostClassifier(
                iterations=boost_size,
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
            "all",
        ),
        "AdaBoost": (
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        AdaBoostClassifier(
                            estimator=DecisionTreeClassifier(
                                max_depth=2,
                                min_samples_leaf=2,
                                random_state=RANDOM_STATE,
                            ),
                            n_estimators=ada_size,
                            learning_rate=0.1,
                            random_state=RANDOM_STATE,
                        ),
                    ),
                ]
            ),
            "numeric",
        ),
    }


def fit_predict_proba(
    estimator: Any,
    feature_mode: str,
    x_fit: pd.DataFrame,
    y_fit: pd.Series,
    x_predict: pd.DataFrame,
    cat_features: list[str],
) -> tuple[Any, np.ndarray]:
    fitted = clone(estimator)
    if feature_mode == "all":
        fitted.fit(x_fit, y_fit, cat_features=cat_features)
    else:
        fitted.fit(x_fit, y_fit)
    return fitted, fitted.predict_proba(x_predict)[:, 1]


def best_mcc_threshold(y_true: pd.Series, probability: np.ndarray) -> float:
    thresholds = np.linspace(0.05, 0.95, 181)
    scores = [matthews_corrcoef(y_true, (probability >= threshold).astype(int)) for threshold in thresholds]
    return float(thresholds[int(np.argmax(scores))])


def metric_row(name: str, y_true: pd.Series, probability: np.ndarray, threshold: float) -> dict[str, float | str]:
    prediction = (probability >= threshold).astype(int)
    return {
        "model": name,
        "threshold": threshold,
        "accuracy": accuracy_score(y_true, prediction),
        "precision": precision_score(y_true, prediction, zero_division=0),
        "recall": recall_score(y_true, prediction, zero_division=0),
        "f1": f1_score(y_true, prediction, zero_division=0),
        "roc_auc": roc_auc_score(y_true, probability),
        "pr_auc": average_precision_score(y_true, probability),
        "balanced_accuracy": balanced_accuracy_score(y_true, prediction),
        "mcc": matthews_corrcoef(y_true, prediction),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--quick", action="store_true", help="Use three folds and smaller ensembles for a smoke test.")
    args = parser.parse_args()

    df = pd.read_csv(args.dataset, encoding="utf-8-sig")
    y = df["y_enlist_positive"].astype(int)
    record_id = df["record_id"].copy()
    x = df.drop(columns=["record_id", "y_enlist_positive", "enlist_willingness_raw"])
    cat_features = [column for column in x.columns if column.startswith("raw_cat_")]
    x[cat_features] = x[cat_features].astype(str)
    numeric_features = [column for column in x.columns if column not in cat_features]

    x_train, x_test, y_train, y_test, id_train, id_test = train_test_split(
        x, y, record_id, test_size=0.2, stratify=y, random_state=RANDOM_STATE
    )
    x_train, x_test = x_train.reset_index(drop=True), x_test.reset_index(drop=True)
    y_train, y_test = y_train.reset_index(drop=True), y_test.reset_index(drop=True)
    id_train, id_test = id_train.reset_index(drop=True), id_test.reset_index(drop=True)

    n_splits = 3 if args.quick else 5
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    models = make_models(args.quick)
    oof = pd.DataFrame(index=x_train.index)
    test_probabilities = pd.DataFrame(index=x_test.index)

    for name in BASE_MODEL_NAMES:
        estimator, feature_mode = models[name]
        train_data = x_train if feature_mode == "all" else x_train[numeric_features]
        test_data = x_test if feature_mode == "all" else x_test[numeric_features]
        fold_oof = np.zeros(len(x_train))
        fold_test = np.zeros((n_splits, len(x_test)))
        for fold, (fit_index, valid_index) in enumerate(cv.split(train_data, y_train), start=1):
            fitted, fold_oof[valid_index] = fit_predict_proba(
                estimator,
                feature_mode,
                train_data.iloc[fit_index],
                y_train.iloc[fit_index],
                train_data.iloc[valid_index],
                cat_features,
            )
            fold_test[fold - 1] = fitted.predict_proba(test_data)[:, 1]
            print(f"completed {name} fold {fold}/{n_splits}")
        oof[name] = fold_oof
        test_probabilities[name] = fold_test.mean(axis=0)

    meta_model = LogisticRegression(C=1.0, penalty="l2", max_iter=2000, random_state=RANDOM_STATE)
    meta_oof = cross_val_predict(meta_model, oof[BASE_MODEL_NAMES], y_train, cv=cv, method="predict_proba")[:, 1]
    stack_threshold = best_mcc_threshold(y_train, meta_oof)
    meta_model.fit(oof[BASE_MODEL_NAMES], y_train)
    test_probabilities["Stacking"] = meta_model.predict_proba(test_probabilities[BASE_MODEL_NAMES])[:, 1]

    thresholds = {name: best_mcc_threshold(y_train, oof[name].to_numpy()) for name in BASE_MODEL_NAMES}
    thresholds["Stacking"] = stack_threshold
    metrics = [metric_row(name, y_test, test_probabilities[name].to_numpy(), thresholds[name]) for name in thresholds]

    args.report_dir.mkdir(parents=True, exist_ok=True)
    oof_output = pd.concat([id_train.rename("record_id"), y_train.rename("y_true"), oof], axis=1)
    oof_output["Stacking_meta_cv"] = meta_oof
    oof_output.to_csv(args.report_dir / "base_oof_predictions.csv", index=False, encoding="utf-8-sig")
    test_output = pd.concat([id_test.rename("record_id"), y_test.rename("y_true"), test_probabilities], axis=1)
    for name, threshold in thresholds.items():
        test_output[f"{name}_prediction"] = (test_output[name] >= threshold).astype(int)
    test_output.to_csv(args.report_dir / "test_predictions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(metrics).to_csv(args.report_dir / "model_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        {"feature": ["intercept", *BASE_MODEL_NAMES], "coefficient": [meta_model.intercept_[0], *meta_model.coef_[0]]}
    ).to_csv(args.report_dir / "meta_coefficients.csv", index=False, encoding="utf-8-sig")
    summary = {
        "random_state": RANDOM_STATE,
        "n_splits": n_splits,
        "quick": args.quick,
        "train_rows": len(y_train),
        "test_rows": len(y_test),
        "train_positive": int(y_train.sum()),
        "test_positive": int(y_test.sum()),
        "base_models": BASE_MODEL_NAMES,
        "threshold_selection": "training OOF MCC maximization",
        "prediction_strategy": "mean probability across fold models",
        "thresholds": thresholds,
    }
    (args.report_dir / "split_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote reports to {args.report_dir}")


if __name__ == "__main__":
    main()
