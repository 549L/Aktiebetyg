"""
Bolagsspecifika tekniska signaler, byggda från aktiens EGEN kurshistorik -
till skillnad från t.ex. CNN:s marknadsbreda Fear & Greed-index (som visar
samma värde för alla bolag).

  - Fear & Greed (0-100): RSI (14 dagar) + position i 52-veckors-
    intervallet. Lågt värde = rädsla/översåld (kan vara ett köpläge), högt
    värde = girighet/överköpt (kan vara läge att avvakta).
  - MA200: hur mycket dagens pris avviker från sitt 200-dagars glidande
    medelvärde. Över MA200 = långsiktig uppåttrend (grönt), under MA200 =
    långsiktig nedåttrend (rött) - ett av de mest använda trendfiltren i
    teknisk analys.

Båda räknas ut från SAMMA kurshistorik (ett enda anrop till Yahoos
chart-API) via `get_stock_signals`, så en analys inte behöver hämta samma
data två gånger.
"""

from yahoo_client import get_chart_data


def _rsi(closes: list, period: int = 14):
    """Wilder-utjämnad RSI över hela serien, baserat på de senaste `period`
    prisförändringarna. Returnerar None om serien är för kort."""
    if len(closes) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _range_position(closes: list, current: float):
    """0 = vid årslägsta, 100 = vid årshögsta."""
    window = closes[-252:] if len(closes) > 252 else closes
    low = min(window)
    high = max(window)
    if high == low:
        return 50.0
    return (current - low) / (high - low) * 100.0


def _rating_from_score(score: float) -> str:
    if score < 25:
        return "extreme fear"
    if score < 45:
        return "fear"
    if score < 56:
        return "neutral"
    if score < 76:
        return "greed"
    return "extreme greed"


def _ma200_signal(closes: list, current: float):
    """Returnerar {"ma200": ..., "pct_vs_ma200": ...} eller None om det
    inte finns minst 200 dagars kurshistorik att räkna medelvärdet på."""
    if len(closes) < 200:
        return None
    ma200 = sum(closes[-200:]) / 200
    if ma200 == 0:
        return None
    return {"ma200": ma200, "pct_vs_ma200": (current - ma200) / ma200}


def get_stock_signals(ticker: str) -> dict:
    """Hämtar ett års kurshistorik EN gång och räknar ut både Fear & Greed
    och MA200-signalen från den. Returnerar {"fear_greed": {...} | None,
    "ma200": {...} | None, "chart": {...}}.

    "chart" är samma 1-års kursdata som redan hämtats här, vidarebefordrad
    så att /api/analyze kan skicka med den direkt i sitt svar - då slipper
    frontend göra ett till (identiskt) nätverksanrop till /api/chart bara
    för att rita startgrafen. Sparar särskilt mycket tid när anropen går via
    en proxy (se yahoo_client.py) där varje extra request kostar sekunder."""
    chart = get_chart_data(ticker, "1y")
    closes = [p["close"] for p in chart.get("points", [])]
    if len(closes) < 15:
        return {"fear_greed": None, "ma200": None, "chart": chart}

    current = closes[-1]

    fear_greed = None
    rsi = _rsi(closes)
    if rsi is not None:
        position = _range_position(closes, current)
        score = round((rsi + position) / 2)
        fear_greed = {"score": score, "rating": _rating_from_score(score)}

    ma200 = _ma200_signal(closes, current)

    return {"fear_greed": fear_greed, "ma200": ma200, "chart": chart}
