"""
Lagring av användarskapade betygsskalor ("Egna betygsskalor"), sparade
lokalt som en JSON-fil (data/custom_scales.json) - samma mönster som
history_store.py använder för sökhistoriken.

En sparad skala har alltid ett "default"-nyckeltalsset som gäller alla
branscher, plus valfria bransch-överlägg (nyckel "sector:<Yahoo-sektor>",
samma konvention som config/metrics.py PROFILES) - en bransch utan eget
överlägg faller tillbaka på skalans egna "default"-set.

Varje nyckeltalsrad lagras minimalt (key/weight_pct/ideal/tolerance) -
resten (etikett, källa, formatering, text) slås upp i METRIC_CATALOG vid
hydrering i resolve_profiles(), inte dupliceras per skala.
"""

import json
import os
import re
import time
import uuid

from config.industries import SECTOR_TRANSLATIONS
from config.metric_catalog import METRIC_CATALOG

_SCALES_PATH = os.path.join(os.path.dirname(__file__), "data", "custom_scales.json")

_VALID_PROFILE_KEYS = {"default"} | {f"sector:{s}" for s in SECTOR_TRANSLATIONS}

_DEFAULT_COLOR = "#f5c518"
_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _clean_color(color):
    """Faller tillbaka på standardfärgen (appens guldaccent) om värdet
    saknas eller inte är en giltig hex-färg - ogiltig färg ska inte hindra
    att skalan går att spara."""
    if isinstance(color, str) and _HEX_COLOR_RE.match(color):
        return color
    return _DEFAULT_COLOR


def _load():
    if not os.path.exists(_SCALES_PATH):
        return {}
    try:
        with open(_SCALES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(scales):
    os.makedirs(os.path.dirname(_SCALES_PATH), exist_ok=True)
    with open(_SCALES_PATH, "w", encoding="utf-8") as f:
        json.dump(scales, f, ensure_ascii=False, indent=2)


def _validate_profiles(profiles):
    """Kastar ValueError (svensk text, tänkt att visas direkt för
    användaren) om profiles-strukturen inte går att spara."""
    if not isinstance(profiles, dict) or not profiles.get("default", {}).get("metrics"):
        raise ValueError("Standarduppsättningen måste ha minst ett nyckeltal.")

    for profile_key, slot in profiles.items():
        if profile_key not in _VALID_PROFILE_KEYS:
            raise ValueError(f"Okänd bransch: {profile_key}")
        metrics = slot.get("metrics") if isinstance(slot, dict) else None
        if not metrics:
            raise ValueError("Ett branschöverlägg måste ha minst ett nyckeltal (eller tas bort helt).")
        for row in metrics:
            key = row.get("key")
            if key not in METRIC_CATALOG:
                raise ValueError(f"Okänt nyckeltal: {key}")
            try:
                weight_pct = float(row["weight_pct"])
                ideal = float(row["ideal"])
                tolerance = float(row["tolerance"])
            except (KeyError, TypeError, ValueError):
                raise ValueError(f"Vikt, idealvärde och tolerans måste vara tal för {key}.")
            if tolerance <= 0:
                raise ValueError(f"Toleransen för {key} måste vara större än 0.")
            if weight_pct <= 0:
                raise ValueError(f"Vikten för {key} måste vara större än 0.")


def list_scales():
    scales = _load()
    rows = [
        {
            "id": s["id"],
            "name": s["name"],
            "color": s.get("color", _DEFAULT_COLOR),
            "created_at": s["created_at"],
            "updated_at": s["updated_at"],
        }
        for s in scales.values()
    ]
    rows.sort(key=lambda r: r["name"].lower())
    return rows


def get_scale(scale_id):
    return _load().get(scale_id)


def create_scale(name, profiles, color=None):
    name = (name or "").strip()
    if not name:
        raise ValueError("Skalan måste ha ett namn.")
    _validate_profiles(profiles)

    scales = _load()
    scale_id = uuid.uuid4().hex
    now = time.time()
    record = {
        "id": scale_id,
        "name": name,
        "color": _clean_color(color),
        "created_at": now,
        "updated_at": now,
        "profiles": profiles,
    }
    scales[scale_id] = record
    _save(scales)
    return record


def update_scale(scale_id, name, profiles, color=None):
    name = (name or "").strip()
    if not name:
        raise ValueError("Skalan måste ha ett namn.")
    _validate_profiles(profiles)

    scales = _load()
    if scale_id not in scales:
        return None
    record = scales[scale_id]
    record["name"] = name
    record["color"] = _clean_color(color)
    record["profiles"] = profiles
    record["updated_at"] = time.time()
    _save(scales)
    return record


def delete_scale(scale_id):
    scales = _load()
    if scale_id not in scales:
        return False
    del scales[scale_id]
    _save(scales)
    return True


def _hydrate_metric(row):
    catalog_entry = METRIC_CATALOG.get(row["key"])
    if not catalog_entry:
        # Nyckeltalet fanns i katalogen när skalan sparades men finns inte
        # längre (t.ex. borttaget ur config/metrics.py) - hoppa tyst över
        # raden istället för att krascha hela analysen, samma toleranta
        # mönster som _evaluate_scoring_metric redan använder för saknad
        # Yahoo-data.
        return None

    weight = float(row["weight_pct"]) / 100.0
    ideal = float(row["ideal"])
    tolerance = float(row["tolerance"])

    metric = {
        "key": catalog_entry["key"],
        "label": catalog_entry["label"],
        "source": catalog_entry["source"],
        "type": catalog_entry["type"],
        "ideal": ideal,
        "weight": weight,
        "format": catalog_entry["format"],
        "positive_text": catalog_entry["positive_text"],
        "negative_text": catalog_entry["negative_text"],
    }
    if catalog_entry.get("fallback_source"):
        metric["fallback_source"] = catalog_entry["fallback_source"]

    if metric["type"] == "target":
        metric["scale"] = tolerance
    elif metric["type"] == "higher_better":
        metric["floor"] = ideal - tolerance
    else:
        metric["ceiling"] = ideal + tolerance

    return metric


def resolve_profiles(scale_id):
    """Hydrerar en sparad skala till en PROFILES-formad dict, redo för
    scoring._select_profile(). None om scale_id inte finns."""
    record = get_scale(scale_id)
    if not record:
        return None

    profiles = {}
    for profile_key, slot in record["profiles"].items():
        metrics = [_hydrate_metric(row) for row in slot.get("metrics", [])]
        metrics = [m for m in metrics if m is not None]
        if not metrics:
            continue

        if profile_key == "default":
            label = record["name"]
        else:
            sector_name = profile_key.split(":", 1)[1]
            sector_label = SECTOR_TRANSLATIONS.get(sector_name, sector_name)
            label = f"{record['name']} ({sector_label})"

        profiles[profile_key] = {"label": label, "scoring": metrics, "insight": []}

    # scoring._select_profile faller alltid tillbaka på profiles["default"]
    # - om alla dess nyckeltal blivit ogiltiga sedan skalan sparades (t.ex.
    # borttagna ur katalogen) går skalan inte längre att räkna med.
    if "default" not in profiles:
        return None

    return profiles
