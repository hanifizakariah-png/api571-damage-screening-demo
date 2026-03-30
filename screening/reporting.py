from io import BytesIO

import pandas as pd


GENERAL_ASSUMPTIONS = [
    "Simplified API 571-aligned screening logic was used together with a local ML support layer.",
    "Excel uploads read the first worksheet only.",
    "Unmapped uploaded columns are treated as missing inputs.",
    "Boolean-like values are normalized from common text values such as yes/no and true/false.",
    "Confidence is qualitative only and is based on technical screening evidence, data quality, and local ML support.",
]


def _qualitative_confidence(
    status: str,
    score: int,
    data_quality: str,
    triggered_conditions: str,
    knowledge_alignment: str,
    ml_probability: float,
) -> str:
    triggered_count = 0 if triggered_conditions in {"", "None"} else len(triggered_conditions.split("; "))

    if (
        status == "Likely"
        and data_quality == "Sufficient for screening"
        and score >= 8
        and knowledge_alignment == "Strong"
        and ml_probability >= 0.65
    ):
        return "High"
    if (
        status == "Likely"
        and data_quality != "Insufficient data"
        and triggered_count >= 2
        and knowledge_alignment in {"Strong", "Moderate"}
        and ml_probability >= 0.35
    ):
        return "Medium"
    if (
        status == "Needs engineer review"
        and data_quality == "Sufficient for screening"
        and score >= 6
        and knowledge_alignment != "Weak"
        and ml_probability >= 0.25
    ):
        return "Medium"
    return "Low"


def attach_quality_and_confidence(results_df: pd.DataFrame, quality_df: pd.DataFrame) -> pd.DataFrame:
    merged = results_df.merge(
        quality_df[["source_row", "data_quality", "missing_critical_fields", "weak_inputs"]],
        on="source_row",
        how="left",
    )
    merged["confidence"] = merged.apply(
        lambda row: _qualitative_confidence(
            row["status"],
            int(row["score"]),
            row["data_quality"],
            row["triggered_conditions"],
            row.get("knowledge_alignment", "Weak"),
            float(row.get("ml_probability", 0.0)),
        ),
        axis=1,
    )
    return merged


def build_assumptions_text(mapping: dict, results_row: pd.Series) -> str:
    unmapped_fields = sorted(field for field, source in mapping.items() if not source)
    assumptions = list(GENERAL_ASSUMPTIONS)

    if unmapped_fields:
        assumptions.append(
            "Unmapped expected fields for this run: " + ", ".join(unmapped_fields) + "."
        )
    if results_row.get("data_gaps") and results_row["data_gaps"] != "None":
        assumptions.append("Row-level data gaps: " + results_row["data_gaps"] + ".")
    if results_row.get("weak_inputs") and results_row["weak_inputs"] != "None":
        assumptions.append("Weak inputs noted: " + results_row["weak_inputs"] + ".")
    if results_row.get("knowledge_alignment"):
        assumptions.append(
            "Knowledge-base alignment for this mechanism: "
            + str(results_row["knowledge_alignment"])
            + "."
        )
    if results_row.get("ml_probability") is not None:
        assumptions.append(
            "Local self-training ML probability for this mechanism: "
            + str(results_row["ml_probability"])
            + "."
        )

    return " ".join(assumptions)


def build_export_dataframe(
    original_df: pd.DataFrame,
    mapped_df: pd.DataFrame,
    quality_df: pd.DataFrame,
    results_df: pd.DataFrame,
    mapping: dict,
) -> pd.DataFrame:
    original_export = original_df.copy().reset_index(drop=True)
    original_export.columns = [f"original_{column}" for column in original_export.columns]
    original_export.insert(0, "source_row", original_export.index)

    mapped_export = mapped_df.copy().reset_index(drop=True)
    mapped_export.columns = [f"mapped_{column}" for column in mapped_export.columns]
    mapped_export.insert(0, "source_row", mapped_export.index)

    results_export = results_df.copy()
    if "data_quality" not in results_export.columns or "confidence" not in results_export.columns:
        results_export = attach_quality_and_confidence(results_export, quality_df)
    results_export["assumptions_used"] = results_export.apply(
        lambda row: build_assumptions_text(mapping, row),
        axis=1,
    )

    export_df = results_export.merge(original_export, on="source_row", how="left")
    export_df = export_df.merge(mapped_export, on="source_row", how="left")
    return export_df


def build_results_workbook_bytes(export_df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    assumptions_df = pd.DataFrame({"assumptions_used": GENERAL_ASSUMPTIONS})

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, sheet_name="screening_results", index=False)
        assumptions_df.to_excel(writer, sheet_name="assumptions", index=False)

    buffer.seek(0)
    return buffer.getvalue()
