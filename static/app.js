const form = document.getElementById("search-form");
const input = document.getElementById("ticker-input");
const suggestionsEl = document.getElementById("suggestions");
const statusEl = document.getElementById("status");
const result = document.getElementById("result");

let currentViewStyle = null;

const VIEW_STYLE_LABELS = {
    growth: "Tillväxtvy",
    stability: "Stabil vy",
};

document.querySelectorAll(".view-style-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        const style = btn.dataset.style;
        currentViewStyle = currentViewStyle === style ? null : style;
        document.querySelectorAll(".view-style-btn").forEach((b) => {
            b.setAttribute("aria-pressed", b.dataset.style === currentViewStyle ? "true" : "false");
        });
        document.body.classList.toggle("view-growth", currentViewStyle === "growth");
        document.body.classList.toggle("view-stability", currentViewStyle === "stability");
        if (currentTicker) {
            runAnalysis(currentTicker);
        }
    });
});

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
        if (currentViewStyle) {
            url.searchParams.set("style", currentViewStyle);
        }
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
