from __future__ import annotations

from urllib.parse import quote_plus

from ..models import RestrictedKeyword
from .ml_service import predict_query


SAFE_SEARCH_LIBRARY = {
    "games": [
        {"name": "Coolmath Games", "url": "https://www.coolmathgames.com", "description": "Logic, puzzle, and strategy games for kids."},
        {"name": "PBS Kids Games", "url": "https://pbskids.org/games", "description": "Educational games with learning-focused play."},
        {"name": "National Geographic Kids Games", "url": "https://kids.nationalgeographic.com/games", "description": "Animal, science, and exploration games."},
    ],
    "movies": [
        {"name": "Common Sense Media", "url": "https://www.commonsensemedia.org/movie-reviews", "description": "Family-friendly movie reviews and age guidance."},
        {"name": "Disney Family Movies", "url": "https://movies.disney.com/", "description": "Kid-safe family movie content and trailers."},
        {"name": "PBS Kids Videos", "url": "https://pbskids.org/video/", "description": "Educational videos and safe kids entertainment."},
    ],
    "cartoons": [
        {"name": "PBS Kids Video", "url": "https://pbskids.org/video/", "description": "Cartoons and learning videos for children."},
        {"name": "Nick Jr.", "url": "https://www.nickjr.com/", "description": "Preschool cartoons and activities."},
        {"name": "Kids Learning Tube", "url": "https://www.youtube.com/@KidsLearningTube", "description": "Animated educational content."},
    ],
    "drawing": [
        {"name": "Art for Kids Hub", "url": "https://www.artforkidshub.com/", "description": "Drawing tutorials for kids and beginners."},
        {"name": "Crayola", "url": "https://www.crayola.com/for-kids/", "description": "Creative drawing ideas, printables, and activities."},
        {"name": "Tate Kids Art", "url": "https://www.tate.org.uk/kids", "description": "Art inspiration and drawing ideas for children."},
    ],
    "reading": [
        {"name": "Storyline Online", "url": "https://storylineonline.net/", "description": "Read-aloud stories by actors and educators."},
        {"name": "Epic!", "url": "https://www.getepic.com/", "description": "Digital reading library for kids."},
        {"name": "Oxford Owl", "url": "https://www.oxfordowl.co.uk/", "description": "Free books and guided reading resources."},
    ],
    "coding": [
        {"name": "Code.org", "url": "https://code.org/", "description": "Beginner-friendly coding lessons for students."},
        {"name": "Scratch", "url": "https://scratch.mit.edu/", "description": "Creative coding with safe community learning."},
        {"name": "Khan Academy", "url": "https://www.khanacademy.org/", "description": "Structured learning in math, coding, and science."},
    ],
    "science": [
        {"name": "National Geographic Kids", "url": "https://kids.nationalgeographic.com/", "description": "Safe science, animals, and nature content."},
        {"name": "NASA Kids Club", "url": "https://www.nasa.gov/kidsclub/", "description": "Space learning content for children."},
        {"name": "Smithsonian Kids", "url": "https://www.si.edu/kids", "description": "Museum-backed educational discovery content."},
    ],
    "music": [
        {"name": "Sesame Street", "url": "https://www.sesamestreet.org/", "description": "Sing-alongs and learning songs for kids."},
        {"name": "Kids Bop", "url": "https://kidzbop.com/", "description": "Family-friendly music content."},
        {"name": "PBS Kids Music", "url": "https://pbskids.org/music", "description": "Music learning for young children."},
    ],
    "sports": [
        {"name": "GoNoodle", "url": "https://www.gonoodle.com/", "description": "Movement and active play videos for kids."},
        {"name": "Khan Academy Wellness", "url": "https://www.khanacademy.org/", "description": "Educational wellness and movement resources."},
        {"name": "National Geographic Kids", "url": "https://kids.nationalgeographic.com/", "description": "Kid-safe sports and activity content."},
    ],
}

DEFAULT_SAFE_RESULTS = [
    {"name": "Kiddle", "url": "https://www.kiddle.co/", "description": "Kid-friendly safe search results."},
    {"name": "Common Sense Media", "url": "https://www.commonsensemedia.org/", "description": "Age ratings and safe browsing guidance."},
    {"name": "National Geographic Kids", "url": "https://kids.nationalgeographic.com/", "description": "Educational and age-appropriate discovery content."},
]


def normalize_query(text: str) -> str:
    return (text or "").strip().lower()


def search_options(query: str) -> list[dict]:
    encoded = quote_plus((query or "").strip())
    return [
        {"name": "Kiddle (Kid Safe Search)", "url": f"https://www.kiddle.co/s.php?q={encoded}", "description": "Kid-focused safe search for general browsing."},
        {"name": "Google SafeSearch", "url": f"https://www.google.com/search?q={encoded}&safe=active", "description": "General search with safe mode enabled."},
        {"name": "Bing SafeSearch", "url": f"https://www.bing.com/search?q={encoded}&adlt=strict", "description": "Strict safe search filtering option."},
        {"name": "YouTube Kids Topics", "url": f"https://www.youtubekids.com/search?q={encoded}", "description": "Video-focused content for children."},
    ]


def topic_sites(normalized: str) -> tuple[str | None, list[dict]]:
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
    }
    for topic, aliases in topic_aliases.items():
        if any(alias in normalized for alias in aliases):
            return topic, SAFE_SEARCH_LIBRARY[topic]
    return None, DEFAULT_SAFE_RESULTS


def classify_hybrid_text(text: str) -> dict:
    normalized = normalize_query(text)
    keyword_match = None
    for keyword in RestrictedKeyword.query.filter_by(active=True).all():
        if keyword.keyword.lower() in normalized:
            keyword_match = keyword
            break

    topic, recommendation_sites = topic_sites(normalized)
    ml_prediction = predict_query(text)
    rule_based_label = "unsafe" if keyword_match else "safe"
    final_label = "unsafe" if rule_based_label == "unsafe" or ml_prediction.label == "unsafe" else "safe"

    decision_reason = []
    if keyword_match:
        decision_reason.append(f"Rule engine matched '{keyword_match.keyword}'")
    if ml_prediction.label == "unsafe":
        decision_reason.append(f"ML model flagged unsafe with {round(ml_prediction.confidence * 100, 1)}% confidence")
    if not decision_reason:
        decision_reason.append("Both rule engine and ML model marked the query as safe")

    return {
        "normalized": normalized,
        "keyword": keyword_match.keyword if keyword_match else None,
        "category": keyword_match.category if keyword_match else ("ml-detected risk" if ml_prediction.label == "unsafe" else None),
        "severity": keyword_match.severity if keyword_match else ("high" if ml_prediction.label == "unsafe" else None),
        "rule_based_label": rule_based_label,
        "ml_label": ml_prediction.label,
        "ml_confidence": ml_prediction.confidence,
        "unsafe_probability": ml_prediction.unsafe_probability,
        "safe_probability": ml_prediction.safe_probability,
        "model_name": ml_prediction.model_name,
        "model_accuracy": ml_prediction.accuracy,
        "top_terms": ml_prediction.top_terms,
        "is_restricted": final_label == "unsafe",
        "final_label": final_label,
        "recommended_sites": recommendation_sites,
        "search_topic": topic,
        "search_options": search_options(text),
        "decision_reason": decision_reason,
    }
