from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from math import sqrt


def _as_utc_naive(value: datetime | None) -> datetime:
    if value is None:
        return datetime.utcnow()
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _recent_weight(event_time: datetime, now: datetime) -> float:
    age_hours = max((now - _as_utc_naive(event_time)).total_seconds() / 3600.0, 0.0)
    if age_hours <= 24:
        return 1.0
    if age_hours <= 72:
        return 0.8
    if age_hours <= 168:
        return 0.55
    return 0.3


def _bounded_score(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return round(min(max(value, lower), upper), 2)


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = _mean(values)
    variance = sum((value - avg) ** 2 for value in values) / len(values)
    return sqrt(variance)


@dataclass
class ChildInsight:
    child_id: int
    child_name: str
    risk_score: float
    risk_level: str
    confidence: str
    anomaly_count: int
    anomalies: list[str]
    top_factors: list[dict]
    recommendations: list[str]
    metrics: dict

    def to_dict(self) -> dict:
        return {
            "child_id": self.child_id,
            "child_name": self.child_name,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "anomaly_count": self.anomaly_count,
            "anomalies": self.anomalies,
            "top_factors": self.top_factors,
            "recommendations": self.recommendations,
            "metrics": self.metrics,
        }


def _risk_level(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "moderate"
    return "low"


def _confidence(event_count: int) -> str:
    if event_count >= 20:
        return "high"
    if event_count >= 8:
        return "medium"
    return "limited"


def _build_recommendations(metrics: dict, anomalies: list[str], child) -> list[str]:
    recommendations: list[str] = []
    if metrics["restricted_rate"] >= 0.25:
        recommendations.append("Increase keyword coverage and review recent restricted search categories.")
    if metrics["late_night_ratio"] >= 0.18:
        recommendations.append("Enable stricter bedtime monitoring because late-night activity is elevated.")
    if metrics["screen_time_vs_limit"] > 1.1:
        recommendations.append(
            f"Child exceeded the configured screen-time limit by {round((metrics['screen_time_vs_limit'] - 1) * 100, 1)}%."
        )
    if metrics["activity_burst_score"] >= 70:
        recommendations.append("Investigate short bursts of rapid activity that may indicate evasive browsing behavior.")
    if anomalies:
        recommendations.append("Review the anomaly flags to confirm whether the recent pattern represents a behavior shift.")
    if metrics["safe_ratio"] >= 0.85 and not recommendations:
        recommendations.append("Behavior looks stable; maintain current settings and continue periodic review.")
    if not recommendations:
        recommendations.append(
            f"Monitor {child.child_name}'s recent activity for trend changes and adjust controls only if the score rises."
        )
    return recommendations[:4]


def score_child_behavior(child, histories, activities, alerts, safe_results, screen_time_hours: float) -> ChildInsight:
    now = datetime.utcnow()
    history_events = sorted(histories, key=lambda item: _as_utc_naive(getattr(item, "search_time", None) or item.created_at))
    activity_events = sorted(activities, key=lambda item: _as_utc_naive(getattr(item, "occurred_at", None) or item.created_at))
    all_events = []
    restricted_events = []
    hourly_activity = Counter()
    category_counter = Counter()
    recent_spacing_minutes: list[float] = []

    previous_time = None
    for item in history_events:
        event_time = _as_utc_naive(getattr(item, "search_time", None) or item.created_at)
        weight = _recent_weight(event_time, now)
        all_events.append((event_time, item.is_restricted, weight))
        hourly_activity[event_time.hour] += 1
        if item.matched_category:
            category_counter[item.matched_category] += 1
        if item.is_restricted:
            restricted_events.append((event_time, weight))
        if previous_time is not None:
            recent_spacing_minutes.append(max((event_time - previous_time).total_seconds() / 60.0, 0.0))
        previous_time = event_time

    for item in activity_events:
        event_time = _as_utc_naive(getattr(item, "occurred_at", None) or item.created_at)
        weight = _recent_weight(event_time, now)
        all_events.append((event_time, item.is_restricted, weight))
        hourly_activity[event_time.hour] += 1
        if item.matched_category:
            category_counter[item.matched_category] += 1
        if item.is_restricted:
            restricted_events.append((event_time, weight))

    all_events.sort(key=lambda item: item[0])

    event_count = len(all_events)
    restricted_count = len(restricted_events)
    safe_result_count = len([item for item in safe_results if not item.is_restricted])
    safe_ratio = _safe_divide(safe_result_count, max(len(safe_results), 1))
    restricted_rate = _safe_divide(restricted_count, max(event_count, 1))
    weighted_restricted = sum(30 * weight for _, weight in restricted_events)
    late_night_events = sum(1 for event_time, _, _ in all_events if event_time.hour >= 23 or event_time.hour <= 5)
    late_night_ratio = _safe_divide(late_night_events, max(event_count, 1))
    alert_pressure = min(len(alerts) * 6, 25)
    screen_time_vs_limit = _safe_divide(screen_time_hours, max(getattr(child, "screen_time_limit_hours", 2.0), 0.5))

    burst_score = 0.0
    if recent_spacing_minutes:
        short_gaps = len([gap for gap in recent_spacing_minutes if gap <= 5])
        burst_score = _bounded_score(_safe_divide(short_gaps, len(recent_spacing_minutes)) * 100)

    category_focus_ratio = _safe_divide(max(category_counter.values(), default=0), max(sum(category_counter.values()), 1))
    restricted_recent = len([1 for event_time, _ in restricted_events if (now - event_time).total_seconds() <= 48 * 3600])
    restricted_baseline = len([1 for event_time, _ in restricted_events if (now - event_time).total_seconds() > 48 * 3600])

    anomaly_flags: list[str] = []
    hourly_values = list(hourly_activity.values())
    peak_hour_count = max(hourly_values, default=0)
    avg_hour_count = _mean([float(value) for value in hourly_values]) if hourly_values else 0.0
    std_hour_count = _stddev([float(value) for value in hourly_values]) if hourly_values else 0.0

    if late_night_ratio >= 0.2 and late_night_events >= 2:
        anomaly_flags.append("late-night activity spike")
    if restricted_recent >= 3 and restricted_recent > max(restricted_baseline, 1):
        anomaly_flags.append("recent restricted-attempt surge")
    if peak_hour_count >= 3 and std_hour_count and (peak_hour_count - avg_hour_count) / std_hour_count >= 1.5:
        anomaly_flags.append("unusual concentration within a single hour")
    if burst_score >= 70:
        anomaly_flags.append("rapid-fire activity burst")
    if category_focus_ratio >= 0.7 and sum(category_counter.values()) >= 4:
        anomaly_flags.append("risk concentrated in one content category")

    factor_map = {
        "restricted_behavior": restricted_rate * 45,
        "late_night_usage": late_night_ratio * 22,
        "screen_time_pressure": max(screen_time_vs_limit - 1.0, 0.0) * 24,
        "alert_frequency": alert_pressure,
        "activity_burstiness": burst_score * 0.16,
        "category_concentration": category_focus_ratio * 14,
        "recent_restricted_weight": weighted_restricted,
    }
    risk_score = _bounded_score(sum(factor_map.values()))

    factor_labels = {
        "restricted_behavior": "Restricted behavior frequency",
        "late_night_usage": "Late-night usage pattern",
        "screen_time_pressure": "Screen-time limit pressure",
        "alert_frequency": "Alert frequency",
        "activity_burstiness": "Activity burstiness",
        "category_concentration": "Category concentration",
        "recent_restricted_weight": "Recent restricted-event recency",
    }
    top_factors = [
        {"name": factor_labels[name], "impact": round(value, 2)}
        for name, value in sorted(factor_map.items(), key=lambda item: item[1], reverse=True)
        if value > 0
    ][:4]

    metrics = {
        "event_count": event_count,
        "restricted_count": restricted_count,
        "safe_result_count": safe_result_count,
        "restricted_rate": round(restricted_rate, 4),
        "safe_ratio": round(safe_ratio, 4),
        "late_night_ratio": round(late_night_ratio, 4),
        "screen_time_hours": round(screen_time_hours, 2),
        "screen_time_limit_hours": float(getattr(child, "screen_time_limit_hours", 2.0) or 2.0),
        "screen_time_vs_limit": round(screen_time_vs_limit, 4),
        "activity_burst_score": round(burst_score, 2),
        "category_focus_ratio": round(category_focus_ratio, 4),
        "top_category": category_counter.most_common(1)[0][0] if category_counter else None,
        "peak_activity_hour": max(hourly_activity, key=hourly_activity.get) if hourly_activity else None,
    }

    return ChildInsight(
        child_id=child.id,
        child_name=child.child_name,
        risk_score=risk_score,
        risk_level=_risk_level(risk_score),
        confidence=_confidence(event_count),
        anomaly_count=len(anomaly_flags),
        anomalies=anomaly_flags,
        top_factors=top_factors,
        recommendations=_build_recommendations(metrics, anomaly_flags, child),
        metrics=metrics,
    )


def build_parent_ai_insights(parent_id: int, children, histories, activities, alerts, safe_results, screen_time_by_child: dict[int, float]) -> dict:
    history_by_child = defaultdict(list)
    activity_by_child = defaultdict(list)
    alert_by_child = defaultdict(list)
    safe_by_child = defaultdict(list)

    for item in histories:
        history_by_child[item.child_id].append(item)
    for item in activities:
        activity_by_child[item.child_id].append(item)
    for item in alerts:
        alert_by_child[item.child_id].append(item)
    for item in safe_results:
        safe_by_child[item.child_id].append(item)

    child_insights = [
        score_child_behavior(
            child,
            history_by_child.get(child.id, []),
            activity_by_child.get(child.id, []),
            alert_by_child.get(child.id, []),
            safe_by_child.get(child.id, []),
            screen_time_by_child.get(child.id, 0.0),
        ).to_dict()
        for child in children
    ]

    if not child_insights:
        return {
            "parent_id": parent_id,
            "average_risk_score": 0,
            "highest_risk_score": 0,
            "highest_risk_child": None,
            "children_monitored": 0,
            "anomaly_count": 0,
            "risk_distribution": {"low": 0, "moderate": 0, "high": 0, "critical": 0},
            "priority_actions": ["Add a child profile and begin monitoring to generate behavior insights."],
            "children": [],
        }

    avg_risk = round(_mean([item["risk_score"] for item in child_insights]), 2)
    highest = max(child_insights, key=lambda item: item["risk_score"])
    distribution = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
    total_anomalies = 0
    priority_actions: list[str] = []

    for insight in child_insights:
        distribution[insight["risk_level"]] += 1
        total_anomalies += insight["anomaly_count"]
        for recommendation in insight["recommendations"]:
            if recommendation not in priority_actions:
                priority_actions.append(recommendation)

    return {
        "parent_id": parent_id,
        "average_risk_score": avg_risk,
        "highest_risk_score": highest["risk_score"],
        "highest_risk_child": highest["child_name"],
        "children_monitored": len(child_insights),
        "anomaly_count": total_anomalies,
        "risk_distribution": distribution,
        "priority_actions": priority_actions[:5],
        "children": child_insights,
    }
