import pandas as pd

from screening.schema import CRITICAL_FIELDS, FIELD_METADATA, RECOMMENDED_FIELDS


WEAK_TEXT_VALUES = {"", "unknown", "n/a", "na", "tbd", "check", "uncertain"}


def _is_missing_or_weak(value):
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    if isinstance(value, str) and value.strip().lower() in WEAK_TEXT_VALUES:
        return True
    return False


def classify_data_quality_row(row):
    missing_critical = [
        field for field in CRITICAL_FIELDS if _is_missing_or_weak(row.get(field))
    ]
    missing_recommended = [
        field for field in RECOMMENDED_FIELDS if _is_missing_or_weak(row.get(field))
    ]

    weak_inputs = []
    if _is_missing_or_weak(row.get("notes")):
        weak_inputs.append("Limited notes or contextual comments")
    if _is_missing_or_weak(row.get("pressure_kpag")):
        weak_inputs.append("Pressure missing or weak")
    if _is_missing_or_weak(row.get("pwht_status")):
        weak_inputs.append("PWHT status missing or weak")
    if _is_missing_or_weak(row.get("water_present")):
        weak_inputs.append("Water presence missing or weak")

    if not missing_critical and len(missing_recommended) <= 1:
        classification = "Sufficient for screening"
    elif len(missing_critical) <= 3:
        classification = "Partially sufficient"
    else:
        classification = "Insufficient data"

    return {
        "data_quality": classification,
        "missing_critical_fields": ", ".join(missing_critical) if missing_critical else "None",
        "missing_recommended_fields": (
            ", ".join(missing_recommended) if missing_recommended else "None"
        ),
        "weak_inputs": ", ".join(dict.fromkeys(weak_inputs)) if weak_inputs else "None",
    }


def assess_data_quality(df: pd.DataFrame) -> pd.DataFrame:
    quality_rows = []

    for source_row, row in df.iterrows():
        base = classify_data_quality_row(row)
        quality_rows.append(
            {
                "source_row": source_row,
                "equipment_tag": row.get("equipment_tag", ""),
                "unit": row.get("unit", ""),
                "service_description": row.get("service_description", ""),
                **base,
            }
        )

    return pd.DataFrame(quality_rows)


def build_quality_summary(quality_df: pd.DataFrame) -> dict:
    return {
        "sufficient": int((quality_df["data_quality"] == "Sufficient for screening").sum()),
        "partial": int((quality_df["data_quality"] == "Partially sufficient").sum()),
        "insufficient": int((quality_df["data_quality"] == "Insufficient data").sum()),
    }


def describe_expected_field(field_name: str) -> str:
    config = FIELD_METADATA[field_name]
    return f"{config['label']}: {config['description']}"
