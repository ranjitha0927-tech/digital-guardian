from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from flask import current_app
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


MODEL_NAME = "tfidf-logistic-regression-v1"
SAFE_LABEL = "safe"
UNSAFE_LABEL = "unsafe"


@dataclass
class QueryPrediction:
    label: str
    confidence: float
    unsafe_probability: float
    safe_probability: float
    model_name: str
    top_terms: list[str]
    accuracy: float

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "unsafe_probability": self.unsafe_probability,
            "safe_probability": self.safe_probability,
            "model_name": self.model_name,
            "top_terms": self.top_terms,
            "accuracy": self.accuracy,
        }


def _config_path(name: str) -> Path:
    return Path(current_app.config[name])


def _artifact_dir() -> Path:
    path = Path(current_app.config["ML_ARTIFACT_DIR"])
    path.mkdir(parents=True, exist_ok=True)
    return path


def _dataset_path() -> Path:
    path = Path(current_app.config["ML_DATA_DIR"]) / "search_training_dataset.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_dataset() -> pd.DataFrame:
    dataset_path = _dataset_path()
    if not dataset_path.exists():
        raise FileNotFoundError(f"Training dataset missing: {dataset_path}")
    frame = pd.read_csv(dataset_path)
    frame["text"] = frame["text"].fillna("").astype(str).str.strip()
    frame["label"] = frame["label"].fillna(SAFE_LABEL).astype(str).str.strip().str.lower()
    frame = frame[frame["text"] != ""]
    return frame


def _metadata_payload(accuracy: float, training_size: int) -> dict:
    return {
        "model_name": MODEL_NAME,
        "trained_at_utc": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
        "accuracy": round(accuracy, 4),
        "training_size": training_size,
        "labels": [SAFE_LABEL, UNSAFE_LABEL],
    }


def train_text_classifier(force: bool = False) -> dict:
    model_path = _config_path("ML_MODEL_PATH")
    metadata_path = _config_path("ML_METADATA_PATH")
    _artifact_dir()

    if model_path.exists() and metadata_path.exists() and not force:
        return load_model_metadata()

    frame = _load_dataset()
    train_frame, test_frame = train_test_split(
        frame,
        test_size=0.25,
        random_state=42,
        stratify=frame["label"],
    )

    pipeline = Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True, stop_words="english")),
            ("classifier", LogisticRegression(max_iter=1200, class_weight="balanced")),
        ]
    )
    pipeline.fit(train_frame["text"], train_frame["label"])

    predictions = pipeline.predict(test_frame["text"])
    accuracy = accuracy_score(test_frame["label"], predictions)
    payload = {"pipeline": pipeline}

    with model_path.open("wb") as handle:
        pickle.dump(payload, handle)

    metadata = _metadata_payload(accuracy=float(accuracy), training_size=len(frame))
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
    return metadata


def bootstrap_ml_assets() -> None:
    if not current_app.config.get("ML_AUTO_TRAIN", True):
        return
    train_text_classifier(force=False)


def _load_model_bundle() -> tuple[Pipeline, dict]:
    model_path = _config_path("ML_MODEL_PATH")
    metadata_path = _config_path("ML_METADATA_PATH")
    if not model_path.exists() or not metadata_path.exists():
        train_text_classifier(force=False)

    with model_path.open("rb") as handle:
        payload = pickle.load(handle)
    with metadata_path.open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)
    return payload["pipeline"], metadata


def load_model_metadata() -> dict:
    metadata_path = _config_path("ML_METADATA_PATH")
    if not metadata_path.exists():
        return train_text_classifier(force=False)
    with metadata_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def predict_query(query: str) -> QueryPrediction:
    normalized_query = (query or "").strip()
    pipeline, metadata = _load_model_bundle()
    probabilities = pipeline.predict_proba([normalized_query])[0]
    classes = list(pipeline.classes_)
    class_probs = {label: float(probabilities[index]) for index, label in enumerate(classes)}
    unsafe_probability = class_probs.get(UNSAFE_LABEL, 0.0)
    safe_probability = class_probs.get(SAFE_LABEL, 0.0)
    label = UNSAFE_LABEL if unsafe_probability >= safe_probability else SAFE_LABEL
    confidence = max(unsafe_probability, safe_probability)

    vectorizer: TfidfVectorizer = pipeline.named_steps["tfidf"]
    tokens = [token for token in vectorizer.build_tokenizer()(normalized_query.lower()) if len(token) > 2]
    top_terms = list(dict.fromkeys(tokens))[:5]
    return QueryPrediction(
        label=label,
        confidence=round(confidence, 4),
        unsafe_probability=round(unsafe_probability, 4),
        safe_probability=round(safe_probability, 4),
        model_name=metadata.get("model_name", MODEL_NAME),
        top_terms=top_terms,
        accuracy=float(metadata.get("accuracy", 0.0)),
    )


def _event_time(item):
    return getattr(item, "search_time", None) or getattr(item, "occurred_at", None) or item.created_at


def _vectorize_event(item, current_probability: float = 0.0) -> list[float]:
    event_time = _event_time(item)
    query_text = getattr(item, "search_query", None) or getattr(item, "target_name", "") or ""
    restricted_flag = 1.0 if getattr(item, "is_restricted", False) else 0.0
    return [
        float(event_time.hour),
        float(event_time.weekday()),
        float(len((query_text or "").split())),
        float(len(query_text)),
        restricted_flag,
        float(current_probability if restricted_flag else 0.0),
    ]


def detect_behavior_anomaly(recent_histories, recent_activities, current_features: dict) -> dict:
    baseline_vectors = [_vectorize_event(item) for item in list(recent_histories)[-20:] + list(recent_activities)[-20:]]
    current_vector = np.array(
        [[
            float(current_features.get("hour", 0)),
            float(current_features.get("weekday", 0)),
            float(current_features.get("query_terms", 0)),
            float(current_features.get("query_length", 0)),
            float(current_features.get("restricted_flag", 0)),
            float(current_features.get("unsafe_probability", 0)),
        ]]
    )

    if len(baseline_vectors) < 8:
        heuristic = (
            current_features.get("restricted_flag", 0) == 1
            and current_features.get("unsafe_probability", 0) >= 0.75
        ) or current_features.get("hour", 12) >= 23 or current_features.get("hour", 12) <= 5
        return {
            "anomaly_detected": bool(heuristic),
            "anomaly_score": 0.65 if heuristic else 0.18,
            "method": "heuristic-fallback",
        }

    matrix = np.array(baseline_vectors + current_vector.tolist())
    contamination = min(max(1.0 / max(len(matrix), 10), 0.05), 0.2)
    model = IsolationForest(random_state=42, contamination=contamination)
    model.fit(matrix[:-1])
    score = float(-model.score_samples(current_vector)[0])
    prediction = int(model.predict(current_vector)[0])
    return {
        "anomaly_detected": prediction == -1,
        "anomaly_score": round(score, 4),
        "method": "isolation-forest",
    }
