"""
Community-chatt - alla inloggade konton kan skriva och se allas
meddelanden i ett enda gemensamt, publikt flöde. Enkelt och append-only:
inget stöd för att redigera eller ta bort enskilda meddelanden (samma
avgränsning som t.ex. historiken i history_store.py).

Sparas i Upstash Redis när UPSTASH_REDIS_REST_URL/-TOKEN är satta, annars
i en lokal JSON-fil (data/community.json) - se remote_store.py.
"""

import json
import os
import time
import uuid

import remote_store

_PATH = os.path.join(os.path.dirname(__file__), "data", "community.json")
_REDIS_KEY = "aktiebetyg:community"

_MAX_MESSAGE_LENGTH = 500
# Begränsar hur mycket historik som sparas/skickas - en enkel chatt behöver
# inte oändlig historik, och håller Redis-posten/svaret litet.
_MAX_STORED = 200


def _load():
    if remote_store.enabled():
        return remote_store.get_json(_REDIS_KEY, [])
    if not os.path.exists(_PATH):
        return []
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save(messages):
    if remote_store.enabled():
        remote_store.set_json(_REDIS_KEY, messages)
        return
    os.makedirs(os.path.dirname(_PATH), exist_ok=True)
    with open(_PATH, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def list_messages(limit=100):
    """De `limit` senaste meddelandena, äldst först (redo att skrivas ut
    i den ordningen direkt)."""
    return _load()[-limit:]


def post_message(username, text):
    """Lägger till ett meddelande från `username`. Kastar ValueError
    (svensk text) om texten är tom eller för lång."""
    if not username:
        raise ValueError("Du måste vara inloggad för att skriva i Community.")
    text = (text or "").strip()
    if not text:
        raise ValueError("Meddelandet kan inte vara tomt.")
    if len(text) > _MAX_MESSAGE_LENGTH:
        raise ValueError(f"Meddelandet får vara högst {_MAX_MESSAGE_LENGTH} tecken.")

    messages = _load()
    message = {
        "id": uuid.uuid4().hex,
        "username": username,
        "text": text,
        "created_at": time.time(),
    }
    messages.append(message)
    if len(messages) > _MAX_STORED:
        messages = messages[-_MAX_STORED:]
    _save(messages)
    return message
