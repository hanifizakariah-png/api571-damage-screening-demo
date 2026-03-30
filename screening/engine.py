import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from screening.context_reasoner import evaluate_kahneman_gate, load_knowledge_base
from screening.model_learning import train_self_learning_model


RULES_PATH = Path(__file__).with_name("rules.json")


@lru_cache(maxsize=1)
def load_rules():
    with open(RULES_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_text(value):
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip().lower()


def is_missing(value):
    if value is None:
        return True
    if pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def list_missing_fields(row):
    ignored_fields = {"equipment_tag", "notes"}
    return [
        column
        for column, value in row.items()
        if column not in ignored_fields and is_missing(value)
    ]


def evaluate_condition(row, condition):
    field = condition["field"]
    operator = condition["operator"]
    expected = condition["value"]
    actual = row.get(field)

    if is_missing(actual):
        return False

    if operator == "equals":
        return actual == expected

    if operator == "greater_or_equal":
        return actual >= expected

    if operator == "between":
        lower, upper = expected
        return lower <= actual <= upper

    if operator == "contains_any":
        actual_text = normalize_text(actual)
        return any(token.lower() in actual_text for token in expected)

    raise ValueError(f"Unsupported operator: {operator}")


def evaluate_rule(row, rule, knowledge_base):
    gate = evaluate_kahneman_gate(row, rule, knowledge_base)
    if not gate["gate_passed"]:
        return {
            "mechanism": rule["name"],
            "score": 0,
            "base_score": 0,
            "ml_probability": 0.0,
            "triggered_conditions": gate["gate_triggers"],
            "selection_reason": gate["gate_reason"],
            "status": "Gate failed",
            "knowledge_alignment": gate["knowledge_alignment"],
            "reasoning_model": gate["reasoning_model"],
        }

    missing_fields = [field for field in rule["required_fields"] if is_missing(row.get(field))]
    if missing_fields:
        return {
            "mechanism": rule["name"],
            "score": 0,
            "base_score": 0,
            "ml_probability": 0.0,
            "triggered_conditions": gate["gate_triggers"],
            "selection_reason": (
                f"Mandatory prerequisites are present, but screening is incomplete because required fields are missing: "
                f"{', '.join(missing_fields)}."
            ),
            "status": "Insufficient data",
            "knowledge_alignment": gate["knowledge_alignment"],
            "reasoning_model": "Kahneman-inspired gate + self-training ML support",
        }

    triggered_conditions = list(gate["gate_triggers"])
    score = 0
    gate_labels = []

    for condition in rule["conditions"]:
        if evaluate_condition(row, condition):
            triggered_conditions.append(condition["label"])
            score += condition["score"]
            if condition.get("gate"):
                gate_labels.append(condition["label"])

    required_gates = [condition["label"] for condition in rule["conditions"] if condition.get("gate")]
    missing_gates = [label for label in required_gates if label not in gate_labels]

    if score >= rule["minimum_score"] and not missing_gates:
        status = "Likely"
        reason = rule["description"]
    elif score > 0:
        status = "Needs engineer review"
        if missing_gates:
            reason = (
                "This mechanism is technically credible because some key indicators are present, "
                f"but one or more core conditions are still missing or not confirmed: {', '.join(missing_gates)}."
            )
        else:
            reason = (
                "This mechanism is technically credible because several relevant indicators are present, "
                f"but the overall evidence does not yet meet the selection threshold of {rule['minimum_score']}."
            )
    else:
        status = "Not indicated"
        reason = "No strong technical indicators matched for this mechanism."

    return {
        "mechanism": rule["name"],
        "score": score,
        "base_score": score,
        "ml_probability": 0.0,
        "triggered_conditions": triggered_conditions,
        "selection_reason": (
            reason
        ),
        "status": status,
        "knowledge_alignment": gate["knowledge_alignment"],
        "reasoning_model": "Kahneman-inspired gate + self-training ML support",
    }


def summarize_top_results(row_result, top_n=3):
    actionable = [
        item
        for item in row_result
        if item["status"] in {"Likely", "Needs engineer review"}
    ]
    ordered = sorted(
        actionable,
        key=lambda item: (
            0 if item["status"] == "Likely" else 1,
            -item["score"],
            item["mechanism"],
        ),
    )
    if ordered:
        return ordered[:top_n]

    insufficient = [item for item in row_result if item["status"] == "Insufficient data"]
    if insufficient:
        return insufficient[:1]

    return [
        {
            "mechanism": "Needs engineer review",
            "score": 0,
            "base_score": 0,
            "ml_probability": 0.0,
            "triggered_conditions": [],
            "selection_reason": (
                "No mechanism passed the mandatory early gate or detailed screening logic."
            ),
            "status": "Needs engineer review",
            "knowledge_alignment": "Weak",
            "reasoning_model": "Kahneman-inspired gate + self-training ML support",
        }
    ]


def screen_dataframe(df):
    rules = load_rules()
    knowledge_base = load_knowledge_base()

    row_results = {}
    for source_row, row in df.iterrows():
        row_results[source_row] = [
            evaluate_rule(row, rule, knowledge_base)
            for rule in rules
        ]

    row_labels = {
        source_row: [
            result["mechanism"]
            for result in results
            if result["status"] in {"Likely", "Needs engineer review"}
        ]
        for source_row, results in row_results.items()
    }
    mechanisms = [rule["name"] for rule in rules]
    ml_scores = train_self_learning_model(df, row_labels, mechanisms)

    output_rows = []
    for source_row, row in df.iterrows():
        updated_results = []
        for result in row_results[source_row]:
            ml_probability = ml_scores.get(source_row, {}).get(result["mechanism"], 0.0)
            ml_bonus = int(round(ml_probability * 3))
            result = result.copy()
            result["ml_probability"] = round(ml_probability, 2)

            if result["status"] in {"Likely", "Needs engineer review"}:
                result["score"] = result["base_score"] + ml_bonus

            result["triggered_conditions"] = list(dict.fromkeys(result["triggered_conditions"]))
            updated_results.append(result)

        screened = summarize_top_results(updated_results)
        missing_fields = list_missing_fields(row)
        for rank, result in enumerate(screened, start=1):
            output_rows.append(
                {
                    "source_row": source_row,
                    "equipment_tag": row["equipment_tag"],
                    "unit": row["unit"],
                    "service_description": row["service_description"],
                    "candidate_rank": rank,
                    "mechanism": result["mechanism"],
                    "score": result["score"],
                    "base_score": result["base_score"],
                    "ml_probability": result["ml_probability"],
                    "status": result["status"],
                    "knowledge_alignment": result["knowledge_alignment"],
                    "reasoning_model": result["reasoning_model"],
                    "data_gaps": ", ".join(missing_fields) if missing_fields else "None",
                    "triggered_conditions": "; ".join(result["triggered_conditions"])
                    if result["triggered_conditions"]
                    else "None",
                    "selection_reason": result["selection_reason"],
                }
            )

    return pd.DataFrame(output_rows)
