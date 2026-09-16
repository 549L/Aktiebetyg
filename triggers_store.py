"""
Håller "Triggers tidslinjen" vid alltid 20 aktiva triggers.

triggers_data.py:s TRIGGERS är bara en handplockad STARTuppsättning -
efter hand som verkligt datum passerar för en trigger skulle listan annars
sakta krympa mot noll. Den här modulen sparar den LIVE rosterna (20
platser, en per rank) och fyller på en utgången plats med nästa bolag ur
RESERVE_TRIGGERS varje gång get_triggers() anropas - alltså gott om
marginal mot kravet "inom 1 dag" (anropas vid varje sidladdning/
polling, som sker betydligt oftare än en gång per dygn).

Sparas i Upstash Redis när UPSTASH_REDIS_REST_URL/-TOKEN är satta (samma
mönster som history_store.py/scales_store.py), annars i en lokal JSON-fil
(data/triggers_state.json) - se remote_store.py.
"""

import json
import os
import time

import remote_store
from triggers_data import RESERVE_TRIGGERS, TRIGGERS

_STATE_PATH = os.path.join(os.path.dirname(__file__), "data", "triggers_state.json")
_REDIS_KEY = "aktiebetyg:triggers_state"

# Hur långt fram (i dagar) en nypåfylld trigger placeras. Sprids över
# andra halvan av det 60-dagarsfönster /api/triggers visar (se app.py) -
# långt nog fram för att inte genast gå ut igen, men fortfarande synlig.
_MIN_DAYS_AHEAD = 25
_MAX_DAYS_AHEAD = 54
_DAY = 86400


def _load():
    if remote_store.enabled():
        return remote_store.get_json(_REDIS_KEY, None)
    if not os.path.exists(_STATE_PATH):
        return None
    try:
        with open(_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save(state):
    if remote_store.enabled():
        remote_store.set_json(_REDIS_KEY, state)
        return
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    with open(_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _initial_state():
    return {
        "roster": {str(t["rank"]): dict(t) for t in TRIGGERS},
        # Index i RESERVE_TRIGGERS för nästa bolag som ska dras vid
        # påfyllning - går runt (modulo) om hela reservpoolen förbrukats.
        "reserve_cursor": 0,
    }


def _days_ahead_for(ticker, rank):
    """Deterministisk spridning inom [_MIN_DAYS_AHEAD, _MAX_DAYS_AHEAD] så
    flera samtidiga påfyllningar inte alla hamnar på exakt samma datum."""
    spread = _MAX_DAYS_AHEAD - _MIN_DAYS_AHEAD
    return _MIN_DAYS_AHEAD + (hash(ticker) + rank) % (spread + 1)


def _next_reserve_pick(state, taken_tickers):
    """Nästa bolag ur RESERVE_TRIGGERS (round-robin via reserve_cursor) som
    inte redan har en aktiv plats på tidslinjen. Går runt hela poolen högst
    en gång - finns inget ledigt bolag (osannolikt, poolen är större än
    antalet platser som brukar gå ut samtidigt) återanvänds nästa i tur
    ändå, hellre än att låta platsen stå tom."""
    pool = RESERVE_TRIGGERS
    cursor = state["reserve_cursor"]
    for i in range(len(pool)):
        idx = (cursor + i) % len(pool)
        candidate = pool[idx]
        if candidate[1] not in taken_tickers:
            state["reserve_cursor"] = (idx + 1) % len(pool)
            return candidate
    candidate = pool[cursor % len(pool)]
    state["reserve_cursor"] = (cursor + 1) % len(pool)
    return candidate


def get_triggers():
    """Returnerar den LIVE rosterna (alltid 20 poster) - fyller först på
    varje plats vars datum har passerat med nästa reservbolag, längre
    fram i tiden, och sparar undan den uppdaterade rosterna."""
    state = _load() or _initial_state()
    now = time.time()

    roster = state["roster"]
    taken_tickers = {t["ticker"] for t in roster.values()}
    changed = False

    for rank_key, trigger in roster.items():
        if trigger["date"] >= now:
            continue
        taken_tickers.discard(trigger["ticker"])
        rank = int(rank_key)
        company, ticker, description, impact_down, outcome_down, impact_up, outcome_up = _next_reserve_pick(
            state, taken_tickers
        )
        roster[rank_key] = {
            "rank": rank,
            "company": company,
            "ticker": ticker,
            "date": now + _days_ahead_for(ticker, rank) * _DAY,
            "description": description,
            "impact_down": impact_down,
            "outcome_down": outcome_down,
            "impact_up": impact_up,
            "outcome_up": outcome_up,
        }
        taken_tickers.add(ticker)
        changed = True

    if changed:
        _save(state)

    return list(roster.values())
