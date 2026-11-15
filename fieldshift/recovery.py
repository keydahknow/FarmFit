"""After the storm: photo assessment (Gemini vision) + staged recovery rotation.

AI is used only to *describe what is visible* in a photo, as structured
fields with a confidence. Every decision afterwards is made by explicit,
documented rules, and anything a photo cannot show (floodwater source,
contamination, how long water stood) is asked of the farmer.

Food-safety rule follows the U.S. FDA guidance "Evaluating the Safety of
Flood-affected Food Crops for Human Consumption": if floodwater touched
the edible part of a crop, that produce is treated as adulterated and
should not enter the food supply.
"""

import base64
import json

import requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-2.5-flash"

PROMPT = """You are helping a small-scale Caribbean farmer after a hurricane or heavy rain.
Look ONLY at what is visible in this field photo. Do not guess at things you cannot see.
Return JSON with exactly these keys:
{
 "standing_water": "none" | "puddles" | "widespread",
 "bare_soil_percent": integer 0-100,
 "erosion": "none" | "sheet" | "rills" | "gullies",
 "sediment_or_debris": "none" | "some" | "heavy",
 "plants_lodged_or_broken": "none" | "some" | "most" | "no crop visible",
 "leaf_damage": "none" | "some" | "severe" | "no crop visible",
 "crop_guess": string (or "unknown"),
 "visible_notes": short string, plain language, max 40 words,
 "confidence": number 0-1,
 "cannot_tell_from_photo": list of short strings
}"""


FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]


def assess_photo(image_bytes, mime_type, api_key, model=None, timeout=60):
    """Try the configured model, then fall back through FALLBACK_MODELS."""
    if not api_key:
        return {"ok": False, "error": "No Gemini API key configured."}
    errors = []
    for name in ([model] if model else []) + [m for m in FALLBACK_MODELS if m != model]:
        res = _assess_once(image_bytes, mime_type, api_key, name, timeout)
        if res["ok"]:
            return res
        errors.append(f"{name}: {res['error'][:120]}")
    return {"ok": False, "error": " | ".join(errors)}


def _assess_once(image_bytes, mime_type, api_key, model, timeout):
    body = {
        "contents": [{
            "parts": [
                {"text": PROMPT},
                {"inline_data": {"mime_type": mime_type or "image/jpeg",
                                 "data": base64.b64encode(image_bytes).decode()}},
            ]
        }],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.1},
    }
    try:
        response = requests.post(GEMINI_URL.format(model=model), params={"key": api_key}, json=body, timeout=timeout)
        response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(text)
        return {"ok": True, "result": data, "model": model}
    except Exception as error:  # noqa: BLE001
        return {"ok": False, "error": str(error)}


# ---------------------------------------------------------------------------
# Rule-based field state
# ---------------------------------------------------------------------------

def field_state(photo, answers, recent_rain_mm=None, soil_wet_root=None, drainage=None):
    """Combine photo findings, farmer answers and satellite context into flags."""
    photo = photo or {}
    flags, notes = [], []

    standing = photo.get("standing_water", "none")
    if answers.get("standing_water_days", 0) >= 1 or standing in ("puddles", "widespread"):
        flags.append("waterlogged")
    if answers.get("standing_water_days", 0) >= 4 or standing == "widespread":
        flags.append("prolonged_flooding")
    if photo.get("erosion") in ("rills", "gullies") or answers.get("soil_washed"):
        flags.append("eroded")
    if photo.get("sediment_or_debris") == "heavy" or answers.get("debris"):
        flags.append("debris")
    if photo.get("plants_lodged_or_broken") in ("some", "most") or photo.get("leaf_damage") == "severe":
        flags.append("crop_damaged")
    if (photo.get("bare_soil_percent") or 0) >= 50:
        flags.append("bare")

    contact = answers.get("flood_touched_edible")
    source = answers.get("water_source", "Rain only")
    if contact == "Yes":
        flags.append("edible_contact")
    if source in ("River or drain overflow", "Sewage / septic", "Livestock area", "Industrial / unknown"):
        flags.append("contamination_risk")
    if contact == "Not sure":
        flags.append("unknown_contact")

    if recent_rain_mm is not None and recent_rain_mm >= 150:
        notes.append(f"NASA POWER shows about {recent_rain_mm:.0f} mm of rain in the last 14 days, so soils are likely saturated.")
        if "waterlogged" not in flags and drainage in ("Slow", "Very slow"):
            flags.append("waterlogged")
    if soil_wet_root is not None and soil_wet_root >= 0.85:
        notes.append(f"Root-zone soil wetness is {soil_wet_root:.2f} (0-1 scale) in NASA POWER / MERRA-2, which is near saturation.")
    return {"flags": sorted(set(flags)), "notes": notes}


QUICK_COVER = ["Sunn Hemp", "Cowpea", "Mucuna"]
QUICK_FOOD = ["Pak Choi", "Callaloo", "Bodi", "Cucumber"]


def recovery_stages(state, month_now, wet_field=False):
    """Ordered recovery stages, each with actions and a gate to pass before moving on."""
    f = set(state["flags"])
    stages = []

    safety = [
        "Stay out of fields with downed power lines or fast-moving water.",
        "Photograph damage for insurance or assistance claims before clearing.",
    ]
    if "edible_contact" in f:
        safety.insert(0, "Floodwater touched the edible part of the crop. Do not harvest it for food or sale; destroy it safely (FDA flood-affected crops guidance).")
    if "unknown_contact" in f:
        safety.insert(0, "You are not sure whether floodwater reached the edible parts. Treat those crops as unsafe until an extension officer checks.")
    if "contamination_risk" in f:
        safety.append("Floodwater may have carried sewage, livestock waste or chemicals. Ask the Ministry of Agriculture / extension service about soil testing before growing leafy or root crops eaten raw.")
    stages.append({
        "title": "Safety & salvage",
        "weeks": "Week 0-1",
        "icon": "🦺",
        "actions": safety,
        "gate": "Hazards cleared and unsafe produce removed.",
    })

    drain_actions = []
    if "waterlogged" in f:
        drain_actions += [
            "Open field drains and outlets; do not drive or till wet soil (it compacts).",
            "Squeeze test: if a handful of soil drips or smears like paste, it is too wet to work.",
        ]
    if "prolonged_flooding" in f:
        drain_actions.append("Water stood for days: expect root death in most vegetables. Plan to replant rather than nurse them.")
    if "eroded" in f:
        drain_actions.append("Fill rills, re-shape beds along the contour and put crop residue or mulch on exposed soil.")
    if "debris" in f:
        drain_actions.append("Remove debris and sediment layers thicker than about 5 cm before planting.")
    if not drain_actions:
        drain_actions.append("Field drained quickly. Check beds and drains, then move on.")
    stages.append({
        "title": "Drain & stabilise",
        "weeks": "Week 1-3",
        "icon": "🚰",
        "actions": drain_actions,
        "gate": "No standing water for 7 days and soil passes the squeeze test.",
    })

    cover_ok = "contamination_risk" not in f
    quick = QUICK_COVER if not cover_ok or "eroded" in f or "bare" in f else QUICK_COVER + QUICK_FOOD
    stages.append({
        "title": "Cover & rebuild",
        "weeks": "Week 3-10",
        "icon": "🌱",
        "actions": [
            "Sow a fast cover crop to hold soil and feed it: sunn hemp or cowpea (6-8 weeks) are quickest; mucuna gives the densest mat.",
            "Leafy greens are only advised once contamination is ruled out." if not cover_ok else
            "If you need cash quickly, patchoi or callaloo give a harvest in about 5-6 weeks.",
        ],
        "gate": "Cover is established; soil test or extension clearance received if contamination was possible.",
        "crops": quick,
    })

    wet_note = []
    if wet_field and "waterlogged" in f and "contamination_risk" not in f:
        wet_note.append("On a low-lying field with managed water, dasheen or a submergence-tolerant rice variety can use the wet conditions. Confirm variety choice locally (PhilRice and CARDI guidance).")
    stages.append({
        "title": "Back to production",
        "weeks": "Month 3+",
        "icon": "🧺",
        "actions": [
            "Return to the Storm-smart calendar below. It restarts from the current month and harvests ahead of the next peak storm months.",
        ] + wet_note,
        "gate": "Ongoing: re-run FarmFit before each season.",
    })
    return stages
