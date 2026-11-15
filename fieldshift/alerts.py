"""Storm and drought alerts for a farm.

Delivery is privacy-first: alerts are published to a public ntfy topic
for the farm (https://ntfy.sh, free, open source, no sign-up). Farmers
subscribe to the topic in the ntfy phone app, so FarmFit never stores a
phone number. Optional SMS uses Twilio when TWILIO_* secrets and an
ALERT_SMS mapping ({"farm_id": ["+1868..."]}) are configured as GitHub
or Streamlit secrets (never in the repository).

The same rules run in the app (preview) and on a schedule
(scripts/check_alerts.py via .github/workflows/storm-alerts.yml).
"""

import hashlib
import json
import os
import re

import requests

from . import stormwatch, water

NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")


def topic_for(farm_id=None, lat=None, lon=None, label=None):
    """Stable, hard-to-guess-by-accident topic name for a farm."""
    base = farm_id or f"{lat:.2f},{lon:.2f}"
    slug = re.sub(r"[^a-z0-9]+", "-", (label or farm_id or "farm").lower()).strip("-")[:28]
    digest = hashlib.sha1(f"farmfit:{base}".encode()).hexdigest()[:6]
    return f"farmfit-{slug}-{digest}"


def subscribe_url(topic):
    return f"{NTFY_SERVER}/{topic}"


def evaluate(lat, lon, label, active=None, record=None, recent=None):
    """Return alert dicts {key, level, title, message, priority, tags}."""
    alerts = []
    for s in active or []:
        th = stormwatch.threat(s, lat, lon)
        if th["level"] == "monitor":
            continue
        eta = f" It could arrive in about {th['eta_h']:.0f} hours." if th["eta_h"] and th["toward"] else ""
        level = th["level"]
        alerts.append({
            "key": f"storm:{s.get('id') or s['name']}:{level}",
            "level": level,
            "title": f"{'ACT NOW' if level == 'act now' else 'GET READY'}: {s['name']} near {label}",
            "message": (f"{s['classification']} {s['name']} ({(s['intensity_kt'] or 0):.0f} kt) is {th['distance_km']:,.0f} km from your farm."
                        f"{eta} Harvest what is ready, clear drains, store seed and fuel, move livestock high. "
                        "Follow your national met service for official warnings."),
            "priority": "urgent" if level == "act now" else "high",
            "tags": "cyclone,warning",
        })
    if record is not None and recent is not None:
        anomalies, end = water.rain_anomalies(record, recent, windows=(60,))
        for a in anomalies:
            if a["key"] in ("dry2",):
                alerts.append({
                    "key": f"drought:{end:%Y-%m}",
                    "level": "dry",
                    "title": f"Very dry at {label}",
                    "message": (f"Only {a['total_mm']:.0f} mm of rain in the last 60 days (normal about {a['normal_mm']:.0f} mm), "
                                f"drier than {100 - a['percentile']:.0f}% of the last 30 years (NASA POWER). "
                                "Prioritise water for crops at flowering, mulch beds, and check your tank level."),
                    "priority": "default", "tags": "sunny,droplet",
                })
            elif a["key"] == "wet2":
                alerts.append({
                    "key": f"wet:{end:%Y-%m}",
                    "level": "wet",
                    "title": f"Very wet at {label}",
                    "message": (f"{a['total_mm']:.0f} mm of rain in the last 60 days (normal about {a['normal_mm']:.0f} mm). "
                                "Keep drains open, avoid working wet soil, watch for root rot."),
                    "priority": "default", "tags": "cloud_with_rain",
                })
    return alerts


def send_ntfy(topic, alert, timeout=15):
    r = requests.post(
        f"{NTFY_SERVER}/{topic}",
        data=alert["message"].encode("utf-8"),
        headers={"Title": alert["title"].encode("utf-8"), "Priority": alert.get("priority", "default"),
                 "Tags": alert.get("tags", "")},
        timeout=timeout,
    )
    r.raise_for_status()
    return True


def send_sms(numbers, alert, timeout=20):
    sid, token, sender = (os.environ.get(k) for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM"))
    if not (sid and token and sender and numbers):
        return 0
    sent = 0
    for n in numbers:
        r = requests.post(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", auth=(sid, token),
                          data={"From": sender, "To": n, "Body": f"{alert['title']}\n{alert['message']}"[:600]}, timeout=timeout)
        sent += r.ok
    return sent


def sms_numbers(farm_id):
    try:
        return json.loads(os.environ.get("ALERT_SMS", "{}")).get(farm_id, [])
    except ValueError:
        return []


def qr_svg(url, scale=4):
    try:
        import segno
        return segno.make(url, error="m").svg_inline(scale=scale, dark="#1F2B3A", light=None)
    except Exception:  # noqa: BLE001
        return ""
