"""
Delat stjärnbetyg (1-5) på betygsskalor - både de tre inbyggda (549L-
skalorna, nycklade på "growth"/"stability"/"default") och egna sparade
skalor (nycklade på deras uuid, samma id som scales_store.py använder).

Sparas i Upstash Redis när UPSTASH_REDIS_REST_URL/-TOKEN är satta (så att
betygen inte försvinner när Render-tjänsten somnar/startar om), annars i
en lokal JSON-fil (data/scale_ratings.json) - se remote_store.py.

Lagras som {scale_id: {username: stars}} - ETT betyg per inloggad
användare och skala. Sätter du ett nytt betyg på en skala du redan
betygsatt ersätts ditt gamla, du kan alltså inte rösta flera gånger för
att dra snittet åt ett håll (kräver inloggning, se users_store.py/
app.py). Genomsnittet räknas ut vid läsning.
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
    if not entry:
        return {"average": None, "count": 0}
    values = list(entry.values())
    return {"average": sum(values) / len(values), "count": len(values)}


def get_all_ratings():
    """{scale_id: {"average": float | None, "count": int}} för alla
    skalor som fått minst ett betyg."""
    ratings = _load()
    return {scale_id: _summarize(entry) for scale_id, entry in ratings.items()}


def get_user_rating(scale_id, username):
    """Det betyg (1-5) `username` redan satt på `scale_id`, eller None."""
    return _load().get(scale_id, {}).get(username)


def rate_scale(scale_id, username, stars):
    """Sätter/ersätter `username`s betyg (1-5 stjärnor) på en skala och
    returnerar det uppdaterade genomsnittet. Sätter flera olika personer
    olika betyg blir resultatet snittet av alla - t.ex. 5 + 3 ger 4.0."""
    if not username:
        raise ValueError("Du måste vara inloggad för att betygsätta.")
    try:
        stars = float(stars)
    except (TypeError, ValueError):
        raise ValueError("Betyget måste vara ett tal mellan 1 och 5.")
    if not (1 <= stars <= 5):
        raise ValueError("Betyget måste vara mellan 1 och 5 stjärnor.")

    ratings = _load()
    entry = ratings.setdefault(scale_id, {})
    entry[username] = stars
    _save(ratings)
    return _summarize(entry)


def delete_rating(scale_id):
    """Städar bort alla betyg när skalan de hör till tas bort."""
    ratings = _load()
    if scale_id in ratings:
        del ratings[scale_id]
        _save(ratings)
