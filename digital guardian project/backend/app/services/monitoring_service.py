from datetime import datetime, time, timezone

from ..extensions import db
from ..models import (
    ActivityLog,
    Alert,
    BrowsingHistory,
    ChildProfile,
    MlPredictionLog,
    NotificationLog,
    Report,
    ParentUser,
    RestrictedKeyword,
    SafeSearchResult,
)
from .ai_risk_service import build_parent_ai_insights
from .filtering_service import DEFAULT_SAFE_RESULTS, classify_hybrid_text
from .ml_service import detect_behavior_anomaly
from .notification_service import dispatch_email, dispatch_sms, normalize_sms_recipient

SAFE_SEARCH_LIBRARY = {
    "games": [
        {
            "name": "Coolmath Games",
            "url": "https://www.coolmathgames.com",
            "description": "Logic, puzzle, and strategy games for kids.",
        },
        {
            "name": "PBS Kids Games",
            "url": "https://pbskids.org/games",
            "description": "Educational games with learning-focused play.",
        },
        {
            "name": "National Geographic Kids Games",
            "url": "https://kids.nationalgeographic.com/games",
            "description": "Animal, science, and exploration games.",
        },
    ],
    "movies": [
        {
            "name": "Common Sense Media",
            "url": "https://www.commonsensemedia.org/movie-reviews",
            "description": "Family-friendly movie reviews and age guidance.",
        },
        {
            "name": "Disney Family Movies",
            "url": "https://movies.disney.com/",
            "description": "Kid-safe family movie content and trailers.",
        },
        {
            "name": "PBS Kids Videos",
            "url": "https://pbskids.org/video/",
            "description": "Educational videos and safe kids entertainment.",
        },
    ],
    "cartoons": [
        {
            "name": "PBS Kids Video",
            "url": "https://pbskids.org/video/",
            "description": "Cartoons and learning videos for children.",
        },
        {
            "name": "Nick Jr.",
            "url": "https://www.nickjr.com/",
            "description": "Preschool cartoons and activities.",
        },
        {
            "name": "Kids Learning Tube",
            "url": "https://www.youtube.com/@KidsLearningTube",
            "description": "Animated educational content.",
        },
    ],
    "drawing": [
        {
            "name": "Art for Kids Hub",
            "url": "https://www.artforkidshub.com/",
            "description": "Drawing tutorials for kids and beginners.",
        },
        {
            "name": "Crayola",
            "url": "https://www.crayola.com/for-kids/",
            "description": "Creative drawing ideas, printables, and activities.",
        },
        {
            "name": "Tate Kids Art",
            "url": "https://www.tate.org.uk/kids",
            "description": "Art inspiration and drawing ideas for children.",
        },
    ],
    "reading": [
        {
            "name": "Storyline Online",
            "url": "https://storylineonline.net/",
            "description": "Read-aloud stories by actors and educators.",
        },
        {
            "name": "Epic!",
            "url": "https://www.getepic.com/",
            "description": "Digital reading library for kids.",
        },
        {
            "name": "Oxford Owl",
            "url": "https://www.oxfordowl.co.uk/",
            "description": "Free books and guided reading resources.",
        },
    ],
    "coding": [
        {
            "name": "Code.org",
            "url": "https://code.org/",
            "description": "Beginner-friendly coding lessons for students.",
        },
        {
            "name": "Scratch",
            "url": "https://scratch.mit.edu/",
            "description": "Creative coding with safe community learning.",
        },
        {
            "name": "Khan Academy",
            "url": "https://www.khanacademy.org/",
            "description": "Structured learning in math, coding, and science.",
        },
    ],
    "science": [
        {
            "name": "National Geographic Kids",
            "url": "https://kids.nationalgeographic.com/",
            "description": "Safe science, animals, and nature content.",
        },
        {
            "name": "NASA Kids Club",
            "url": "https://www.nasa.gov/kidsclub/",
            "description": "Space learning content for children.",
        },
        {
            "name": "Smithsonian Kids",
            "url": "https://www.si.edu/kids",
            "description": "Museum-backed educational discovery content.",
        },
    ],
    "music": [
        {
            "name": "Sesame Street",
            "url": "https://www.sesamestreet.org/",
            "description": "Sing-alongs and learning songs for kids.",
        },
        {
            "name": "Kids Bop",
            "url": "https://kidzbop.com/",
            "description": "Family-friendly music content.",
        },
        {
            "name": "PBS Kids Music",
            "url": "https://pbskids.org/music",
            "description": "Music learning for young children.",
        },
    ],
    "sports": [
        {
            "name": "GoNoodle",
            "url": "https://www.gonoodle.com/",
            "description": "Movement and active play videos for kids.",
        },
        {
            "name": "Khan Academy Wellness",
            "url": "https://www.khanacademy.org/",
            "description": "Educational wellness and movement resources.",
        },
        {
            "name": "National Geographic Kids",
            "url": "https://kids.nationalgeographic.com/",
            "description": "Kid-safe sports and activity content.",
        },
    ],
    "math": [
        {
            "name": "Khan Academy Math",
            "url": "https://www.khanacademy.org/math",
            "description": "Structured, kid-friendly math learning paths.",
        },
        {
            "name": "Prodigy Math",
            "url": "https://www.prodigygame.com/main-en/",
            "description": "Game-based math practice for children.",
        },
        {
            "name": "Math Playground",
            "url": "https://www.mathplayground.com/",
            "description": "Interactive puzzles and math games.",
        },
    ],
    "history": [
        {
            "name": "National Geographic History",
            "url": "https://kids.nationalgeographic.com/history",
            "description": "Age-appropriate history stories and facts.",
        },
        {
            "name": "Britannica Kids",
            "url": "https://kids.britannica.com/",
            "description": "Kid-safe encyclopedia for history and culture.",
        },
        {
            "name": "Ducksters History",
            "url": "https://www.ducksters.com/history/",
            "description": "Simple history topics for school students.",
        },
    ],
    "geography": [
        {
            "name": "National Geographic Kids Maps",
            "url": "https://kids.nationalgeographic.com/geography",
            "description": "Geography, maps, and place discovery for kids.",
        },
        {
            "name": "Seterra Geography Games",
            "url": "https://www.seterra.com/",
            "description": "Geography quiz games for learners.",
        },
        {
            "name": "Britannica Kids Geography",
            "url": "https://kids.britannica.com/",
            "description": "Safe geography explainers and references.",
        },
    ],
}

EMERGENCY_MESSAGE = "Emergency alert from Digital Guardian"


def _utc_now():
    return datetime.utcnow()


def _as_utc_naive(value: datetime):
    if value is None:
        return _utc_now()
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _as_local_time(value: datetime):
    return _as_utc_naive(value).replace(tzinfo=timezone.utc).astimezone()


def _estimate_screen_time_hours(histories, activities):
    timestamps = []
    for item in histories:
        timestamps.append(_as_utc_naive(getattr(item, "search_time", None) or item.created_at))
    for item in activities:
        timestamps.append(_as_utc_naive(getattr(item, "occurred_at", None) or item.created_at))

    if not timestamps:
        return 0.0

    timestamps.sort()
    if len(timestamps) == 1:
        return 0.2

    active_minutes = 10.0
    previous = timestamps[0]
    for current in timestamps[1:]:
        gap_minutes = max((current - previous).total_seconds() / 60.0, 0.0)
        active_minutes += min(gap_minutes, 30.0)
        previous = current

    return round(active_minutes / 60.0, 2)


def _screen_time_by_child(histories, activities):
    child_ids = {item.child_id for item in histories} | {item.child_id for item in activities}
    return {
        child_id: _estimate_screen_time_hours(
            [item for item in histories if item.child_id == child_id],
            [item for item in activities if item.child_id == child_id],
        )
        for child_id in child_ids
    }


def _normalize_query(text: str):
    return (text or "").strip().lower()


def _topic_sites(normalized: str):
    topic_aliases = {
        "games": ["games", "game", "gaming", "play"],
        "movies": ["movie", "movies", "film", "films", "cinema"],
        "cartoons": ["cartoon", "cartoons", "animation", "animated"],
        "drawing": ["drawing", "draw", "sketch", "art", "painting"],
        "reading": ["reading", "book", "books", "story", "stories"],
        "coding": ["coding", "code", "programming", "developer", "computer"],
        "science": ["science", "space", "astronomy", "nature", "experiment"],
        "music": ["music", "song", "songs", "sing", "singing"],
        "sports": ["sports", "fitness", "exercise", "workout", "soccer", "cricket"],
        "math": ["math", "mathematics", "algebra", "geometry", "numbers", "fractions"],
        "history": ["history", "civilization", "ancient", "war", "freedom", "timeline"],
        "geography": ["geography", "map", "countries", "continents", "earth", "places"],
    }
    for topic, aliases in topic_aliases.items():
        if any(alias in normalized for alias in aliases):
            return topic, SAFE_SEARCH_LIBRARY[topic]
    return None, DEFAULT_SAFE_RESULTS


def _search_options(query: str):
    normalized = (query or "").strip()
    encoded = quote_plus(normalized)
    return [
        {
            "name": "Kiddle (Kid Safe Search)",
            "url": f"https://www.kiddle.co/s.php?q={encoded}",
            "description": "Kid-focused safe search for general browsing.",
        },
        {
            "name": "Google SafeSearch",
            "url": f"https://www.google.com/search?q={encoded}&safe=active",
            "description": "General search with safe mode enabled.",
        },
        {
            "name": "Bing SafeSearch",
            "url": f"https://www.bing.com/search?q={encoded}&adlt=strict",
            "description": "Strict safe search filtering option.",
        },
        {
            "name": "YouTube Kids Topics",
            "url": f"https://www.youtubekids.com/search?q={encoded}",
            "description": "Video-focused content for children.",
        },
        {
            "name": "Britannica Kids",
            "url": f"https://kids.britannica.com/search?query={encoded}",
            "description": "Safe encyclopedia search option.",
        },
    ]


def classify_text(text: str):
    return classify_hybrid_text(text)


def create_notification(parent_id, child_id, trigger_type, title, message, recipient, meta=None, provider=None, delivery_status="sent", channel="sms"):
    notification = NotificationLog(
        parent_id=parent_id,
        child_id=child_id,
        trigger_type=trigger_type,
        title=title,
        message=message,
        recipient=recipient,
        provider=provider or "simulated_twilio",
        channel=channel,
        delivery_status=delivery_status,
        meta_json=meta or {},
        sent_at=_utc_now(),
    )
    db.session.add(notification)
    return notification


def _dispatch_sms(parent: ParentUser, message: str):
    return dispatch_sms(parent, message)


def _dispatch_email(parent: ParentUser, subject: str, message: str):
    return dispatch_email(parent, subject, message)


def _normalize_sms_recipient(raw_number: str):
    return normalize_sms_recipient(raw_number)


def create_alert(parent_id, child_id, title, description, severity, history_id=None, activity_id=None):
    alert = Alert(
        parent_id=parent_id,
        child_id=child_id,
        history_id=history_id,
        activity_id=activity_id,
        title=title,
        description=description,
        severity=severity or "high",
    )
    db.session.add(alert)
    return alert


def analyze_search(parent_id, child, search_query, site_url, device_name, search_time):
    analysis = classify_text(search_query)
    search_time = _as_utc_naive(search_time)
    recent_histories = BrowsingHistory.query.filter_by(parent_id=parent_id, child_id=child.id).order_by(BrowsingHistory.created_at.desc()).limit(25).all()
    recent_activities = ActivityLog.query.filter_by(parent_id=parent_id, child_id=child.id).order_by(ActivityLog.created_at.desc()).limit(25).all()
    anomaly = detect_behavior_anomaly(
        recent_histories,
        recent_activities,
        {
            "hour": search_time.hour,
            "weekday": search_time.weekday(),
            "query_terms": len((search_query or "").split()),
            "query_length": len(search_query or ""),
            "restricted_flag": 1 if analysis["is_restricted"] else 0,
            "unsafe_probability": analysis.get("unsafe_probability", 0.0),
        },
    )

    history = BrowsingHistory(
        parent_id=parent_id,
        child_id=child.id,
        search_query=search_query,
        site_url=site_url,
        device_name=device_name or child.device_name,
        activity_type="browser_search",
        matched_keyword=analysis["keyword"],
        matched_category=analysis["category"],
        is_restricted=analysis["is_restricted"],
        search_time=search_time,
    )
    db.session.add(history)
    db.session.flush()

    generated_alerts = []
    created_notifications = []
    safe_reason = None
    parent = child.parent
    sms_dispatch = None
    email_dispatch = None
    ml_log = MlPredictionLog(
        parent_id=parent_id,
        child_id=child.id,
        history_id=history.id,
        input_text=search_query,
        rule_based_label=analysis.get("rule_based_label", "safe"),
        ml_label=analysis.get("ml_label", "safe"),
        final_label=analysis.get("final_label", "safe"),
        confidence_score=analysis.get("ml_confidence", 0.0),
        anomaly_score=anomaly.get("anomaly_score"),
        anomaly_detected=anomaly.get("anomaly_detected", False),
        model_name=analysis.get("model_name", "hybrid-text-classifier"),
        feature_json={
            "search_topic": analysis.get("search_topic"),
            "unsafe_probability": analysis.get("unsafe_probability"),
            "safe_probability": analysis.get("safe_probability"),
            "top_terms": analysis.get("top_terms", []),
            "decision_reason": analysis.get("decision_reason", []),
            "anomaly_method": anomaly.get("method"),
        },
    )
    db.session.add(ml_log)

    if analysis["is_restricted"]:
        blocked_reason = (
            f"Restricted keyword matched: {analysis['keyword']}"
            if analysis["keyword"]
            else "Machine learning classifier marked the query as unsafe."
        )
        category_label = (analysis["category"] or "unsafe activity").title()
        title = f"{category_label} detected"
        description = (
            f"{child.child_name} searched for '{search_query}'. "
            f"Rule engine: {analysis.get('rule_based_label', 'safe')}. "
            f"ML model: {analysis.get('ml_label', 'safe')} at {round(analysis.get('ml_confidence', 0.0) * 100, 1)}% confidence."
        )
        generated_alerts.append(
            create_alert(
                parent_id=parent_id,
                child_id=child.id,
                history_id=history.id,
                title=title,
                description=description,
                severity=analysis["severity"] or "high",
            )
        )
        sms_message = (
            f"Alert: Your child attempted to access restricted content ({category_label}) "
            f"at {_as_local_time(search_time).strftime('%I:%M %p')}. Please check Digital Guardian App."
        )
        email_message = (
            f"Digital Guardian detected unsafe search activity for {child.child_name}.\n\n"
            f"Query: {search_query}\n"
            f"Rule result: {analysis.get('rule_based_label', 'safe')}\n"
            f"ML result: {analysis.get('ml_label', 'safe')} ({round(analysis.get('ml_confidence', 0.0) * 100, 1)}% confidence)\n"
            f"Reason: {'; '.join(analysis.get('decision_reason', []))}\n"
            f"Anomaly detected: {'Yes' if anomaly.get('anomaly_detected') else 'No'}"
        )
        sms_dispatch = _dispatch_sms(parent, sms_message) if parent else {"provider": "none", "delivery_status": "skipped"}
        email_dispatch = _dispatch_email(parent, "Digital Guardian unsafe activity alert", email_message) if parent else {"provider": "none", "delivery_status": "skipped"}
        created_notifications.append(
            create_notification(
                parent_id=parent_id,
                child_id=child.id,
                trigger_type="restricted_search",
                title="Restricted search detected",
                message=sms_message,
                recipient=_parent_recipient(child),
                meta={"search_query": search_query, "site_url": site_url, "ml_confidence": analysis.get("ml_confidence", 0.0)},
                provider=(sms_dispatch or {}).get("provider", "simulated_twilio"),
                delivery_status=(sms_dispatch or {}).get("delivery_status", "sent"),
            )
        )
        created_notifications.append(
            create_notification(
                parent_id=parent_id,
                child_id=child.id,
                trigger_type="restricted_search_email",
                title="Restricted search email alert",
                message=email_message,
                recipient=parent.email if parent else "unknown",
                meta={"search_query": search_query, "site_url": site_url},
                provider=(email_dispatch or {}).get("provider", "simulated_email"),
                delivery_status=(email_dispatch or {}).get("delivery_status", "sent"),
                channel="email",
            )
        )
        safe_reason = blocked_reason
        recommended_sites = []
        search_topic = None
    else:
        recommended_sites = analysis["recommended_sites"]
        search_topic = analysis["search_topic"]
        if anomaly.get("anomaly_detected"):
            generated_alerts.append(
                create_alert(
                    parent_id=parent_id,
                    child_id=child.id,
                    history_id=history.id,
                    title="Behavior anomaly detected",
                    description=(
                        f"Digital Guardian detected an unusual browsing pattern for {child.child_name} "
                        f"while searching '{search_query}'."
                    ),
                    severity="medium",
                )
            )

    if is_late_night(search_time):
        generated_alerts.append(
            create_alert(
                parent_id=parent_id,
                child_id=child.id,
                history_id=history.id,
                title="Late night browsing warning",
        description=f"{child.child_name} was active at {_as_local_time(search_time).strftime('%I:%M %p')}.",
                severity="medium" if not analysis["is_restricted"] else "high",
            )
        )

    safe_result = SafeSearchResult(
        parent_id=parent_id,
        child_id=child.id,
        history_id=history.id,
        search_query=search_query,
        matched_keyword=analysis["keyword"],
        search_topic=search_topic,
        is_restricted=analysis["is_restricted"],
        recommended_sites=recommended_sites if not analysis["is_restricted"] else [],
        blocked_reason=safe_reason,
    )
    db.session.add(safe_result)

    recalculate_reports(parent_id)
    db.session.commit()

    return {
        "history_id": history.id,
        "is_restricted": analysis["is_restricted"],
        "is_game_related": analysis["search_topic"] == "games",
        "matched_keyword": analysis["keyword"],
        "matched_category": analysis["category"],
        "severity": analysis["severity"],
        "search_topic": analysis["search_topic"],
        "rule_based_label": analysis.get("rule_based_label"),
        "ml_label": analysis.get("ml_label"),
        "ml_confidence": analysis.get("ml_confidence"),
        "unsafe_probability": analysis.get("unsafe_probability"),
        "model_name": analysis.get("model_name"),
        "anomaly_detected": anomaly.get("anomaly_detected", False),
        "anomaly_score": anomaly.get("anomaly_score"),
        "decision_reason": analysis.get("decision_reason", []),
        "generated_alerts": len(generated_alerts),
        "generated_notifications": len(created_notifications),
        "recommended_sites": recommended_sites,
        "search_options": analysis["search_options"],
        "blocked_reason": safe_reason,
        "sms_delivery": sms_dispatch or {"provider": "simulated_twilio", "delivery_status": "sent"},
        "email_delivery": email_dispatch or {"provider": "simulated_email", "delivery_status": "sent"},
        "message": (
            f"Access blocked immediately. Restricted content detected for category '{analysis['category'] or 'unsafe activity'}'."
            if analysis["is_restricted"]
            else "Safe search recorded successfully with hybrid analysis."
        ),
    }


def log_activity(parent_id, child, event_type, title, target_url=None, details=None, keyword=None, is_restricted=False, matched_category=None, app_name=None, occurred_at=None):
    occurred_at = _as_utc_naive(occurred_at)
    activity = ActivityLog(
        parent_id=parent_id,
        child_id=child.id,
        event_type=event_type,
        app_name=app_name,
        target_name=title,
        target_url=target_url,
        details=details,
        keyword=keyword,
        matched_category=matched_category,
        is_restricted=is_restricted,
        occurred_at=occurred_at,
    )
    db.session.add(activity)
    db.session.flush()

    alert = None
    notification = None
    email_notification = None
    if is_restricted:
        sms_message = f"Alert: Your child accessed restricted {event_type.replace('_', ' ')} at {_as_local_time(occurred_at).strftime('%I:%M %p')}."
        email_message = (
            f"Restricted activity detected for {child.child_name}.\n\n"
            f"Event: {event_type}\n"
            f"Target: {title}\n"
            f"Details: {details or 'Not provided'}"
        )
        sms_dispatch = _dispatch_sms(child.parent, sms_message) if child.parent else {"provider": "none", "delivery_status": "skipped"}
        email_dispatch = _dispatch_email(child.parent, "Digital Guardian restricted activity alert", email_message) if child.parent else {"provider": "none", "delivery_status": "skipped"}
        alert = create_alert(
            parent_id=parent_id,
            child_id=child.id,
            activity_id=activity.id,
            title=f"Restricted {event_type.replace('_', ' ')}",
            description=details or f"{child.child_name} triggered a restricted {event_type} event.",
            severity="high",
        )
        notification = create_notification(
            parent_id=parent_id,
            child_id=child.id,
            trigger_type=event_type,
            title="Restricted activity detected",
            message=sms_message,
            recipient=_parent_recipient(child),
            meta={"target_url": target_url, "details": details, "keyword": keyword},
            provider=(sms_dispatch or {}).get("provider", "simulated_twilio"),
            delivery_status=(sms_dispatch or {}).get("delivery_status", "sent"),
        )
        email_notification = create_notification(
            parent_id=parent_id,
            child_id=child.id,
            trigger_type=f"{event_type}_email",
            title="Restricted activity email alert",
            message=email_message,
            recipient=child.parent.email if child.parent else "unknown",
            meta={"target_url": target_url, "details": details, "keyword": keyword},
            provider=(email_dispatch or {}).get("provider", "simulated_email"),
            delivery_status=(email_dispatch or {}).get("delivery_status", "sent"),
            channel="email",
        )

    recalculate_reports(parent_id)
    db.session.commit()

    return {
        "activity_id": activity.id,
        "is_restricted": is_restricted,
        "alert_id": alert.id if alert else None,
        "notification_id": notification.id if notification else None,
        "email_notification_id": email_notification.id if email_notification else None,
    }


def emergency_alert(parent_id, child):
    now = _utc_now()
    sms_message = f"Alert: Your child requested emergency help at {_as_local_time(now).strftime('%I:%M %p')}. Please check Digital Guardian App."
    parent = child.parent
    sms_allowed = bool(
        parent
        and parent.settings
        and parent.settings.notification_enabled
        and parent.settings.emergency_alerts_enabled
    )
    sms_dispatch = _dispatch_sms(parent, sms_message) if sms_allowed and parent else {
        "provider": "disabled",
        "delivery_status": "skipped",
        "reference": None,
        "details": "Emergency alerts are disabled in parent settings.",
    }
    email_dispatch = _dispatch_email(parent, "Digital Guardian emergency alert", sms_message) if parent else {
        "provider": "none",
        "delivery_status": "skipped",
        "reference": None,
        "details": "Parent email not available.",
    }
    notification = create_notification(
        parent_id=parent_id,
        child_id=child.id,
        trigger_type="emergency",
        title="Emergency alert triggered",
        message=sms_message,
        recipient=_parent_recipient(child),
        meta={"source": "emergency_button"},
        provider=(sms_dispatch or {}).get("provider", "simulated_twilio"),
        delivery_status=(sms_dispatch or {}).get("delivery_status", "sent"),
    )
    email_notification = create_notification(
        parent_id=parent_id,
        child_id=child.id,
        trigger_type="emergency_email",
        title="Emergency alert email",
        message=sms_message,
        recipient=parent.email if parent else "unknown",
        meta={"source": "emergency_button"},
        provider=(email_dispatch or {}).get("provider", "simulated_email"),
        delivery_status=(email_dispatch or {}).get("delivery_status", "sent"),
        channel="email",
    )
    alert = create_alert(
        parent_id=parent_id,
        child_id=child.id,
        title="Emergency alert",
        description=f"{child.child_name} pressed the emergency alert button.",
        severity="critical",
    )
    recalculate_reports(parent_id)
    db.session.commit()
    return {
        "notification_id": notification.id,
        "email_notification_id": email_notification.id,
        "alert_id": alert.id,
        "sms_delivery": sms_dispatch or {"provider": "simulated_twilio", "delivery_status": "sent"},
        "email_delivery": email_dispatch or {"provider": "simulated_email", "delivery_status": "sent"},
    }


def _parent_recipient(child):
    parent = child.parent
    if parent and parent.phone_number:
        return parent.phone_number
    return parent.email if parent else "unknown"


def is_late_night(search_time: datetime):
    current_time = _as_local_time(search_time).time()
    return current_time >= time(23, 0) or current_time <= time(5, 0)


def recalculate_reports(parent_id: int):
    histories = BrowsingHistory.query.filter_by(parent_id=parent_id).order_by(BrowsingHistory.created_at.desc()).all()
    activities = ActivityLog.query.filter_by(parent_id=parent_id).order_by(ActivityLog.created_at.desc()).all()
    safe_results = SafeSearchResult.query.filter_by(parent_id=parent_id).order_by(SafeSearchResult.created_at.desc()).all()
    notifications = NotificationLog.query.filter_by(parent_id=parent_id).order_by(NotificationLog.created_at.desc()).all()
    ml_predictions = MlPredictionLog.query.filter_by(parent_id=parent_id).order_by(MlPredictionLog.created_at.desc()).all()
    alerts = Alert.query.filter_by(parent_id=parent_id).order_by(Alert.created_at.desc()).all()
    children = ChildProfile.query.filter_by(parent_id=parent_id).order_by(ChildProfile.created_at.asc()).all()
    total = len(histories)
    restricted = (
        len([item for item in histories if item.is_restricted])
        + len([item for item in activities if item.is_restricted])
        + len([item for item in safe_results if item.is_restricted])
    )
    safe_searches = len([item for item in safe_results if not item.is_restricted])
    screen_time_hours = _estimate_screen_time_hours(histories, activities)
    screen_time_by_child = _screen_time_by_child(histories, activities)
    safe_score = 100 if (total + len(activities)) == 0 else round((((total + len(activities)) - restricted) / max((total + len(activities)), 1)) * 100, 2)
    ai_summary = build_parent_ai_insights(
        parent_id,
        children,
        histories,
        activities,
        alerts,
        safe_results,
        screen_time_by_child,
    )

    report = Report.query.filter_by(parent_id=parent_id, report_type="summary").first()
    breakdown = summarize_week(histories, activities)
    payload = {
        "weekly_breakdown": breakdown,
        "monthly_summary": {
            "sessions": total,
            "restricted_attempts": restricted,
            "activities_logged": len(activities),
            "safe_searches": safe_searches,
            "notifications_sent": len(notifications),
            "ml_predictions": len(ml_predictions),
            "ml_unsafe_predictions": len([item for item in ml_predictions if item.final_label == "unsafe"]),
            "behavior_anomalies": len([item for item in ml_predictions if item.anomaly_detected]),
        },
        "safe_sites": DEFAULT_SAFE_RESULTS,
        "ai_summary": ai_summary,
    }

    if report is None:
        report = Report(parent_id=parent_id, report_type="summary")
        db.session.add(report)

    report.week_label = "Current Week"
    report.month_label = _as_local_time(_utc_now()).strftime("%B %Y")
    report.screen_time_hours = screen_time_hours
    report.restricted_attempts_count = restricted
    report.safe_browsing_score = safe_score
    report.summary_json = payload


def summarize_week(histories, activities):
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    summary = {day: {"day": day, "safe": 0, "restricted": 0} for day in day_labels}
    for item in histories + activities:
        event_time = getattr(item, "search_time", None) or getattr(item, "occurred_at", None) or item.created_at
        label = _as_local_time(event_time).strftime("%a")
        if label not in summary:
            continue
        if item.is_restricted:
            summary[label]["restricted"] += 1
        else:
            summary[label]["safe"] += 1
    return [summary[day] for day in day_labels]


def build_dashboard_payload(parent_id: int):
    _ensure_demo_child(parent_id)
    _seed_demo_monitoring_data(parent_id)
    histories = BrowsingHistory.query.filter_by(parent_id=parent_id).order_by(BrowsingHistory.created_at.desc()).all()
    alerts = Alert.query.filter_by(parent_id=parent_id).order_by(Alert.created_at.desc()).all()
    notifications = NotificationLog.query.filter_by(parent_id=parent_id).order_by(NotificationLog.created_at.desc()).all()
    ml_predictions = MlPredictionLog.query.filter_by(parent_id=parent_id).order_by(MlPredictionLog.created_at.desc()).all()
    safe_results = SafeSearchResult.query.filter_by(parent_id=parent_id).order_by(SafeSearchResult.created_at.desc()).all()
    activities = ActivityLog.query.filter_by(parent_id=parent_id).order_by(ActivityLog.created_at.desc()).all()
    children = ChildProfile.query.filter_by(parent_id=parent_id).order_by(ChildProfile.created_at.desc()).all()
    report = Report.query.filter_by(parent_id=parent_id, report_type="summary").first()

    if report is None:
        recalculate_reports(parent_id)
        report = Report.query.filter_by(parent_id=parent_id, report_type="summary").first()

    summary = report.summary_json or {}
    total_events = len(histories) + len(activities)
    restricted = len([item for item in histories if item.is_restricted]) + len([item for item in activities if item.is_restricted])
    safe_searches = len([item for item in safe_results if not item.is_restricted])
    ai_summary = summary.get("ai_summary")
    if not ai_summary:
        ai_summary = build_parent_ai_insights(
            parent_id,
            children,
            histories,
            activities,
            alerts,
            safe_results,
            _screen_time_by_child(histories, activities),
        )

    return {
        "parent": {
            "id": parent_id,
        },
        "demo_child": _demo_child_payload(parent_id),
        "metrics": {
            "screen_time_hours": report.screen_time_hours if report else 0,
            "restricted_attempts": report.restricted_attempts_count if report else 0,
            "safe_browsing_score": report.safe_browsing_score if report else 100,
            "total_events": total_events,
            "safe_searches": safe_searches,
            "unsafe_searches": restricted,
            "notifications_sent": len(notifications),
            "ml_predictions": len(ml_predictions),
            "ml_unsafe_predictions": len([item for item in ml_predictions if item.final_label == "unsafe"]),
            "behavior_anomalies": len([item for item in ml_predictions if item.anomaly_detected]),
            "alerts_open": len([alert for alert in alerts if alert.status == "open"]),
            "restricted_ratio": round((restricted / max(total_events, 1)) * 100, 1),
        },
        "weekly_breakdown": summary.get("weekly_breakdown", summarize_week(histories, activities)),
        "monthly_summary": summary.get("monthly_summary", {}),
        "ai_summary": ai_summary,
        "safe_sites": summary.get("safe_sites", DEFAULT_SAFE_RESULTS),
        "ml_predictions": [
            {
                "id": item.id,
                "input_text": item.input_text,
                "child_name": item.child.child_name if item.child else None,
                "rule_based_label": item.rule_based_label,
                "ml_label": item.ml_label,
                "final_label": item.final_label,
                "confidence_score": item.confidence_score,
                "anomaly_detected": item.anomaly_detected,
                "anomaly_score": item.anomaly_score,
                "created_at": item.created_at.replace(tzinfo=timezone.utc).isoformat() if item.created_at.tzinfo is None else item.created_at.astimezone(timezone.utc).isoformat(),
            }
            for item in ml_predictions[:12]
        ],
        "safe_results": [
            {
                "id": item.id,
                "search_query": item.search_query,
                "search_topic": item.search_topic,
                "is_restricted": item.is_restricted,
                "recommended_sites": item.recommended_sites,
                "blocked_reason": item.blocked_reason,
                "child_name": item.child.child_name if item.child else None,
                "created_at": item.created_at.replace(tzinfo=timezone.utc).isoformat() if item.created_at.tzinfo is None else item.created_at.astimezone(timezone.utc).isoformat(),
            }
            for item in safe_results[:10]
        ],
    }


def _ensure_demo_child(parent_id: int):
    existing = ChildProfile.query.filter_by(parent_id=parent_id).order_by(ChildProfile.created_at.desc()).first()
    if existing is not None:
        return existing

    parent = ParentUser.query.get(parent_id)
    if parent is None:
        return None

    child = ChildProfile(
        parent_id=parent.id,
        child_name=f"{parent.parent_name}'s Child",
        child_username=f"child{parent.id}_demo",
        age=12,
        gender="Prefer not to say",
        grade="Grade 7",
        school_name="Digital Guardian Demo School",
        parent_contact=parent.phone_number or parent.email,
        device_name="Family Tablet",
        screen_time_limit_hours=2.0,
        notes="Auto-generated demo child profile for project walkthroughs.",
    )
    child.set_password(f"DG-{parent.id}123")
    db.session.add(child)
    db.session.commit()
    return child


def _demo_child_payload(parent_id: int):
    child = ChildProfile.query.filter_by(parent_id=parent_id).order_by(ChildProfile.created_at.desc()).first()
    if child is None:
        child = _ensure_demo_child(parent_id)
    if child is None:
        return None
    if not child.notes or "Auto-generated demo" not in child.notes:
        return None
    return {
        "id": child.id,
        "child_name": child.child_name,
        "child_username": child.child_username,
        "password": f"DG-{parent_id}123",
    }


def _seed_demo_monitoring_data(parent_id: int):
    child = _ensure_demo_child(parent_id)
    if child is None:
        return

    histories_exist = BrowsingHistory.query.filter_by(parent_id=parent_id).first() is not None
    activities_exist = ActivityLog.query.filter_by(parent_id=parent_id).first() is not None

    seeded_items = []
    if not histories_exist:
        seeded_items.append(
            BrowsingHistory(
                parent_id=parent_id,
                child_id=child.id,
                search_query="games",
                site_url="https://www.kiddle.co/s.php?q=games",
                device_name=child.device_name,
                activity_type="browser_search",
                matched_keyword=None,
                matched_category=None,
                is_restricted=False,
            )
        )
    if not activities_exist:
        seeded_items.append(
            ActivityLog(
                parent_id=parent_id,
                child_id=child.id,
                event_type="app_open",
                app_name="YouTube Kids",
                target_name="YouTube Kids",
                target_url="app://YouTube Kids",
                details="Starter activity created for the dashboard demo state.",
                is_restricted=False,
            )
        )

    if seeded_items:
        db.session.add_all(seeded_items)
        db.session.commit()
