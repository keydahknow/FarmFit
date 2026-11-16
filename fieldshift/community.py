"""Community pest and disease watch: farmer reports, area alerts, officer review.

Safeguards built in:
- Every report starts as "unverified" and is shown that way until an
  agricultural officer verifies or dismisses it.
- The exact farm location is never stored: points are snapped to the centre
  of a ~2 km grid cell before saving.
- AI (Gemini) may suggest what a photo shows, labelled as a suggestion with a
  confidence value; it never sets the category or the status.
- Alerts carry only category, severity and the approximate area.

Storage is a JSON-lines file plus resized photos (COMMUNITY_DIR, default
data/community). On Streamlit Community Cloud that disk is reset when the app
restarts; a production deployment would point COMMUNITY_DIR at a persistent
volume or swap these four functions for a database.
"""

import base64
import io
import json
import math
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

DIR = Path(os.environ.get("COMMUNITY_DIR", Path(__file__).resolve().parents[1] / "data" / "community"))
GRID = 0.02            # ~2.2 km: how far a report's location is blurred
AREA = 0.25            # ~28 km: alert area for "follow my area"
NTFY = "https://ntfy.sh"

CATEGORIES = {
    "insects": ("Insects and caterpillars", "#C2502F", "e.g. fall armyworm, beet armyworm, whitefly, aphids, thrips"),
    "locusts": ("Locusts and grasshoppers", "#8E3B1F", "swarms or many hoppers eating leaves"),
    "fungal": ("Fungal disease", "#7A5BA6", "e.g. early or late blight, powdery or downy mildew, leaf spots, rust"),
    "bacterial": ("Bacterial disease", "#3F7EA0", "e.g. bacterial wilt (sudden wilting), black rot, soft rot"),
    "viral": ("Viral disease", "#D99A2B", "e.g. leaf curl, mosaic (mottled yellow leaves), stunting"),
    "animals": ("Rats, birds or other animals", "#6b4a32", "damage from rodents, birds, stray livestock"),
    "weeds": ("Invasive weeds", "#3F7A4C", "fast-spreading weeds taking over fields"),
    "other": ("Other or not sure", "#4C5563", "describe what you see"),
}
SEVERITY = {"low": "A few plants", "medium": "Part of the field", "high": "Most of the field or spreading fast"}
STATUS = {"unverified": "Unverified", "verified": "Verified by an officer", "dismissed": "Dismissed after review"}

# General integrated pest management steps (FAO IPM, CABI PlantwisePlus). Not a diagnosis.
PREVENT = {
    "insects": ["Scout the field twice a week, checking leaf undersides and growing points.",
                "Remove and destroy egg masses and badly infested plants.",
                "Use pesticides only as your extension officer advises; rotate products to avoid resistance."],
    "locusts": ["Report swarms to the Ministry of Agriculture straight away: control is coordinated by government.",
                "Do not spray on your own near water or bees."],
    "fungal": ["Remove infected leaves; do not compost them.", "Water the soil, not the leaves; water in the morning.",
               "Space plants for air flow and rotate away from the same crop family."],
    "bacterial": ["Pull and bag wilted plants; clean tools between plants.",
                  "Do not replant the same family (tomato, pepper, eggplant) in that bed for at least a season."],
    "viral": ["Remove plants with mottled or curled leaves early.", "Control whitefly and aphids, which spread viruses.",
              "Use clean seedlings from a trusted nursery."],
    "animals": ["Clear bush and rubbish around the field; store feed and harvest off the ground."],
    "weeds": ["Remove before they seed; mulch or cover-crop bare ground."],
    "other": ["Take clear photos of the whole plant, a close-up of the damage and the underside of a leaf for your extension officer."],
}

AI_PROMPT = """You help Caribbean farmers triage crop problems from a photo. Reply as JSON with keys:
category (one of: insects, locusts, fungal, bacterial, viral, animals, weeds, other),
likely (short name of the most likely pest or disease, or "unclear"),
confidence (0-1), visible (one sentence on what is actually visible), next_step (one sentence).
If the photo is unclear or not a plant, set category "other" and confidence below 0.3. Never claim certainty."""


def _path():
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / "photos").mkdir(exist_ok=True)
    return DIR / "reports.jsonl"


def blur(lat, lon, grid=GRID):
    """Centre of the ~2 km cell the point falls in: never the farm itself."""
    return (round((math.floor(lat / grid) + 0.5) * grid, 4), round((math.floor(lon / grid) + 0.5) * grid, 4))


def area_topic(lat, lon):
    a, b = blur(lat, lon, AREA)
    return f"farmfit-pests-{a:+.3f}{b:+.3f}".replace("+", "n").replace("-", "s").replace(".", "")


def distance_km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = 0.5 - math.cos((lat2 - lat1) * p) / 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2
    return 12742 * math.asin(math.sqrt(a))


def load():
    path = _path()
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _save_all(reports):
    path = _path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in reports))
    tmp.replace(path)


def save_photo(image_bytes, report_id, max_side=900):
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        im.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=82)  # re-encoding also drops EXIF, including GPS
        name = f"{report_id}.jpg"
        (DIR / "photos" / name).write_bytes(buf.getvalue())
        return name
    except Exception:  # noqa: BLE001
        return None


def add(lat, lon, category, severity, description, crop=None, area_name="", photo=None, ai=None, now=None):
    if category not in CATEGORIES or severity not in SEVERITY:
        raise ValueError("unknown category or severity")
    blat, blon = blur(lat, lon)
    rid = uuid.uuid4().hex[:10]
    report = {
        "id": rid, "created": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "lat": blat, "lon": blon, "category": category, "severity": severity,
        "description": (description or "").strip()[:600], "crop": crop or "", "area": (area_name or "").strip()[:80],
        "status": "unverified", "reviewer": "", "guidance": "", "followers": 0, "ai": ai or None,
        "photo": save_photo(photo, rid) if photo else None,
    }
    reports = load()
    reports.append(report)
    _save_all(reports)
    return report


def update(report_id, **changes):
    reports = load()
    for r in reports:
        if r["id"] == report_id:
            r.update({k: v for k, v in changes.items() if k in ("status", "reviewer", "guidance", "followers")})
            r["reviewed"] = datetime.now(timezone.utc).isoformat(timespec="seconds") if "status" in changes else r.get("reviewed")
    _save_all(reports)


def photo_bytes(report):
    if not report.get("photo"):
        return None
    p = DIR / "photos" / report["photo"]
    return p.read_bytes() if p.exists() else None


def nearby(reports, lat, lon, km=25, days=30, now=None):
    now = now or datetime.now(timezone.utc)
    out = []
    for r in reports:
        age = now - datetime.fromisoformat(r["created"])
        if age <= timedelta(days=days) and r.get("status") != "dismissed":
            d = distance_km(lat, lon, r["lat"], r["lon"])
            if d <= km:
                out.append({**r, "km": d, "age_days": age.total_seconds() / 86400})
    return sorted(out, key=lambda r: r["km"])


def hotspots(reports, days=14, min_reports=3, now=None):
    """Areas (~28 km cells) with several recent reports of the same kind: a possible outbreak."""
    now = now or datetime.now(timezone.utc)
    cells = {}
    for r in reports:
        if r.get("status") == "dismissed" or now - datetime.fromisoformat(r["created"]) > timedelta(days=days):
            continue
        key = (blur(r["lat"], r["lon"], AREA), r["category"])
        cells.setdefault(key, []).append(r)
    return [{"lat": k[0][0], "lon": k[0][1], "category": k[1], "count": len(v),
             "verified": sum(x["status"] == "verified" for x in v)}
            for k, v in cells.items() if len(v) >= min_reports]


def notify_area(report, timeout=10):
    """Push a short, anonymous alert to everyone following this area."""
    label = CATEGORIES[report["category"]][0]
    msg = (f"{label} reported near {report['area'] or 'your area'} ({SEVERITY[report['severity']].lower()}). "
           f"Status: unverified. Check your crops and the FarmFit pest map.")
    try:
        r = requests.post(f"{NTFY}/{area_topic(report['lat'], report['lon'])}", data=msg.encode(),
                          headers={"Title": "FarmFit pest watch", "Tags": "bug", "Priority": "default"}, timeout=timeout)
        return r.ok
    except Exception:  # noqa: BLE001
        return False


def ai_triage(image_bytes, mime_type, api_key, model=None):
    """Gemini's suggestion for a photo. A suggestion only, never a diagnosis."""
    if not api_key:
        return {"ok": False, "error": "No Gemini API key configured."}
    from . import assistant
    body = {"contents": [{"parts": [{"text": AI_PROMPT}, {"inline_data": {"mime_type": mime_type or "image/jpeg",
                                                                          "data": base64.b64encode(image_bytes).decode()}}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.1}}
    try:
        resp, name = assistant.generate(api_key, body, preferred=model)
        data = json.loads(resp["candidates"][0]["content"]["parts"][0]["text"])
        if data.get("category") not in CATEGORIES:
            data["category"] = "other"
        data["confidence"] = max(0.0, min(1.0, float(data.get("confidence", 0))))
        return {"ok": True, "result": data, "model": name}
    except Exception as error:  # noqa: BLE001
        return {"ok": False, "error": str(error)[:400]}


def example_reports(lat, lon, now=None):
    """SIMULATED reports for demonstrating the map. Clearly flagged; never saved."""
    now = now or datetime.now(timezone.utc)
    spec = [(0.03, 0.05, "insects", "high", "Caterpillars in the corn whorls, ragged leaves", "Corn", 1, "verified"),
            (-0.04, 0.02, "insects", "medium", "Leaves eaten, frass in the funnel", "Corn", 2, "unverified"),
            (0.06, -0.03, "fungal", "medium", "Brown spots with rings on lower tomato leaves", "Tomato", 3, "unverified"),
            (-0.02, -0.07, "bacterial", "high", "Pepper plants wilting suddenly in the heat", "Sweet Pepper", 5, "verified"),
            (0.09, 0.08, "viral", "low", "Curled, yellow-mottled leaves on a few plants", "Tomato", 8, "unverified"),
            (-0.07, 0.10, "animals", "medium", "Rats in the sweet potato beds", "Sweet Potato", 4, "unverified")]
    out = []
    for i, (dl, dn, cat, sev, desc, crop, age, status) in enumerate(spec):
        blat, blon = blur(lat + dl, lon + dn)
        out.append({"id": f"example{i}", "created": (now - timedelta(days=age)).isoformat(timespec="seconds"),
                    "lat": blat, "lon": blon, "category": cat, "severity": sev, "description": desc, "crop": crop,
                    "area": "", "status": status, "reviewer": "", "guidance": "", "followers": 0, "ai": None,
                    "photo": None, "simulated": True})
    return out
