"""
Minimalt användarkonto-system - bara användarnamn + lösenord, ingen
e-post/verifiering. Enda syftet är att kunna knyta ett stjärnbetyg på en
betygsskala till en person, så samma person inte kan rösta om och om
igen (se ratings_store.py).

Lösenord lagras ALDRIG i klartext - bara en saltad hash via Werkzeug
(som redan följer med Flask, inget nytt beroende).

Sparas i Upstash Redis när UPSTASH_REDIS_REST_URL/-TOKEN är satta,
annars i en lokal JSON-fil (data/users.json) - se remote_store.py.

Ett admin-konto ("549L") skapas automatiskt första gången modulen
används, om det inte redan finns.
"""

import json
import os
import time

from werkzeug.security import check_password_hash, generate_password_hash

import remote_store

_USERS_PATH = os.path.join(os.path.dirname(__file__), "data", "users.json")
_REDIS_KEY = "aktiebetyg:users"

_ADMIN_USERNAME = "549L"
_ADMIN_PASSWORD = "1"

# Profilbilder lagras som en data-URL direkt på kontot (samma Redis-post) -
# ingen separat filuppladdning/blob-lagring behövs. Bilden skalas ned och
# komprimeras till JPEG i webbläsaren innan den skickas hit, så gränsen
# nedan bara skyddar mot en orimligt stor eller manipulerad begäran.
_MAX_AVATAR_LENGTH = 300_000
_ALLOWED_AVATAR_PREFIXES = ("data:image/jpeg;base64,", "data:image/png;base64,", "data:image/webp;base64,")


def _load():
    if remote_store.enabled():
        return remote_store.get_json(_REDIS_KEY, {})
    if not os.path.exists(_USERS_PATH):
        return {}
    try:
        with open(_USERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(users):
    if remote_store.enabled():
        remote_store.set_json(_REDIS_KEY, users)
        return
    os.makedirs(os.path.dirname(_USERS_PATH), exist_ok=True)
    with open(_USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _ensure_admin_seeded():
    users = _load()
    if _ADMIN_USERNAME not in users:
        users[_ADMIN_USERNAME] = {
            "password_hash": generate_password_hash(_ADMIN_PASSWORD),
            "is_admin": True,
            "created_at": time.time(),
        }
        _save(users)


def create_user(username, password):
    """Skapar ett nytt konto. Kastar ValueError (svensk text) om
    användarnamnet är upptaget eller fälten är ogiltiga."""
    username = (username or "").strip()
    if not username:
        raise ValueError("Ange ett användarnamn.")
    if not password:
        raise ValueError("Ange ett lösenord.")

    _ensure_admin_seeded()
    users = _load()
    if username in users:
        raise ValueError("Användarnamnet är upptaget.")

    users[username] = {
        "password_hash": generate_password_hash(password),
        "is_admin": False,
        "created_at": time.time(),
    }
    _save(users)
    return {"username": username, "is_admin": False}


def verify_login(username, password):
    """Returnerar {"username", "is_admin"} vid lyckad inloggning, annars
    None. Kastar aldrig - fel användarnamn/lösenord ska bara ge None så
    anroparen kan visa ett generellt felmeddelande."""
    _ensure_admin_seeded()
    username = (username or "").strip()
    users = _load()
    account = users.get(username)
    if not account or not check_password_hash(account["password_hash"], password or ""):
        return None
    return {"username": username, "is_admin": account.get("is_admin", False), "avatar": account.get("avatar")}


def get_user(username):
    _ensure_admin_seeded()
    account = _load().get(username)
    if not account:
        return None
    return {
        "username": username,
        "is_admin": account.get("is_admin", False),
        "created_at": account.get("created_at"),
        "avatar": account.get("avatar"),
    }


def list_users():
    """Alla konton (utan lösenordshash) - underlag för användarsökningen."""
    _ensure_admin_seeded()
    users = _load()
    return [
        {
            "username": name,
            "is_admin": account.get("is_admin", False),
            "created_at": account.get("created_at"),
            "avatar": account.get("avatar"),
        }
        for name, account in users.items()
    ]


def set_avatar(username, data_url):
    """Sätter `username`s profilbild till `data_url` (en data:image/...
    base64-URL, redan nedskalad/komprimerad av klienten). Kastar ValueError
    (svensk text) om värdet inte ser ut som en bild eller är för stort."""
    if not isinstance(data_url, str) or not data_url.startswith(_ALLOWED_AVATAR_PREFIXES):
        raise ValueError("Profilbilden måste vara en PNG-, JPEG- eller WEBP-bild.")
    if len(data_url) > _MAX_AVATAR_LENGTH:
        raise ValueError("Profilbilden är för stor - välj en mindre bild.")

    users = _load()
    if username not in users:
        raise ValueError("Användaren hittades inte.")
    users[username]["avatar"] = data_url
    _save(users)
    return data_url


def remove_avatar(username):
    users = _load()
    if username in users:
        users[username]["avatar"] = None
        _save(users)
