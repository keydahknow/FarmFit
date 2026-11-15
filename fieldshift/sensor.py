"""Ground truth: compare a farmer's own soil-moisture probe with NASA data.

Satellites (SMAP 9 km) and reanalysis (POWER/MERRA-2 ~55 km) see an area
far larger than one field, and a cheap capacitive probe reports relative
wetness, not calibrated volumetric water. So we compare *patterns*, not
absolute values: each series is turned into a standardised anomaly
z = (x - mean) / std over the shared days, and we report the Pearson
correlation r and the number of overlapping days.

Readings follow the IFRS sensor contract with soil fields added:
    {"device_id": "...", "ts": "2026-11-02T14:05:00Z", "soil_raw": 2310,
     "soil_pct": 41.2, "battery_v": 4.1, "seq": 1043}
"""

import io
import json

import numpy as np
import pandas as pd
import requests

NTFY_SERVER = "https://ntfy.sh"


def calibrate(raw, dry_raw, wet_raw):
    """Two-point calibration to 0-100 % relative wetness (capacitive probes read lower when wetter)."""
    pct = (dry_raw - np.asarray(raw, float)) / (dry_raw - wet_raw) * 100
    return np.clip(pct, 0, 100)


def parse_csv(file_bytes, dry_raw=2900, wet_raw=1300):
    df = pd.read_csv(io.BytesIO(file_bytes))
    cols = {c.lower().strip(): c for c in df.columns}
    tcol = cols.get("ts") or cols.get("timestamp") or cols.get("time") or cols.get("date")
    if not tcol:
        raise ValueError("CSV needs a 'ts' (timestamp) column")
    ts = pd.to_datetime(df[tcol], utc=True, errors="coerce")
    if "soil_pct" in cols:
        value = pd.to_numeric(df[cols["soil_pct"]], errors="coerce")
    elif "soil_vwc" in cols:
        value = pd.to_numeric(df[cols["soil_vwc"]], errors="coerce") * 100
    elif "soil_raw" in cols:
        value = pd.Series(calibrate(pd.to_numeric(df[cols["soil_raw"]], errors="coerce"), dry_raw, wet_raw))
    else:
        raise ValueError("CSV needs soil_pct, soil_vwc or soil_raw")
    out = pd.Series(value.to_numpy(), index=ts).dropna()
    out = out[out.index.notna()].sort_index()
    out.index = out.index.tz_convert(None)
    return out.rename("sensor_pct")


def poll_ntfy(topic, since="12h", timeout=15):
    """Recent readings a probe published to its ntfy topic (ntfy.sh keeps ~12 h)."""
    r = requests.get(f"{NTFY_SERVER}/{topic}/json", params={"poll": 1, "since": since}, timeout=timeout)
    r.raise_for_status()
    rows = []
    for line in r.text.splitlines():
        try:
            msg = json.loads(line)
            body = json.loads(msg.get("message", "{}"))
        except ValueError:
            continue
        ts = body.get("ts") or msg.get("time")
        val = body.get("soil_pct")
        if val is None and body.get("soil_raw") is not None:
            val = float(calibrate([body["soil_raw"]], 2900, 1300)[0])
        if val is not None:
            rows.append((pd.to_datetime(ts, unit="s" if isinstance(ts, (int, float)) else None, utc=True), float(val)))
    if not rows:
        return pd.Series(dtype=float, name="sensor_pct")
    s = pd.Series(dict(rows)).sort_index()
    s.index = s.index.tz_convert(None)
    return s.rename("sensor_pct")


def compare(sensor, references):
    """Daily means, z-scores and correlations against reference series (name -> Series)."""
    daily = sensor.resample("D").mean().dropna()
    frame = pd.DataFrame({"Your probe": daily})
    stats = []
    for name, ref in references.items():
        if ref is None or len(ref) == 0:
            continue
        r = ref.copy()
        r.index = pd.to_datetime(r.index).tz_localize(None) if getattr(r.index, "tz", None) else pd.to_datetime(r.index)
        frame[name] = r.resample("D").mean().reindex(frame.index).interpolate(limit=3)
        both = frame[["Your probe", name]].dropna()
        corr = float(both.corr().iloc[0, 1]) if len(both) >= 5 else None
        stats.append({"reference": name, "days": len(both), "r": corr})
    z = (frame - frame.mean()) / frame.std(ddof=0)
    return z.reset_index(names="date"), stats
