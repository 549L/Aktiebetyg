const form = document.getElementById("search-form");
const input = document.getElementById("ticker-input");
const suggestionsEl = document.getElementById("suggestions");
const statusEl = document.getElementById("status");
const result = document.getElementById("result");

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

let searchAbortController = null;
let searchDebounceTimer = null;
let activeSuggestionIndex = -1;
let currentSuggestions = [];
let currentIndustryFilter = null;

const industryFilterChip = document.getElementById("industry-filter-chip");
const industryFilterLabel = document.getElementById("industry-filter-label");
const industryFilterClear = document.getElementById("industry-filter-clear");

function setIndustryFilter(label) {
    currentIndustryFilter = label;
    industryFilterLabel.textContent = label;
    industryFilterChip.classList.remove("hidden");
    input.value = "";
    hideSuggestions();
    input.focus();
}

function clearIndustryFilter() {
    currentIndustryFilter = null;
    industryFilterChip.classList.add("hidden");
}

industryFilterClear.addEventListener("click", clearIndustryFilter);

function hideSuggestions() {
    suggestionsEl.classList.add("hidden");
    suggestionsEl.innerHTML = "";
    currentSuggestions = [];
    activeSuggestionIndex = -1;
}

function renderSuggestions(matches) {
    currentSuggestions = matches;
    activeSuggestionIndex = -1;
    suggestionsEl.innerHTML = "";

    if (matches.length === 0) {
        hideSuggestions();
        return;
    }

    matches.forEach((match) => {
        const li = document.createElement("li");
        li.innerHTML = `<span>${match.name}</span><span class="suggestion-symbol">${match.symbol}${match.exchange ? " · " + match.exchange : ""}</span>`;
        li.addEventListener("mousedown", (e) => {
            // mousedown (before blur) så klicket hinner registreras innan listan döljs
            e.preventDefault();
            selectSuggestion(match);
        });
        suggestionsEl.appendChild(li);
    });

    suggestionsEl.classList.remove("hidden");
}

function selectSuggestion(match) {
    input.value = match.symbol;
    hideSuggestions();
    runAnalysis(match.symbol);
}

input.addEventListener("input", () => {
    const query = input.value.trim();
    clearTimeout(searchDebounceTimer);

    if (query.length < 2) {
        hideSuggestions();
        return;
    }

    searchDebounceTimer = setTimeout(async () => {
        if (searchAbortController) searchAbortController.abort();
        searchAbortController = new AbortController();

        try {
            const industryParam = currentIndustryFilter
                ? `?industry=${encodeURIComponent(currentIndustryFilter)}`
                : "";
            const res = await fetch(`/api/search/${encodeURIComponent(query)}${industryParam}`, {
                signal: searchAbortController.signal,
            });
            const matches = await res.json();
            renderSuggestions(matches);
        } catch (err) {
            if (err.name !== "AbortError") hideSuggestions();
        }
    }, 250);
});

input.addEventListener("keydown", (e) => {
    if (suggestionsEl.classList.contains("hidden") || currentSuggestions.length === 0) return;

    if (e.key === "ArrowDown") {
        e.preventDefault();
        activeSuggestionIndex = Math.min(activeSuggestionIndex + 1, currentSuggestions.length - 1);
        updateActiveSuggestion();
    } else if (e.key === "ArrowUp") {
        e.preventDefault();
        activeSuggestionIndex = Math.max(activeSuggestionIndex - 1, 0);
        updateActiveSuggestion();
    } else if (e.key === "Enter" && activeSuggestionIndex >= 0) {
        e.preventDefault();
        selectSuggestion(currentSuggestions[activeSuggestionIndex]);
    } else if (e.key === "Escape") {
        hideSuggestions();
    }
});

function updateActiveSuggestion() {
    [...suggestionsEl.children].forEach((li, i) => {
        li.classList.toggle("active", i === activeSuggestionIndex);
    });
}

document.addEventListener("click", (e) => {
    if (!suggestionsEl.contains(e.target) && e.target !== input) {
        hideSuggestions();
    }
});

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

loadTop10();

const industriesList = document.getElementById("industries-list");
const industriesEmpty = document.getElementById("industries-empty");

async function loadIndustries() {
    try {
        const res = await fetch("/api/industries");
        const industries = await res.json();

        industriesList.innerHTML = "";
        if (industries.length === 0) {
            industriesEmpty.classList.remove("hidden");
            return;
        }
        industriesEmpty.classList.add("hidden");

        industries.forEach((item) => {
            const li = document.createElement("li");
            li.innerHTML = `${item.label} <span class="industry-count">${item.count}</span>`;
            li.addEventListener("click", () => setIndustryFilter(item.label));
            industriesList.appendChild(li);
        });
    } catch (err) {
        // Branschrutan är en extra funktion - misslyckas hämtningen visar vi bara ingenting.
    }
}

loadIndustries();

form.addEventListener("submit", (e) => {
    e.preventDefault();
    hideSuggestions();
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
        loadIndustries();
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
    document.getElementById("company-description").textContent = data.description || "";
    const viewLabel = data.view_style_label || VIEW_STYLE_LABELS[data.view_style] || null;
    document.getElementById("scale-label").textContent = data.scale
        ? (viewLabel ? `(${data.scale} · ${viewLabel})` : `(${data.scale})`)
        : "";
    renderFearGreed(data.fear_greed);

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
// inte råkar ligga i topp-5 ändå går att hitta och välja.
const MAX_VISIBLE_SCALES = 5;

let currentScaleId = "default";
let customScales = [];
let scaleRatings = {}; // { rawId: {average, count} }
let scalesSearchQuery = "";

const scalesListEl = document.getElementById("scales-list");
const createScaleBtn = document.getElementById("create-scale-btn");
const scalesSearchInput = document.getElementById("scales-search");

function allScaleEntries() {
    const builtin = BUILTIN_SCALES.map((s) => ({ rawId: s.id, scaleId: s.id, name: s.name, isCustom: false, color: null }));
    const custom = customScales.map((s) => ({ rawId: s.id, scaleId: `custom:${s.id}`, name: s.name, isCustom: true, color: s.color }));
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
    const { scaleId, rawId, name, isCustom, color } = entry;
    const li = document.createElement("li");
    li.className = "scale-row" + (scaleId === currentScaleId ? " active" : "");

    const topRow = document.createElement("div");
    topRow.className = "scale-row-top";

    const nameSpan = document.createElement("span");
    nameSpan.className = "scale-row-name";
    nameSpan.textContent = name;
    if (isCustom && color) nameSpan.style.color = color;
    nameSpan.addEventListener("click", () => selectScale(scaleId));
    topRow.appendChild(nameSpan);

    if (isCustom) {
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

        topRow.appendChild(actions);
    }

    li.appendChild(topRow);
    li.appendChild(buildStarRating(rawId));

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

function applyScaleTheme(scaleId) {
    document.body.classList.remove("view-growth", "view-stability");
    document.body.style.removeProperty("--accent");
    if (scaleId === "growth") {
        document.body.classList.add("view-growth");
    } else if (scaleId === "stability") {
        document.body.classList.add("view-stability");
    } else if (scaleId.startsWith("custom:")) {
        const rawId = scaleId.slice("custom:".length);
        const scale = customScales.find((s) => s.id === rawId);
        if (scale && scale.color) {
            document.body.style.setProperty("--accent", scale.color);
        }
    }
}

function selectScale(scaleId) {
    currentScaleId = scaleId;
    applyScaleTheme(scaleId);
    renderScalesList();
    if (currentTicker) runAnalysis(currentTicker);
}

loadScales();

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
const scaleColorInput = document.getElementById("scale-color-input");
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
            scaleColorInput.value = record.color || "#f5c518";
            editorSlots = {};
            Object.entries(record.profiles).forEach(([key, slot]) => {
                editorSlots[key] = slot.metrics.map((m) => ({ ...m }));
            });
        } catch (err) {
            scaleNameInput.value = "";
            scaleColorInput.value = "#f5c518";
        }
    } else {
        editorScaleId = null;
        scaleEditorTitle.textContent = "Skapa egen betygsskala";
        scaleNameInput.value = "";
        scaleColorInput.value = "#f5c518";
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

createScaleBtn.addEventListener("click", () => openScaleEditor(null));
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
    const name = scaleNameInput.value.trim();
    const color = scaleColorInput.value;
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
            body: JSON.stringify({ name, color, profiles }),
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
