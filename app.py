import os

from flask import Flask, jsonify, render_template, request, session

import ratings_store
import scales_store
import user_ratings_store
import users_store
from scoring import analyze_ticker
from yahoo_client import search_symbols, search_by_industry, get_chart_data, CHART_RANGES
from history_store import record_result, recent_n
from config.metric_catalog import METRIC_CATALOG, BUILTIN_PROFILE_ROWS

app = Flask(__name__)
# Krävs för att signera inloggningskakan (Flask-sessionen). Sätt
# FLASK_SECRET_KEY på Render så inloggningar inte ogiltigförklaras vid
# varje omstart - lokalt räcker en hårdkodad utvecklingsnyckel.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-osaker-nyckel-andra-i-produktion")

# Hela sidan kräver inloggning utom själva inloggnings-/registreringsflödet
# och statiska filer (annars skulle inte ens inloggningsformuläret gå att
# visa/stila). Se users_store.py för kontona - ett admin-konto ("549L")
# skapas automatiskt.
_PUBLIC_ENDPOINTS = {"index", "login", "register", "me", "static"}


@app.before_request
def _require_login():
    if request.endpoint in _PUBLIC_ENDPOINTS or request.endpoint is None:
        return None
    if not session.get("username"):
        return jsonify({"error": "Du måste logga in för att använda Aktiebetyg."}), 401
    return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/register", methods=["POST"])
def register():
    body = request.get_json(silent=True) or {}
    try:
        account = users_store.create_user(body.get("username"), body.get("password"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    session["username"] = account["username"]
    return jsonify(account), 201


@app.route("/api/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    account = users_store.verify_login(body.get("username"), body.get("password"))
    if not account:
        return jsonify({"error": "Fel användarnamn eller lösenord."}), 401
    session["username"] = account["username"]
    return jsonify(account)


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"loggedOut": True})


@app.route("/api/me")
def me():
    username = session.get("username")
    account = users_store.get_user(username) if username else None
    if not account:
        session.clear()
        return jsonify({"username": None})
    return jsonify(account)


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


@app.route("/api/analyze/<ticker>")
def analyze(ticker):
    # ?scale= ersätter gamla ?style= - "growth"/"stability" är de inbyggda
    # tillväxt-/stabil-vyerna (viktar om profilen), "custom:<id>" en egen
    # sparad betygsskala (byter ut profilen helt). Allt annat/utelämnat =
    # appens vanliga skala, oförändrat.
    scale_param = request.args.get("scale")
    view_style = scale_param if scale_param in ("growth", "stability") else None

    custom_scale_profiles = None
    if scale_param and scale_param.startswith("custom:"):
        custom_scale_profiles = scales_store.resolve_profiles(scale_param.split(":", 1)[1])
        if custom_scale_profiles is None:
            return jsonify({"error": "Betygsskalan kunde inte hittas - den kan ha tagits bort."}), 404

    try:
        result = analyze_ticker(ticker, view_style=view_style, custom_scale_profiles=custom_scale_profiles)
    except Exception as exc:
        return jsonify({"error": f"Något gick fel: {exc}"}), 500

    if "error" in result:
        return jsonify(result), 404

    record_result(session.get("username"), result)
    return jsonify(result)


@app.route("/api/recent")
def recent():
    return jsonify(recent_n(session.get("username"), 10))


@app.route("/api/metric-catalog")
def metric_catalog():
    return jsonify(list(METRIC_CATALOG.values()))


@app.route("/api/builtin-profiles")
def builtin_profiles():
    return jsonify(BUILTIN_PROFILE_ROWS)


@app.route("/api/scales", methods=["GET", "POST"])
def scales():
    if request.method == "GET":
        return jsonify(scales_store.list_scales())

    body = request.get_json(silent=True) or {}
    try:
        record = scales_store.create_scale(
            body.get("name"), body.get("profiles") or {}, color=body.get("color"), created_by=session.get("username")
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(record), 201


@app.route("/api/scales/<scale_id>", methods=["GET", "PUT", "DELETE"])
def scale_detail(scale_id):
    if request.method == "GET":
        record = scales_store.get_scale(scale_id)
        if record is None:
            return jsonify({"error": "Betygsskalan hittades inte."}), 404
        return jsonify(record)

    if request.method == "DELETE":
        if not scales_store.delete_scale(scale_id):
            return jsonify({"error": "Betygsskalan hittades inte."}), 404
        ratings_store.delete_rating(scale_id)
        return jsonify({"deleted": True})

    body = request.get_json(silent=True) or {}
    try:
        record = scales_store.update_scale(
            scale_id, body.get("name"), body.get("profiles") or {}, color=body.get("color")
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if record is None:
        return jsonify({"error": "Betygsskalan hittades inte."}), 404
    return jsonify(record)


@app.route("/api/ratings")
def ratings():
    return jsonify(ratings_store.get_all_ratings())


@app.route("/api/scales/<scale_id>/rating", methods=["POST"])
def rate_scale(scale_id):
    body = request.get_json(silent=True) or {}
    try:
        summary = ratings_store.rate_scale(scale_id, session.get("username"), body.get("stars"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(summary)


@app.route("/api/users")
def users_search():
    # Utan sökord: en kort standardlista (högst rankade konton överst),
    # samma mönster som betygsskalor-panelen. Med sökord: alla konton vars
    # användarnamn matchar, oavsett hur många - sökningen är tänkt att
    # kunna hitta vem som helst, inte bara de mest populära.
    query = request.args.get("q", "").strip().lower()
    ratings = user_ratings_store.get_all_ratings()

    rows = users_store.list_users()
    if query:
        rows = [u for u in rows if query in u["username"].lower()]

    for row in rows:
        row["rating"] = ratings.get(row["username"], {"average": None, "count": 0})

    rows.sort(key=lambda u: (u["rating"]["average"] is None, -(u["rating"]["average"] or 0), u["username"].lower()))

    if not query:
        rows = rows[:5]
    return jsonify(rows)


@app.route("/api/users/<username>")
def user_profile(username):
    account = users_store.get_user(username)
    if not account:
        return jsonify({"error": "Användaren hittades inte."}), 404
    account["rating"] = user_ratings_store.get_all_ratings().get(username, {"average": None, "count": 0})
    account["scales"] = scales_store.list_scales_by_owner(username)
    return jsonify(account)


@app.route("/api/users/<username>/rating", methods=["POST"])
def rate_user(username):
    if not users_store.get_user(username):
        return jsonify({"error": "Användaren hittades inte."}), 404
    body = request.get_json(silent=True) or {}
    try:
        summary = user_ratings_store.rate_user(username, session.get("username"), body.get("stars"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(summary)


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
