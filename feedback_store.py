"""
Feedback som besökare skickar in från rutan bredvid Triggers tidslinjen
på hemskärmen. En enkel brevlåda till adminkontot (549L) - INTE en
offentlig lista. /api/feedback GET kollar därför explicit i app.py att
den inloggade är admin, till skillnad från appens övriga GET-endpoints
som är öppna även för gäster (se _require_login i app.py).

Sparas i Upstash Redis när UPSTASH_REDIS_REST_URL/-TOKEN är satta, annars
i en lokal JSON-fil (data/feedback.json) - se remote_store.py, samma
mönster som history_store.py/scales_store.py.
"""

import json
import os
import time
import uuid

import remote_store

_FEEDBACK_PATH = os.path.join(os.path.dirname(__file__), "data", "feedback.json")
_REDIS_KEY = "aktiebetyg:feedback"
_MAX_LENGTH = 1000


def _load():
    if remote_store.enabled():
        return remote_store.get_json(_REDIS_KEY, [])
    if not os.path.exists(_FEEDBACK_PATH):
        return []
    try:
        with open(_FEEDBACK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save(entries):
    if remote_store.enabled():
        remote_store.set_json(_REDIS_KEY, entries)
        return
    os.makedirs(os.path.dirname(_FEEDBACK_PATH), exist_ok=True)
    with open(_FEEDBACK_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def add_feedback(text, username, category=None):
    """Kastar ValueError (svensk text, tänkt att visas direkt för
    användaren) om texten är tom eller orimligt lång. `category` är vilken
    av de tre ämnesknapparna (se FEEDBACK_QUICK_OPTIONS i app.js) som
    valdes innan förklaringen skrevs - sparas rått, oskickat/ogiltigt
    värde blir bara None, så cirkeldiagrammet i 549L:s profil (se
    /api/feedback i app.py) räknar det som "annat" istället för att
    krascha på en okänd kategori."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Skriv något innan du skickar.")
    if len(text) > _MAX_LENGTH:
        raise ValueError(f"Feedbacken får vara högst {_MAX_LENGTH} tecken.")

    entries = _load()
    entries.append({
        "id": uuid.uuid4().hex,
        "text": text,
        "category": (category or "").strip() or None,
        "username": username,
        "created_at": time.time(),
    })
    _save(entries)


def list_feedback():
    """Senast inskickad först."""
    return sorted(_load(), key=lambda e: e.get("created_at", 0), reverse=True)
