"""
Stjärnbetyg (1-5) på ANVÄNDARKONTON - skiljer sig från ratings_store.py
som betygsätter betygsskalor. Samma modell: ett betyg per inloggad person
och konto, du kan ändra ditt eget men inte rösta flera gånger.

Sparas i Upstash Redis när UPSTASH_REDIS_REST_URL/-TOKEN är satta, annars
i en lokal JSON-fil (data/user_ratings.json) - se remote_store.py.
"""

import json
import os

import remote_store

_RATINGS_PATH = os.path.join(os.path.dirname(__file__), "data", "user_ratings.json")
_REDIS_KEY = "aktiebetyg:user_ratings"


def _load():
    if remote_store.enabled():
        return remote_store.get_json(_REDIS_KEY, {})
    if not os.path.exists(_RATINGS_PATH):
        return {}
    try:
        with open(_RATINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(ratings):
    if remote_store.enabled():
        remote_store.set_json(_REDIS_KEY, ratings)
        return
    os.makedirs(os.path.dirname(_RATINGS_PATH), exist_ok=True)
    with open(_RATINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(ratings, f, ensure_ascii=False, indent=2)


def _summarize(entry):
    if not entry:
        return {"average": None, "count": 0}
    values = list(entry.values())
    return {"average": sum(values) / len(values), "count": len(values)}


def get_all_ratings():
    """{username: {"average": float | None, "count": int}} för alla
    konton som fått minst ett betyg."""
    ratings = _load()
    return {username: _summarize(entry) for username, entry in ratings.items()}


def get_user_rating(target_username, rater_username):
    return _load().get(target_username, {}).get(rater_username)


def rate_user(target_username, rater_username, stars):
    """Sätter/ersätter `rater_username`s betyg (1-5) på `target_username`s
    konto och returnerar det uppdaterade genomsnittet."""
    if not rater_username:
        raise ValueError("Du måste vara inloggad för att betygsätta.")
    try:
        stars = float(stars)
    except (TypeError, ValueError):
        raise ValueError("Betyget måste vara ett tal mellan 1 och 5.")
    if not (1 <= stars <= 5):
        raise ValueError("Betyget måste vara mellan 1 och 5 stjärnor.")

    ratings = _load()
    entry = ratings.setdefault(target_username, {})
    entry[rater_username] = stars
    _save(ratings)
    return _summarize(entry)
