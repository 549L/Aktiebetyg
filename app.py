import os
import time

from flask import Flask, jsonify, render_template, request, session, url_for

import community_store
import ratings_store
import scales_store
import user_ratings_store
import users_store
from scoring import analyze_ticker
from yahoo_client import search_symbols, search_by_industry, get_chart_data, CHART_RANGES
from history_store import record_result, recent_n
from config.metric_catalog import METRIC_CATALOG, BUILTIN_PROFILE_ROWS
from triggers_data import TRIGGERS_DISCLAIMER
from triggers_store import get_triggers
import feedback_store

app = Flask(__name__)
# Krävs för att signera inloggningskakan (Flask-sessionen). Sätt
# FLASK_SECRET_KEY på Render så inloggningar inte ogiltigförklaras vid
# varje omstart - lokalt räcker en hårdkodad utvecklingsnyckel.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-osaker-nyckel-andra-i-produktion")

# TILLFÄLLIG engångsseedning av "Benjamin Grahams Scale" på 549L-kontot -
# skapandet kräver annars en inloggad session (create_scale sätter
# created_by från session["username"]), men det finns inget sätt att logga
# in som 549L här utan lösenordet. Körs en gång vid processtart (en
# gunicorn-worker på Render), skyddad av en koll så den inte skapar
# dubbletter vid omstart. Tas bort igen så snart den bekräftats köra live.
if not any(
    s.get("name") == "Benjamin Grahams Scale" and s.get("created_by") == "549L"
    for s in scales_store.list_scales()
):
    scales_store.create_scale(
        "Benjamin Grahams Scale",
        {
            "default": {
                "metrics": [
                    {"key": "pe_ratio", "ideal": 12, "tolerance": 22, "weight_pct": 28},
                    {"key": "price_to_book", "ideal": 1.0, "tolerance": 2.5, "weight_pct": 27},
                    {"key": "current_ratio", "ideal": 2.2, "tolerance": 1.0, "weight_pct": 12},
                    {"key": "debt_to_equity", "ideal": 40, "tolerance": 160, "weight_pct": 10},
                    {"key": "dividend_yield", "ideal": 0.025, "tolerance": 0.025, "weight_pct": 10},
                    {"key": "profit_margin", "ideal": 0.08, "tolerance": 0.08, "weight_pct": 8},
                    {"key": "revenue_growth", "ideal": 0.05, "tolerance": 0.08, "weight_pct": 5},
                ]
            },
            "sector:Financial Services": {
                "metrics": [
                    {"key": "price_to_book", "ideal": 1.0, "tolerance": 2.0, "weight_pct": 30},
                    {"key": "roe", "ideal": 0.10, "tolerance": 0.06, "weight_pct": 25},
                    {"key": "pe_ratio", "ideal": 10, "tolerance": 16, "weight_pct": 20},
                    {"key": "dividend_yield", "ideal": 0.035, "tolerance": 0.025, "weight_pct": 15},
                    {"key": "profit_margin", "ideal": 0.15, "tolerance": 0.12, "weight_pct": 10},
                ]
            },
            "sector:Real Estate": {
                "metrics": [
                    {"key": "dividend_yield", "ideal": 0.045, "tolerance": 0.03, "weight_pct": 30},
                    {"key": "price_to_book", "ideal": 1.0, "tolerance": 1.5, "weight_pct": 25},
                    {"key": "net_debt_to_ebitda", "ideal": 6.0, "tolerance": 3.0, "weight_pct": 25},
                    {"key": "profit_margin", "ideal": 0.15, "tolerance": 0.12, "weight_pct": 20},
                ]
            },
        },
        created_by="549L",
    )

# Inloggnings-/registreringsflödet och statiska filer är alltid publika
# (annars skulle inte ens inloggningsformuläret gå att visa/stila). Se
# users_store.py för kontona - ett admin-konto ("549L") skapas automatiskt.
_PUBLIC_ENDPOINTS = {"index", "login", "register", "me", "static"}


@app.before_request
def _require_login():
    if request.endpoint in _PUBLIC_ENDPOINTS or request.endpoint is None:
        return None
    # Gästläge: att LÄSA (GET) - söka, analysera, bläddra bland skalor/
    # profiler/community/triggers - är öppet utan konto. Att SKRIVA något
    # (skapa en skala, rösta, skriva ett meddelande, ändra sin egen
    # profil o.s.v.) knyts alltid till ett användarnamn och kräver
    # fortfarande inloggning - det är bara de icke-GET-anropen nedan.
    if request.method in ("GET", "HEAD"):
        return None
    if not session.get("username"):
        return jsonify({"error": "Du måste logga in för att göra det här."}), 401
    return None


@app.after_request
def _cache_control(response):
    # API-svar och själva sidan (index.html) är personliga eller ändras
    # ofta (svaret skiljer sig per inloggat konto) - utan no-store kan
    # webbläsaren återanvända ett cachat svar från en annan användare efter
    # att man loggat in som någon annan i samma flik.
    #
    # /static/* (app.js/style.css/favicon.svg) är däremot samma för alla
    # och fick tidigare också no-store av misstag, vilket tvingade
    # webbläsaren att hämta om hela app.js (~90 kB) och style.css (~35 kB)
    # på nytt vid VARJE sidladdning. index.html länkar till dem med en
    # "?v=<filens ändringstidpunkt>"-parameter (se asset_url ovan) - byter
    # alltså URL automatiskt så fort filen verkligen ändras (t.ex. vid en
    # omdeploy) - så de kan cachas i väldigt lång tid (immutable, ett år)
    # helt utan risk för inaktuell JS/CSS: en gammal sidvisning fortsätter
    # peka på den gamla (fortfarande cachade) URL:en, en ny sidvisning får
    # den nya URL:en och hämtar filen på nytt.
    if request.endpoint == "static":
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    else:
        response.headers["Cache-Control"] = "no-store"
    return response


@app.context_processor
def _inject_asset_version():
    # Lägger till "?v=<filens ändringstidpunkt>" på statiska filers URL:er
    # i index.html (se asset_url nedan) - byter URL varje gång filen
    # verkligen ändras (t.ex. vid en omdeploy), så webbläsaren aldrig kan
    # visa en gammal cachad app.js/style.css av misstag. Det gör att de
    # kan cachas väldigt länge (se /static/*-fallet i _cache_control) utan
    # att riskera inaktuell JS/CSS efter en omdeploy.
    def asset_url(filename):
        path = os.path.join(app.static_folder, filename)
        try:
            version = int(os.path.getmtime(path))
        except OSError:
            version = 0
        return f"{url_for('static', filename=filename)}?v={version}"

    return {"asset_url": asset_url}


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
    return jsonify(recent_n(session.get("username"), 5))


@app.route("/api/metric-catalog")
def metric_catalog():
    return jsonify(list(METRIC_CATALOG.values()))


@app.route("/api/builtin-profiles")
def builtin_profiles():
    return jsonify(BUILTIN_PROFILE_ROWS)


@app.route("/api/triggers")
def triggers():
    # Se triggers_data.py/triggers_store.py - en handplockad, självpåfyllande
    # lista, INTE en live datakälla. disclaimer skickas alltid med så
    # frontend kan visa den synligt. get_triggers() fyller redan på utgångna
    # platser med nya, men filtrerar ändå till "nu och max ~2 månader
    # framåt" här också som ett extra skyddsnät.
    now = time.time()
    window_end = now + 60 * 86400
    upcoming = [t for t in get_triggers() if now <= t["date"] <= window_end]
    return jsonify({"disclaimer": TRIGGERS_DISCLAIMER, "triggers": upcoming})


@app.route("/api/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        try:
            feedback_store.add_feedback(body.get("text"), session.get("username"), body.get("category"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"ok": True}), 201

    # GET är annars öppet även för gäster (se _require_login), men
    # feedback är en brevlåda bara 549L (och ingen annan, oavsett
    # is_admin-flaggan) ska kunna läsa - kollas därför explicit här
    # istället för att förlita sig på hooken. Samma mönster som
    # _BUILTIN_SCALES_FOR_549L nedan använder för att peka ut exakt det
    # kontot.
    if session.get("username") != "549L":
        return jsonify({"error": "Du har inte behörighet att se det här."}), 403
    return jsonify(feedback_store.list_feedback())


@app.route("/api/scales", methods=["GET", "POST"])
def scales():
    if request.method == "GET":
        return jsonify(scales_store.list_scales())

    body = request.get_json(silent=True) or {}
    try:
        record = scales_store.create_scale(
            body.get("name"), body.get("profiles") or {}, created_by=session.get("username")
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

    # Ändra/ta bort är bara tillåtet för den som skapade skalan (eller en
    # admin) - annars skulle vem som helst inloggad kunna redigera eller
    # radera andras betygsskalor via samma API som ägaren själv använder.
    existing = scales_store.get_scale(scale_id)
    if existing is None:
        return jsonify({"error": "Betygsskalan hittades inte."}), 404

    username = session.get("username")
    account = users_store.get_user(username)
    is_owner = existing.get("created_by") == username
    if not is_owner and not (account and account.get("is_admin")):
        return jsonify({"error": "Du kan bara ändra dina egna betygsskalor."}), 403

    if request.method == "DELETE":
        scales_store.delete_scale(scale_id)
        ratings_store.delete_rating(scale_id)
        return jsonify({"deleted": True})

    body = request.get_json(silent=True) or {}
    try:
        record = scales_store.update_scale(
            scale_id, body.get("name"), body.get("profiles") or {}
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
        rows = rows[:3]
    return jsonify(rows)


# De tre inbyggda skalorna (se BUILTIN_SCALES i app.js) är statiska och
# lever inte i scales_store - för att de ändå ska synas på 549L:s profilsida
# listas de här separat och märks med is_builtin så frontend vet att de ska
# väljas via sitt bara id (t.ex. "growth"), inte "custom:<id>".
_BUILTIN_SCALES_FOR_549L = [
    {"id": "growth", "name": "549L Tillväxt Bolag", "is_builtin": True},
    {"id": "stability", "name": "549L Stabila Bolag", "is_builtin": True},
    {"id": "default", "name": "549L Vanliga bolag", "is_builtin": True},
]


@app.route("/api/users/<username>")
def user_profile(username):
    account = users_store.get_user(username)
    if not account:
        return jsonify({"error": "Användaren hittades inte."}), 404
    account["rating"] = user_ratings_store.get_all_ratings().get(username, {"average": None, "count": 0})

    # dict(s) kopierar varje inbyggd skala - annars skulle "rating" nedan
    # skrivas in i den delade _BUILTIN_SCALES_FOR_549L-listan permanent.
    builtin_scales = [dict(s) for s in _BUILTIN_SCALES_FOR_549L] if username == "549L" else []
    scales = builtin_scales + scales_store.list_scales_by_owner(username)

    scale_ratings = ratings_store.get_all_ratings()
    for scale in scales:
        scale["rating"] = scale_ratings.get(scale["id"], {"average": None, "count": 0})

    # Högst betygsatta skalan överst, obetygsatta sist - samma sortering
    # som användarsökningen redan använder.
    scales.sort(key=lambda s: (s["rating"]["average"] is None, -(s["rating"]["average"] or 0)))
    account["scales"] = scales

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


@app.route("/api/me/avatar", methods=["POST", "DELETE"])
def me_avatar():
    username = session.get("username")
    if request.method == "DELETE":
        users_store.remove_avatar(username)
        return jsonify({"avatar": None})

    body = request.get_json(silent=True) or {}
    try:
        avatar = users_store.set_avatar(username, body.get("image"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"avatar": avatar})


@app.route("/api/me/bio", methods=["POST"])
def me_bio():
    body = request.get_json(silent=True) or {}
    try:
        bio = users_store.set_bio(session.get("username"), body.get("bio"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"bio": bio})


@app.route("/api/me/color", methods=["POST"])
def me_color():
    body = request.get_json(silent=True) or {}
    try:
        color = users_store.set_accent_color(session.get("username"), body.get("color"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"accent_color": color})


@app.route("/api/community/rooms", methods=["GET", "POST"])
def community_rooms():
    if request.method == "GET":
        ticker = request.args.get("ticker", "").strip()
        if ticker:
            return jsonify(community_store.find_rooms_by_ticker(ticker))
        return jsonify(community_store.list_rooms())

    body = request.get_json(silent=True) or {}
    try:
        room = community_store.create_room(
            body.get("name"), session.get("username"), ticker=body.get("ticker")
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(room), 201


@app.route("/api/community/rooms/<room_id>")
def community_room_detail(room_id):
    room = community_store.get_room(room_id)
    if room is None:
        return jsonify({"error": "Chatten hittades inte."}), 404
    return jsonify(room)


@app.route("/api/community/rooms/<room_id>/messages", methods=["POST"])
def community_room_messages(room_id):
    if community_store.get_room(room_id) is None:
        return jsonify({"error": "Chatten hittades inte."}), 404
    body = request.get_json(silent=True) or {}
    try:
        message = community_store.post_message(room_id, session.get("username"), body.get("text"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(message), 201


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
