"""
Historik över alla aktier som analyserats i appen. Används för listan
("Senast sökta") som visas under sökfältet.

Sparas i Upstash Redis när UPSTASH_REDIS_REST_URL/-TOKEN är satta (så att
historiken överlever att Render-tjänsten somnar/startar om), annars i en
lokal JSON-fil (data/history.json) - se remote_store.py.

Varje gång en aktie analyseras sparas/uppdateras dess senaste betyg här,
tillsammans med en tidsstämpel för när den senast söktes.
"""

import json
import os
import time

import remote_store
from config.industries import SECTOR_TRANSLATIONS

_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "data", "history.json")
_REDIS_KEY = "aktiebetyg:history"


def _load():
    if remote_store.enabled():
        return remote_store.get_json(_REDIS_KEY, {})
    if not os.path.exists(_HISTORY_PATH):
        return {}
    try:
        with open(_HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(history):
    if remote_store.enabled():
        remote_store.set_json(_REDIS_KEY, history)
        return
    os.makedirs(os.path.dirname(_HISTORY_PATH), exist_ok=True)
    with open(_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def record_result(result):
    """Sparar/uppdaterar den senaste analysen av en aktie i historiken."""
    if result.get("score") is None:
        return

    history = _load()
    history[result["ticker"]] = {
        "ticker": result["ticker"],
        "name": result["name"],
        "score": result["score"],
        "price": result.get("price"),
        "currency": result.get("currency", ""),
        "sector": result.get("sector", ""),
        "industry": result.get("industry", ""),
        "scale": result.get("scale", ""),
        "last_analyzed": time.time(),
    }
    _save(history)


def recent_n(n=10):
    """De n senast sökta/analyserade aktierna, senast sökt först. Söker du
    på samma aktie igen flyttas den fram till toppen igen (tidsstämpeln
    uppdateras varje gång, oavsett om betyget ändras)."""
    history = _load()
    entries = list(history.values())
    # Äldre poster (sparade innan tidsstämpeln fanns) saknar "last_analyzed"
    # - de hamnar sist istället för att krascha sorteringen.
    entries.sort(key=lambda e: e.get("last_analyzed", 0), reverse=True)
    return entries[:n]


def distinct_industries():
    """Alla sektorer (de nya, breda betygsskalorna - Teknik, Finans, Industri
    m.fl.) med antal analyserade bolag i varje - inklusive sektorer där du
    ännu inte analyserat något bolag (count 0), så hela listan alltid syns
    i branschrutan. Grupperas på sektor (inte den snävare "industry"-nivån)
    så att den matchar de sektorbaserade betygsskalorna i
    config/metrics.py."""
    history = _load()

    # Starta med samtliga sektorer på 0, så att branschrutan alltid visar
    # hela listan även för sektorer du inte analyserat något bolag i än.
    counts = {label: 0 for label in SECTOR_TRANSLATIONS.values()}

    for entry in history.values():
        label = entry.get("sector") or ""
        if not label:
            continue
        counts[label] = counts.get(label, 0) + 1

    industries = [{"label": label, "count": count} for label, count in counts.items()]
    industries.sort(key=lambda i: (-i["count"], i["label"]))
    return industries
