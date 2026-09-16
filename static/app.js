const form = document.getElementById("search-form");
const input = document.getElementById("ticker-input");
const suggestionsEl = document.getElementById("suggestions");
const statusEl = document.getElementById("status");
const result = document.getElementById("result");

// ---------------------------------------------------------------------------
// Ihopfällbara rutor - "Senast sökta"/"Sök användare"/"Sök betygsskalor" kan
// fällas ihop till bara rubriken (t.ex. för en städigare vy), samma knapp
// fäller ut den igen. Generell för alla tre - inget särfall per ruta.
// ---------------------------------------------------------------------------
document.querySelectorAll(".panel-toggle-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        const section = btn.closest("section");
        const title = section.querySelector(".panel-header h3").textContent;
        const collapsed = section.classList.toggle("panel-collapsed");
        btn.textContent = collapsed ? "+" : "−";
        btn.setAttribute("aria-expanded", String(!collapsed));
        btn.setAttribute("aria-label", (collapsed ? "Visa " : "Dölj ") + title);
    });
});

const VIEW_STYLE_LABELS = {
    growth: "Tillväxtvy",
    stability: "Stabil vy",
};

const RATING_LABELS = {
    "extreme fear": "Extrem rädsla",
    "fear": "Rädsla",
    "neutral": "Neutral",
    "greed": "Girighet",
    "extreme greed": "Extrem girighet",
};

function ratingClass(rating) {
    if (rating === "extreme fear" || rating === "fear") return "good";
    if (rating === "greed" || rating === "extreme greed") return "bad";
    return "neutral";
}

function renderFearGreed(fearGreed) {
    const badge = document.getElementById("fear-greed-badge");
    if (!fearGreed || fearGreed.score === undefined) {
        badge.classList.add("hidden");
        return;
    }
    document.getElementById("fear-greed-value").textContent = `${fearGreed.score}/100`;
    const ratingEl = document.getElementById("fear-greed-rating");
    ratingEl.textContent = RATING_LABELS[fearGreed.rating] || fearGreed.rating;
    ratingEl.className = `fear-greed-rating ${ratingClass(fearGreed.rating)}`;
    badge.classList.remove("hidden");
}

// Nästa rapport (liten ruta, alltid synlig) + "Kommande händelser" (upp
// till tre - rapportdatum, X-dag/utdelning, räkenskapsårets slut) visas
// för ALLA bolag oavsett vald betygsskala, se scoring.py:s
// _upcoming_events. "Okänt"/en tom-lista-text istället för att dölja
// rutan/sektionen om inget hittades - de ska alltid synas på samma ställe.
function renderUpcomingEvents(data) {
    document.getElementById("next-report-value").textContent = data.next_report_date
        ? formatAccountDate(data.next_report_date)
        : "Okänt";

    const listEl = document.getElementById("upcoming-events-list");
    listEl.innerHTML = "";
    const events = data.upcoming_events || [];

    if (events.length === 0) {
        const li = document.createElement("li");
        li.className = "muted";
        li.textContent = "Inga kända kommande händelser hittades.";
        listEl.appendChild(li);
        return;
    }

    events.forEach((event) => {
        const li = document.createElement("li");

        const label = document.createElement("span");
        label.className = "upcoming-event-label";
        label.textContent = event.label;
        li.appendChild(label);

        const date = document.createElement("span");
        date.className = "upcoming-event-date";
        date.textContent = formatAccountDate(event.date);
        li.appendChild(date);

        listEl.appendChild(li);
    });
}

// Ticker-autocomplete - återanvänds både av huvudsökrutan (väljer man ett
// förslag analyseras aktien direkt) och av "länka till en aktie"-fältet när
// man skapar en community-chatt (väljer man ett förslag fylls bara fältet i).
function createTickerAutocomplete(inputEl, suggestionsListEl, onSelect) {
    let abortController = null;
    let debounceTimer = null;
    let activeIndex = -1;
    let suggestions = [];

    function hide() {
        suggestionsListEl.classList.add("hidden");
        suggestionsListEl.innerHTML = "";
        suggestions = [];
        activeIndex = -1;
    }

    function updateActive() {
        [...suggestionsListEl.children].forEach((li, i) => {
            li.classList.toggle("active", i === activeIndex);
        });
    }

    function pick(match) {
        inputEl.value = match.symbol;
        hide();
        onSelect(match);
    }

    function render(matches) {
        suggestions = matches;
        activeIndex = -1;
        suggestionsListEl.innerHTML = "";

        if (matches.length === 0) {
            hide();
            return;
        }

        matches.forEach((match) => {
            const li = document.createElement("li");
            li.innerHTML = `<span>${match.name}</span><span class="suggestion-symbol">${match.symbol}${match.exchange ? " · " + match.exchange : ""}</span>`;
            li.addEventListener("mousedown", (e) => {
                // mousedown (före blur) så klicket hinner registreras innan listan döljs
                e.preventDefault();
                pick(match);
            });
            suggestionsListEl.appendChild(li);
        });

        suggestionsListEl.classList.remove("hidden");
    }

    inputEl.addEventListener("input", () => {
        const query = inputEl.value.trim();
        clearTimeout(debounceTimer);

        if (query.length < 2) {
            hide();
            return;
        }

        debounceTimer = setTimeout(async () => {
            if (abortController) abortController.abort();
            abortController = new AbortController();

            try {
                const res = await fetch(`/api/search/${encodeURIComponent(query)}`, {
                    signal: abortController.signal,
                });
                render(await res.json());
            } catch (err) {
                if (err.name !== "AbortError") hide();
            }
        }, 250);
    });

    inputEl.addEventListener("keydown", (e) => {
        if (suggestionsListEl.classList.contains("hidden") || suggestions.length === 0) return;

        if (e.key === "ArrowDown") {
            e.preventDefault();
            activeIndex = Math.min(activeIndex + 1, suggestions.length - 1);
            updateActive();
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            activeIndex = Math.max(activeIndex - 1, 0);
            updateActive();
        } else if (e.key === "Enter" && activeIndex >= 0) {
            e.preventDefault();
            pick(suggestions[activeIndex]);
        } else if (e.key === "Escape") {
            hide();
        }
    });

    document.addEventListener("click", (e) => {
        if (!suggestionsListEl.contains(e.target) && e.target !== inputEl) {
            hide();
        }
    });

    return { hide };
}

const tickerAutocomplete = createTickerAutocomplete(input, suggestionsEl, (match) => runAnalysis(match.symbol));

const top10List = document.getElementById("top10-list");
const top10Empty = document.getElementById("top10-empty");

function scoreClass(score) {
    if (score >= 70) return "good";
    if (score >= 40) return "medium";
    return "bad";
}

async function loadTop10() {
    // Namnet "top10" är historiskt (listan sorterade tidigare på högst
    // betyg) - den visar nu istället de senast sökta aktierna.
    try {
        const res = await fetch("/api/recent");
        const entries = await res.json();

        top10List.innerHTML = "";
        if (entries.length === 0) {
            top10Empty.classList.remove("hidden");
            return;
        }
        top10Empty.classList.add("hidden");

        entries.forEach((entry) => {
            const li = document.createElement("li");
            const industry = entry.industry || entry.sector || "";
            li.innerHTML = `
                <span class="top10-name">${entry.name} <span class="top10-ticker">${entry.ticker}</span></span>
                ${industry ? `<span class="top10-industry">${industry}</span>` : ""}
                <span class="top10-score ${scoreClass(entry.score)}">${entry.score}</span>
            `;
            li.addEventListener("click", () => {
                input.value = entry.ticker;
                runAnalysis(entry.ticker);
            });
            top10List.appendChild(li);
        });
    } catch (err) {
        // Topplistan är en extra funktion - misslyckas hämtningen visar vi bara ingenting.
    }
}

form.addEventListener("submit", (e) => {
    e.preventDefault();
    tickerAutocomplete.hide();
    const ticker = input.value.trim();
    if (!ticker) return;
    runAnalysis(ticker);
});

async function runAnalysis(ticker) {
    statusEl.textContent = `Hämtar data för ${ticker.toUpperCase()}...`;
    statusEl.classList.remove("error");
    result.classList.add("hidden");
    form.querySelector("button").disabled = true;
    currentTicker = ticker;

    try {
        const url = new URL(`/api/analyze/${encodeURIComponent(ticker)}`, window.location.origin);
        url.searchParams.set("scale", currentScaleId);
        const res = await fetch(url);
        const data = await res.json();

        if (!res.ok || data.error) {
            statusEl.textContent = data.error || "Kunde inte hämta data.";
            statusEl.classList.add("error");
            return;
        }

        renderResult(data);
        statusEl.textContent = "";
        loadTop10();
        checkResultChat(data.ticker);
    } catch (err) {
        statusEl.textContent = "Nätverksfel: kunde inte nå servern.";
        statusEl.classList.add("error");
    } finally {
        form.querySelector("button").disabled = false;
    }
}

function renderResult(data) {
    document.getElementById("company-name").textContent = `${data.name} (${data.ticker})`;
    document.getElementById("ticker-price").textContent = data.price
        ? `Pris: ${data.price} ${data.currency}`
        : "";
    document.getElementById("ticker-industry").textContent = data.industry || data.sector || "";
    document.getElementById("result-scale-badge").textContent = currentScaleDisplayName() || "";
    document.getElementById("company-description").textContent = data.description || "";
    const viewLabel = data.view_style_label || VIEW_STYLE_LABELS[data.view_style] || null;
    document.getElementById("scale-label").textContent = data.scale
        ? (viewLabel ? `(${data.scale} · ${viewLabel})` : `(${data.scale})`)
        : "";
    renderFearGreed(data.fear_greed);
    renderUpcomingEvents(data);

    const scoreValue = document.getElementById("score-value");
    const scoreBadge = document.getElementById("score-badge");
    scoreValue.textContent = data.score !== null ? data.score : "?";

    scoreBadge.classList.remove("good", "medium", "bad");
    if (data.score === null) {
        // no class
    } else if (data.score >= 70) {
        scoreBadge.classList.add("good");
    } else if (data.score >= 40) {
        scoreBadge.classList.add("medium");
    } else {
        scoreBadge.classList.add("bad");
    }

    const positivesList = document.getElementById("positives-list");
    positivesList.innerHTML = "";
    if (data.positives.length === 0) {
        positivesList.innerHTML = "<li>Inga tydliga styrkor hittades i tillgänglig data.</li>";
    } else {
        data.positives.forEach((text) => {
            const li = document.createElement("li");
            li.textContent = text;
            positivesList.appendChild(li);
        });
    }

    const negativesList = document.getElementById("negatives-list");
    negativesList.innerHTML = "";
    if (data.negatives.length === 0) {
        negativesList.innerHTML = "<li>Inga tydliga svagheter hittades i tillgänglig data.</li>";
    } else {
        data.negatives.forEach((text) => {
            const li = document.createElement("li");
            li.textContent = text;
            negativesList.appendChild(li);
        });
    }

    const tbody = document.querySelector("#metrics-table tbody");
    tbody.innerHTML = "";
    data.metrics.forEach((m) => {
        const tr = document.createElement("tr");
        const cls = scoreClass(m.score);
        tr.innerHTML = `
            <td>${m.label}</td>
            <td class="metric-value ${cls}">${m.value}</td>
            <td class="metric-ideal">${m.ideal || "–"}</td>
            <td class="metric-score ${cls}">${m.score} / 100</td>
            <td>${Math.round(m.weight * 100)}%</td>
        `;
        tbody.appendChild(tr);
    });

    result.classList.remove("hidden");

    currentTicker = data.ticker;
    if (currentChartPeriod === "1y" && data.chart) {
        // /api/analyze skickar redan med ett års kursdata (den hämtas ändå
        // internt för Fear & Greed/MA200) - slipper då ett extra
        // nätverksanrop för att rita startgrafen.
        drawChart(data.chart, "1y");
    } else {
        loadChart(currentTicker, currentChartPeriod);
    }
}

let currentTicker = null;
let currentChartPeriod = "1y";

const chartSvg = document.getElementById("chart-svg");
const chartRangeButtons = document.querySelectorAll("#chart-ranges button");

chartRangeButtons.forEach((button) => {
    button.addEventListener("click", () => {
        currentChartPeriod = button.dataset.period;
        chartRangeButtons.forEach((b) => b.classList.toggle("active", b === button));
        if (currentTicker) loadChart(currentTicker, currentChartPeriod);
    });
});

const macdSvg = document.getElementById("macd-svg");
const macdToggle = document.getElementById("macd-toggle");
let macdEnabled = false;

macdToggle.addEventListener("click", () => {
    macdEnabled = !macdEnabled;
    macdToggle.setAttribute("aria-pressed", String(macdEnabled));
    renderMACD();
});

// Grafens koordinatsystem (mått i SVG-enheter, matchar viewBox i index.html).
// Sparas globalt tillsammans med skalfunktionerna för sista ritade grafen,
// så att framtida indikatorer (glidande medelvärden, RSI-band m.m. -
// t.ex. inklistrade från TradingView) enkelt kan rita på exakt samma
// koordinater som prislinjen, istället för att räkna ut sin egen skala.
const CHART_LAYOUT = { width: 640, height: 220, marginLeft: 56, marginRight: 14, marginTop: 12, marginBottom: 28 };
let currentChart = null; // { points, xScale(i), yScale(price), plot: {left, right, top, bottom} }

function svgEl(tag, attrs) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
    return el;
}

function formatAxisPrice(value, max) {
    const decimals = max >= 100 ? 0 : max >= 10 ? 1 : 2;
    return value.toFixed(decimals);
}

function formatAxisDate(date, period) {
    if (period === "1d") return date.toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" });
    if (period === "1w") return date.toLocaleDateString("sv-SE", { day: "numeric", month: "numeric" });
    if (period === "1y") return date.toLocaleDateString("sv-SE", { month: "short", year: "2-digit" });
    return date.toLocaleDateString("sv-SE", { year: "numeric" });
}

// MACD (12, 26, close, 9) - standardformeln: MACD-linjen är skillnaden
// mellan ett 12- och ett 26-perioders exponentiellt glidande medelvärde
// (EMA) av stängningskursen, signallinjen är ett 9-perioders EMA av
// MACD-linjen, och histogrammet är skillnaden mellan de två.

function ema(values, period) {
    // Returnerar en lika lång array som `values`, med `null` för index där
    // det inte finns tillräckligt med data för att räkna ut ett EMA-värde
    // än (standard: seedas med ett enkelt medelvärde (SMA) av de första
    // `period` värdena).
    const result = new Array(values.length).fill(null);
    if (values.length < period) return result;

    const k = 2 / (period + 1);
    let prev = values.slice(0, period).reduce((sum, v) => sum + v, 0) / period;
    result[period - 1] = prev;
    for (let i = period; i < values.length; i++) {
        prev = values[i] * k + prev * (1 - k);
        result[i] = prev;
    }
    return result;
}

function computeMACD(closes, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9) {
    const emaFast = ema(closes, fastPeriod);
    const emaSlow = ema(closes, slowPeriod);
    const macdLine = closes.map((_, i) => (emaFast[i] !== null && emaSlow[i] !== null) ? emaFast[i] - emaSlow[i] : null);

    const validStart = macdLine.findIndex((v) => v !== null);
    const signalLine = new Array(closes.length).fill(null);
    if (validStart !== -1) {
        const signalOfValid = ema(macdLine.slice(validStart), signalPeriod);
        signalOfValid.forEach((v, i) => { signalLine[validStart + i] = v; });
    }

    const histogram = closes.map((_, i) => (macdLine[i] !== null && signalLine[i] !== null) ? macdLine[i] - signalLine[i] : null);
    return { macdLine, signalLine, histogram };
}

function renderMACD() {
    macdSvg.innerHTML = "";

    if (!macdEnabled || !currentChart) {
        macdSvg.classList.add("hidden");
        return;
    }

    const closes = currentChart.points.map((p) => p.close);
    const { macdLine, signalLine, histogram } = computeMACD(closes);
    const allValues = [...macdLine, ...signalLine, ...histogram].filter((v) => v !== null);
    if (allValues.length === 0) {
        macdSvg.classList.add("hidden");
        return;
    }
    macdSvg.classList.remove("hidden");

    const maxAbs = Math.max(...allValues.map(Math.abs)) || 1;
    const width = 640, height = 110, marginTop = 10, marginBottom = 20;
    const { left, right } = currentChart.plot; // samma vänster-/högermarginal som prisgrafen, för perfekt x-justering
    const plotTop = marginTop, plotBottom = height - marginBottom;
    const plotHeight = plotBottom - plotTop;

    const xScale = currentChart.xScale; // återanvänder EXAKT samma x-skala som prislinjen
    const yScale = (v) => plotTop + (1 - (v + maxAbs) / (2 * maxAbs)) * plotHeight;

    // Nollinje.
    macdSvg.appendChild(svgEl("line", {
        class: "macd-zero-line", x1: left, x2: right, y1: yScale(0).toFixed(1), y2: yScale(0).toFixed(1),
    }));

    // Histogram.
    const barWidth = Math.max(1, ((right - left) / closes.length) * 0.6);
    histogram.forEach((v, i) => {
        if (v === null) return;
        const x = xScale(i) - barWidth / 2;
        const y0 = yScale(0);
        const y1 = yScale(v);
        macdSvg.appendChild(svgEl("rect", {
            class: `macd-hist-bar ${v >= 0 ? "up" : "down"}`,
            x: x.toFixed(1), width: barWidth.toFixed(1),
            y: Math.min(y0, y1).toFixed(1), height: Math.max(1, Math.abs(y1 - y0)).toFixed(1),
        }));
    });

    // MACD- och signallinjen (hoppar över de inledande punkterna utan värde).
    const macdCoords = macdLine.map((v, i) => (v === null ? null : `${xScale(i).toFixed(1)},${yScale(v).toFixed(1)}`)).filter(Boolean);
    const signalCoords = signalLine.map((v, i) => (v === null ? null : `${xScale(i).toFixed(1)},${yScale(v).toFixed(1)}`)).filter(Boolean);

    macdSvg.appendChild(svgEl("polyline", {
        points: macdCoords.join(" "), fill: "none", stroke: "#5b8cff", "stroke-width": "1.5",
        "vector-effect": "non-scaling-stroke",
    }));
    macdSvg.appendChild(svgEl("polyline", {
        points: signalCoords.join(" "), fill: "none", stroke: "var(--yellow)", "stroke-width": "1.5",
        "vector-effect": "non-scaling-stroke",
    }));

    // Y-axel: bara toppen och nollan, så panelen inte blir för rörig.
    macdSvg.appendChild(svgEl("text", {
        class: "chart-axis-label y", x: left - 6, y: plotTop + 4,
    })).textContent = maxAbs.toFixed(2);
    macdSvg.appendChild(svgEl("text", {
        class: "chart-axis-label y", x: left - 6, y: yScale(0).toFixed(1),
    })).textContent = "0";
}

async function loadChart(ticker, period) {
    try {
        const res = await fetch(`/api/chart/${encodeURIComponent(ticker)}?period=${period}`);
        const data = await res.json();
        drawChart(data, period);
    } catch (err) {
        chartSvg.innerHTML = "";
        currentChart = null;
        renderMACD();
    }
}

function drawChart(data, period) {
    chartSvg.innerHTML = "";
    currentChart = null;

    try {
        const points = data.points || [];
        if (points.length < 2) return;

        const closes = points.map((p) => p.close);
        const min = Math.min(...closes);
        const max = Math.max(...closes);
        const range = max - min || 1;

        const { width, height, marginLeft, marginRight, marginTop, marginBottom } = CHART_LAYOUT;
        const plot = { left: marginLeft, right: width - marginRight, top: marginTop, bottom: height - marginBottom };
        const plotWidth = plot.right - plot.left;
        const plotHeight = plot.bottom - plot.top;

        const xScale = (i) => plot.left + (points.length === 1 ? 0 : (i / (points.length - 1)) * plotWidth);
        const yScale = (price) => plot.top + (1 - (price - min) / range) * plotHeight;

        currentChart = { points, xScale, yScale, plot, currency: data.currency || "" };

        // Y-axel: prisnivåer + horisontella hjälplinjer.
        const yTickCount = 4;
        for (let t = 0; t <= yTickCount; t++) {
            const price = min + (range * t) / yTickCount;
            const y = yScale(price);
            chartSvg.appendChild(svgEl("line", {
                class: "chart-gridline", x1: plot.left, x2: plot.right, y1: y.toFixed(1), y2: y.toFixed(1),
            }));
            chartSvg.appendChild(svgEl("text", {
                class: "chart-axis-label y", x: plot.left - 6, y: y.toFixed(1),
            })).textContent = formatAxisPrice(price, max);
        }

        // X-axel: tidpunkter under grafen.
        const xTickCount = Math.min(5, points.length);
        for (let t = 0; t < xTickCount; t++) {
            const i = xTickCount === 1 ? 0 : Math.round((t / (xTickCount - 1)) * (points.length - 1));
            const x = xScale(i);
            chartSvg.appendChild(svgEl("text", {
                class: "chart-axis-label x", x: x.toFixed(1), y: plot.bottom + 16,
            })).textContent = formatAxisDate(new Date(points[i].t * 1000), period);
        }

        // Axellinjer.
        chartSvg.appendChild(svgEl("line", {
            class: "chart-axis-line", x1: plot.left, x2: plot.left, y1: plot.top, y2: plot.bottom,
        }));
        chartSvg.appendChild(svgEl("line", {
            class: "chart-axis-line", x1: plot.left, x2: plot.right, y1: plot.bottom, y2: plot.bottom,
        }));

        // Prislinjen.
        const rising = closes[closes.length - 1] >= closes[0];
        const color = rising ? "var(--green)" : "var(--red)";
        const coords = points.map((p, i) => `${xScale(i).toFixed(1)},${yScale(p.close).toFixed(1)}`);
        chartSvg.appendChild(svgEl("polyline", {
            points: coords.join(" "), fill: "none", stroke: color, "stroke-width": "2",
            "vector-effect": "non-scaling-stroke",
        }));
    } catch (err) {
        // Grafen är en extra funktion - misslyckas hämtningen lämnas den bara tom.
    } finally {
        renderMACD();
    }
}

// ---------------------------------------------------------------------------
// Betygsskalor: de tre inbyggda (549L-skalorna, motsvarar det som förut var
// tillväxt/stabil/vanlig-knapparna) + användarens egna, sparade skalor.
// currentScaleId styr vilken skala som används vid nästa analys och skickas
// som ?scale= till /api/analyze - "growth"/"stability" viktar om appens
// vanliga profiler precis som innan, "default" är oförändrat normalläge,
// "custom:<id>" är en egen skala.
// ---------------------------------------------------------------------------

const BUILTIN_SCALES = [
    { id: "growth", name: "549L Tillväxt Bolag" },
    { id: "stability", name: "549L Stabila Bolag" },
    { id: "default", name: "549L Vanliga bolag" },
];

// Listan visar bara de MAX_VISIBLE_SCALES högst rankade skalorna (obetygsatta
// sist) - sökrutan går igenom ALLA skalor utan den gränsen, så en skala som
// inte råkar ligga i topp-3 ändå går att hitta och välja.
const MAX_VISIBLE_SCALES = 3;

let currentScaleId = "default";
let customScales = [];
let scaleRatings = {}; // { rawId: {average, count} }
let scalesSearchQuery = "";

const scalesListEl = document.getElementById("scales-list");
const createScaleBtn = document.getElementById("create-scale-btn");
const scalesSearchInput = document.getElementById("scales-search");

function allScaleEntries() {
    const builtin = BUILTIN_SCALES.map((s) => ({ rawId: s.id, scaleId: s.id, name: s.name, isCustom: false }));
    const custom = customScales.map((s) => ({ rawId: s.id, scaleId: `custom:${s.id}`, name: s.name, isCustom: true, createdBy: s.created_by }));
    return [...builtin, ...custom];
}

async function loadScales() {
    try {
        const [scalesRes, ratingsRes] = await Promise.all([
            fetch("/api/scales"),
            fetch("/api/ratings"),
        ]);
        customScales = await scalesRes.json();
        scaleRatings = await ratingsRes.json();
    } catch (err) {
        customScales = [];
        scaleRatings = {};
    }
    renderScalesList();
}

function ratingFor(rawId) {
    return scaleRatings[rawId] || { average: null, count: 0 };
}

function renderScalesList() {
    scalesListEl.innerHTML = "";

    let entries = allScaleEntries();
    const q = scalesSearchQuery.trim().toLowerCase();
    if (q) {
        entries = entries.filter((e) => e.name.toLowerCase().includes(q));
    }

    // Högst betygsatta överst. Obetygsatta (average null) sorteras sist,
    // och behåller annars sin ursprungliga ordning (inbyggda skalor först).
    entries = entries
        .map((e, i) => ({ ...e, _rating: ratingFor(e.rawId), _order: i }))
        .sort((a, b) => {
            const ra = a._rating.average;
            const rb = b._rating.average;
            if (ra === null && rb === null) return a._order - b._order;
            if (ra === null) return 1;
            if (rb === null) return -1;
            return rb - ra;
        });

    if (!q) {
        entries = entries.slice(0, MAX_VISIBLE_SCALES);
    }

    if (entries.length === 0) {
        const li = document.createElement("li");
        li.className = "muted";
        li.textContent = "Inga betygsskalor matchade sökningen.";
        scalesListEl.appendChild(li);
        return;
    }

    entries.forEach((entry) => scalesListEl.appendChild(buildScaleRow(entry)));
}

function buildScaleRow(entry) {
    const { scaleId, rawId, name, isCustom, createdBy } = entry;
    const li = document.createElement("li");
    li.className = "scale-row" + (scaleId === currentScaleId ? " active" : "");

    const topRow = document.createElement("div");
    topRow.className = "scale-row-top";

    const nameSpan = document.createElement("span");
    nameSpan.className = "scale-row-name";
    nameSpan.textContent = name;
    nameSpan.addEventListener("click", () => selectScale(scaleId));
    topRow.appendChild(nameSpan);

    // Man får bara redigera/ta bort betygsskalor man själv skapat (en
    // admin undantaget) - annars skulle vem som helst inloggad kunna ändra
    // eller radera andras skalor. Servern kollar samma sak - det här är
    // bara för att inte ens visa knapparna när de ändå skulle nekas.
    const isOwnScale = isCustom && (createdBy === currentUsername || currentIsAdmin);

    if (isOwnScale) {
        const actions = document.createElement("span");
        actions.className = "scale-row-actions";

        const editBtn = document.createElement("button");
        editBtn.type = "button";
        editBtn.className = "scale-row-icon-btn";
        editBtn.textContent = "✎";
        editBtn.setAttribute("aria-label", `Redigera ${name}`);
        editBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            openScaleEditor(rawId);
        });
        actions.appendChild(editBtn);

        const deleteBtn = document.createElement("button");
        deleteBtn.type = "button";
        deleteBtn.className = "scale-row-icon-btn";
        deleteBtn.textContent = "✕";
        deleteBtn.setAttribute("aria-label", `Ta bort ${name}`);
        deleteBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            if (!confirm(`Ta bort betygsskalan "${name}"?`)) return;
            await fetch(`/api/scales/${rawId}`, { method: "DELETE" });
            if (currentScaleId === scaleId) selectScale("default");
            loadScales();
        });
        actions.appendChild(deleteBtn);

        topRow.appendChild(buildStarRating(rawId));
        topRow.appendChild(actions);
    } else {
        topRow.appendChild(buildStarRating(rawId));
    }

    li.appendChild(topRow);

    return li;
}

function buildStarRating(rawId) {
    const wrap = document.createElement("div");
    wrap.className = "star-rating";

    const rating = ratingFor(rawId);
    const filled = rating.average !== null ? Math.round(rating.average) : 0;

    for (let i = 1; i <= 5; i++) {
        const star = document.createElement("button");
        star.type = "button";
        star.className = "star" + (i <= filled ? " filled" : "");
        star.textContent = "★";
        star.setAttribute("aria-label", `Betygsätt ${i} av 5 stjärnor`);
        star.addEventListener("click", async (e) => {
            e.stopPropagation();
            if (!requireLogin("betygsätta en betygsskala")) return;
            try {
                const res = await fetch(`/api/scales/${rawId}/rating`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ stars: i }),
                });
                scaleRatings[rawId] = await res.json();
            } catch (err) {
                // Betyget är en extra funktion - misslyckas anropet lämnas listan bara oförändrad.
            }
            renderScalesList();
        });
        wrap.appendChild(star);
    }

    const countLabel = document.createElement("span");
    countLabel.className = "star-rating-count";
    countLabel.textContent = rating.count > 0
        ? `${rating.average.toFixed(1)} (${rating.count})`
        : "Inga betyg än";
    wrap.appendChild(countLabel);

    return wrap;
}

scalesSearchInput.addEventListener("input", () => {
    scalesSearchQuery = scalesSearchInput.value;
    renderScalesList();
});

function selectScale(scaleId) {
    currentScaleId = scaleId;
    renderScalesList();
    if (currentTicker) runAnalysis(currentTicker);
}

// Namnet på den just nu valda betygsskalan (inbyggd eller egen) - visas som
// en egen markering i analysrutan (se renderResult) så man alltid vet
// vilken skala man tittar på, istället för att sidans färg ändrades (togs
// bort - enda stället man numera ändrar sidans färg är i sin egen profil).
function currentScaleDisplayName() {
    const entry = allScaleEntries().find((e) => e.scaleId === currentScaleId);
    return entry ? entry.name : null;
}

// ---------------------------------------------------------------------------
// Sök användare - hittar konton på sidan och öppnar en profilsida med
// kontots betygsskalor, när det skapades, och ett stjärnbetyg (1-5) på
// själva kontot. Utan sökord visas bara de högst rankade kontona (samma
// mönster som betygsskalor-listan) - sökningen visar alla träffar,
// oavsett hur högt de är rankade.
// ---------------------------------------------------------------------------

const usersListEl = document.getElementById("users-list");
const usersEmptyEl = document.getElementById("users-empty");
const usersSearchInput = document.getElementById("users-search");
let usersSearchDebounce = null;

// Profilbild med bokstavsavatar som reserv - delas av kontofältet,
// användarlistan och profilsidan.
function avatarInitial(username) {
    return (username || "?").trim().charAt(0).toUpperCase();
}

function renderAvatarInto(el, username, avatarUrl) {
    el.innerHTML = "";
    if (avatarUrl) {
        const img = document.createElement("img");
        img.src = avatarUrl;
        img.alt = username;
        el.appendChild(img);
    } else {
        el.textContent = avatarInitial(username);
    }
}

async function loadUsers(query = "") {
    try {
        const res = await fetch(`/api/users?q=${encodeURIComponent(query)}`);
        renderUsersList(await res.json());
    } catch (err) {
        // Användarsökningen är en extra funktion - misslyckas hämtningen visar vi bara ingenting.
    }
}

function buildReadonlyStars(rating) {
    const wrap = document.createElement("div");
    wrap.className = "star-rating";
    const filled = rating.average !== null ? Math.round(rating.average) : 0;
    for (let i = 1; i <= 5; i++) {
        const star = document.createElement("span");
        star.className = "star" + (i <= filled ? " filled" : "");
        star.textContent = "★";
        wrap.appendChild(star);
    }
    const countLabel = document.createElement("span");
    countLabel.className = "star-rating-count";
    countLabel.textContent = rating.count > 0 ? `${rating.average.toFixed(1)} (${rating.count})` : "Inga betyg än";
    wrap.appendChild(countLabel);
    return wrap;
}

function renderUsersList(users) {
    usersListEl.innerHTML = "";
    if (users.length === 0) {
        usersEmptyEl.classList.remove("hidden");
        return;
    }
    usersEmptyEl.classList.add("hidden");

    users.forEach((user) => {
        const li = document.createElement("li");
        li.className = "scale-row";

        const topRow = document.createElement("div");
        topRow.className = "scale-row-top";

        // Avatar + namn hör ihop och ska aldrig separeras av en radbrytning
        // (till skillnad från stjärnbetyget, som gärna får hamna på en egen
        // rad när det är trångt) - därför en egen undergrupp här.
        const identity = document.createElement("span");
        identity.className = "user-row-identity";

        const avatar = document.createElement("span");
        avatar.className = "avatar avatar-sm";
        renderAvatarInto(avatar, user.username, user.avatar);
        identity.appendChild(avatar);

        const nameSpan = document.createElement("span");
        nameSpan.className = "scale-row-name";
        nameSpan.textContent = user.is_admin ? `${user.username} (admin)` : user.username;
        identity.appendChild(nameSpan);

        topRow.appendChild(identity);
        topRow.appendChild(buildReadonlyStars(user.rating));

        li.appendChild(topRow);
        li.addEventListener("click", () => openUserProfile(user.username));
        usersListEl.appendChild(li);
    });
}

usersSearchInput.addEventListener("input", () => {
    clearTimeout(usersSearchDebounce);
    const query = usersSearchInput.value;
    usersSearchDebounce = setTimeout(() => loadUsers(query), 250);
});

loadUsers();

// --- Användarens profilsida ---

const userProfileEl = document.getElementById("user-profile");
const userProfileAvatarEl = document.getElementById("user-profile-avatar");
const userProfileUsernameEl = document.getElementById("user-profile-username");
const userProfileMetaEl = document.getElementById("user-profile-meta");
const userProfileRatingEl = document.getElementById("user-profile-rating");
const userProfileScalesEl = document.getElementById("user-profile-scales");
const userProfileScalesEmptyEl = document.getElementById("user-profile-scales-empty");
const userProfileBackBtn = document.getElementById("user-profile-back");
const userProfileAvatarControlsEl = document.getElementById("user-profile-avatar-controls");
const userProfileAvatarInput = document.getElementById("user-profile-avatar-input");
const userProfileAvatarErrorEl = document.getElementById("user-profile-avatar-error");
const userProfileBioEl = document.getElementById("user-profile-bio");
const userProfileBioControlsEl = document.getElementById("user-profile-bio-controls");
const userProfileColorSectionEl = document.getElementById("user-profile-color-section");
const userProfileColorControlsEl = document.getElementById("user-profile-color-controls");
const userProfileFeedbackSectionEl = document.getElementById("user-profile-feedback-section");
const userProfileFeedbackListEl = document.getElementById("user-profile-feedback-list");
const userProfileFeedbackEmptyEl = document.getElementById("user-profile-feedback-empty");
const feedbackChartWrapEl = document.getElementById("feedback-chart-wrap");
const feedbackChartEl = document.getElementById("feedback-chart");
const feedbackChartLegendEl = document.getElementById("feedback-chart-legend");

// Egen accentfärg - ersätter --accent (se style.css) genom hela sidan när
// man är inloggad. Enda stället man kan ändra den är i sin egen profil -
// vilken betygsskala man valt påverkar den inte (se selectScale/renderResult
// för hur skalvalet istället visas, som en egen markering i analysrutan).
function applyAccentColor(color) {
    if (color) {
        document.documentElement.style.setProperty("--accent", color);
    } else {
        document.documentElement.style.removeProperty("--accent");
    }
}

// "Byt profilbild"/"Ta bort profilbild" byggs (och rivs ned) i DOM:en här
// istället för att bara döljas med CSS - så knapparna aldrig kan finnas
// kvar av misstag när man tittar på någon annans profil.
function renderOwnAvatarControls(isOwnProfile, hasAvatar) {
    userProfileAvatarControlsEl.querySelectorAll("button").forEach((btn) => btn.remove());
    userProfileAvatarControlsEl.classList.toggle("hidden", !isOwnProfile);
    if (!isOwnProfile) return;

    const changeBtn = document.createElement("button");
    changeBtn.type = "button";
    changeBtn.textContent = "Byt profilbild";
    changeBtn.addEventListener("click", () => userProfileAvatarInput.click());

    if (hasAvatar) {
        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.textContent = "Ta bort profilbild";
        removeBtn.addEventListener("click", removeOwnAvatar);
        userProfileAvatarInput.after(changeBtn, removeBtn);
    } else {
        userProfileAvatarInput.after(changeBtn);
    }
}

// Redigeringsfältet för biografin byggs (och rivs ned) i DOM:en på samma
// sätt som profilbildens knappar - existerar bara alls när man tittar på
// sitt eget konto, så det aldrig kan hamna kvar redigerbart på någon
// annans profil.
function renderOwnBioControls(isOwnProfile, bio) {
    userProfileBioControlsEl.innerHTML = "";
    userProfileBioControlsEl.classList.toggle("hidden", !isOwnProfile);
    if (!isOwnProfile) return;

    const textarea = document.createElement("textarea");
    textarea.className = "user-profile-bio-input";
    textarea.maxLength = 500;
    textarea.placeholder = "Skriv något om dig själv...";
    textarea.value = bio;

    const actions = document.createElement("div");
    actions.className = "user-profile-bio-actions";

    const saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.textContent = "Spara biografi";

    const errorEl = document.createElement("span");
    errorEl.className = "editor-error hidden";

    saveBtn.addEventListener("click", async () => {
        errorEl.classList.add("hidden");
        try {
            const res = await fetch("/api/me/bio", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ bio: textarea.value }),
            });
            const data = await res.json();
            if (!res.ok) {
                errorEl.textContent = data.error || "Kunde inte spara biografin.";
                errorEl.classList.remove("hidden");
                return;
            }
            textarea.value = data.bio;
            userProfileBioEl.textContent = data.bio || "Ingen biografi än.";
        } catch (err) {
            errorEl.textContent = "Nätverksfel: kunde inte nå servern.";
            errorEl.classList.remove("hidden");
        }
    });

    actions.appendChild(saveBtn);
    actions.appendChild(errorEl);
    userProfileBioControlsEl.appendChild(textarea);
    userProfileBioControlsEl.appendChild(actions);
}

// Färgväljaren byggs (och rivs ned) i DOM:en på samma sätt som
// biografins redigeringsfält - existerar bara alls när man tittar på
// sitt eget konto.
function renderOwnColorControls(isOwnProfile, color) {
    userProfileColorControlsEl.innerHTML = "";
    userProfileColorSectionEl.classList.toggle("hidden", !isOwnProfile);
    if (!isOwnProfile) return;

    const colorInput = document.createElement("input");
    colorInput.type = "color";
    colorInput.value = color || "#f5c518";

    const saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.textContent = "Spara färg";

    const errorEl = document.createElement("span");
    errorEl.className = "editor-error hidden";

    saveBtn.addEventListener("click", async () => {
        errorEl.classList.add("hidden");
        try {
            const res = await fetch("/api/me/color", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ color: colorInput.value }),
            });
            const data = await res.json();
            if (!res.ok) {
                errorEl.textContent = data.error || "Kunde inte spara färgen.";
                errorEl.classList.remove("hidden");
                return;
            }
            currentAccentColor = data.accent_color;
            applyAccentColor(currentAccentColor);
            renderOwnColorControls(true, currentAccentColor);
        } catch (err) {
            errorEl.textContent = "Nätverksfel: kunde inte nå servern.";
            errorEl.classList.remove("hidden");
        }
    });

    userProfileColorControlsEl.appendChild(colorInput);
    userProfileColorControlsEl.appendChild(saveBtn);

    if (color) {
        const resetBtn = document.createElement("button");
        resetBtn.type = "button";
        resetBtn.className = "login-toggle-btn";
        resetBtn.textContent = "Återställ till standard";
        resetBtn.addEventListener("click", async () => {
            errorEl.classList.add("hidden");
            try {
                const res = await fetch("/api/me/color", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ color: null }),
                });
                const data = await res.json();
                if (!res.ok) {
                    errorEl.textContent = data.error || "Kunde inte återställa färgen.";
                    errorEl.classList.remove("hidden");
                    return;
                }
                currentAccentColor = data.accent_color;
                applyAccentColor(currentAccentColor);
                renderOwnColorControls(true, currentAccentColor);
            } catch (err) {
                errorEl.textContent = "Nätverksfel: kunde inte nå servern.";
                errorEl.classList.remove("hidden");
            }
        });
        userProfileColorControlsEl.appendChild(resetBtn);
    }

    userProfileColorControlsEl.appendChild(errorEl);
}

function formatAccountDate(timestamp) {
    if (!timestamp) return "okänt datum";
    return new Date(timestamp * 1000).toLocaleDateString("sv-SE", { year: "numeric", month: "long", day: "numeric" });
}

// Feedback-listan visas bara på 549L:s (adminkontots) EGEN profil - byggs
// (och rivs ned) i DOM:en på samma sätt som avatar/biografi/färg-
// kontrollerna ovan, så den aldrig kan hamna kvar synlig av misstag på
// någon annans profil. Servern nekar ändå GET /api/feedback för alla
// andra (se app.py), det här är bara för att slippa ett onödigt
// 403-anrop/en tom ruta för alla utom en.
async function renderOwnFeedbackSection(showFeedback) {
    userProfileFeedbackSectionEl.classList.toggle("hidden", !showFeedback);
    if (!showFeedback) return;

    userProfileFeedbackListEl.innerHTML = "";
    feedbackChartWrapEl.classList.add("hidden");
    try {
        const res = await fetch("/api/feedback");
        if (!res.ok) return;
        const entries = await res.json();

        renderFeedbackChart(entries);

        if (entries.length === 0) {
            userProfileFeedbackEmptyEl.classList.remove("hidden");
            return;
        }
        userProfileFeedbackEmptyEl.classList.add("hidden");

        entries.forEach((entry) => {
            const li = document.createElement("li");

            const textEl = document.createElement("span");
            textEl.className = "feedback-list-text";
            textEl.textContent = entry.text;
            li.appendChild(textEl);

            const metaEl = document.createElement("span");
            metaEl.className = "feedback-list-meta";
            metaEl.textContent = `${entry.username} · ${formatAccountDate(entry.created_at)}`;
            li.appendChild(metaEl);

            userProfileFeedbackListEl.appendChild(li);
        });
    } catch (err) {
        // Feedbacklistan är en extra funktion - misslyckas hämtningen visas bara inget.
    }
}

function buildInteractiveUserStars(username, rating) {
    const wrap = document.createElement("div");
    wrap.className = "star-rating";
    const filled = rating.average !== null ? Math.round(rating.average) : 0;

    for (let i = 1; i <= 5; i++) {
        const star = document.createElement("button");
        star.type = "button";
        star.className = "star" + (i <= filled ? " filled" : "");
        star.textContent = "★";
        star.setAttribute("aria-label", `Betygsätt ${i} av 5 stjärnor`);
        star.addEventListener("click", async () => {
            if (!requireLogin("betygsätta en användare")) return;
            try {
                const res = await fetch(`/api/users/${encodeURIComponent(username)}/rating`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ stars: i }),
                });
                const updated = await res.json();
                userProfileRatingEl.innerHTML = "";
                userProfileRatingEl.appendChild(buildInteractiveUserStars(username, updated));
                loadUsers(usersSearchInput.value);
            } catch (err) {
                // Betyget är en extra funktion - misslyckas anropet ändras inget.
            }
        });
        wrap.appendChild(star);
    }

    const countLabel = document.createElement("span");
    countLabel.className = "star-rating-count";
    countLabel.textContent = rating.count > 0 ? `${rating.average.toFixed(1)} (${rating.count})` : "Inga betyg än";
    wrap.appendChild(countLabel);

    return wrap;
}

async function openUserProfile(username) {
    // Fail-safe: nollställ kontrollerna direkt, innan vi ens vet vem som är
    // inloggad - går hämtningen nedan fel ska "Byt profilbild"/biografins
    // redigeringsfält ändå aldrig kunna hamna synligt av misstag.
    renderOwnAvatarControls(false, false);
    renderOwnBioControls(false, "");
    renderOwnColorControls(false, null);
    renderOwnFeedbackSection(false);

    try {
        const [profileRes, meRes] = await Promise.all([
            fetch(`/api/users/${encodeURIComponent(username)}`),
            fetch("/api/me"),
        ]);
        const account = await profileRes.json();
        if (!profileRes.ok) return;

        // Kollar vem som faktiskt är inloggad just nu (istället för att lita
        // på den lokala `currentUsername`-variabeln) så att "Byt profilbild"
        // aldrig kan hamna kvar synlig på någon annans profil.
        const me = await meRes.json();

        renderAvatarInto(userProfileAvatarEl, account.username, account.avatar);
        userProfileUsernameEl.textContent = account.is_admin ? `${account.username} (admin)` : account.username;
        userProfileMetaEl.textContent = `Medlem sedan ${formatAccountDate(account.created_at)}`;

        const isOwnProfile = Boolean(me.username) && account.username === me.username;
        renderOwnAvatarControls(isOwnProfile, isOwnProfile && Boolean(account.avatar));
        userProfileAvatarErrorEl.classList.add("hidden");
        renderOwnFeedbackSection(isOwnProfile && Boolean(me.is_admin));

        userProfileBioEl.textContent = account.bio || "Ingen biografi än.";
        renderOwnBioControls(isOwnProfile, account.bio || "");
        renderOwnColorControls(isOwnProfile, account.accent_color || null);

        userProfileRatingEl.innerHTML = "";
        userProfileRatingEl.appendChild(buildInteractiveUserStars(account.username, account.rating));

        userProfileScalesEl.innerHTML = "";
        if (account.scales.length === 0) {
            userProfileScalesEmptyEl.classList.remove("hidden");
        } else {
            userProfileScalesEmptyEl.classList.add("hidden");
            account.scales.forEach((scale) => {
                const li = document.createElement("li");
                li.className = "scale-row";

                const topRow = document.createElement("div");
                topRow.className = "scale-row-top";
                const nameSpan = document.createElement("span");
                nameSpan.className = "scale-row-name";
                nameSpan.textContent = scale.name;
                if (scale.color) nameSpan.style.color = scale.color;
                topRow.appendChild(nameSpan);
                li.appendChild(topRow);

                li.appendChild(buildReadonlyStars(scale.rating));
                li.addEventListener("click", () => {
                    closeUserProfile();
                    selectScale(scale.is_builtin ? scale.id : `custom:${scale.id}`);
                });
                userProfileScalesEl.appendChild(li);
            });
        }

        mainViewEl.classList.add("hidden");
        scaleEditorEl.classList.add("hidden");
        userProfileEl.classList.remove("hidden");
        window.scrollTo(0, 0);
    } catch (err) {
        // Går inte att öppna profilen - lämna kvar där man var.
    }
}

function closeUserProfile() {
    userProfileEl.classList.add("hidden");
    mainViewEl.classList.remove("hidden");
}

userProfileBackBtn.addEventListener("click", closeUserProfile);

// --- Profilbild - läses in lokalt, skalas ned till max 200px och
// komprimeras till JPEG i webbläsaren innan uppladdning, så att en stor
// telefonbild aldrig skickas rå till servern/Redis. ---

function resizeImageFile(file, maxSize = 200, quality = 0.85) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error("Kunde inte läsa filen."));
        reader.onload = () => {
            const img = new Image();
            img.onerror = () => reject(new Error("Filen är inte en giltig bild."));
            img.onload = () => {
                const scale = Math.min(1, maxSize / Math.max(img.width, img.height));
                const w = Math.round(img.width * scale);
                const h = Math.round(img.height * scale);
                const canvas = document.createElement("canvas");
                canvas.width = w;
                canvas.height = h;
                canvas.getContext("2d").drawImage(img, 0, 0, w, h);
                resolve(canvas.toDataURL("image/jpeg", quality));
            };
            img.src = reader.result;
        };
        reader.readAsDataURL(file);
    });
}

userProfileAvatarInput.addEventListener("change", async () => {
    const file = userProfileAvatarInput.files[0];
    userProfileAvatarInput.value = "";
    if (!file) return;

    userProfileAvatarErrorEl.classList.add("hidden");
    if (!file.type.startsWith("image/")) {
        userProfileAvatarErrorEl.textContent = "Välj en bildfil.";
        userProfileAvatarErrorEl.classList.remove("hidden");
        return;
    }

    try {
        const dataUrl = await resizeImageFile(file);
        const res = await fetch("/api/me/avatar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image: dataUrl }),
        });
        const data = await res.json();
        if (!res.ok) {
            userProfileAvatarErrorEl.textContent = data.error || "Kunde inte spara profilbilden.";
            userProfileAvatarErrorEl.classList.remove("hidden");
            return;
        }
        currentAvatar = data.avatar;
        renderAvatarInto(userProfileAvatarEl, currentUsername, currentAvatar);
        renderAccountAvatar();
        renderOwnAvatarControls(true, true);
        loadUsers(usersSearchInput.value);
    } catch (err) {
        userProfileAvatarErrorEl.textContent = "Kunde inte läsa eller skala om bilden.";
        userProfileAvatarErrorEl.classList.remove("hidden");
    }
});

async function removeOwnAvatar() {
    try {
        await fetch("/api/me/avatar", { method: "DELETE" });
    } catch (err) {
        // Misslyckas anropet nätverksmässigt - lämna bilden orörd.
        return;
    }
    currentAvatar = null;
    renderAvatarInto(userProfileAvatarEl, currentUsername, null);
    renderAccountAvatar();
    renderOwnAvatarControls(true, false);
    loadUsers(usersSearchInput.value);
}

// ---------------------------------------------------------------------------
// Skalredigeraren - skapa/redigera en egen betygsskala. Öppnas som en egen
// fullbred sektion (#scale-editor) som ersätter huvudinnehållet (#main-view)
// tills man går tillbaka, istället för en trång modal - det behövs plats
// för branschflikar + en hel nyckeltalslista.
// ---------------------------------------------------------------------------

let metricCatalog = [];
let metricCatalogByKey = {};
let builtinProfileRows = {};

let editorScaleId = null; // null = skapar ny skala, annars id på skalan som redigeras
let editorSlots = {};     // { "default": [rader...], "sector:X": [rader...] }
let editorActiveSlot = "default";

const mainViewEl = document.getElementById("main-view");
const scaleEditorEl = document.getElementById("scale-editor");
const scaleEditorTitle = document.getElementById("scale-editor-title");
const scaleEditorBack = document.getElementById("scale-editor-back");
const scaleNameInput = document.getElementById("scale-name-input");
const scaleSectorTabsEl = document.getElementById("scale-sector-tabs");
const copyBuiltinSelect = document.getElementById("copy-builtin-select");
const copyBuiltinBtn = document.getElementById("copy-builtin-btn");
const weightIndicatorEl = document.getElementById("scale-weight-indicator");
const metricRowsEl = document.getElementById("scale-metric-rows");
const addMetricBtn = document.getElementById("add-metric-btn");
const metricPickerEl = document.getElementById("metric-picker");
const metricPickerSearch = document.getElementById("metric-picker-search");
const metricPickerList = document.getElementById("metric-picker-list");
const scaleSaveBtn = document.getElementById("scale-save-btn");
const scaleEditorError = document.getElementById("scale-editor-error");

const SECTOR_TAB_LABELS = { "default": "Standard (alla branscher)" };

async function loadEditorData() {
    if (metricCatalog.length > 0) return; // ladda katalogen/profilerna bara en gång
    try {
        const [catalogRes, profilesRes] = await Promise.all([
            fetch("/api/metric-catalog"),
            fetch("/api/builtin-profiles"),
        ]);
        metricCatalog = await catalogRes.json();
        metricCatalogByKey = Object.fromEntries(metricCatalog.map((m) => [m.key, m]));
        builtinProfileRows = await profilesRes.json();
    } catch (err) {
        metricCatalog = [];
        metricCatalogByKey = {};
        builtinProfileRows = {};
    }
}

async function openScaleEditor(existingId) {
    await loadEditorData();
    scaleEditorError.classList.add("hidden");

    if (existingId) {
        editorScaleId = existingId;
        scaleEditorTitle.textContent = "Redigera betygsskala";
        editorSlots = { default: [] };
        try {
            const res = await fetch(`/api/scales/${existingId}`);
            const record = await res.json();
            scaleNameInput.value = record.name;
            editorSlots = {};
            Object.entries(record.profiles).forEach(([key, slot]) => {
                editorSlots[key] = slot.metrics.map((m) => ({ ...m }));
            });
        } catch (err) {
            scaleNameInput.value = "";
        }
    } else {
        editorScaleId = null;
        scaleEditorTitle.textContent = "Skapa egen betygsskala";
        scaleNameInput.value = "";
        editorSlots = { default: [] };
    }

    editorActiveSlot = "default";
    renderSectorTabs();
    renderCopyBuiltinOptions();
    renderMetricRows();
    metricPickerEl.classList.add("hidden");

    mainViewEl.classList.add("hidden");
    scaleEditorEl.classList.remove("hidden");
    window.scrollTo(0, 0);
}

function closeScaleEditor() {
    scaleEditorEl.classList.add("hidden");
    mainViewEl.classList.remove("hidden");
}

createScaleBtn.addEventListener("click", () => {
    if (!requireLogin("skapa en egen betygsskala")) return;
    openScaleEditor(null);
});
scaleEditorBack.addEventListener("click", closeScaleEditor);

function currentSlotRows() {
    if (!editorSlots[editorActiveSlot]) editorSlots[editorActiveSlot] = [];
    return editorSlots[editorActiveSlot];
}

function renderSectorTabs() {
    scaleSectorTabsEl.innerHTML = "";
    Object.keys(builtinProfileRows).forEach((key) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "scale-sector-tab" + (key === editorActiveSlot ? " active" : "");
        const hasOverride = key !== "default" && editorSlots[key] && editorSlots[key].length > 0;
        const label = SECTOR_TAB_LABELS[key] || builtinProfileRows[key].label;
        btn.textContent = hasOverride ? `${label} ●` : label;
        btn.addEventListener("click", () => {
            editorActiveSlot = key;
            renderSectorTabs();
            renderCopyBuiltinOptions();
            renderMetricRows();
        });
        scaleSectorTabsEl.appendChild(btn);
    });
}

function renderCopyBuiltinOptions() {
    copyBuiltinSelect.innerHTML = "";
    Object.entries(builtinProfileRows).forEach(([key, profile]) => {
        const opt = document.createElement("option");
        opt.value = key;
        opt.textContent = profile.label;
        copyBuiltinSelect.appendChild(opt);
    });
    copyBuiltinSelect.value = editorActiveSlot in builtinProfileRows ? editorActiveSlot : "default";
}

copyBuiltinBtn.addEventListener("click", () => {
    const source = builtinProfileRows[copyBuiltinSelect.value];
    if (!source) return;
    editorSlots[editorActiveSlot] = source.metrics.map((m) => ({ ...m }));
    renderSectorTabs();
    renderMetricRows();
});

function formatRowValue(value, unit) {
    const shown = unit === "%" ? value * 100 : value;
    return Math.round(shown * 100) / 100;
}

function formatCurveNumber(value, unit) {
    const n = Math.round(value * 100) / 100;
    return unit === "%" ? `${(n * 100).toFixed(1)}%` : unit === "x" ? `${n}x` : `${n}`;
}

// Ritar exakt samma klockformade avklingningskurva som scoring.py faktiskt
// räknar ut betyget med (_gaussian_falloff, sigma = tolerans/2.5) - så
// bilden visar verkligheten, inte bara en illustration. Strecket vid
// "idealvärde ± tolerans" är där betyget faller till ~13 poäng, precis som
// i den riktiga uträkningen.
function buildToleranceCurveSvg(type, ideal, tolerance, unit) {
    const width = 260, height = 74, padX = 12, padY = 10;
    const plotW = width - padX * 2, plotH = height - padY * 2;
    const sigma = Math.max(tolerance, 1e-9) / 2.5;
    const span = tolerance * 1.6;
    const xMin = ideal - span;
    const xMax = ideal + span;

    const scoreAt = (v) => {
        if (type === "higher_better") return v >= ideal ? 100 : 100 * Math.exp(-0.5 * ((ideal - v) / sigma) ** 2);
        if (type === "lower_better") return v <= ideal ? 100 : 100 * Math.exp(-0.5 * ((v - ideal) / sigma) ** 2);
        return 100 * Math.exp(-0.5 * ((v - ideal) / sigma) ** 2);
    };
    const xScale = (v) => padX + ((v - xMin) / (xMax - xMin)) * plotW;
    const yScale = (score) => padY + (1 - score / 100) * plotH;

    const steps = 48;
    let path = "";
    for (let i = 0; i <= steps; i++) {
        const v = xMin + (i / steps) * (xMax - xMin);
        path += (i === 0 ? "M" : "L") + xScale(v).toFixed(1) + "," + yScale(scoreAt(v)).toFixed(1) + " ";
    }

    const idealX = xScale(ideal).toFixed(1);
    const edgeXs = type === "target"
        ? [xScale(ideal - tolerance).toFixed(1), xScale(ideal + tolerance).toFixed(1)]
        : type === "higher_better"
            ? [xScale(ideal - tolerance).toFixed(1)]
            : [xScale(ideal + tolerance).toFixed(1)];

    const edgeLines = edgeXs.map((x) => `<line x1="${x}" y1="${padY}" x2="${x}" y2="${height - padY}" class="tolerance-edge-line"/>`).join("");

    return `
        <svg viewBox="0 0 ${width} ${height}" class="tolerance-curve" aria-hidden="true">
            <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" class="tolerance-axis"/>
            <path d="${path}" class="tolerance-path"/>
            ${edgeLines}
            <line x1="${idealX}" y1="${padY}" x2="${idealX}" y2="${height - padY}" class="tolerance-ideal-line"/>
            <circle cx="${idealX}" cy="${yScale(100).toFixed(1)}" r="3" class="tolerance-ideal-dot"/>
        </svg>
        <div class="tolerance-visual-caption">
            <span><span class="tolerance-dot-legend"></span> Idealvärde: <strong>${formatCurveNumber(ideal, unit)}</strong></span>
            <span><span class="tolerance-edge-legend"></span> Blir dåligt betyg vid: <strong>${edgeXs.length === 2
                ? `${formatCurveNumber(ideal - tolerance, unit)} / ${formatCurveNumber(ideal + tolerance, unit)}`
                : formatCurveNumber(type === "higher_better" ? ideal - tolerance : ideal + tolerance, unit)}</strong></span>
        </div>
    `;
}

function renderMetricRows() {
    const rows = currentSlotRows();
    metricRowsEl.innerHTML = "";

    if (rows.length === 0) {
        const li = document.createElement("li");
        li.className = "muted scale-metric-empty";
        li.textContent = editorActiveSlot === "default"
            ? "Inga nyckeltal ännu - lägg till minst ett med knappen nedan."
            : "Inget branschöverlägg - den här branschen använder skalans standarduppsättning tills du lägger till nyckeltal här.";
        metricRowsEl.appendChild(li);
        updateWeightIndicator();
        return;
    }

    rows.forEach((row, index) => {
        const catalogEntry = metricCatalogByKey[row.key];
        if (!catalogEntry) return;
        const unit = catalogEntry.unit;
        const unitSuffix = unit === "%" ? " (%)" : unit === "x" ? " (x)" : "";
        const weightPct = formatRowValue(row.weight_pct, "");

        const li = document.createElement("li");
        li.className = "scale-metric-row";
        li.innerHTML = `
            <div class="scale-metric-row-header">
                <span class="scale-metric-label">${catalogEntry.label}</span>
                <button type="button" class="scale-metric-remove" aria-label="Ta bort ${catalogEntry.label}">✕</button>
            </div>
            <div class="scale-metric-row-body">
                <div class="weight-slider-wrap">
                    <span class="weight-slider-value">${weightPct}%</span>
                    <div class="weight-slider-track">
                        <input type="range" min="1" max="100" step="1" class="row-weight weight-slider" value="${weightPct}">
                    </div>
                    <span class="weight-slider-caption">Vikt - dra för att höja/sänka</span>
                </div>
                <div class="tolerance-panel">
                    <div class="tolerance-visual"></div>
                    <div class="tolerance-inputs">
                        <label class="scale-metric-input">Idealvärde${unitSuffix}
                            <input type="number" step="any" class="row-ideal" value="${formatRowValue(row.ideal, unit)}">
                        </label>
                        <label class="scale-metric-input">Tolerans${unitSuffix}
                            <input type="number" step="any" min="0" class="row-tolerance" value="${formatRowValue(row.tolerance, unit)}">
                        </label>
                    </div>
                </div>
            </div>
        `;

        const visualEl = li.querySelector(".tolerance-visual");
        const refreshCurve = () => {
            visualEl.innerHTML = buildToleranceCurveSvg(catalogEntry.type, row.ideal, row.tolerance || 1e-9, unit);
        };
        refreshCurve();

        const weightSlider = li.querySelector(".row-weight");
        const weightValueEl = li.querySelector(".weight-slider-value");
        weightSlider.addEventListener("input", (e) => {
            row.weight_pct = parseFloat(e.target.value) || 0;
            weightValueEl.textContent = `${row.weight_pct}%`;
            updateWeightSliderCaps();
            updateWeightIndicator();
        });
        li.querySelector(".row-ideal").addEventListener("input", (e) => {
            const raw = parseFloat(e.target.value) || 0;
            row.ideal = unit === "%" ? raw / 100 : raw;
            refreshCurve();
        });
        li.querySelector(".row-tolerance").addEventListener("input", (e) => {
            const raw = parseFloat(e.target.value) || 0;
            row.tolerance = unit === "%" ? raw / 100 : raw;
            refreshCurve();
        });
        li.querySelector(".scale-metric-remove").addEventListener("click", () => {
            rows.splice(index, 1);
            renderSectorTabs();
            renderMetricRows();
        });

        metricRowsEl.appendChild(li);
    });

    updateWeightSliderCaps();
    updateWeightIndicator();
}

// Håller varje viktslider inom det utrymme som faktiskt finns kvar (100%
// minus vad de ANDRA nyckeltalen i samma bransch/standard-uppsättning redan
// väger) - man kan alltså inte dra upp en vikt så att summan går över 100%,
// utan måste sänka en annan vikt först för att få utrymme.
function updateWeightSliderCaps() {
    const rows = currentSlotRows();

    // Städa eventuellt överskott (t.ex. efter "kopiera nyckeltal" eller en
    // inläst skala vars vikter råkar summera till över 100%) genom att gå
    // igenom raderna i ordning och dra ner EN i taget mot en löpande total -
    // annars skulle varje överskriden rad klippas mot samma (för höga)
    // starttotal och tillsammans sänka summan långt under 100%.
    let total = rows.reduce((sum, r) => sum + (r.weight_pct || 0), 0);
    rows.forEach((row) => {
        const othersSum = total - row.weight_pct;
        const max = Math.max(1, Math.floor(100 - othersSum));
        if (row.weight_pct > max) {
            total -= row.weight_pct - max;
            row.weight_pct = max;
        }
    });

    metricRowsEl.querySelectorAll(".row-weight").forEach((slider, i) => {
        const row = rows[i];
        if (!row) return;
        const othersSum = total - row.weight_pct;
        slider.max = Math.max(1, Math.floor(100 - othersSum));
        if (parseFloat(slider.value) !== row.weight_pct) {
            slider.value = row.weight_pct;
            const valueEl = slider.closest(".weight-slider-wrap").querySelector(".weight-slider-value");
            if (valueEl) valueEl.textContent = `${row.weight_pct}%`;
        }
    });
}

function updateWeightIndicator() {
    const total = currentSlotRows().reduce((sum, r) => sum + (r.weight_pct || 0), 0);
    weightIndicatorEl.textContent = `Vikt: ${Math.round(total)}% av 100%`;
    weightIndicatorEl.classList.remove("weight-ok", "weight-off");
    weightIndicatorEl.classList.add(Math.abs(total - 100) <= 2 ? "weight-ok" : "weight-off");
}

addMetricBtn.addEventListener("click", () => {
    metricPickerSearch.value = "";
    renderMetricPicker("");
    metricPickerEl.classList.remove("hidden");
    metricPickerSearch.focus();
});

metricPickerSearch.addEventListener("input", () => renderMetricPicker(metricPickerSearch.value));

function renderMetricPicker(query) {
    const usedKeys = new Set(currentSlotRows().map((r) => r.key));
    const q = query.trim().toLowerCase();

    metricPickerList.innerHTML = "";
    metricCatalog
        .filter((m) => !usedKeys.has(m.key))
        .filter((m) => !q || m.label.toLowerCase().includes(q))
        .forEach((m) => {
            const li = document.createElement("li");
            li.textContent = m.label;
            li.addEventListener("mousedown", (e) => {
                e.preventDefault();
                const rows = currentSlotRows();
                // Ett nytt nyckeltal ska bara ta det utrymme som faktiskt
                // finns kvar - inte tvinga ner de vikter du redan satt.
                const usedWeight = rows.reduce((sum, r) => sum + (r.weight_pct || 0), 0);
                const headroom = Math.max(1, Math.floor(100 - usedWeight));
                rows.push({
                    key: m.key,
                    weight_pct: Math.min(Math.round(m.default_weight * 100), headroom),
                    ideal: m.default_ideal,
                    tolerance: m.default_tolerance,
                });
                metricPickerEl.classList.add("hidden");
                renderSectorTabs();
                renderMetricRows();
            });
            metricPickerList.appendChild(li);
        });

    if (metricPickerList.children.length === 0) {
        const li = document.createElement("li");
        li.className = "muted";
        li.textContent = "Inga fler nyckeltal att lägga till.";
        metricPickerList.appendChild(li);
    }
}

document.addEventListener("click", (e) => {
    if (!metricPickerEl.classList.contains("hidden") && !metricPickerEl.contains(e.target) && e.target !== addMetricBtn) {
        metricPickerEl.classList.add("hidden");
    }
});

scaleSaveBtn.addEventListener("click", async () => {
    if (!requireLogin("spara en betygsskala")) return;
    const name = scaleNameInput.value.trim();
    scaleEditorError.classList.add("hidden");

    const profiles = {};
    Object.entries(editorSlots).forEach(([key, rows]) => {
        if (rows.length === 0) return;
        profiles[key] = {
            metrics: rows.map((r) => ({ key: r.key, weight_pct: r.weight_pct, ideal: r.ideal, tolerance: r.tolerance })),
        };
    });

    const url = editorScaleId ? `/api/scales/${editorScaleId}` : "/api/scales";
    const method = editorScaleId ? "PUT" : "POST";

    try {
        const res = await fetch(url, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, profiles }),
        });
        const data = await res.json();
        if (!res.ok) {
            scaleEditorError.textContent = data.error || "Kunde inte spara betygsskalan.";
            scaleEditorError.classList.remove("hidden");
            return;
        }
        closeScaleEditor();
        await loadScales();
        selectScale(`custom:${data.id}`);
    } catch (err) {
        scaleEditorError.textContent = "Nätverksfel: kunde inte nå servern.";
        scaleEditorError.classList.remove("hidden");
    }
});

// ---------------------------------------------------------------------------
// Inloggning - hela sidan är låst bakom ett konto (bara användarnamn +
// lösenord, se users_store.py). #app-content initieras (sökning, skalor,
// historik osv.) först efter att /api/me bekräftat en aktiv inloggning.
// ---------------------------------------------------------------------------

const loginGateEl = document.getElementById("login-gate");
const loginGateTitle = document.getElementById("login-gate-title");
const accountBarEl = document.getElementById("account-bar");
const accountAvatarEl = document.getElementById("account-avatar");
const accountUsernameEl = document.getElementById("account-username");
const appContentEl = document.getElementById("app-content");
const loginForm = document.getElementById("login-form");
const authUsernameInput = document.getElementById("auth-username");
const authPasswordInput = document.getElementById("auth-password");
const loginError = document.getElementById("login-error");
const loginSubmitBtn = document.getElementById("login-submit-btn");
const loginToggleBtn = document.getElementById("login-toggle-btn");
const logoutBtn = document.getElementById("logout-btn");
const guestModeBtn = document.getElementById("guest-mode-btn");
const loginGateGuestNoticeEl = document.getElementById("login-gate-guest-notice");

let authMode = "login"; // "login" | "register"
let appInitialized = false;
let currentUsername = null;
let currentAvatar = null;
let currentAccentColor = null;
let currentIsAdmin = false;
// Gästläge: bläddra fritt (sök, analysera, se skalor/profiler/community/
// triggers) utan konto - men allt som kräver ett användarnamn (skapa en
// skala, rösta, skriva ett meddelande, ändra sin profil) är fortfarande
// stängt. Se requireLogin() nedan, som alla sådana knappar/formulär
// kollar mot innan de faktiskt gör något.
let isGuest = false;

// Kallas av alla knappar/formulär som kräver ett konto - visar
// inloggningsvyn med en förklaring istället för att försöka anropet (som
// ändå bara skulle få 401 från servern) om man är gäst. Returnerar true
// om man FÅR gå vidare (dvs. inte gäst).
function requireLogin(actionText) {
    if (!isGuest) return true;
    showLoggedOut();
    loginGateGuestNoticeEl.textContent = `Logga in eller skapa ett konto för att ${actionText}.`;
    loginGateGuestNoticeEl.classList.remove("hidden");
    return false;
}

function renderAccountAvatar() {
    renderAvatarInto(accountAvatarEl, currentUsername, currentAvatar);
}

function goToOwnProfile() {
    if (isGuest) {
        requireLogin("se din profil");
        return;
    }
    if (currentUsername) openUserProfile(currentUsername);
}

accountAvatarEl.addEventListener("click", goToOwnProfile);
accountUsernameEl.addEventListener("click", goToOwnProfile);

// ---------------------------------------------------------------------------
// Community - namngivna, publika chattrum. Ett "General"-rum finns alltid,
// och vem som helst inloggad kan skapa fler, valfritt länkade till en
// specifik aktieticker - då dyker chatten upp i analysvyn för just den
// aktien (se checkResultChat). Pollar med jämna mellanrum medan man är
// inloggad så att andras nya meddelanden/rum dyker upp automatiskt.
// ---------------------------------------------------------------------------

let communityRooms = [];
let communitySearchQuery = "";
// Tickrar (t.ex. "AAPL") vars bolagsnamn matchar den senaste sökningen -
// slås upp asynkront via /api/search (samma endpoint som ticker-
// autocompleten) så man kan söka på "Apple" och hitta chattar länkade
// till AAPL, inte bara chattar som råkar heta "Apple" i sitt eget namn.
let communitySearchTickerMatches = new Set();
let communitySearchDebounce = null;
let communitySearchAbort = null;
let currentRoomId = null;

const communitySearchInput = document.getElementById("community-search");
const communityRoomsListEl = document.getElementById("community-rooms-list");
const createRoomBtn = document.getElementById("create-room-btn");
const createRoomFormEl = document.getElementById("create-room-form");
const newRoomNameInput = document.getElementById("new-room-name");
const newRoomTickerInput = document.getElementById("new-room-ticker");
const newRoomTickerSuggestionsEl = document.getElementById("new-room-ticker-suggestions");
const saveRoomBtn = document.getElementById("save-room-btn");
const cancelRoomBtn = document.getElementById("cancel-room-btn");
const createRoomErrorEl = document.getElementById("create-room-error");

createTickerAutocomplete(newRoomTickerInput, newRoomTickerSuggestionsEl, () => {});

function formatMessageTime(timestamp) {
    if (!timestamp) return "";
    return new Date(timestamp * 1000).toLocaleString("sv-SE", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
    });
}

async function loadCommunityRooms() {
    try {
        const res = await fetch("/api/community/rooms");
        communityRooms = await res.json();
    } catch (err) {
        communityRooms = [];
    }
    renderCommunityRoomsList();
}

// Samma mönster som MAX_VISIBLE_SCALES - utan sökord visas bara de tre
// första (General överst, sen senast aktiva) för en kort, städad
// standardlista. Sökrutan går igenom ALLA rum utan den gränsen.
const MAX_VISIBLE_ROOMS = 3;

function renderCommunityRoomsList() {
    communityRoomsListEl.innerHTML = "";
    const q = communitySearchQuery.trim().toLowerCase();
    const rooms = q
        ? communityRooms.filter((r) =>
            r.name.toLowerCase().includes(q) ||
            (r.ticker && r.ticker.toLowerCase().includes(q)) ||
            (r.ticker && communitySearchTickerMatches.has(r.ticker))
        )
        : communityRooms.slice(0, MAX_VISIBLE_ROOMS);

    if (rooms.length === 0) {
        const li = document.createElement("li");
        li.className = "muted";
        li.textContent = "Inga chattar matchade sökningen.";
        communityRoomsListEl.appendChild(li);
        return;
    }

    rooms.forEach((room) => {
        const li = document.createElement("li");
        li.className = "scale-row";

        const topRow = document.createElement("div");
        topRow.className = "scale-row-top";

        const nameSpan = document.createElement("span");
        nameSpan.className = "scale-row-name";
        nameSpan.textContent = room.name;
        topRow.appendChild(nameSpan);

        if (room.ticker) {
            const tickerTag = document.createElement("span");
            tickerTag.className = "room-ticker-tag";
            tickerTag.textContent = room.ticker;
            topRow.appendChild(tickerTag);
        }
        li.appendChild(topRow);

        const countSpan = document.createElement("span");
        countSpan.className = "muted room-message-count";
        countSpan.textContent = room.message_count > 0 ? `${room.message_count} meddelanden` : "Inga meddelanden än";
        li.appendChild(countSpan);

        li.addEventListener("click", () => openChatRoom(room.id));
        communityRoomsListEl.appendChild(li);
    });
}

communitySearchInput.addEventListener("input", () => {
    communitySearchQuery = communitySearchInput.value;
    renderCommunityRoomsList();

    clearTimeout(communitySearchDebounce);
    const query = communitySearchQuery.trim();
    if (query.length < 2) {
        communitySearchTickerMatches = new Set();
        return;
    }

    communitySearchDebounce = setTimeout(async () => {
        if (communitySearchAbort) communitySearchAbort.abort();
        communitySearchAbort = new AbortController();
        try {
            const res = await fetch(`/api/search/${encodeURIComponent(query)}`, {
                signal: communitySearchAbort.signal,
            });
            const matches = await res.json();
            communitySearchTickerMatches = new Set(matches.map((m) => m.symbol));
            renderCommunityRoomsList();
        } catch (err) {
            if (err.name !== "AbortError") communitySearchTickerMatches = new Set();
        }
    }, 250);
});

createRoomBtn.addEventListener("click", () => {
    if (!requireLogin("skapa en ny chatt")) return;
    createRoomFormEl.classList.toggle("hidden");
    createRoomErrorEl.classList.add("hidden");
    if (!createRoomFormEl.classList.contains("hidden")) {
        newRoomNameInput.focus();
    }
});

cancelRoomBtn.addEventListener("click", () => {
    createRoomFormEl.classList.add("hidden");
    newRoomNameInput.value = "";
    newRoomTickerInput.value = "";
    createRoomErrorEl.classList.add("hidden");
});

saveRoomBtn.addEventListener("click", async () => {
    if (!requireLogin("skapa en ny chatt")) return;
    const name = newRoomNameInput.value.trim();
    const ticker = newRoomTickerInput.value.trim();
    createRoomErrorEl.classList.add("hidden");

    try {
        const res = await fetch("/api/community/rooms", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, ticker }),
        });
        const data = await res.json();
        if (!res.ok) {
            createRoomErrorEl.textContent = data.error || "Kunde inte skapa chatten.";
            createRoomErrorEl.classList.remove("hidden");
            return;
        }
        newRoomNameInput.value = "";
        newRoomTickerInput.value = "";
        createRoomFormEl.classList.add("hidden");
        await loadCommunityRooms();
        openChatRoom(data.id);
    } catch (err) {
        createRoomErrorEl.textContent = "Nätverksfel: kunde inte nå servern.";
        createRoomErrorEl.classList.remove("hidden");
    }
});

// --- Själva chattrummet - en egen fullbred sektion, samma mönster som
// profilsidan/skalredigeraren (ersätter #main-view tills man går tillbaka). ---

const chatRoomEl = document.getElementById("chat-room");
const chatRoomBackBtn = document.getElementById("chat-room-back");
const chatRoomTitleEl = document.getElementById("chat-room-title");
const chatRoomMetaEl = document.getElementById("chat-room-meta");
const chatRoomTickerBtn = document.getElementById("chat-room-ticker-btn");
const chatRoomMessagesEl = document.getElementById("chat-room-messages");
const chatRoomEmptyEl = document.getElementById("chat-room-empty");
const chatRoomForm = document.getElementById("chat-room-form");
const chatRoomInput = document.getElementById("chat-room-input");
const chatRoomErrorEl = document.getElementById("chat-room-error");

// Ger varje användarnamn en egen, stabil färg (samma namn -> samma färg
// varje gång, ingen lagring behövs) så man snabbt kan skilja vem som
// skrivit vad i en chatt med flera deltagare - istället för att alla
// namn visades i samma (tidigare: --accent, alltså läsarens egen
// accentfärg efter förra ändringen) enda färg.
function usernameColor(username) {
    let hash = 0;
    for (let i = 0; i < username.length; i++) {
        hash = (hash << 5) - hash + username.charCodeAt(i);
        hash |= 0;
    }
    const hue = Math.abs(hash) % 360;
    return `hsl(${hue}, 65%, 65%)`;
}

function renderChatMessages(container, emptyEl, messages) {
    container.innerHTML = "";
    if (messages.length === 0) {
        if (emptyEl) emptyEl.classList.remove("hidden");
        return;
    }
    if (emptyEl) emptyEl.classList.add("hidden");

    messages.forEach((msg) => {
        const li = document.createElement("li");
        li.className = "community-message";

        const head = document.createElement("div");
        head.className = "community-message-head";

        const userSpan = document.createElement("span");
        userSpan.className = "community-message-user";
        userSpan.textContent = msg.username;
        userSpan.style.color = usernameColor(msg.username);
        userSpan.addEventListener("click", () => openUserProfile(msg.username));
        head.appendChild(userSpan);

        const timeSpan = document.createElement("span");
        timeSpan.className = "community-message-time";
        timeSpan.textContent = formatMessageTime(msg.created_at);
        head.appendChild(timeSpan);

        li.appendChild(head);

        const textDiv = document.createElement("div");
        textDiv.className = "community-message-text";
        textDiv.textContent = msg.text;
        li.appendChild(textDiv);

        container.appendChild(li);
    });

    container.scrollTop = container.scrollHeight;
}

async function loadChatRoom(roomId) {
    try {
        const res = await fetch(`/api/community/rooms/${roomId}`);
        if (!res.ok) return;
        const room = await res.json();
        chatRoomTitleEl.textContent = room.name;
        chatRoomMetaEl.textContent = room.ticker ? `Länkad till ${room.ticker}` : "Öppen för alla ämnen";
        if (room.ticker) {
            chatRoomTickerBtn.textContent = `📈 Se analys av ${room.ticker}`;
            chatRoomTickerBtn.dataset.ticker = room.ticker;
            chatRoomTickerBtn.classList.remove("hidden");
        } else {
            chatRoomTickerBtn.classList.add("hidden");
        }
        renderChatMessages(chatRoomMessagesEl, chatRoomEmptyEl, room.messages);
    } catch (err) {
        // Chatten är en extra funktion - misslyckas hämtningen visas bara inget nytt.
    }
}

async function openChatRoom(roomId) {
    currentRoomId = roomId;
    await loadChatRoom(roomId);
    mainViewEl.classList.add("hidden");
    scaleEditorEl.classList.add("hidden");
    userProfileEl.classList.add("hidden");
    chatRoomEl.classList.remove("hidden");
    window.scrollTo(0, 0);
    startChatRoomPolling();
}

function closeChatRoom() {
    currentRoomId = null;
    stopChatRoomPolling();
    chatRoomEl.classList.add("hidden");
    mainViewEl.classList.remove("hidden");
}

// Snabbväg från en aktielänkad chatt till samma akties analys - alltid
// med "549L Vanliga bolag" (den vanliga/oviktade skalan), oavsett vilken
// betygsskala man råkade ha valt innan man gick in i chatten.
chatRoomTickerBtn.addEventListener("click", () => {
    const ticker = chatRoomTickerBtn.dataset.ticker;
    if (!ticker) return;
    closeChatRoom();
    currentScaleId = "default";
    renderScalesList();
    document.getElementById("ticker-input").value = ticker;
    runAnalysis(ticker);
});

chatRoomBackBtn.addEventListener("click", closeChatRoom);

chatRoomForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!requireLogin("skriva i chatten")) return;
    const text = chatRoomInput.value.trim();
    if (!text || !currentRoomId) return;

    chatRoomErrorEl.classList.add("hidden");
    try {
        const res = await fetch(`/api/community/rooms/${currentRoomId}/messages`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
        });
        const data = await res.json();
        if (!res.ok) {
            chatRoomErrorEl.textContent = data.error || "Kunde inte skicka meddelandet.";
            chatRoomErrorEl.classList.remove("hidden");
            return;
        }
        chatRoomInput.value = "";
        loadChatRoom(currentRoomId);
        loadCommunityRooms();
    } catch (err) {
        chatRoomErrorEl.textContent = "Nätverksfel: kunde inte nå servern.";
        chatRoomErrorEl.classList.remove("hidden");
    }
});

// ---------------------------------------------------------------------------
// Triggers tidslinjen - en egen fullbred sektion (samma "ersätter
// #main-view"-mönster som profilsidan/chattrummet) med en horisontell
// tidslinje över upp till 20 handplockade, rankade potentiella triggers
// inom de närmaste ~2 månaderna (se triggers_data.py på serversidan).
// ---------------------------------------------------------------------------

const triggersLauncherBtn = document.getElementById("triggers-launcher");
const triggersTimelineEl = document.getElementById("triggers-timeline");
const triggersBackBtn = document.getElementById("triggers-back");
const triggersTimelineScrollEl = document.getElementById("triggers-timeline-scroll");
const triggersTimelineTrackEl = document.getElementById("triggers-timeline-track");
const triggersCountTabs = document.querySelectorAll(".triggers-count-tab");
const timelineScrubberTrackEl = document.getElementById("timeline-scrubber-track");
const timelineScrubberThumbEl = document.getElementById("timeline-scrubber-thumb");

let triggersData = [];
let triggersCount = 20;

// Eget draghandtag istället för webbläsarens vanliga (bottenplacerade)
// scrollbar - samma idé (dra för att scrolla sida till sida, handtagets
// bredd/position speglar hur stor del av tidslinjen som syns), bara
// flyttat till mitten av rutan och egen-stilat. thumb-bredden/positionen
// räknas om varje gång man scrollar (native scroll, t.ex. via styrplatta)
// och varje gång man drar handtaget själv.
function updateTimelineScrubber() {
    const trackWidth = timelineScrubberTrackEl.clientWidth;
    const contentWidth = triggersTimelineScrollEl.scrollWidth;
    const visibleWidth = triggersTimelineScrollEl.clientWidth;

    if (contentWidth <= visibleWidth || trackWidth === 0) {
        timelineScrubberThumbEl.style.width = "100%";
        timelineScrubberThumbEl.style.left = "0px";
        return;
    }

    const thumbWidth = Math.max(30, (visibleWidth / contentWidth) * trackWidth);
    const maxScrollLeft = contentWidth - visibleWidth;
    const maxThumbLeft = trackWidth - thumbWidth;
    const thumbLeft = maxScrollLeft > 0 ? (triggersTimelineScrollEl.scrollLeft / maxScrollLeft) * maxThumbLeft : 0;

    timelineScrubberThumbEl.style.width = `${thumbWidth}px`;
    timelineScrubberThumbEl.style.left = `${thumbLeft}px`;
}

function scrollTimelineTo(ratio) {
    const contentWidth = triggersTimelineScrollEl.scrollWidth;
    const visibleWidth = triggersTimelineScrollEl.clientWidth;
    const maxScrollLeft = Math.max(0, contentWidth - visibleWidth);
    triggersTimelineScrollEl.scrollLeft = Math.min(Math.max(ratio, 0), 1) * maxScrollLeft;
}

triggersTimelineScrollEl.addEventListener("scroll", updateTimelineScrubber);
window.addEventListener("resize", updateTimelineScrubber);

let scrubberDrag = null;

timelineScrubberThumbEl.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    scrubberDrag = { startX: e.clientX, startScrollLeft: triggersTimelineScrollEl.scrollLeft };
    timelineScrubberThumbEl.setPointerCapture(e.pointerId);
});

timelineScrubberThumbEl.addEventListener("pointermove", (e) => {
    if (!scrubberDrag) return;
    const trackWidth = timelineScrubberTrackEl.clientWidth;
    const thumbWidth = timelineScrubberThumbEl.offsetWidth;
    const contentWidth = triggersTimelineScrollEl.scrollWidth;
    const visibleWidth = triggersTimelineScrollEl.clientWidth;
    const maxThumbLeft = trackWidth - thumbWidth;
    const maxScrollLeft = contentWidth - visibleWidth;
    if (maxThumbLeft <= 0 || maxScrollLeft <= 0) return;

    const deltaX = e.clientX - scrubberDrag.startX;
    triggersTimelineScrollEl.scrollLeft = scrubberDrag.startScrollLeft + (deltaX / maxThumbLeft) * maxScrollLeft;
});

function endScrubberDrag(e) {
    if (!scrubberDrag) return;
    scrubberDrag = null;
    try {
        timelineScrubberThumbEl.releasePointerCapture(e.pointerId);
    } catch (err) {
        // redan släppt - inget att göra.
    }
}

timelineScrubberThumbEl.addEventListener("pointerup", endScrubberDrag);
timelineScrubberThumbEl.addEventListener("pointercancel", endScrubberDrag);

// Klick direkt på spåret (utanför handtaget) hoppar dit istället för att
// bara flytta ett litet steg, som en vanlig scrollbar.
timelineScrubberTrackEl.addEventListener("pointerdown", (e) => {
    if (e.target === timelineScrubberThumbEl) return;
    const rect = timelineScrubberTrackEl.getBoundingClientRect();
    const clickRatio = (e.clientX - rect.left) / rect.width;
    const contentWidth = triggersTimelineScrollEl.scrollWidth;
    const visibleWidth = triggersTimelineScrollEl.clientWidth;
    const centeredRatio = (clickRatio * contentWidth - visibleWidth / 2) / Math.max(1, contentWidth - visibleWidth);
    scrollTimelineTo(centeredRatio);
});

async function loadTriggers() {
    triggersTimelineTrackEl.innerHTML = "";
    try {
        const res = await fetch("/api/triggers");
        const data = await res.json();
        triggersData = data.triggers || [];
    } catch (err) {
        triggersData = [];
    }
    renderTriggersTimeline();
}

// Liten tabell i själva rutan på hemskärmen - alla bolag som finns med
// på tidslinjen, rankade, med sin möjliga kursförändring. Ingen egen
// klickfunktion per rad (hela rutan öppnar redan hela tidslinjen).
// Hämtas en gång vid inloggning, oberoende av loadTriggers() ovan (som
// bara körs när man faktiskt öppnar fullskärmsvyn) - annars skulle
// tabellen förbli tom tills man redan öppnat tidslinjen en gång.
async function loadTriggersMiniPreview() {
    try {
        const res = await fetch("/api/triggers");
        const data = await res.json();
        triggersData = data.triggers || [];
    } catch (err) {
        triggersData = [];
    }
    renderTriggersMiniPreview();
}

function renderTriggersMiniPreview() {
    const body = document.getElementById("triggers-mini-table-body");
    if (!body) return;
    body.innerHTML = "";

    const events = triggersData.slice().sort((a, b) => a.date - b.date);
    events.forEach((event) => {
        const tr = document.createElement("tr");

        const companyTd = document.createElement("td");
        companyTd.className = "triggers-mini-table-company";
        companyTd.textContent = `${event.company} `;
        const tickerEl = document.createElement("span");
        tickerEl.className = "triggers-mini-table-ticker";
        tickerEl.textContent = event.ticker;
        companyTd.appendChild(tickerEl);
        tr.appendChild(companyTd);

        const dateTd = document.createElement("td");
        dateTd.className = "triggers-mini-table-date";
        dateTd.textContent = new Date(event.date * 1000).toLocaleDateString("sv-SE", { day: "numeric", month: "short" });
        tr.appendChild(dateTd);

        const impactTd = document.createElement("td");
        impactTd.className = "triggers-mini-table-impact";
        const downEl = document.createElement("span");
        downEl.className = "timeline-event-impact-down";
        downEl.textContent = `↓ −${event.impact_down}%`;
        const upEl = document.createElement("span");
        upEl.className = "timeline-event-impact-up";
        upEl.textContent = `↑ +${event.impact_up}%`;
        impactTd.appendChild(downEl);
        impactTd.appendChild(upEl);
        tr.appendChild(impactTd);

        body.appendChild(tr);
    });
}

// ---------------------------------------------------------------------------
// Feedback - rutan bredvid Triggers tidslinjen där alla kan skicka in
// feedback till adminkontot (549L). Bara SKICKA-formuläret finns här; att
// LÄSA inskickad feedback går bara i 549L:s egen profil (se
// renderOwnFeedbackSection nedan) - servern (app.py) nekar GET /api/feedback
// för alla andra ändå, det här är bara för att inte visa en läsvy som
// skulle misslyckas för alla utom en.
//
// De tre knapparna väljer bara ÄMNE - klicket skickar inget själv (en ren
// "bugg"-etikett utan förklaring vore inte till stor hjälp). Att klicka en
// knapp öppnar istället skriv-rutan, förifylld med ämnet som etikett, och
// man måste skriva en egen förklaring där innan "Skicka feedback" faktiskt
// skickar något.
// ---------------------------------------------------------------------------

const FEEDBACK_QUICK_OPTIONS = [
    "Jag hittade en bugg.",
    "Jag har förslag på en ny funktion.",
    "Sidan kändes långsam.",
];

// Samma tre ämnen som cirkeldiagrammet i 549L:s profil bryter ner
// inskickad feedback på (se renderFeedbackChart längre ner) - en färg
// per ämne, återanvänds i både diagrammet och dess legend.
const FEEDBACK_CATEGORY_COLORS = {
    "Jag hittade en bugg.": "var(--red)",
    "Jag har förslag på en ny funktion.": "var(--green)",
    "Sidan kändes långsam.": "var(--yellow)",
};

const feedbackQuickOptionsEl = document.getElementById("feedback-quick-options");
const feedbackExplainEl = document.getElementById("feedback-explain");
const feedbackExplainLabelEl = document.getElementById("feedback-explain-label");
const feedbackTextEl = document.getElementById("feedback-text");
const feedbackSendBtn = document.getElementById("feedback-send-btn");
const feedbackStatusEl = document.getElementById("feedback-status");

let selectedFeedbackCategory = null;

FEEDBACK_QUICK_OPTIONS.forEach((category) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "feedback-quick-btn";
    btn.textContent = category;
    btn.addEventListener("click", () => selectFeedbackCategory(category, btn));
    feedbackQuickOptionsEl.appendChild(btn);
});

function selectFeedbackCategory(category, btn) {
    selectedFeedbackCategory = category;
    feedbackQuickOptionsEl.querySelectorAll(".feedback-quick-btn").forEach((b) => {
        b.classList.toggle("active", b === btn);
    });
    feedbackExplainLabelEl.textContent = `${category} Berätta mer:`;
    feedbackExplainEl.classList.remove("hidden");
    feedbackStatusEl.classList.add("hidden");
    feedbackTextEl.value = "";
    feedbackTextEl.focus();
}

async function sendFeedback(text, category) {
    if (!requireLogin("skicka feedback")) return;

    feedbackStatusEl.classList.remove("hidden", "feedback-success");
    feedbackStatusEl.textContent = "";

    try {
        const res = await fetch("/api/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, category }),
        });
        const data = await res.json();
        if (!res.ok) {
            feedbackStatusEl.textContent = data.error || "Kunde inte skicka feedbacken.";
            return;
        }
        feedbackTextEl.value = "";
        feedbackStatusEl.textContent = "Tack för din feedback!";
        feedbackStatusEl.classList.add("feedback-success");
        selectedFeedbackCategory = null;
        feedbackQuickOptionsEl.querySelectorAll(".feedback-quick-btn").forEach((b) => b.classList.remove("active"));
        feedbackExplainEl.classList.add("hidden");
    } catch (err) {
        feedbackStatusEl.textContent = "Nätverksfel: kunde inte nå servern.";
    }
}

feedbackSendBtn.addEventListener("click", () => {
    const explanation = feedbackTextEl.value.trim();
    if (!explanation) {
        feedbackStatusEl.classList.remove("hidden", "feedback-success");
        feedbackStatusEl.textContent = "Beskriv gärna lite mer innan du skickar.";
        return;
    }
    const text = selectedFeedbackCategory ? `${selectedFeedbackCategory} ${explanation}` : explanation;
    sendFeedback(text, selectedFeedbackCategory);
});

// Cirkeldiagram över hur många gånger varje ämnesknapp faktiskt skickats
// in (inte bara klickats i - se selectFeedbackCategory ovan, en klickad
// men aldrig skickad kategori räknas inte) - bara synligt på 549L:s egen
// profil (renderOwnFeedbackSection), tänkt att visa vad som är värt att
// lägga utvecklingstid på. Handritad SVG, ingen extern chart-bibliotek -
// samma mönster som prislinjediagrammet ovan i filen.
function renderFeedbackChart(entries) {
    const counts = FEEDBACK_QUICK_OPTIONS.map((category) => ({
        category,
        count: entries.filter((e) => e.category === category).length,
    }));
    const total = counts.reduce((sum, c) => sum + c.count, 0);

    feedbackChartWrapEl.classList.toggle("hidden", total === 0);
    if (total === 0) return;

    feedbackChartEl.innerHTML = "";
    feedbackChartEl.appendChild(buildFeedbackPieSvg(counts, total));

    feedbackChartLegendEl.innerHTML = "";
    counts.forEach(({ category, count }) => {
        const li = document.createElement("li");

        const swatch = document.createElement("span");
        swatch.className = "feedback-chart-swatch";
        swatch.style.background = FEEDBACK_CATEGORY_COLORS[category];
        li.appendChild(swatch);

        const label = document.createElement("span");
        label.textContent = `${category} (${count})`;
        li.appendChild(label);

        feedbackChartLegendEl.appendChild(li);
    });
}

function buildFeedbackPieSvg(counts, total) {
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", "0 0 200 200");
    svg.setAttribute("width", "160");
    svg.setAttribute("height", "160");

    const cx = 100;
    const cy = 100;
    const r = 90;
    let angle = -Math.PI / 2;

    counts.forEach(({ category, count }) => {
        if (count === 0) return;
        const fraction = count / total;
        const nextAngle = angle + fraction * Math.PI * 2;

        const path = document.createElementNS(svgNS, "path");
        if (fraction >= 0.999) {
            // En enda kategori har alla röster - en vanlig "M ... A ... Z"-båge
            // blir degenererad vid exakt 360 grader, rita två halvcirklar istället.
            path.setAttribute("d", `M ${cx - r} ${cy} A ${r} ${r} 0 1 1 ${cx + r} ${cy} A ${r} ${r} 0 1 1 ${cx - r} ${cy} Z`);
        } else {
            const x1 = cx + r * Math.cos(angle);
            const y1 = cy + r * Math.sin(angle);
            const x2 = cx + r * Math.cos(nextAngle);
            const y2 = cy + r * Math.sin(nextAngle);
            const largeArc = fraction > 0.5 ? 1 : 0;
            path.setAttribute("d", `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`);
        }
        path.style.fill = FEEDBACK_CATEGORY_COLORS[category];
        svg.appendChild(path);

        angle = nextAngle;
    });

    return svg;
}

// Baslinjen ligger mitt i rutan - hälften av händelserna (växlande i
// datumordning) får sin vertikala linje uppåt, hälften nedåt, så man kan
// bläddra rakt fram genom ALLA händelser istället för att de travas i en
// enda, allt högre stapel uppåt (som tidigare kunde bli så hög att man
// inte kom åt de översta genom att bara scrolla). Varje sida packas för
// sig med samma "lägsta fria våning"-algoritm som innan, så etiketter
// aldrig överlappar varandra inom samma sida.
function renderTriggersTimeline() {
    const track = triggersTimelineTrackEl;
    track.innerHTML = "";

    const events = triggersData.slice(0, triggersCount).slice().sort((a, b) => a.date - b.date);
    if (events.length === 0) {
        track.style.width = "100%";
        track.style.height = "80px";
        const empty = document.createElement("p");
        empty.className = "muted";
        empty.textContent = "Inga triggers hittades inom de närmaste två månaderna.";
        track.appendChild(empty);
        updateTimelineScrubber();
        return;
    }

    const PX_PER_DAY = 110;
    const LANE_HEIGHT = 125;
    const MIN_GAP_PX = 165;
    const SIDE_PADDING = 90;
    const BASELINE_MARGIN = 16;

    const minDate = events[0].date;
    const maxDate = events[events.length - 1].date;
    const daySpan = Math.max(1, (maxDate - minDate) / 86400);
    const trackWidth = Math.max(SIDE_PADDING * 2 + daySpan * PX_PER_DAY, triggersTimelineScrollEl.clientWidth);

    function xFor(date) {
        return SIDE_PADDING + ((date - minDate) / 86400) * PX_PER_DAY;
    }

    function packLanes(subset) {
        const laneLastX = [];
        return subset.map(({ event, x }) => {
            let lane = 0;
            while (laneLastX[lane] !== undefined && x - laneLastX[lane] < MIN_GAP_PX) {
                lane++;
            }
            laneLastX[lane] = x;
            return { event, x, lane };
        });
    }

    const withX = events.map((event, i) => ({ event, x: xFor(event.date), side: i % 2 === 0 ? "up" : "down" }));
    const upPlaced = packLanes(withX.filter((e) => e.side === "up"));
    const downPlaced = packLanes(withX.filter((e) => e.side === "down"));

    const maxUpLane = upPlaced.length ? Math.max(...upPlaced.map((p) => p.lane)) : -1;
    const maxDownLane = downPlaced.length ? Math.max(...downPlaced.map((p) => p.lane)) : -1;

    // EDGE_CLEARANCE måste rymma en hel ruta (~110px hög) plus liten
    // marginal - annars stack den yttersta våningens ruta (den som ligger
    // längst bort från baslinjen, t.ex. Intel/Amazon om de hamnar där) ut
    // ovanför/under själva spårets kant. Den delen av rutan fick då ingen
    // plats i dokumentets scrollhöjd alls, så den gick inte att nå genom
    // att skrolla - bara halva rutan syntes, resten var permanent
    // avklippt. (BASELINE_MARGIN används fortfarande nedan i
    // linje/etikett-formlerna, men tar där ut sig självt - det är bara
    // här, i hur mycket totalt utrymme som reserveras, som det faktiskt
    // spelade roll.)
    const EDGE_CLEARANCE = 130;
    const upSpace = (maxUpLane + 1) * LANE_HEIGHT + EDGE_CLEARANCE;
    const downSpace = (maxDownLane + 1) * LANE_HEIGHT + EDGE_CLEARANCE;
    const trackHeight = upSpace + downSpace;
    const baselineY = upSpace; // avstånd från trackens topp ner till baslinjen

    track.style.width = `${trackWidth}px`;
    track.style.height = `${trackHeight}px`;

    // Placerar det egna scroll-handtaget exakt i höjd med baslinjen
    // (inte bara mitt i hela rutan, som kan hamna en bit ovanför/under
    // baslinjen om upp- och nersidan behöver olika många våningar) - 10px
    // är .triggers-timeline-scroll's egen padding-top.
    const scrubberEl = document.querySelector(".timeline-scrubber");
    scrubberEl.style.top = `${10 + baselineY}px`;
    scrubberEl.style.transform = "translateY(-50%)";

    const toBottomPx = (yFromTop) => trackHeight - yFromTop;

    const baseline = document.createElement("div");
    baseline.className = "timeline-baseline";
    baseline.style.top = `${baselineY}px`;
    track.appendChild(baseline);

    // Månadsmarkeringar mitt på baslinjen, som referens för var på
    // tidslinjen man befinner sig.
    const firstMonth = new Date(minDate * 1000);
    firstMonth.setUTCDate(1);
    firstMonth.setUTCHours(0, 0, 0, 0);
    for (let cursor = new Date(firstMonth); cursor.getTime() / 1000 <= maxDate + 86400 * 31; cursor.setUTCMonth(cursor.getUTCMonth() + 1)) {
        const monthTs = cursor.getTime() / 1000;
        if (monthTs < minDate - 86400 * 31) continue;
        const x = xFor(monthTs);

        const tick = document.createElement("div");
        tick.className = "timeline-month-tick";
        tick.style.left = `${x}px`;
        tick.style.top = `${baselineY - 7}px`;
        track.appendChild(tick);

        const label = document.createElement("div");
        label.className = "timeline-month-label";
        label.style.left = `${x}px`;
        label.style.top = `${baselineY + 12}px`;
        label.textContent = cursor.toLocaleDateString("sv-SE", { month: "short", year: "numeric" });
        track.appendChild(label);
    }

    function renderSide(placed, side) {
        placed.forEach(({ event, x, lane }) => {
            const lineLength = BASELINE_MARGIN + (lane + 1) * LANE_HEIGHT;

            const line = document.createElement("div");
            line.className = "timeline-event-line";
            line.style.left = `${x}px`;
            line.style.height = `${lineLength - BASELINE_MARGIN}px`;
            if (side === "up") {
                line.style.bottom = `${toBottomPx(baselineY)}px`;
            } else {
                line.style.top = `${baselineY}px`;
            }
            track.appendChild(line);

            const dot = document.createElement("div");
            dot.className = "timeline-event-dot";
            dot.style.left = `${x}px`;
            dot.style.top = `${baselineY}px`;
            track.appendChild(dot);

            const label = document.createElement("div");
            label.className = `timeline-event-label timeline-event-label-${side}`;
            label.style.left = `${x}px`;
            if (side === "up") {
                label.style.bottom = `${toBottomPx(baselineY - lineLength + BASELINE_MARGIN)}px`;
            } else {
                label.style.top = `${baselineY + lineLength - BASELINE_MARGIN}px`;
            }

            const rankEl = document.createElement("span");
            rankEl.className = "timeline-event-rank";
            rankEl.textContent = `#${event.rank}`;
            label.appendChild(rankEl);

            const companyEl = document.createElement("span");
            companyEl.className = "timeline-event-company";
            companyEl.textContent = `${event.company} `;
            const tickerEl = document.createElement("span");
            tickerEl.className = "timeline-event-ticker";
            tickerEl.textContent = event.ticker;
            companyEl.appendChild(tickerEl);
            label.appendChild(companyEl);

            const dateEl = document.createElement("span");
            dateEl.className = "timeline-event-date";
            dateEl.textContent = formatAccountDate(event.date);
            label.appendChild(dateEl);

            // Ungefärlig, historiskt grundad bedömning av hur mycket
            // aktien skulle kunna röra sig procentuellt beroende på om
            // utfallet blir positivt eller negativt - se disclaimern.
            // Själva förklaringen av triggern och de möjliga utfallen
            // syns bara i detaljvyn (se openTriggerDetail) - rutan här
            // ska hållas liten så alla får plats utan att man behöver
            // scrolla vertikalt.
            const impactEl = document.createElement("span");
            impactEl.className = "timeline-event-impact";
            const downEl = document.createElement("span");
            downEl.className = "timeline-event-impact-down";
            downEl.textContent = `↓ −${event.impact_down}%`;
            const upEl = document.createElement("span");
            upEl.className = "timeline-event-impact-up";
            upEl.textContent = `↑ +${event.impact_up}%`;
            impactEl.appendChild(downEl);
            impactEl.appendChild(upEl);
            label.appendChild(impactEl);

            label.addEventListener("click", () => openTriggerDetail(event));

            track.appendChild(label);
        });
    }

    renderSide(upPlaced, "up");
    renderSide(downPlaced, "down");

    triggersTimelineScrollEl.scrollLeft = 0;
    updateTimelineScrubber();
}

// Detaljvy för en enskild trigger - öppnas när man klickar på dess ruta
// på tidslinjen. Visar den fullständiga förklaringen samt vad ett
// positivt/negativt utfall skulle innebära och den ungefärliga
// kurspåverkan för var av dem, istället för att trycka in allt i den
// lilla rutan på själva tidslinjen.
const triggerDetailOverlayEl = document.getElementById("trigger-detail-overlay");
const triggerDetailCloseBtn = document.getElementById("trigger-detail-close");

function openTriggerDetail(event) {
    document.getElementById("trigger-detail-rank").textContent = `#${event.rank}`;
    document.getElementById("trigger-detail-company").textContent = `${event.company} (${event.ticker})`;
    document.getElementById("trigger-detail-date").textContent = formatAccountDate(event.date);
    document.getElementById("trigger-detail-description").textContent = event.description;
    document.getElementById("trigger-detail-impact-up").textContent = `+${event.impact_up}%`;
    document.getElementById("trigger-detail-outcome-up").textContent = event.outcome_up;
    document.getElementById("trigger-detail-impact-down").textContent = `−${event.impact_down}%`;
    document.getElementById("trigger-detail-outcome-down").textContent = event.outcome_down;
    triggerDetailOverlayEl.classList.remove("hidden");
}

function closeTriggerDetail() {
    triggerDetailOverlayEl.classList.add("hidden");
}

triggerDetailCloseBtn.addEventListener("click", closeTriggerDetail);
triggerDetailOverlayEl.addEventListener("click", (e) => {
    if (e.target === triggerDetailOverlayEl) closeTriggerDetail();
});
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !triggerDetailOverlayEl.classList.contains("hidden")) closeTriggerDetail();
});

function openTriggersTimeline() {
    mainViewEl.classList.add("hidden");
    scaleEditorEl.classList.add("hidden");
    userProfileEl.classList.add("hidden");
    chatRoomEl.classList.add("hidden");
    triggersTimelineEl.classList.remove("hidden");
    window.scrollTo(0, 0);
    loadTriggers();
}

function closeTriggersTimeline() {
    triggersTimelineEl.classList.add("hidden");
    mainViewEl.classList.remove("hidden");
}

triggersLauncherBtn.addEventListener("click", openTriggersTimeline);
triggersBackBtn.addEventListener("click", closeTriggersTimeline);

triggersCountTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
        triggersCountTabs.forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        triggersCount = parseInt(tab.dataset.count, 10);
        renderTriggersTimeline();
    });
});

// --- Chattlänk i analysvyn - visas om en chatt är länkad till den
// analyserade aktien. ---

const resultChatLinkEl = document.getElementById("result-chat-link");
const resultChatTickerLabelEl = document.getElementById("result-chat-ticker-label");
const resultChatRoomsEl = document.getElementById("result-chat-rooms");
let resultChatRequestId = 0;

// Bygger en egen liten "chattkort"-sektion per rum länkat till aktien -
// namn, en förhandsvisning av de senaste meddelandena och en egen
// "Öppna chatt"-knapp, så flera chattar om samma aktie kan visas sida
// vid sida istället för att bara den första hittade chatten syntes.
function buildResultChatRoom(room) {
    const wrap = document.createElement("div");
    wrap.className = "result-chat-room";

    const name = document.createElement("p");
    name.className = "result-chat-room-name";
    name.textContent = room.name;
    wrap.appendChild(name);

    const preview = document.createElement("ul");
    preview.className = "result-chat-preview";
    renderChatMessages(preview, null, room.messages.slice(-3));
    if (room.messages.length === 0) {
        const li = document.createElement("li");
        li.className = "muted";
        li.textContent = "Inga meddelanden än — bli först med att skriva något!";
        preview.appendChild(li);
    }
    wrap.appendChild(preview);

    const openBtn = document.createElement("button");
    openBtn.type = "button";
    openBtn.textContent = "Öppna chatt";
    openBtn.addEventListener("click", () => openChatRoom(room.id));
    wrap.appendChild(openBtn);

    return wrap;
}

async function checkResultChat(ticker) {
    const requestId = ++resultChatRequestId;
    resultChatLinkEl.classList.add("hidden");
    resultChatRoomsEl.innerHTML = "";
    if (!ticker) return;

    try {
        const res = await fetch(`/api/community/rooms?ticker=${encodeURIComponent(ticker)}`);
        const rooms = await res.json();
        if (requestId !== resultChatRequestId) return;
        if (!rooms.length) return;

        const fullRooms = await Promise.all(
            rooms.map((room) => fetch(`/api/community/rooms/${room.id}`).then((r) => r.json()))
        );
        if (requestId !== resultChatRequestId) return;

        resultChatTickerLabelEl.textContent = ticker;
        resultChatRoomsEl.innerHTML = "";
        fullRooms.forEach((room) => resultChatRoomsEl.appendChild(buildResultChatRoom(room)));

        resultChatLinkEl.classList.remove("hidden");
    } catch (err) {
        // Chattlänken är en extra funktion - misslyckas den visas den bara inte.
    }
}

let communityPollTimer = null;

function startCommunityPolling() {
    stopCommunityPolling();
    communityPollTimer = setInterval(() => {
        loadCommunityRooms();
        if (currentRoomId) loadChatRoom(currentRoomId);
    }, 8000);
}

function stopCommunityPolling() {
    if (communityPollTimer) {
        clearInterval(communityPollTimer);
        communityPollTimer = null;
    }
    stopChatRoomPolling();
}

let chatRoomPollTimer = null;

function startChatRoomPolling() {
    stopChatRoomPolling();
    chatRoomPollTimer = setInterval(() => {
        if (currentRoomId) loadChatRoom(currentRoomId);
    }, 5000);
}

function stopChatRoomPolling() {
    if (chatRoomPollTimer) {
        clearInterval(chatRoomPollTimer);
        chatRoomPollTimer = null;
    }
}

function showLoggedOut() {
    isGuest = false;
    currentUsername = null;
    currentAvatar = null;
    currentAccentColor = null;
    currentIsAdmin = false;
    logoutBtn.textContent = "Logga ut";
    appContentEl.classList.add("hidden");
    accountBarEl.classList.add("hidden");
    loginGateEl.classList.remove("hidden");
    applyAccentColor(null);
    stopCommunityPolling();
}

function showLoggedIn(account) {
    isGuest = false;
    currentUsername = account.username;
    currentAvatar = account.avatar || null;
    currentAccentColor = account.accent_color || null;
    currentIsAdmin = Boolean(account.is_admin);
    applyAccentColor(currentAccentColor);

    loginGateEl.classList.add("hidden");
    loginGateGuestNoticeEl.classList.add("hidden");
    logoutBtn.textContent = "Logga ut";
    accountUsernameEl.textContent = account.username;
    renderAccountAvatar();
    accountBarEl.classList.remove("hidden");
    appContentEl.classList.remove("hidden");

    if (!appInitialized) {
        appInitialized = true;
        loadTop10();
        loadUsers();
        loadScales();
        loadCommunityRooms();
        loadTriggersMiniPreview();
    }
    startCommunityPolling();
}

// Samma app-vy som showLoggedIn, men utan konto - allt som kräver
// inloggning gated bakom requireLogin() istället för att bara döljas,
// eftersom en gäst annars inte skulle förstå VARFÖR t.ex. "+ Skapa egen
// betygsskala" inte gör något.
function showGuestMode() {
    isGuest = true;
    currentUsername = null;
    currentAvatar = null;
    currentAccentColor = null;
    currentIsAdmin = false;
    applyAccentColor(null);

    loginGateEl.classList.add("hidden");
    loginGateGuestNoticeEl.classList.add("hidden");
    accountUsernameEl.textContent = "Gäst";
    renderAccountAvatar();
    logoutBtn.textContent = "Logga in";
    accountBarEl.classList.remove("hidden");
    appContentEl.classList.remove("hidden");

    if (!appInitialized) {
        appInitialized = true;
        loadTop10();
        loadUsers();
        loadScales();
        loadCommunityRooms();
        loadTriggersMiniPreview();
    }
    startCommunityPolling();
}

loginToggleBtn.addEventListener("click", () => {
    authMode = authMode === "login" ? "register" : "login";
    loginGateTitle.textContent = authMode === "login" ? "Logga in" : "Skapa konto";
    loginSubmitBtn.textContent = authMode === "login" ? "Logga in" : "Skapa konto";
    loginToggleBtn.textContent = authMode === "login" ? "Skapa konto istället" : "Logga in istället";
    loginError.classList.add("hidden");
});

loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    loginError.classList.add("hidden");
    loginSubmitBtn.disabled = true;

    const username = authUsernameInput.value.trim();
    const password = authPasswordInput.value;
    const endpoint = authMode === "login" ? "/api/login" : "/api/register";

    try {
        const res = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
        const data = await res.json();
        if (!res.ok) {
            loginError.textContent = data.error || "Något gick fel.";
            loginError.classList.remove("hidden");
            return;
        }
        authPasswordInput.value = "";
        showLoggedIn(data);
    } catch (err) {
        loginError.textContent = "Nätverksfel: kunde inte nå servern.";
        loginError.classList.remove("hidden");
    } finally {
        loginSubmitBtn.disabled = false;
    }
});

logoutBtn.addEventListener("click", async () => {
    // Samma knapp återanvänds för gäster, bara med annan text ("Logga
    // in") satt av showGuestMode() - då finns ingen session att logga ut
    // från, så hoppa direkt till inloggningsvyn istället för att anropa
    // /api/logout i onödan.
    if (isGuest) {
        showLoggedOut();
        return;
    }
    try {
        await fetch("/api/logout", { method: "POST" });
    } catch (err) {
        // Även om anropet misslyckas nätverksmässigt - visa inloggningsvyn ändå.
    }
    showLoggedOut();
});

guestModeBtn.addEventListener("click", showGuestMode);

(async function checkLoginOnLoad() {
    try {
        const res = await fetch("/api/me");
        const data = await res.json();
        if (data.username) {
            showLoggedIn(data);
        } else {
            showLoggedOut();
        }
    } catch (err) {
        showLoggedOut();
    }
})();
