import hashlib
import json
import re
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression


HISTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "ml_training_history.jsonl"
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _normalize_text(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().lower()


def row_to_features(row):
    features = {}

    for field in ["temperature_c", "pressure_kpag"]:
        value = row.get(field)
        if value is not None and not pd.isna(value):
            features[f"num_{field}"] = float(value)

    for field in [
        "water_present",
        "h2s_present",
        "co2_present",
        "chlorides_present",
        "amine_present",
        "caustic_present",
        "sulfur_present",
        "insulation_present",
        "cyclic_service",
    ]:
        value = row.get(field)
        if value is True:
            features[f"flag_{field}"] = 1
        elif value is False:
            features[f"flag_{field}"] = 0
        else:
            features[f"flag_{field}"] = -1

    for field in ["material", "phase", "component_type", "unit", "pwht_status"]:
        text = _normalize_text(row.get(field))
        if text:
            features[f"cat_{field}={text}"] = 1

    text_blob = " ".join(
        [
            _normalize_text(row.get("service_description")),
            _normalize_text(row.get("notes")),
            _normalize_text(row.get("component_type")),
            _normalize_text(row.get("material")),
        ]
    )
    for token in set(TOKEN_PATTERN.findall(text_blob)):
        if len(token) >= 3:
            features[f"tok_{token}"] = 1

    return features


def _record_id(features, labels):
    payload = json.dumps(
        {"features": features, "labels": sorted(labels)},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_training_entries(df, row_labels):
    entries = []
    for source_row, row in df.iterrows():
        labels = sorted(row_labels.get(source_row, []))
        features = row_to_features(row)
        entries.append(
            {
                "record_id": _record_id(features, labels),
                "features": features,
                "labels": labels,
            }
        )
    return entries


def _load_history():
    if not HISTORY_PATH.exists():
        return []

    entries = []
    for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def _save_history(entries):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    unique = {}
    for entry in entries:
        unique[entry["record_id"]] = entry
    HISTORY_PATH.write_text(
        "\n".join(json.dumps(entry, sort_keys=True) for entry in unique.values()),
        encoding="utf-8",
    )


def train_self_learning_model(df, row_labels, mechanisms):
    current_entries = _build_training_entries(df, row_labels)
    history_entries = _load_history()
    train_entries = history_entries if history_entries else current_entries

    features = [entry["features"] for entry in train_entries]
    vectorizer = DictVectorizer(sparse=True)
    x_train = vectorizer.fit_transform(features)

    models = {}
    base_rates = {}
    for mechanism in mechanisms:
        y_train = [1 if mechanism in entry["labels"] else 0 for entry in train_entries]
        positives = sum(y_train)
        base_rates[mechanism] = positives / len(y_train) if y_train else 0.0

        if positives == 0 or positives == len(y_train):
            models[mechanism] = None
            continue

        model = LogisticRegression(max_iter=1000)
        model.fit(x_train, y_train)
        models[mechanism] = model

    current_features = [entry["features"] for entry in current_entries]
    x_current = vectorizer.transform(current_features)

    scores = {}
    for row_index, source_row in enumerate(df.index):
        scores[source_row] = {}
        for mechanism in mechanisms:
            model = models[mechanism]
            if model is None:
                probability = base_rates[mechanism]
            else:
                probability = float(model.predict_proba(x_current[row_index])[0][1])
            scores[source_row][mechanism] = probability

    _save_history(history_entries + current_entries)
    return scores
