import json
from functools import lru_cache
from pathlib import Path

import pandas as pd


KB_PATH = Path(__file__).with_name("knowledge_base.json")


@lru_cache(maxsize=1)
def load_knowledge_base():
    with open(KB_PATH, "r", encoding="utf-8") as handle:
        entries = json.load(handle)
    return {entry["name"]: entry for entry in entries}


def _normalize_text(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().lower()


def _contains_any(text, terms):
    return any(term.lower() in text for term in terms)


def _build_text_context(row):
    parts = [
        row.get("service_description", ""),
        row.get("notes", ""),
        row.get("component_type", ""),
        row.get("unit", ""),
        row.get("phase", ""),
        row.get("material", ""),
    ]
    return " | ".join(_normalize_text(part) for part in parts if _normalize_text(part))


def _fast_gate_cues(row, kb_entry):
    text_blob = _build_text_context(row)
    matched_cues = [
        cue for cue in kb_entry.get("text_cues", []) if cue.lower() in text_blob
    ]
    if not matched_cues:
        return []
    return ["Service context mentions: " + ", ".join(sorted(set(matched_cues)))]


def _mandatory_checks_from_rule(rule):
    checks = []
    for condition in rule["conditions"]:
        if not condition.get("gate"):
            continue
        if condition["operator"] == "equals" and condition["value"] is True:
            checks.append(("flag", condition))
        elif condition["operator"] == "contains_any":
            checks.append(("text", condition))
    return checks


def evaluate_kahneman_gate(row, rule, knowledge_base):
    kb_entry = knowledge_base.get(rule["name"], {})
    fast_cues = _fast_gate_cues(row, kb_entry)
    mandatory_checks = _mandatory_checks_from_rule(rule)

    passed_checks = []
    failed_checks = []

    for check_type, condition in mandatory_checks:
        field = condition["field"]
        actual = row.get(field)

        if check_type == "flag":
            if actual is True:
                passed_checks.append(condition["label"])
            else:
                failed_checks.append(condition["label"])

        if check_type == "text":
            actual_text = _normalize_text(actual)
            if _contains_any(actual_text, condition["value"]):
                passed_checks.append(condition["label"])
            else:
                failed_checks.append(condition["label"])

    gate_triggers = list(fast_cues)
    if passed_checks:
        gate_triggers.extend(passed_checks)

    if failed_checks:
        return {
            "gate_passed": False,
            "gate_triggers": gate_triggers,
            "knowledge_alignment": "Weak" if not passed_checks else "Moderate",
            "gate_reason": (
                "This mechanism is not screened because mandatory prerequisites are not met: "
                + ", ".join(failed_checks)
                + "."
            ),
            "reasoning_model": "Kahneman-inspired gate only (System 1 cues + System 2 prerequisite checks)",
        }

    alignment = "Strong" if len(passed_checks) >= 2 else "Moderate"
    return {
        "gate_passed": True,
        "gate_triggers": gate_triggers,
        "knowledge_alignment": alignment,
        "gate_reason": (
            "Mandatory prerequisites for this mechanism are present."
        ),
        "reasoning_model": "Kahneman-inspired gate only (System 1 cues + System 2 prerequisite checks)",
    }
