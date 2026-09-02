from flask import Flask, jsonify, render_template, request

from scoring import analyze_ticker
from yahoo_client import search_symbols, search_by_industry, get_chart_data, CHART_RANGES
from history_store import record_result, recent_n, distinct_industries

app = Flask(__name__)


@app.route("/api/_debug_yahoo")
def _debug_yahoo():
    """Tillfällig diagnos-route för att se exakt vad som händer mot Yahoo
    Finance från produktionsservern (t.ex. om molnleverantörens IP blockeras).
    Tas bort igen när felsökningen är klar."""
    from curl_cffi import requests as creq
    info = {}
    try:
        session = creq.Session(impersonate="chrome")
        r1 = session.get("https://fc.yahoo.com", timeout=10)
        info["fc_status"] = r1.status_code
        r2 = session.get("https://query2.finance.yahoo.com/v1/test/getcrumb", timeout=10)
        info["crumb_status"] = r2.status_code
        info["crumb_text"] = r2.text[:200]
        r3 = session.get(
            "https://query1.finance.yahoo.com/v10/finance/quoteSummary/AAPL",
            params={"modules": "price", "crumb": r2.text},
            timeout=10,
        )
        info["quote_status"] = r3.status_code
        info["quote_body"] = r3.text[:500]
    except Exception as exc:
        info["exception"] = f"{type(exc).__name__}: {exc}"
    return jsonify(info)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search/<query>")
def search(query):
    if len(query.strip()) < 2:
        return jsonify([])
    industry = request.args.get("industry", "").strip()
    try:
        if industry:
            results = search_by_industry(query, industry)
        else:
            results = search_symbols(query)
    except Exception:
        results = []
    return jsonify(results)


@app.route("/api/industries")
def industries():
    return jsonify(distinct_industries())


@app.route("/api/analyze/<ticker>")
def analyze(ticker):
    view_style = request.args.get("style")
    if view_style not in ("growth", "stability"):
        view_style = None
    try:
        result = analyze_ticker(ticker, view_style=view_style)
    except Exception as exc:
        return jsonify({"error": f"Något gick fel: {exc}"}), 500

    if "error" in result:
        return jsonify(result), 404

    record_result(result)
    return jsonify(result)


@app.route("/api/recent")
def recent():
    return jsonify(recent_n(10))


@app.route("/api/chart/<ticker>")
def chart(ticker):
    period = request.args.get("period", "1y")
    if period not in CHART_RANGES:
        period = "1y"
    try:
        data = get_chart_data(ticker, period)
    except Exception:
        data = {"points": [], "currency": ""}
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
