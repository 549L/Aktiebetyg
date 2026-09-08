"""
Delad hjälpmodul för att låta history_store.py/scales_store.py/
ratings_store.py spara sin data i Upstash Redis (ett gratis, riktigt
beständigt nyckel/värde-lager) istället för bara en lokal JSON-fil.

Behövs eftersom Renders gratisnivå har en helt flyktig disk - lokalt
sparad data (sökhistorik, egna betygsskalor, stjärnbetyg) försvinner inte
bara vid omdeploy utan varje gång tjänsten somnar och väcks igen (efter
~15 min inaktivitet, vilket händer ofta).

Sätts miljövariablerna UPSTASH_REDIS_REST_URL/UPSTASH_REDIS_REST_TOKEN
(på Render) används Upstash. Är de OSATTA (lokal utveckling) returnerar
enabled() False och varje store-modul faller tillbaka på sin lokala
JSON-fil precis som innan - lokal körning kräver alltså ingen
Upstash-uppkoppling alls.
"""

import json
import os

from curl_cffi import requests as creq

_REST_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
_REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")


def enabled():
    return bool(_REST_URL and _REST_TOKEN)


def _headers():
    return {"Authorization": f"Bearer {_REST_TOKEN}"}


def get_json(key, default):
    """Hämtar och avserialiserar ett JSON-värde. Returnerar `default` om
    nyckeln saknas, Upstash inte är konfigurerat, eller anropet misslyckas
    - en tillfällig nätverksstrul ska inte krascha sidan, bara ge tomt."""
    if not enabled():
        return default
    try:
        resp = creq.get(f"{_REST_URL}/get/{key}", headers=_headers(), timeout=10)
        raw = resp.json().get("result")
        return json.loads(raw) if raw is not None else default
    except Exception:
        return default


def set_json(key, value):
    """Serialiserar och sparar ett JSON-värde. Gör ingenting om Upstash
    inte är konfigurerat (då sparar anropande modul lokalt istället)."""
    if not enabled():
        return
    try:
        creq.post(f"{_REST_URL}/set/{key}", headers=_headers(), data=json.dumps(value), timeout=10)
    except Exception:
        pass
