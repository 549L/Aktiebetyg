"""
Katalog över alla nyckeltal som redan används någonstans i appens inbyggda
betygsskalor (config/metrics.py) - underlaget för "Egna betygsskalor", där
en användare väljer bland dessa och sätter egen vikt/idealvärde/tolerans.

Byggs automatiskt genom att gå igenom PROFILES en gång och deduplicera på
nyckeltalets "key", med "default"-profilens version företrädd och annars
första förekomst i den ordning profilerna är deklarerade i PROFILES. Så
länge ett nytt nyckeltal läggs till i config/metrics.py dyker det
automatiskt upp här också - ingen egen lista att hålla i synk.

Toleransen (hur långt värdet får avvika från idealet innan betyget blir
dåligt) räknas ut ur nyckeltalets "scale"/"floor"/"ceiling" - samma
underliggande tal som redan styr kurvans branthet i scoring.py, bara
uttryckt som en enda vänlig siffra istället för tre olika fältnamn.
"""

from config.metrics import PROFILES

# Ett fåtal nyckeltal förekommer bara i en bransch-specifik variant med
# ordval som passar just den branschen (t.ex. bankers "kreditkvalitet-
# proxy"), vilket skulle se märkligt ut i en generell katalog. Skriver bara
# över de fält som behöver bytas - resten kommer från den deriverade posten.
_CATALOG_OVERRIDES = {
    "operating_margin": {"label": "Rörelsemarginal"},
    "roa": {"label": "Avkastning på totala tillgångar (ROA)"},
    "profit_margin": {
        "label": "Vinstmarginal",
        "positive_text": "Vinstmarginalen på {value} visar god lönsamhet.",
        "negative_text": "Vinstmarginalen på {value} är svag.",
    },
    "current_ratio": {
        "label": "Kassalikviditet (Current ratio)",
        "positive_text": "Kassalikviditeten på {value} visar god kortsiktig betalningsförmåga.",
        "negative_text": "Kassalikviditeten på {value} är låg, vilket kan tyda på likviditetsrisk.",
    },
}

# target_upside finns bara som "insight"-mått (bara positiva/negativa
# punkter, ingen vikt/idealvärde-form) i alla inbyggda profiler - läggs
# till här för hand så den ändå går att använda som ett viktat nyckeltal i
# en egen skala. ideal/floor motsvarar dess good_threshold/bad_threshold.
_EXTRA_METRICS = [
    {
        "key": "target_upside",
        "label": "Analytikernas riktkurs vs pris",
        "source": "computed:target_upside",
        "type": "higher_better",
        "ideal": 0.10,
        "floor": -0.05,
        "weight": 0.10,
        "format": "{:.1%}",
        "positive_text": "Analytikernas riktkurs ligger {value} över dagens pris.",
        "negative_text": "Analytikernas riktkurs ligger {value} under dagens pris.",
    },
]


def _derive_tolerance(metric):
    if metric["type"] == "target":
        return metric["scale"]
    if metric["type"] == "higher_better":
        return metric["ideal"] - metric["floor"]
    return metric["ceiling"] - metric["ideal"]


def _derive_unit(format_str):
    if "%" in format_str:
        return "%"
    if format_str.endswith("x"):
        return "x"
    return ""


def _build_entry(metric):
    entry = {
        "key": metric["key"],
        "label": metric["label"],
        "source": metric["source"],
        "type": metric["type"],
        "format": metric["format"],
        "unit": _derive_unit(metric["format"]),
        "positive_text": metric["positive_text"],
        "negative_text": metric["negative_text"],
        "default_ideal": metric["ideal"],
        "default_tolerance": _derive_tolerance(metric),
        "default_weight": metric["weight"],
    }
    if metric.get("fallback_source"):
        entry["fallback_source"] = metric["fallback_source"]
    overrides = _CATALOG_OVERRIDES.get(metric["key"])
    if overrides:
        entry.update(overrides)
    return entry


def _build_catalog():
    catalog = {}
    profile_order = ["default"] + [k for k in PROFILES if k != "default"]
    for profile_key in profile_order:
        for metric in PROFILES[profile_key]["scoring"]:
            if metric["key"] not in catalog:
                catalog[metric["key"]] = _build_entry(metric)
    for metric in _EXTRA_METRICS:
        catalog.setdefault(metric["key"], _build_entry(metric))
    return catalog


METRIC_CATALOG = _build_catalog()


def _build_builtin_profile_rows():
    rows = {}
    for profile_key, profile in PROFILES.items():
        rows[profile_key] = {
            "label": profile["label"],
            "metrics": [
                {
                    "key": m["key"],
                    "weight_pct": round(m["weight"] * 100, 1),
                    "ideal": m["ideal"],
                    "tolerance": _derive_tolerance(m),
                }
                for m in profile["scoring"]
            ],
        }
    return rows


# Byggkälla för "kopiera nyckeltal från..."-knappen i skalredigeraren, och
# för sektor-flikarnas etiketter (samma 11 branscher + "default" som redan
# finns i PROFILES - ingen egen hårdkodad lista).
BUILTIN_PROFILE_ROWS = _build_builtin_profile_rows()
