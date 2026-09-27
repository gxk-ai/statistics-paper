"""Build the tertiary-indicator analysis dataset from the survey CSV.

The source survey export is treated as read-only. Outputs are written under
artifacts/ so the raw materials remain unchanged.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = ROOT / "paper-materials" / "data" / "raw" / "survey"
DEFAULT_OUTPUT = ROOT / "artifacts" / "tables" / "analysis_dataset.csv"
DEFAULT_DICTIONARY = ROOT / "artifacts" / "tables" / "data_dictionary.csv"


INDICATORS = [
    ("national_defense_cognition", "国防认知", "国防形势认知"),
    ("national_defense_task_cognition", "国防认知", "国防任务认知"),
    ("military_thought_mastery", "国防认知", "军事思想掌握程度"),
    ("national_defense_theory_cognition", "国防认知", "国防理论认知"),
    ("national_defense_law_cognition", "国防认知", "国防法规认知"),
    ("military_training_participation", "军事训练体验", "军事训练参与情况"),
    ("military_skill_scope", "军事训练体验", "军事技能掌握范围"),
    ("national_defense_interest", "军事训练体验", "国防教育兴趣"),
    ("instructor_source_score", "军事训练体验", "军训教官来源"),
    ("instructor_quality_avg", "军事训练体验", "教官综合素养评价"),
    ("military_training_gain", "军事训练体验", "军训收获与感受"),
    ("practice_activity_willingness", "国防实践参与", "国防教育活动参与意愿"),
    ("practice_activity_quality_avg", "国防实践参与", "国防主题活动评价"),
    ("commemoration_participation", "国防实践参与", "重大纪念活动参与度"),
    ("advanced_equipment_attention", "国防实践参与", "国防先进装备关注度"),
    ("theory_course_format", "教学保障", "军事理论课开设形式"),
    ("theory_assessment_format", "教学保障", "国防教育考核形式"),
    ("teaching_quality_avg", "教学保障", "国防教育教学质量评价"),
    ("teaching_support_avg", "教学保障", "教学保障条件评价"),
    ("textbook_support", "教学保障", "教材配套情况"),
    ("school_level", "个人特征", "学校层次"),
    ("school_attribute", "个人特征", "学校属性"),
    ("vision_status", "个人特征", "视力状况"),
    ("grade", "个人特征", "年级"),
    ("gender", "个人特征", "性别"),
    ("major_category", "个人特征", "专业类别"),
]

MISSING_FEATURES = [
    ("military_training_structural_missing", "军事训练体验", "军训跳题结构性缺失"),
    ("textbook_structural_missing", "教学保障", "教材题跳题结构性缺失"),
    ("equipment_structural_missing", "国防实践参与", "阅兵装备题结构性缺失"),
]

RAW_CATEGORICAL_FEATURES = [
    ("raw_cat_school_level", "个人特征", "学校层次原始分类"),
    ("raw_cat_school_attribute", "个人特征", "学校属性原始分类"),
    ("raw_cat_theory_assessment_format", "教学保障", "国防教育考核形式原始分类"),
    ("raw_cat_military_training_place", "军事训练体验", "军事训练场所原始分类"),
    ("raw_cat_instructor_source", "军事训练体验", "军训教官来源原始分类"),
    ("raw_cat_textbook_available", "教学保障", "教材有无原始分类"),
    ("raw_cat_practice_activity_willingness", "国防实践参与", "国防教育活动参与意愿原始分类"),
    ("raw_cat_vision_status", "个人特征", "视力状况原始分类"),
    ("raw_cat_grade", "个人特征", "年级原始分类"),
    ("raw_cat_gender", "个人特征", "性别原始分类"),
    ("raw_cat_major_category", "个人特征", "专业类别原始分类"),
    ("raw_cat_commemoration_participation", "国防实践参与", "重大纪念活动参与方式原始分类"),
]


def numeric(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def sum_columns(row: dict[str, str], columns: list[str], positive_values: set[str] | None = None) -> float | None:
    values = [row.get(col, "") for col in columns]
    if all(value == "" for value in values):
        return None
    if positive_values is None:
        return float(sum(1 for value in values if value == "1"))
    return float(sum(1 for value in values if value in positive_values))


def average_columns(row: dict[str, str], columns: list[str]) -> float | None:
    values = [numeric(row.get(col, "")) for col in columns]
    present = [value for value in values if value is not None]
    if not present:
        return None
    return float(mean(present))


def single_score(row: dict[str, str], column: str, mapping: dict[str, float]) -> float | None:
    value = row.get(column, "")
    if value == "":
        return None
    return mapping.get(value, 0.0)


def raw_category(row: dict[str, str], column: str) -> str:
    value = row.get(column, "")
    return value if value != "" else "missing"


def is_question_column(field: str, question_number: int) -> bool:
    prefix = str(question_number)
    return field.startswith(f"{prefix}.") or field.startswith(f"{prefix}(") or field.startswith(f"{prefix} (")


def find_one_question(fields: list[str], question_number: int) -> str:
    matches = [field for field in fields if is_question_column(field, question_number)]
    if len(matches) != 1:
        raise ValueError(f"Expected one column for question {question_number}, found {len(matches)}")
    return matches[0]


def find_many_questions(fields: list[str], question_number: int, count: int) -> list[str]:
    matches = [field for field in fields if is_question_column(field, question_number)]
    if len(matches) != count:
        raise ValueError(f"Expected {count} columns for question {question_number}, found {len(matches)}")
    return matches


def columns_from_question(fields: list[str], question_number: int, count: int) -> list[str]:
    first = find_one_question(fields, question_number)
    start = fields.index(first)
    return fields[start : start + count]


def build_row(row: dict[str, str], fields: list[str]) -> dict[str, float | int | str | None]:
    q1 = find_one_question(fields, 1)
    q2 = find_one_question(fields, 2)
    q3 = find_many_questions(fields, 3, 4)
    q4 = find_many_questions(fields, 4, 4)
    q5 = find_many_questions(fields, 5, 4)
    q6 = find_many_questions(fields, 6, 6)
    q7 = find_many_questions(fields, 7, 6)
    q12 = find_many_questions(fields, 12, 7)
    q13 = find_one_question(fields, 13)
    q14 = find_one_question(fields, 14)
    q15 = find_one_question(fields, 15)
    q16 = find_many_questions(fields, 16, 4)
    q17 = find_many_questions(fields, 17, 6)
    q18 = find_one_question(fields, 18)
    q19 = columns_from_question(fields, 19, 5)
    q20 = find_many_questions(fields, 20, 7)
    q21 = columns_from_question(fields, 21, 5)
    q22 = columns_from_question(fields, 22, 3)
    q23 = find_one_question(fields, 23)
    q24 = find_many_questions(fields, 24, 6)
    q26 = find_one_question(fields, 26)
    q27 = columns_from_question(fields, 27, 9)
    q32 = find_one_question(fields, 32)
    q33 = find_one_question(fields, 33)
    q34 = find_one_question(fields, 34)
    q35 = find_one_question(fields, 35)
    q37 = find_one_question(fields, 37)
    q38 = find_many_questions(fields, 38, 8)

    enlist_raw = row.get(q13, "")
    if enlist_raw not in {"1", "2", "3", "4", "5"}:
        raise ValueError(f"Unexpected enlistment willingness value: {enlist_raw!r}")

    military_missing = 1 if row.get(q18, "") == "" else 0
    textbook_missing = 1 if row.get(q23, "") == "2" else 0
    equipment_missing = 1 if all(row.get(col, "") == "" for col in q38) else 0
    textbook_score = 0.0 if textbook_missing else sum_columns(row, q24[:3])
    commemoration_score = None if row.get(q37, "") == "" else (0.0 if row.get(q37, "") == "4" else 1.0)

    return {
        "record_id": row.get("序号", ""),
        "y_enlist_positive": 1 if enlist_raw in {"1", "2"} else 0,
        "enlist_willingness_raw": enlist_raw,
        "national_defense_cognition": sum_columns(row, q3[:3]),
        "national_defense_task_cognition": sum_columns(row, q4[:3]),
        "military_thought_mastery": sum_columns(row, q6),
        "national_defense_theory_cognition": sum_columns(row, q7),
        "national_defense_law_cognition": sum_columns(row, q12[:4]),
        "military_training_participation": 1.0 if row.get(q15, "") in {"1", "2", "3", "4"} else 0.0,
        "military_skill_scope": sum_columns(row, q16),
        "national_defense_interest": sum_columns(row, q17[:5]),
        "instructor_source_score": single_score(row, q18, {"1": 2.0, "2": 2.0, "3": 1.0, "4": 1.0, "5": 0.0}),
        "instructor_quality_avg": average_columns(row, q19),
        "military_training_gain": sum_columns(row, [q20[i] for i in [0, 1, 2, 5]]),
        "practice_activity_willingness": single_score(row, q26, {"1": 2.0, "2": 1.0, "3": 0.0}),
        "practice_activity_quality_avg": average_columns(row, q27),
        "commemoration_participation": commemoration_score,
        "advanced_equipment_attention": sum_columns(row, q38),
        "theory_course_format": sum_columns(row, q5),
        "theory_assessment_format": single_score(row, q14, {"1": 4.0, "2": 3.0, "3": 2.0, "4": 1.0, "5": 0.0}),
        "teaching_quality_avg": average_columns(row, q21),
        "teaching_support_avg": average_columns(row, q22),
        "textbook_support": textbook_score,
        "school_level": single_score(row, q1, {"1": 1.0, "2": 0.0}),
        "school_attribute": single_score(row, q2, {"1": 1.0, "2": 0.0, "3": 2.0}),
        "vision_status": single_score(row, q32, {"1": 0.0, "2": 1.0, "3": 2.0}),
        "grade": single_score(row, q33, {"1": 0.0, "2": 1.0, "3": 2.0, "4": 3.0}),
        "gender": single_score(row, q34, {"1": 1.0, "2": 0.0}),
        "major_category": single_score(row, q35, {"1": 0.0, "2": 1.0}),
        "military_training_structural_missing": military_missing,
        "textbook_structural_missing": textbook_missing,
        "equipment_structural_missing": equipment_missing,
        "raw_cat_school_level": raw_category(row, q1),
        "raw_cat_school_attribute": raw_category(row, q2),
        "raw_cat_theory_assessment_format": raw_category(row, q14),
        "raw_cat_military_training_place": raw_category(row, q15),
        "raw_cat_instructor_source": raw_category(row, q18),
        "raw_cat_textbook_available": raw_category(row, q23),
        "raw_cat_practice_activity_willingness": raw_category(row, q26),
        "raw_cat_vision_status": raw_category(row, q32),
        "raw_cat_grade": raw_category(row, q33),
        "raw_cat_gender": raw_category(row, q34),
        "raw_cat_major_category": raw_category(row, q35),
        "raw_cat_commemoration_participation": raw_category(row, q37),
    }


def write_dictionary(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["variable", "secondary_indicator", "tertiary_indicator", "role", "notes"])
        writer.writerow(["y_enlist_positive", "", "参军意愿二分类", "target", "第13题：1/2=积极，3/4/5=不积极"])
        writer.writerow(["enlist_willingness_raw", "", "参军意愿原始五分类", "audit", "保留原始编码用于复核"])
        for variable, secondary, tertiary in INDICATORS:
            writer.writerow([variable, secondary, tertiary, "feature", "按论文3.2.2量化规则生成"])
        for variable, secondary, tertiary in MISSING_FEATURES:
            writer.writerow([variable, secondary, tertiary, "missing_flag", "结构性缺失标记，避免把不适用误当低分"])
        for variable, secondary, tertiary in RAW_CATEGORICAL_FEATURES:
            writer.writerow([variable, secondary, tertiary, "raw_categorical_feature", "仅供CatBoost原生分类变量实验使用"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=None, help="Survey CSV path. Defaults to the only CSV in paper-materials/data/raw/survey.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    args = parser.parse_args()

    input_path = args.input
    if input_path is None:
        csv_paths = list(DEFAULT_INPUT_DIR.glob("*.csv"))
        if len(csv_paths) != 1:
            raise SystemExit(f"Expected exactly one CSV in {DEFAULT_INPUT_DIR}, found {len(csv_paths)}")
        input_path = csv_paths[0]

    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = [build_row(row, fields) for row in reader]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    write_dictionary(args.dictionary)

    positives = sum(int(row["y_enlist_positive"]) for row in rows)
    print(f"wrote {args.output}")
    print(f"wrote {args.dictionary}")
    print(f"rows={len(rows)} positives={positives} negatives={len(rows) - positives}")


if __name__ == "__main__":
    main()
