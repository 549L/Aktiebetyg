"""
Minimal klient mot Yahoo Finances (inofficiella) quoteSummary-API.

Vi använder INTE yfinance-biblioteket, eftersom det drar in pandas som
en beroende - och på den här datorn blockerar Windows Smart App Control
pandas kompilerade DLL-fil (den är inte signerad på "Enterprise"-nivå).
Se README.md för mer detaljer.

Den här klienten gör samma sak som yfinances ".info" i grunden: hämtar
ett crumb + cookies, och slår sedan upp nyckeltal för en ticker som platt
JSON, utan att någonsin importera pandas.
"""

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from curl_cffi import requests as creq

from config.industries import translate_sector, translate_industry

# Yahoo Finance blockerar molnleverantörers IP-adresser (Render m.fl.) med
# 429/401-fel. Sätts miljövariabeln DATAIMPULSE_PROXY (t.ex.
# "http://användare:lösenord@gw.dataimpulse.com:823") routas alla anrop via
# en proxy istället, så det ser ut som vanlig hemtrafik för Yahoo. Lokalt
# (ingen miljövariabel satt) går anropen direkt, precis som innan.
_PROXY_URL = os.environ.get("DATAIMPULSE_PROXY")

_MODULES = "defaultKeyStatistics,financialData,summaryDetail,price,assetProfile"

# Yahoos chart-API tar "range" + "interval"-koder direkt, men de är kryptiska
# (t.ex. "5d"/"15m"). Vi mappar egna, tydliga tidsperiod-namn mot dem här -
# lägg till fler perioder här om du vill kunna välja andra tidsspann.
CHART_RANGES = {
    "1d": {"range": "1d", "interval": "5m"},
    "1w": {"range": "5d", "interval": "15m"},
    "1y": {"range": "1y", "interval": "1d"},
    "5y": {"range": "5y", "interval": "1wk"},
    "10y": {"range": "10y", "interval": "1mo"},
}

# Börskoder som (nästan) alltid är sekundära cross-listings/depåbevis av ett
# utländskt bolag, snarare än bolagets egna hemmabörs. Yahoos sökresultat
# blandar annars in dessa tillsammans med hemmabörsen - t.ex. dyker svenska
# Volvo upp under både Frankfurt, München och Düsseldorf. Lägg till/ta bort
# koder här om du märker att fel börser dyker upp, eller att en börs du vill
# se saknas.
_EXCLUDED_EXCHANGES = {
    "FRA", "DUS", "MUN", "STU", "GER", "BER", "HAM", "HAN",  # tyska regionala börser/Xetra-cross-listings
    "SAO", "BUE", "MEX",                                      # sydamerikanska depåbevis (BDR/ADR)
    "PNK", "PCX", "OTC",                                      # amerikanska OTC/Pink Sheets (ADR)
    "MIL",                                                    # Milano - i praktiken oftast cross-listing av utländska bolag
    "NEO",                                                    # NEO Canada - kanadensiska CDR:er (depåbevis)
}

# Namn där något av de här orden förekommer (oavsett skiljetecken runt
# omkring, t.ex. "MSFT01_DR" på Bangkokbörsen) är typiskt depåbevis snarare
# än en egen börsnotering, och filtreras bort oavsett vilken börs de ligger på.
_DEPOSITARY_RECEIPT_WORDS = {"ADR", "CDR", "BDR", "DRN", "DR"}


def _is_depositary_receipt(name: str) -> bool:
    tokens = re.split(r"[^A-Za-z]+", name.upper())
    return any(token in _DEPOSITARY_RECEIPT_WORDS for token in tokens if token)


def _new_session():
    """Skapar en helt ny session + crumb för varje anrop.

    Vi testade att återanvända en delad session mellan anrop (cachad på
    modulnivå), men det gjorde sökningen opålitlig när appen körs inne i
    Flasks request-hantering - samma fråga kunde ge tomt svar för en
    återanvänd session men lyckades direkt med en färsk. Kostnaden är två
    extra requests per anrop, men det är värt det för pålitligheten.
    """
    session = creq.Session(impersonate="chrome")
    if _PROXY_URL:
        session.proxies = {"http": _PROXY_URL, "https": _PROXY_URL}
    session.get("https://fc.yahoo.com", timeout=10)
    crumb = session.get(
        "https://query2.finance.yahoo.com/v1/test/getcrumb", timeout=10
    ).text
    return session, crumb


def _unwrap(value):
    """Yahoo returnerar de flesta tal som {"raw": x, "fmt": "..."}."""
    if isinstance(value, dict):
        return value.get("raw")
    return value


def _search_candidates(query: str, pool_size: int) -> list:
    """Hämtar och grundfiltrerar sökkandidater (rätt typ, ingen utländsk
    cross-listing/depåbevis, inga dubbletter) - utan att trunkera till en
    slutgiltig gräns. Delas av `search_symbols` och `search_by_industry`.
    """
    quotes = []
    for attempt in range(4):
        session, _ = _new_session()
        try:
            resp = session.get(
                "https://query1.finance.yahoo.com/v1/finance/search",
                params={"q": query, "quotesCount": pool_size, "newsCount": 0},
                timeout=10,
            )
            quotes = resp.json().get("quotes", []) if resp.status_code == 200 else []
        except Exception:
            quotes = []

        if quotes:
            break
        time.sleep(0.3)

    results = []
    seen_names = set()
    for quote in quotes:
        if quote.get("quoteType") not in ("EQUITY", "ETF"):
            continue
        if quote.get("exchange") in _EXCLUDED_EXCHANGES:
            continue
        symbol = quote.get("symbol")
        if not symbol:
            continue

        name = quote.get("shortname") or quote.get("longname") or symbol
        if _is_depositary_receipt(name):
            continue

        dedup_key = name.strip().lower()
        if dedup_key in seen_names:
            continue
        seen_names.add(dedup_key)

        results.append(
            {
                "symbol": symbol,
                "name": name,
                "exchange": quote.get("exchDisp") or quote.get("exchange") or "",
            }
        )

    return results


def search_symbols(query: str, limit: int = 8) -> list:
    """Slår upp ticker-symboler utifrån ett fritextnamn (t.ex. "Volvo" eller
    "Ericsson"), så att användaren inte måste veta den exakta Yahoo-tickern.
    Returnerar en lista med {"symbol", "name", "exchange"}.
    """
    # Hämta fler kandidater än vad vi tänker visa, eftersom en del kommer
    # filtreras bort som sekundära cross-listings i _search_candidates.
    candidates = _search_candidates(query, max(limit * 3, 15))
    return candidates[:limit]


def search_by_industry(query: str, industry: str, limit: int = 8) -> list:
    """Som `search_symbols`, men filtrerar dessutom bort alla träffar vars
    verkliga bransch (hämtad live per kandidat) inte matchar `industry`
    (eller dess sektor, om branschen inte gav träff). Eftersom det kräver
    ett extra API-anrop per kandidat hämtas dessa parallellt för att hålla
    nere väntetiden, men det är ändå långsammare än en vanlig sökning.
    """
    candidates = _search_candidates(query, 20)[:12]
    if not candidates:
        return []

    target = industry.strip().lower()

    def _matches(candidate):
        info = get_info(candidate["symbol"])
        if not info:
            return None
        sector = translate_sector(info.get("sector") or "")
        ind = translate_industry(info.get("industry") or "", info.get("sector") or "")
        if ind.strip().lower() == target or sector.strip().lower() == target:
            candidate_with_industry = dict(candidate, industry=ind)
            return candidate_with_industry
        return None

    matches = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_matches, c) for c in candidates]
        for future in as_completed(futures):
            result = future.result()
            if result:
                matches.append(result)

    # as_completed lämnar tillbaka resultat i den ordning de blir klara, inte
    # i sökrelevansordning - sortera tillbaka mot kandidatlistans ursprungsordning.
    order = {c["symbol"]: i for i, c in enumerate(candidates)}
    matches.sort(key=lambda m: order.get(m["symbol"], 0))

    return matches[:limit]


def get_info(ticker: str) -> dict:
    """Hämtar nyckeltal för en ticker som en platt dict, t.ex.
    {"trailingPE": 35.4, "returnOnEquity": 1.48, "longName": "Apple Inc.", ...}
    Returnerar {} om tickern inte hittas.
    """
    results = None
    for attempt in range(4):
        session, crumb = _new_session()
        try:
            resp = session.get(
                f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}",
                params={"modules": _MODULES, "crumb": crumb},
                timeout=10,
            )
            payload = resp.json().get("quoteSummary", {}) if resp.status_code == 200 else {}
            results = payload.get("result")
        except Exception:
            results = None

        if results:
            break
        time.sleep(0.3)

    if not results:
        return {}

    modules = results[0]
    flat = {}
    for module in modules.values():
        if isinstance(module, dict):
            for key, value in module.items():
                flat[key] = _unwrap(value)

    return flat


def get_chart_data(ticker: str, period: str = "1y") -> dict:
    """Hämtar historisk kursdata för en ticker. `period` är en av nycklarna
    i CHART_RANGES ("1d", "1w", "1y", "5y", "10y"). Returnerar
    {"points": [{"t": unix_sekunder, "close": pris}, ...], "currency": "USD"}
    eller {"points": [], "currency": ""} om inget hittas.
    """
    params = CHART_RANGES.get(period, CHART_RANGES["1y"])

    result = None
    for attempt in range(4):
        session, _ = _new_session()
        try:
            resp = session.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
                params={"range": params["range"], "interval": params["interval"]},
                timeout=10,
            )
            chart = resp.json().get("chart", {}) if resp.status_code == 200 else {}
            results = chart.get("result")
            result = results[0] if results else None
        except Exception:
            result = None

        if result:
            break
        time.sleep(0.3)

    if not result:
        return {"points": [], "currency": ""}

    timestamps = result.get("timestamp", [])
    closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
    points = [
        {"t": t, "close": c}
        for t, c in zip(timestamps, closes)
        if c is not None
    ]

    return {
        "points": points,
        "currency": result.get("meta", {}).get("currency", ""),
    }
