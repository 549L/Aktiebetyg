"""
Enkel, gratis textöversättning via Googles inofficiella översättnings-API
(samma princip som yahoo_client.py använder för aktiedata - inget
API-nyckel behövs, men det är ett oofficiellt endpoint som i teorin kan
sluta fungera om Google ändrar det).

Används just nu för att översätta bolagens engelska verksamhetsbeskrivning
till svenska.
"""

import os
import time
from collections import OrderedDict

from curl_cffi import requests as creq

# Se yahoo_client.py för varför den här finns.
_PROXY_URL = os.environ.get("DATAIMPULSE_PROXY")

# Cachar bara RIKTIGA översättningar i en timme - samma bolagsbeskrivning
# (t.ex. samma aktie analyserad igen, eller flera användare som tittar på
# samma populära bolag) slipper då göra om upp till 4 försök mot Google
# Translate. Medvetet en egen, enkel cache istället för ttl_cache.py:s
# generella dekorator: funktionen returnerar originaltexten OÖVERSATT som
# reserv om alla försök misslyckas, och det får ALDRIG cachas som om det
# vore en lyckad översättning - då skulle en tillfällig nätverksstrul kunna
# göra att en akties beskrivning visas oöversatt i upp till en timme efteråt.
_CACHE_TTL = 3600
_CACHE_MAX_ENTRIES = 500
_cache = OrderedDict()


def translate_to_swedish(text: str) -> str:
    """Översätter engelsk text till svenska. Om översättningen misslyckas
    (nätverksfel, oväntat svar) returneras originaltexten oöversatt istället
    för att visa ett fel - en beskrivning på engelska är bättre än ingen alls."""
    if not text:
        return ""

    cached = _cache.get(text)
    if cached is not None:
        cached_at, translated = cached
        if time.time() - cached_at < _CACHE_TTL:
            _cache.move_to_end(text)
            return translated

    for attempt in range(4):
        try:
            session = creq.Session(impersonate="chrome")
            if _PROXY_URL:
                session.proxies = {"http": _PROXY_URL, "https": _PROXY_URL}
            resp = session.get(
                "https://translate.googleapis.com/translate_a/single",
                params={"client": "gtx", "sl": "en", "tl": "sv", "dt": "t", "q": text},
                timeout=10,
            )
            if resp.status_code == 200:
                segments = resp.json()[0]
                # Ibland kommer enstaka segment tillbaka oöversatta (identiska
                # med originaltexten) - det ger en mening som blandar svenska
                # och engelska. Räknas som ett misslyckat försök, gör om.
                if any(seg[0] == seg[1] and _looks_like_text(seg[1]) for seg in segments):
                    time.sleep(0.3)
                    continue

                translated = "".join(seg[0] for seg in segments if seg[0])
                if translated:
                    _cache[text] = (time.time(), translated)
                    _cache.move_to_end(text)
                    while len(_cache) > _CACHE_MAX_ENTRIES:
                        _cache.popitem(last=False)
                    return translated
        except Exception:
            pass
        time.sleep(0.3)

    return text


def _looks_like_text(segment: str) -> bool:
    return bool(segment) and len(segment.strip()) > 12 and any(c.isalpha() for c in segment)
