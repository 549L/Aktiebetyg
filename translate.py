"""
Enkel, gratis textöversättning via Googles inofficiella översättnings-API
(samma princip som yahoo_client.py använder för aktiedata - inget
API-nyckel behövs, men det är ett oofficiellt endpoint som i teorin kan
sluta fungera om Google ändrar det).

Används just nu för att översätta bolagens engelska verksamhetsbeskrivning
till svenska.
"""

import time

from curl_cffi import requests as creq


def translate_to_swedish(text: str) -> str:
    """Översätter engelsk text till svenska. Om översättningen misslyckas
    (nätverksfel, oväntat svar) returneras originaltexten oöversatt istället
    för att visa ett fel - en beskrivning på engelska är bättre än ingen alls."""
    if not text:
        return ""

    for attempt in range(4):
        try:
            session = creq.Session(impersonate="chrome")
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
                    return translated
        except Exception:
            pass
        time.sleep(0.3)

    return text


def _looks_like_text(segment: str) -> bool:
    return bool(segment) and len(segment.strip()) > 12 and any(c.isalpha() for c in segment)
