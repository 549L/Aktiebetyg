"""
Betygsättningslogik. Läser nyckeltalen i config/metrics.py, hämtar data via
yfinance och räknar ut ett totalbetyg 1-100 samt positiva/negativa punkter.

Du behöver normalt inte ändra i den här filen - lägg istället till/ändra
nyckeltal i config/metrics.py.
"""

import concurrent.futures
import math
import re

from yahoo_client import get_info, search_symbols
from config.metrics import PROFILES, METRIC_STYLE
from config.industries import translate_sector, translate_industry
from translate import translate_to_swedish
from stock_sentiment import get_stock_signals

# Multiplikatorer för "Tillväxtbolag"/"Stabila bolag"-knapparna bredvid
# sökfältet. Byter INTE profil/skala (Teknik har fortfarande sin skala,
# Fastigheter sin osv.) - viktar bara om nyckeltalen INOM den redan valda
# profilen. Se METRIC_STYLE i config/metrics.py för vilka nyckeltal som är
# taggade "growth"/"stability" (otaggade = "neutral", samma vikt i båda
# vyerna - t.ex. Fear & Greed/MA200 som är tidpunktsmått, inte ett mått på
# vilken sorts bolag det är).
_VIEW_LABELS = {"growth": "Tillväxtvy", "stability": "Stabil vy"}
_STYLE_MULTIPLIERS = {
    "growth": {"growth": 2.0, "stability": 0.35, "neutral": 1.0},
    "stability": {"growth": 0.35, "stability": 2.0, "neutral": 1.0},
}


def _renormalize_weights(scoring_results):
    """Skalar om delbetygens vikter så att de summerar till 1.0 - annars
    visar tabellen bara den råa lagrade vikten, som inte stämmer med hur
    stor andel av totalbetyget nyckeltalet faktiskt utgör (t.ex. om ett
    nyckeltal saknar data och faller bort, eller i en egen skala med bara
    ett fåtal nyckeltal ihopräknat under 100%)."""
    total = sum(r["weight"] for r in scoring_results)
    if total > 0:
        for r in scoring_results:
            r["weight"] = r["weight"] / total
    return scoring_results


def _apply_view_style(scoring_results, view_style):
    """Viktar om delbetygens vikter utifrån vald vy (och normaliserar
    tillbaka till summa 1.0). Ändrar inget om view_style saknas/är okänd."""
    multipliers = _STYLE_MULTIPLIERS.get(view_style)
    if not multipliers or not scoring_results:
        return scoring_results

    for r in scoring_results:
        style = METRIC_STYLE.get(r["key"], "neutral")
        r["weight"] = r["weight"] * multipliers[style]

    return _renormalize_weights(scoring_results)


def _select_profile(sector: str, industry: str, profiles: dict = PROFILES) -> dict:
    """Väljer betygsskala utifrån bolagets bransch: exakt bransch (industry)
    slår sektor (sector), som i sin tur slår standardskalan. Se
    config/metrics.py för hur profilerna är uppbyggda.

    `profiles` är PROFILES som standard (appens inbyggda skalor), men kan
    bytas ut mot en hydrerad egen betygsskala från scales_store.py - samma
    "default"/"sector:X"-nyckelkonvention, så funktionen fungerar oförändrad
    för båda."""
    if industry and f"industry:{industry}" in profiles:
        return profiles[f"industry:{industry}"]
    if sector and f"sector:{sector}" in profiles:
        return profiles[f"sector:{sector}"]
    return profiles["default"]

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZÅÄÖ])")


def _cap_length(text: str, max_chars: int = 320) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].rstrip(",.;") + "…"


def _short_description(summary: str, max_sentences: int = 2) -> str:
    """Kortar ner Yahoos ofta ganska långa bolagsbeskrivning (på engelska)
    till bara några meningar, och översätter den till svenska."""
    if not summary:
        return ""
    sentences = _SENTENCE_SPLIT.split(summary.strip())
    short_en = " ".join(sentences[:max_sentences]).strip()
    short_sv = translate_to_swedish(short_en)
    return _cap_length(short_sv)


def _has_price(info):
    return info and (info.get("regularMarketPrice") is not None or info.get("currentPrice") is not None)


def _get_value(info, metric, computed):
    source = metric["source"]
    if source.startswith("computed:"):
        return computed.get(source.split(":", 1)[1])

    value = info.get(source)
    if value is None and metric.get("fallback_source"):
        value = info.get(metric["fallback_source"])
    if value is None and metric.get("treat_missing_as_zero"):
        value = 0.0
    return value


def _gaussian_falloff(distance, sigma):
    """Mjuk avklingningskurva: 100 poäng vid avstånd 0, avtar sedan som en
    klockkurva istället för ett rakt streck. sigma styr hur brant kurvan
    faller - vid avstånd = 2×sigma (där den gamla linjära skalan gav exakt
    0) ger den fortfarande ett litet positivt betyg (~13), så gränsfall
    bedöms mer graderat och ett enda extremvärde slår inte ut hela
    delbetyget lika hårt."""
    return 100.0 * math.exp(-0.5 * (distance / sigma) ** 2)


# Delar "scale"/"floor"/"ceiling"-avståndet med detta för att få sigma.
# Höjt från 2 till 2.5 (brantare kurva) - annars klarar för många "bra men
# inte exceptionella" bolag sig nästan lika bra som de allra bästa, vilket
# gjorde att för många bolag hamnade på 90+.
_SIGMA_DIVISOR = 2.5


def _score_target(value, ideal, scale):
    return _gaussian_falloff(value - ideal, scale / _SIGMA_DIVISOR)


def _score_higher_better(value, ideal, floor):
    if value >= ideal:
        return 100.0
    return _gaussian_falloff(ideal - value, (ideal - floor) / _SIGMA_DIVISOR)


def _score_lower_better(value, ideal, ceiling):
    if value <= ideal:
        return 100.0
    return _gaussian_falloff(value - ideal, (ceiling - ideal) / _SIGMA_DIVISOR)


def _verdict_from_score(score):
    """Omvandlar ett 0-100-betyg till -1..1 för att ranka positiva/negativa punkter."""
    return (score - 50.0) / 50.0


def _verdict_threshold(value, good_threshold, bad_threshold):
    span = good_threshold - bad_threshold
    if span == 0:
        return 0.0
    raw = (value - bad_threshold) / span * 2 - 1
    return max(-1.0, min(1.0, raw))


def _format_ideal(metric):
    """Formaterar idealvärdet med en riktningsprefix så det syns om
    nyckeltalet ska vara så högt/lågt som möjligt eller ligga nära ett
    exakt värde, t.ex. "≥ 20,0 %" eller "≤ 50,0" eller "~ 1,00"."""
    ideal = metric.get("ideal")
    if ideal is None:
        return ""
    formatted = metric["format"].format(ideal)
    if metric["type"] == "higher_better":
        return f"≥ {formatted}"
    if metric["type"] == "lower_better":
        return f"≤ {formatted}"
    return f"~ {formatted}"


def _evaluate_scoring_metric(metric, info, computed):
    value = _get_value(info, metric, computed)
    if value is None:
        return None

    if metric["type"] == "target":
        score = _score_target(value, metric["ideal"], metric["scale"])
    elif metric["type"] == "higher_better":
        score = _score_higher_better(value, metric["ideal"], metric["floor"])
    elif metric["type"] == "lower_better":
        score = _score_lower_better(value, metric["ideal"], metric["ceiling"])
    else:
        raise ValueError(f"Okänd metric-typ: {metric['type']}")

    return {
        "key": metric["key"],
        "label": metric["label"],
        "value": value,
        "display_value": metric["format"].format(value),
        "score": score,
        "weight": metric["weight"],
        "verdict": _verdict_from_score(score),
        "positive_text": metric["positive_text"],
        "negative_text": metric["negative_text"],
        "ideal": metric.get("ideal"),
        "ideal_display": _format_ideal(metric),
    }


def _evaluate_insight_metric(metric, info, computed):
    value = _get_value(info, metric, computed)
    if value is None:
        return None

    verdict = _verdict_threshold(value, metric["good_threshold"], metric["bad_threshold"])

    return {
        "key": metric["key"],
        "label": metric["label"],
        "value": value,
        "display_value": metric["format"].format(value),
        "verdict": verdict,
        "positive_text": metric["positive_text"],
        "negative_text": metric["negative_text"],
    }


def _computed_fields(info, fear_greed, ma200):
    """Nyckeltal som inte finns som ett eget fält hos Yahoo, men som går att
    räkna ut från andra fält som faktiskt finns (t.ex. P/S, nettoskuld/
    EBITDA, fritt kassaflöde-marginal, "Rule of 40" och kassa-runway för
    bolag som förbränner pengar)."""
    computed = {}

    price = info.get("currentPrice") or info.get("regularMarketPrice")
    target = info.get("targetMeanPrice")
    if price and target:
        computed["target_upside"] = (target - price) / price

    if fear_greed:
        computed["fear_greed"] = fear_greed["score"]

    if ma200:
        computed["ma200_pct"] = ma200["pct_vs_ma200"]

    market_cap = info.get("marketCap")
    total_revenue = info.get("totalRevenue")
    if market_cap and total_revenue:
        computed["price_to_sales"] = market_cap / total_revenue

    ebitda = info.get("ebitda")
    total_debt = info.get("totalDebt")
    total_cash = info.get("totalCash")
    if ebitda and ebitda > 0 and total_debt is not None and total_cash is not None:
        computed["net_debt_to_ebitda"] = (total_debt - total_cash) / ebitda

    free_cashflow = info.get("freeCashflow")
    if free_cashflow is not None and total_revenue:
        computed["fcf_margin"] = free_cashflow / total_revenue

    revenue_growth = info.get("revenueGrowth")
    operating_margins = info.get("operatingMargins")
    if revenue_growth is not None and operating_margins is not None:
        computed["rule_of_40"] = revenue_growth * 100 + operating_margins * 100

    operating_cashflow = info.get("operatingCashflow")
    if operating_cashflow is not None and operating_cashflow < 0 and total_cash:
        computed["cash_runway_months"] = total_cash / (abs(operating_cashflow) / 12)

    return computed


def analyze_ticker(ticker: str, view_style: str = None, custom_scale_profiles: dict = None):
    ticker = ticker.strip().upper()
    resolved_ticker = ticker
    info = get_info(ticker)

    if not _has_price(info):
        # Användaren skrev troligen ett bolagsnamn/kortnamn snarare än en exakt
        # Yahoo-ticker (t.ex. "Volvo" istället för "VOLV-B.ST") - slå upp den
        # mest relevanta träffen och använd den istället.
        matches = search_symbols(ticker, limit=1)
        if matches:
            resolved_ticker = matches[0]["symbol"]
            info = get_info(resolved_ticker)

    if not _has_price(info):
        return {"error": f"Hittade ingen data för '{ticker}'. Kontrollera stavningen, eller välj ett förslag i listan."}

    # Kursdata (Fear & Greed/MA200/graf) och textöversättningen är helt
    # oberoende av varandra - kör dem parallellt istället för i sekvens.
    # Sparar flera sekunder per analys, mest märkbart när anropen går via en
    # proxy (se yahoo_client.py) där varje nätverksanrop kostar extra tid.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        signals_future = executor.submit(get_stock_signals, resolved_ticker)
        description_future = executor.submit(_short_description, info.get("longBusinessSummary") or "")
        signals = signals_future.result()
        description = description_future.result()

    fear_greed = signals["fear_greed"]
    ma200 = signals["ma200"]
    chart = signals["chart"]
    computed = _computed_fields(info, fear_greed, ma200)

    raw_sector = info.get("sector") or ""
    raw_industry = info.get("industry") or ""
    profile = _select_profile(raw_sector, raw_industry, profiles=custom_scale_profiles or PROFILES)

    scoring_results = []
    for metric in profile["scoring"]:
        result = _evaluate_scoring_metric(metric, info, computed)
        if result is not None:
            scoring_results.append(result)

    # Egna skalors vikter är redan användarens eget val - tillväxt/stabil-vy
    # (som viktar om INBYGGDA profiler) och en egen skala används aldrig
    # samtidigt i det nya gränssnittet.
    if custom_scale_profiles is None:
        scoring_results = _apply_view_style(scoring_results, view_style)
    else:
        # Egna skalor har fritt valda vikter som sällan summerar till exakt
        # 100% (och kan tappa ytterligare vikt om ett valt nyckeltal saknar
        # data för bolaget) - normalisera om så "Vikt"-kolumnen i tabellen
        # visar hur stor andel av det FAKTISKA totalbetyget varje nyckeltal
        # utgör, inte bara den vikt som skrevs in vid skapandet.
        scoring_results = _renormalize_weights(scoring_results)

    total_weight = sum(r["weight"] for r in scoring_results)
    if total_weight > 0:
        overall_score = sum(r["score"] * r["weight"] for r in scoring_results) / total_weight
    else:
        overall_score = None

    insight_results = []
    for metric in profile.get("insight", []):
        result = _evaluate_insight_metric(metric, info, computed)
        if result is not None:
            insight_results.append(result)

    all_points = scoring_results + insight_results

    positives = sorted([p for p in all_points if p["verdict"] > 0.05], key=lambda p: -p["verdict"])[:3]
    negatives = sorted([p for p in all_points if p["verdict"] < -0.05], key=lambda p: p["verdict"])[:3]

    def fmt(point, template_key):
        return point[template_key].format(value=point["display_value"], ideal=point.get("ideal"))

    return {
        "ticker": resolved_ticker,
        "name": info.get("longName") or info.get("shortName") or resolved_ticker,
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "currency": info.get("currency", ""),
        "sector": translate_sector(raw_sector),
        "industry": translate_industry(raw_industry, raw_sector),
        "description": description,
        "scale": profile["label"],
        "view_style": view_style if view_style in _VIEW_LABELS else None,
        "view_style_label": _VIEW_LABELS.get(view_style),
        "fear_greed": fear_greed,
        "chart": chart,
        "score": round(overall_score) if overall_score is not None else None,
        "metrics": [
            {
                "label": r["label"],
                "value": r["display_value"],
                "ideal": r["ideal_display"],
                "score": round(r["score"]),
                "weight": r["weight"],
            }
            for r in scoring_results
        ],
        "positives": [fmt(p, "positive_text") for p in positives],
        "negatives": [fmt(n, "negative_text") for n in negatives],
    }
