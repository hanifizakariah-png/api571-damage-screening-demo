from io import BytesIO
from pathlib import Path

import pandas as pd

from screening.schema import EXPECTED_FIELDS, FIELD_METADATA


BOOLEAN_COLUMNS = [
    "water_present",
    "h2s_present",
    "co2_present",
    "chlorides_present",
    "amine_present",
    "caustic_present",
    "sulfur_present",
    "insulation_present",
    "cyclic_service",
]

TEXT_COLUMNS = [
    "equipment_tag",
    "unit",
    "service_description",
    "component_type",
    "material",
    "phase",
    "pwht_status",
    "notes",
]

NUMERIC_COLUMNS = ["temperature_c", "pressure_kpag"]


def _to_bool(value):
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "yes", "y", "1"}:
        return True
    if normalized in {"false", "no", "n", "0"}:
        return False
    return None


def normalize_screening_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()

    for column in EXPECTED_FIELDS:
        if column not in normalized.columns:
            normalized[column] = None

    for column in BOOLEAN_COLUMNS:
        normalized[column] = normalized[column].apply(_to_bool)
        normalized[column] = normalized[column].astype("boolean")

    for column in TEXT_COLUMNS:
        normalized[column] = normalized[column].fillna("").astype(str)

    for column in NUMERIC_COLUMNS:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    return normalized[EXPECTED_FIELDS]


def find_missing_expected_columns(df: pd.DataFrame):
    return [column for column in EXPECTED_FIELDS if column not in df.columns]


def load_sample_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    return normalize_screening_dataframe(df)


def load_uploaded_data(file_name: str, file_buffer) -> pd.DataFrame:
    suffix = Path(file_name).suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(file_buffer)
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(file_buffer, sheet_name=0)
    else:
        raise ValueError("Unsupported file type. Please upload a CSV or Excel file.")

    df.columns = [str(column).strip() for column in df.columns]
    return df


def suggest_column_mapping(source_columns):
    source_lookup = {str(column).strip().lower(): column for column in source_columns}
    suggestions = {}

    for expected_field in EXPECTED_FIELDS:
        if expected_field in source_columns:
            suggestions[expected_field] = expected_field
            continue

        normalized_field = expected_field.replace("_", " ").lower()
        matched_column = None
        for normalized_source, original_source in source_lookup.items():
            if normalized_source == normalized_field:
                matched_column = original_source
                break
            if normalized_source.replace(" ", "_") == expected_field:
                matched_column = original_source
                break

        suggestions[expected_field] = matched_column

    return suggestions


def apply_column_mapping(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    selected_columns = {}

    for expected_field in EXPECTED_FIELDS:
        source_column = mapping.get(expected_field)
        if source_column and source_column in df.columns:
            selected_columns[expected_field] = df[source_column]
        else:
            selected_columns[expected_field] = pd.Series([None] * len(df), index=df.index)

    mapped_df = pd.DataFrame(selected_columns)
    return normalize_screening_dataframe(mapped_df)


def build_template_workbook_bytes(sample_df: pd.DataFrame) -> bytes:
    dictionary_rows = []
    for field in EXPECTED_FIELDS:
        config = FIELD_METADATA[field]
        dictionary_rows.append(
            {
                "field_name": field,
                "label": config["label"],
                "importance": config["importance"],
                "description": config["description"],
            }
        )

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        sample_df.to_excel(writer, sheet_name="sample_input", index=False)
        pd.DataFrame(dictionary_rows).to_excel(
            writer,
            sheet_name="data_dictionary",
            index=False,
        )

    buffer.seek(0)
    return buffer.getvalue()
