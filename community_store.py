"""
Community-chattrum - inloggade konton kan skapa egna namngivna chattrum
som alla andra ser och kan skriva i. Ett offentligt "General"-rum finns
alltid (för vad som helst), och ett rum kan valfritt länkas till en
specifik aktieticker - då dyker chatten upp när man analyserar just den
aktien (se app.py:s /api/community/rooms?ticker=...).

Append-only: inget stöd för att redigera eller ta bort enskilda
meddelanden eller rum, samma enkla avgränsning som history_store.py.

Sparas i Upstash Redis när UPSTASH_REDIS_REST_URL/-TOKEN är satta, annars
i en lokal JSON-fil (data/community.json) - se remote_store.py.
"""

import json
import os
import time
import uuid

import remote_store

_PATH = os.path.join(os.path.dirname(__file__), "data", "community.json")
_REDIS_KEY = "aktiebetyg:community_rooms"

_GENERAL_ROOM_ID = "general"
_MAX_MESSAGE_LENGTH = 500
_MAX_NAME_LENGTH = 60
# Begränsar hur mycket historik som sparas/skickas per rum - en enkel
# chatt behöver inte oändlig historik, och håller Redis-posten liten.
_MAX_MESSAGES_PER_ROOM = 200


def _load():
    if remote_store.enabled():
        rooms = remote_store.get_json(_REDIS_KEY, {})
    elif os.path.exists(_PATH):
        try:
            with open(_PATH, "r", encoding="utf-8") as f:
                rooms = json.load(f)
        except (json.JSONDecodeError, OSError):
            rooms = {}
    else:
        rooms = {}

    # Skydd mot den gamla, enklare chatt-lagringen (en platt lista med
    # meddelanden, innan flera namngivna rum fanns) - annars kraschar
    # koden nedan på att indexera en lista med en textnyckel.
    if not isinstance(rooms, dict):
        rooms = {}

    if _GENERAL_ROOM_ID not in rooms:
        rooms[_GENERAL_ROOM_ID] = {
            "id": _GENERAL_ROOM_ID,
            "name": "General",
            "ticker": None,
            "created_by": None,
            "created_at": time.time(),
            "messages": [],
        }
        _save(rooms)
    return rooms


def _save(rooms):
    if remote_store.enabled():
        remote_store.set_json(_REDIS_KEY, rooms)
        return
    os.makedirs(os.path.dirname(_PATH), exist_ok=True)
    with open(_PATH, "w", encoding="utf-8") as f:
        json.dump(rooms, f, ensure_ascii=False, indent=2)


def _room_summary(room):
    """Rummets metadata utan meddelandeinnehåll - underlag för chattlistan
    och ticker-kopplingen, håller svaren små."""
    messages = room.get("messages", [])
    last = messages[-1] if messages else None
    return {
        "id": room["id"],
        "name": room["name"],
        "ticker": room.get("ticker"),
        "created_by": room.get("created_by"),
        "created_at": room.get("created_at"),
        "message_count": len(messages),
        "last_message_at": last["created_at"] if last else room.get("created_at"),
    }


def list_rooms():
    """Alla chattrum (utan meddelanden) - General alltid överst, resten
    sorterade efter senaste aktivitet."""
    rooms = _load()
    general = _room_summary(rooms[_GENERAL_ROOM_ID])
    others = [_room_summary(r) for room_id, r in rooms.items() if room_id != _GENERAL_ROOM_ID]
    others.sort(key=lambda r: r["last_message_at"] or 0, reverse=True)
    return [general] + others


def find_rooms_by_ticker(ticker):
    """Chattrum länkade till en specifik ticker (för att visa vid analys
    av en aktie). Oftast 0 eller 1 träff, men flera stöds."""
    if not ticker:
        return []
    ticker = ticker.strip().upper()
    rooms = _load()
    matches = [_room_summary(r) for r in rooms.values() if (r.get("ticker") or "") == ticker]
    matches.sort(key=lambda r: r["last_message_at"] or 0, reverse=True)
    return matches


def get_room(room_id):
    """Fullständigt chattrum inklusive alla meddelanden, eller None."""
    return _load().get(room_id)


def create_room(name, created_by, ticker=None):
    """Skapar ett nytt chattrum. Kastar ValueError (svensk text) om namnet
    saknas/är för långt eller om ingen är inloggad."""
    name = (name or "").strip()
    if not created_by:
        raise ValueError("Du måste vara inloggad för att skapa en chatt.")
    if not name:
        raise ValueError("Ange ett namn på chatten.")
    if len(name) > _MAX_NAME_LENGTH:
        raise ValueError(f"Namnet får vara högst {_MAX_NAME_LENGTH} tecken.")

    ticker = (ticker or "").strip().upper() or None

    rooms = _load()
    room_id = uuid.uuid4().hex
    room = {
        "id": room_id,
        "name": name,
        "ticker": ticker,
        "created_by": created_by,
        "created_at": time.time(),
        "messages": [],
    }
    rooms[room_id] = room
    _save(rooms)
    return _room_summary(room)


def post_message(room_id, username, text):
    """Lägger till ett meddelande i rummet `room_id` från `username`.
    Kastar ValueError (svensk text) om rummet inte finns, texten är tom/för
    lång, eller ingen är inloggad."""
    if not username:
        raise ValueError("Du måste vara inloggad för att skriva i chatten.")
    text = (text or "").strip()
    if not text:
        raise ValueError("Meddelandet kan inte vara tomt.")
    if len(text) > _MAX_MESSAGE_LENGTH:
        raise ValueError(f"Meddelandet får vara högst {_MAX_MESSAGE_LENGTH} tecken.")

    rooms = _load()
    room = rooms.get(room_id)
    if room is None:
        raise ValueError("Chatten hittades inte.")

    message = {
        "id": uuid.uuid4().hex,
        "username": username,
        "text": text,
        "created_at": time.time(),
    }
    room.setdefault("messages", []).append(message)
    if len(room["messages"]) > _MAX_MESSAGES_PER_ROOM:
        room["messages"] = room["messages"][-_MAX_MESSAGES_PER_ROOM:]
    _save(rooms)
    return message
