"""The farmer's own profile: what onboarding collects and every page uses.

Only location is required. Everything else is optional, because many farmers
have no soil test, sensor or exact measurements. The profile lives in the
session and can be kept as a bookmarkable link (?p=...) or a small JSON file;
no account or server-side storage is needed.
"""

import base64
import json
import zlib
from datetime import date

MODES = {"farm": "Commercial farm", "garden": "Home garden"}
SIZE_UNITS = {"acres": 0.404686, "hectares": 1.0, "square metres": 0.0001}
SOIL_TYPES = ["I don't know", "Clay (sticky, holds water)", "Loam (crumbly, dark)", "Sandy (gritty, dries fast)",
              "Rocky or shallow", "Peat or very wet"]
SOIL_TO_DRAINAGE = {"Clay (sticky, holds water)": "Slow", "Loam (crumbly, dark)": "Moderate",
                    "Sandy (gritty, dries fast)": "Fast", "Rocky or shallow": "Fast", "Peat or very wet": "Very slow"}
WATER = ["Rain only", "Some water (drum, tank or standpipe)", "Reliable irrigation (drip, sprinkler or river)"]
WATER_TO_IRRIGATION = {WATER[0]: "No irrigation", WATER[1]: "Limited irrigation", WATER[2]: "Reliable irrigation"}
EQUIPMENT = ["Hand tools only", "Tractor or rotavator", "Water pump", "Rain tank", "Greenhouse or shade house",
             "Soil moisture sensor", "Weather station", "Smartphone camera"]
GARDEN_SPACES = ["Containers or pots", "Raised bed", "Backyard plot", "Balcony or wall (vertical)"]

FIELDS = ("mode", "name", "lat", "lon", "place", "size", "size_unit", "crops", "soil_type", "ph", "water",
          "equipment", "garden_space", "sun_hours", "notes", "wet_field", "created")


def new(mode="farm"):
    return {"mode": mode, "name": "", "lat": None, "lon": None, "place": "", "size": None, "size_unit": "acres",
            "crops": [], "soil_type": SOIL_TYPES[0], "ph": None, "water": WATER[0], "equipment": [],
            "garden_space": [], "sun_hours": None, "notes": "", "wet_field": False, "created": date.today().isoformat()}


def complete(p):
    return bool(p and p.get("lat") is not None and p.get("lon") is not None and p.get("mode") in MODES)


def hectares(p):
    if not p or not p.get("size"):
        return None
    return float(p["size"]) * SIZE_UNITS.get(p.get("size_unit", "acres"), 1.0)


def irrigation(p):
    return WATER_TO_IRRIGATION.get((p or {}).get("water"), "No irrigation")


def soil_override(p):
    """What the farmer told us beats the 250 m satellite estimate."""
    out = {}
    if p and p.get("ph"):
        out["ph"] = float(p["ph"])
    if p and p.get("soil_type") in SOIL_TO_DRAINAGE:
        out["drainage"] = SOIL_TO_DRAINAGE[p["soil_type"]]
    return out


def encode(p):
    """Compact, URL-safe string for a bookmarkable link."""
    slim = {k: p.get(k) for k in FIELDS if p.get(k) not in (None, "", [], False)}
    raw = zlib.compress(json.dumps(slim, separators=(",", ":")).encode())
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def clean(p):
    """Make a profile from a link or file safe to use: unknown choices fall back to defaults,
    coordinates must be numbers on the globe. Returns None if it can't be a farm."""
    d = new(p.get("mode") if p.get("mode") in MODES else "farm")
    d.update({k: v for k, v in p.items() if k in FIELDS})
    d["mode"] = d["mode"] if d["mode"] in MODES else "farm"
    for key, options in (("water", WATER), ("soil_type", SOIL_TYPES), ("size_unit", list(SIZE_UNITS))):
        if d.get(key) not in options:
            d[key] = options[0]
    for key, options in (("equipment", EQUIPMENT), ("garden_space", GARDEN_SPACES)):
        d[key] = [x for x in (d.get(key) or []) if x in options] if isinstance(d.get(key), list) else []
    d["crops"] = [str(c) for c in d.get("crops") or []][:6] if isinstance(d.get("crops"), list) else []
    try:
        d["lat"], d["lon"] = float(d["lat"]), float(d["lon"])
    except (TypeError, ValueError):
        return None
    if not (-90 <= d["lat"] <= 90 and -180 <= d["lon"] <= 180):
        return None
    for key in ("size", "ph", "sun_hours"):
        try:
            d[key] = float(d[key]) if d.get(key) not in (None, "") else None
        except (TypeError, ValueError):
            d[key] = None
    for key in ("name", "place", "notes"):
        d[key] = str(d.get(key) or "")[:200]
    d["wet_field"] = bool(d.get("wet_field"))
    return d if complete(d) else None


def decode(s):
    try:
        raw = zlib.decompress(base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)))
        data = json.loads(raw)
    except Exception:  # noqa: BLE001
        return None
    return clean(data) if isinstance(data, dict) else None


def from_json(text):
    try:
        data = json.loads(text)
    except Exception:  # noqa: BLE001
        return None
    return clean(data) if isinstance(data, dict) else None


def to_json(p):
    return json.dumps({k: p.get(k) for k in FIELDS}, indent=2)


def rotation_from_crops(crops_grown, start_month, crop_table):
    """A first-guess rotation from the crops a farmer named: planted one after another from this month."""
    rows, m = [], start_month
    for c in crops_grown[:4]:
        if c not in crop_table.index:
            continue
        months = int(max(1, min(12, round(crop_table.loc[c, "days_to_harvest"] / 30.4))))
        rows.append((c, m, months))
        m = (m - 1 + months) % 12 + 1
    return rows
