"""Live storm watch from NOAA NHC's CurrentStorms.json, plus a crop-specific
preparation checklist built from what is in the field this month.

The feed is only populated while NHC is advising on active storms. Fields
used: name, classification (TD/TS/HU/...), intensity (kt), latitudeNumeric,
longitudeNumeric, movementDir (degrees from north), movementSpeed (mph).
"""

import math
from datetime import date

import requests

from .storms import haversine_km

FEED = "https://www.nhc.noaa.gov/CurrentStorms.json"
CLASS_NAMES = {"TD": "Tropical depression", "STD": "Subtropical depression", "TS": "Tropical storm",
               "STS": "Subtropical storm", "HU": "Hurricane", "PTC": "Potential tropical cyclone",
               "PC": "Post-tropical cyclone", "TY": "Typhoon"}


def _num(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().upper()
    try:
        sign = -1 if s.endswith(("S", "W")) else 1
        return sign * float(s.rstrip("NSEW").strip())
    except ValueError:
        return None


def active_storms(timeout=10):
    try:
        r = requests.get(FEED, timeout=timeout)
        r.raise_for_status()
        raw = r.json().get("activeStorms") or []
    except Exception as error:  # noqa: BLE001
        return None, str(error)
    storms = []
    for s in raw:
        lat = _num(s.get("latitudeNumeric", s.get("latitude_numeric", s.get("latitude"))))
        lon = _num(s.get("longitudeNumeric", s.get("longitude_numeric", s.get("longitude"))))
        if lat is None or lon is None:
            continue
        storms.append({
            "name": (s.get("name") or "Unnamed").title(),
            "classification": CLASS_NAMES.get(str(s.get("classification", "")).upper(), s.get("classification", "")),
            "intensity_kt": _num(s.get("intensity")),
            "lat": lat, "lon": lon,
            "dir": _num(s.get("movementDir")), "speed_mph": _num(s.get("movementSpeed")),
            "updated": s.get("lastUpdate"),
            "id": s.get("id") or s.get("binNumber"),
        })
    return storms, None


def bearing_deg(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def threat(storm, lat, lon):
    """Distance, whether it is heading toward the farm, rough arrival time, level."""
    d = float(haversine_km(lat, lon, storm["lat"], storm["lon"]))
    toward = None
    eta_h = None
    if storm.get("dir") is not None:
        b = bearing_deg(storm["lat"], storm["lon"], lat, lon)
        off = abs((storm["dir"] - b + 180) % 360 - 180)
        toward = off <= 45
        if toward and storm.get("speed_mph"):
            eta_h = d / (storm["speed_mph"] * 1.609)
    if d <= 400 or (toward and eta_h is not None and eta_h <= 36):
        level = "act now"
    elif d <= 1000 and toward is not False:
        level = "get ready"
    else:
        level = "monitor"
    return {"distance_km": d, "toward": toward, "eta_h": eta_h, "level": level}


def season_status(today=None):
    today = today or date.today()
    if 6 <= today.month <= 11:
        end = date(today.year, 11, 30)
        return f"Atlantic hurricane season is on: {(end - today).days} days to go (ends 30 Nov)."
    start = date(today.year if today.month < 6 else today.year + 1, 6, 1)
    return f"Off season. The next Atlantic hurricane season starts in {(start - today).days} days (1 Jun)."


TALL = {"Plantain", "Corn", "Sorghum", "Pigeon Peas", "Cassava", "Okra"}
STAKED = {"Tomato", "Sweet Pepper", "Hot Pepper", "Bodi", "Cucumber", "Eggplant"}
UNDERGROUND = {"Sweet Potato", "Dasheen", "Cassava", "Peanut"}
LEAFY = {"Pak Choi", "Callaloo", "Cabbage"}


def checklist(crop, stage, drainage=None, slope_pct=None, heavy_rain_month=False):
    """Preparation steps for a storm in the next 1-3 days, tailored to the field.

    Returns (template, params, tag) tuples; templates are English keys in i18n.T.
    """
    steps = []
    if crop:
        if stage in ("mature", "reproductive") and crop not in ("Sunn Hemp", "Mucuna"):
            steps.append(("Harvest what you can sell now: {crop} is at the {stage} stage, so an early harvest beats a total loss.",
                          {"crop": crop, "stage": stage}, "harvest"))
        if crop in TALL:
            steps.append(("{crop} is tall and top-heavy: prop or stake plants, and for plantain harvest mature bunches first.", {"crop": crop}, "wind"))
        if crop in STAKED:
            steps.append(("Check stakes and trellis lines on the {crop}; loosen ties so stems bend rather than snap.", {"crop": crop.lower()}, "wind"))
        if crop in UNDERGROUND:
            steps.append(("{crop} is mostly underground and usually survives wind; focus on drainage so it does not rot.", {"crop": crop}, "water"))
        if crop in LEAFY:
            steps.append(("{crop} is quick to replant: harvest what is ready and keep seed for a fast restart.", {"crop": crop}, "harvest"))
        if stage == "seedling":
            steps.append(("Seedlings are fragile: hold off transplanting until the storm passes; cover nursery trays.", {}, "wind"))
    else:
        steps.append(("The field is bare: sow nothing now. After the storm, a fast cover crop protects the soil.", {}, "soil"))
    steps.append(("Clear field drains, culverts and outlets so water can leave quickly.", {}, "water"))
    if drainage in ("Slow", "Very slow"):
        steps.append(("This soil drains slowly: open extra drainage furrows at the low end of beds.", {}, "water"))
    elif heavy_rain_month:
        steps.append(("Heavy rain is common this month: open extra drainage furrows at the low end of beds.", {}, "water"))
    if slope_pct is not None and slope_pct >= 5:
        steps.append(("Sloping land ({slope}%): put residue or mulch on bare beds to cut erosion.", {"slope": f"{slope_pct:.0f}"}, "soil"))
    steps += [
        ("Do not apply fertiliser or spray before heavy rain: it washes off and pollutes water.", {}, "soil"),
        ("Move seed, fertiliser, fuel and tools to a dry, raised, tied-down store.", {}, "store"),
        ("Photograph the field and crops now; it speeds up insurance and relief claims.", {}, "store"),
        ("Move livestock to high ground with feed and water for three days.", {}, "store"),
    ]
    return steps


def render_steps(steps, lang="en"):
    from .i18n import t
    out = []
    for template, params, _ in steps:
        p = dict(params)
        if "stage" in p:
            p["stage"] = t(p["stage"], lang)
        out.append(t(template, lang, **p))
    return out
