"""Train and evaluate AdaBoost on the enlistment-willingness analysis dataset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.model_selection import StratifiedKFold, train_test_split


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.adaboost import build_search
from src.training.train_tree_models import (
    evaluate_model,
    load_feature_groups,
    save_permutation_importance,
    write_confusion_matrix,
)


DEFAULT_DATASET = ROOT / "artifacts" / "tables" / "analysis_dataset.csv"
DEFAULT_DICTIONARY = ROOT / "artifacts" / "tables" / "data_dictionary.csv"
DEFAULT_REPORT_DIR = ROOT / "artifacts" / "reports" / "adaboost"
RANDOM_STATE = 2026



def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--quick", action="store_true", help="Use a small parameter search for smoke testing.")
    parser.add_argument("--skip-importance", action="store_true", help="Skip permutation-importance output.")
    args = parser.parse_args()

    df = pd.read_csv(args.dataset, encoding="utf-8-sig")
    y = df["y_enlist_positive"].astype(int)
    x = df.drop(columns=["record_id", "y_enlist_positive", "enlist_willingness_raw"])
    x = x[[column for column in x.columns if not column.startswith("raw_cat_")]]
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE
    )
    search = build_search(
        StratifiedKFold(n_splits=3 if args.quick else 5, shuffle=True, random_state=RANDOM_STATE),
        args.quick,
        RANDOM_STATE,
    )
    print("training AdaBoost")
    search.fit(x_train, y_train)

    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "split_summary.json").write_text(
        json.dumps(
            {
                "random_state": RANDOM_STATE,
                "train_rows": int(len(x_train)),
                "test_rows": int(len(x_test)),
                "train_positive": int(y_train.sum()),
                "train_negative": int(len(y_train) - y_train.sum()),
                "test_positive": int(y_test.sum()),
                "test_negative": int(len(y_test) - y_test.sum()),
                "numeric_features": list(x.columns),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    metrics = evaluate_model("AdaBoost", search.best_estimator_, x_test, y_test)
    pd.DataFrame([metrics]).to_csv(args.report_dir / "model_metrics.csv", index=False, encoding="utf-8-sig")
    (args.report_dir / "best_params.json").write_text(
        json.dumps(search.best_params_, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_confusion_matrix(args.report_dir / "AdaBoost_confusion_matrix.csv", search.best_estimator_, x_test, y_test)
    if not args.skip_importance:
        save_permutation_importance(
            args.report_dir / "AdaBoost_permutation_importance.csv",
            search.best_estimator_,
            x_test,
            y_test,
            load_feature_groups(args.dictionary),
        )
    print(f"wrote reports to {args.report_dir}")


if __name__ == "__main__":
    main()
