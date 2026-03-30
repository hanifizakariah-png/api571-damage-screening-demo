from pathlib import Path

import pandas as pd
import streamlit as st

from screening.data_loader import (
    BOOLEAN_COLUMNS,
    EXPECTED_FIELDS,
    NUMERIC_COLUMNS,
    TEXT_COLUMNS,
    build_template_workbook_bytes,
    find_missing_expected_columns,
    load_sample_data,
    load_uploaded_data,
    normalize_screening_dataframe,
)
from screening.data_quality import assess_data_quality, build_quality_summary
from screening.engine import screen_dataframe
from screening.reporting import (
    attach_quality_and_confidence,
    build_export_dataframe,
    build_results_workbook_bytes,
)
from screening.schema import FIELD_METADATA


BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "sample_input.csv"


def build_identity_mapping(raw_df: pd.DataFrame) -> dict:
    return {
        field: field if field in raw_df.columns else None
        for field in EXPECTED_FIELDS
    }


def render_editable_input_table(screening_df: pd.DataFrame) -> pd.DataFrame:
    st.subheader("Screening Input Table")
    st.markdown(
        "Edit the uploaded data directly in this table. Boolean screening inputs use "
        "real checkboxes, and missing expected columns appear here as blank fields."
    )

    column_config = {}
    for column in BOOLEAN_COLUMNS:
        column_config[column] = st.column_config.CheckboxColumn(
            FIELD_METADATA[column]["label"],
            help=FIELD_METADATA[column]["description"],
            default=False,
        )

    for column in NUMERIC_COLUMNS:
        column_config[column] = st.column_config.NumberColumn(
            FIELD_METADATA[column]["label"],
            help=FIELD_METADATA[column]["description"],
        )

    for column in TEXT_COLUMNS:
        column_config[column] = st.column_config.TextColumn(
            FIELD_METADATA[column]["label"],
            help=FIELD_METADATA[column]["description"],
        )

    edited_df = st.data_editor(
        screening_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config=column_config,
        key="screening_input_editor",
    )

    return normalize_screening_dataframe(edited_df)


def render_data_quality_section(screening_df):
    st.subheader("Data Quality")
    quality_df = assess_data_quality(screening_df)
    summary = build_quality_summary(quality_df)

    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Sufficient", summary["sufficient"])
    metric_2.metric("Partially Sufficient", summary["partial"])
    metric_3.metric("Insufficient", summary["insufficient"])

    st.dataframe(quality_df, use_container_width=True, hide_index=True)
    return quality_df


def render_results_section(original_df, screening_df, quality_df, column_mapping):
    screen_button = st.button("Screen Damage Mechanisms", type="primary")

    if not screen_button:
        st.info("Click `Screen Damage Mechanisms` to evaluate the current dataset.")
        return

    results_df = screen_dataframe(screening_df)
    results_df = attach_quality_and_confidence(results_df, quality_df)
    likely_count = int((results_df["status"] == "Likely").sum())
    review_count = int((results_df["status"] == "Needs engineer review").sum())
    rows_with_gaps = int((results_df["data_gaps"] != "None").sum())

    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Likely Mechanisms", likely_count)
    metric_2.metric("Needs Engineer Review", review_count)
    metric_3.metric("Result Rows With Data Gaps", rows_with_gaps)

    st.subheader("Screening Results")
    display_results_df = results_df[
        [
            "equipment_tag",
            "unit",
            "service_description",
            "candidate_rank",
            "mechanism",
            "score",
            "base_score",
            "ml_probability",
            "confidence",
            "knowledge_alignment",
            "status",
            "data_gaps",
            "triggered_conditions",
            "selection_reason",
        ]
    ]
    st.dataframe(
        display_results_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "equipment_tag": st.column_config.TextColumn("Equipment Tag", width="small"),
            "candidate_rank": st.column_config.NumberColumn("Rank", format="%d"),
            "score": st.column_config.NumberColumn("Score", format="%d"),
            "base_score": st.column_config.NumberColumn("Base Score", format="%d"),
            "ml_probability": st.column_config.NumberColumn("ML Prob.", format="%.2f"),
            "confidence": st.column_config.TextColumn("Confidence", width="small"),
            "knowledge_alignment": st.column_config.TextColumn(
                "KB Alignment",
                width="small",
            ),
            "triggered_conditions": st.column_config.TextColumn(
                "Triggered Conditions",
                width="large",
            ),
            "selection_reason": st.column_config.TextColumn(
                "Why This Was Selected",
                width="large",
            ),
        },
    )

    st.subheader("Why This Was Selected")
    for equipment_tag, equipment_results in results_df.groupby("equipment_tag", sort=False):
        first_row = equipment_results.iloc[0]
        header = (
            f"{equipment_tag} | {first_row['unit']} | "
            f"{first_row['service_description']}"
        )
        with st.expander(header):
            if first_row["data_gaps"] != "None":
                st.warning(f"Data gaps: {first_row['data_gaps']}")

            for _, result_row in equipment_results.iterrows():
                st.markdown(
                    f"""
**Rank {int(result_row["candidate_rank"])}: {result_row["mechanism"]}**

- Status: `{result_row["status"]}`
- Score: `{int(result_row["score"])}`
- Base score: `{int(result_row["base_score"])}`
- Confidence: `{result_row["confidence"]}`
- Knowledge-base alignment: `{result_row["knowledge_alignment"]}`
- Triggered conditions: {result_row["triggered_conditions"]}
- Why this was selected: {result_row["selection_reason"]}
"""
                )

    export_df = build_export_dataframe(
        original_df=original_df,
        mapped_df=screening_df,
        quality_df=quality_df,
        results_df=results_df,
        mapping=column_mapping,
    )
    export_bytes = build_results_workbook_bytes(export_df)
    st.download_button(
        "Download Results to Excel",
        data=export_bytes,
        file_name="api571_screening_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


st.set_page_config(
    page_title="API 571 Damage Mechanism Screening Demo",
    layout="wide",
)

st.title("API 571 Damage Mechanism Screening Demo")
st.caption(
    "Beginner-friendly local MVP for simplified deterministic screening of likely "
    "damage mechanisms for equipment and piping."
)

st.markdown(
    """
This demo uses a hybrid approach: a strict prerequisite gate, transparent rules,
and a local self-training ML support layer. It is meant for screening and
prioritization only, and is not a substitute for engineering review.
"""
)

st.markdown(
    """
Upload a CSV or Excel file, review the actual uploaded state in one editable table,
adjust values directly, then run the screening engine.
"""
)

try:
    sample_df = load_sample_data(DATA_PATH)
except Exception as exc:
    st.error(f"Failed to load sample data: {exc}")
    st.stop()

template_bytes = build_template_workbook_bytes(sample_df)
st.download_button(
    "Download Sample Excel Template",
    data=template_bytes,
    file_name="api571_screening_template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.subheader("Input File")
uploaded_file = st.file_uploader(
    "Upload a CSV or Excel file",
    type=["csv", "xlsx", "xls"],
    help="Excel uploads will read the first sheet by default.",
)

if uploaded_file is not None:
    try:
        raw_input_df = load_uploaded_data(uploaded_file.name, uploaded_file)
    except Exception as exc:
        st.error(f"Failed to read uploaded file: {exc}")
        st.stop()
    st.success(f"Loaded `{uploaded_file.name}` with {len(raw_input_df)} rows.")
else:
    raw_input_df = sample_df.copy()
    st.info("No file uploaded. Using the bundled sample dataset.")

missing_uploaded_columns = find_missing_expected_columns(raw_input_df)
if missing_uploaded_columns:
    st.warning(
        "The uploaded file is missing expected columns: "
        + ", ".join(missing_uploaded_columns)
        + ". They were added to the table as blank fields so you can fill them in directly."
    )

initial_screening_df = normalize_screening_dataframe(raw_input_df)
screening_df = render_editable_input_table(initial_screening_df)
quality_df = render_data_quality_section(screening_df)
column_mapping = build_identity_mapping(raw_input_df)
render_results_section(raw_input_df, screening_df, quality_df, column_mapping)

st.subheader("How To Read This")
st.markdown(
    """
- The single input table shows the actual uploaded state after normalization.
- Boolean screening inputs are editable as checkboxes in the table.
- Missing uploaded columns are added as blank editable fields instead of using a separate mapping step.
- `Data Quality` shows whether each row is sufficient, partially sufficient, or insufficient for screening.
- `confidence` is now based on the early prerequisite gate, data quality, and local ML support.
- `KB Alignment` shows how strongly the row matches the structured damage-mechanism knowledge base at the gate stage.
"""
)
