"""
Delat stjärnbetyg (1-5) på betygsskalor - både de tre inbyggda (549L-
skalorna, nycklade på "growth"/"stability"/"default") och egna sparade
skalor (nycklade på deras uuid, samma id som scales_store.py använder).

Sparas i Upstash Redis när UPSTASH_REDIS_REST_URL/-TOKEN är satta (så att
betygen inte försvinner när Render-tjänsten somnar/startar om), annars i
en lokal JSON-fil (data/scale_ratings.json) - se remote_store.py.

Lagras som summa + antal per skala (inte varje enskilt betyg för sig) -
genomsnittet räknas ut vid läsning.
"""

import json
import os

import remote_store

_RATINGS_PATH = os.path.join(os.path.dirname(__file__), "data", "scale_ratings.json")
_REDIS_KEY = "aktiebetyg:scale_ratings"


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
    if not entry or not entry.get("count"):
        return {"average": None, "count": 0}
    return {"average": entry["sum"] / entry["count"], "count": entry["count"]}


def get_all_ratings():
    """{scale_id: {"average": float | None, "count": int}} för alla
    skalor som fått minst ett betyg."""
    ratings = _load()
    return {scale_id: _summarize(entry) for scale_id, entry in ratings.items()}


def rate_scale(scale_id, stars):
    """Lägger till ett nytt betyg (1-5 stjärnor) och returnerar det
    uppdaterade genomsnittet. Om flera personer sätter olika betyg blir
    resultatet snittet av alla - t.ex. 5 + 3 ger 4.0."""
    try:
        stars = float(stars)
    except (TypeError, ValueError):
        raise ValueError("Betyget måste vara ett tal mellan 1 och 5.")
    if not (1 <= stars <= 5):
        raise ValueError("Betyget måste vara mellan 1 och 5 stjärnor.")

    ratings = _load()
    entry = ratings.setdefault(scale_id, {"sum": 0.0, "count": 0})
    entry["sum"] += stars
    entry["count"] += 1
    _save(ratings)
    return _summarize(entry)


def delete_rating(scale_id):
    """Städar bort ett betyg när skalan den hör till tas bort."""
    ratings = _load()
    if scale_id in ratings:
        del ratings[scale_id]
        _save(ratings)
