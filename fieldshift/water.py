"""Water watch: is this farm drier or wetter than normal right now?

Method (an empirical cousin of the Standardized Precipitation Index):
for the last N days of NASA POWER rain ending on the latest available
day, compute the same calendar window's total in each of the previous
30 years and report the percentile rank. Root-zone soil wetness
(GWETROOT, MERRA-2) is ranked the same way against a +/-15 day window.

    < 10th percentile  very dry      (roughly SPI < -1.3)
    10th-25th          drier than usual
    25th-75th          near normal
    75th-90th          wetter than usual
    > 90th             very wet

A 7-day forecast (Open-Meteo, ECMWF/GFS blend) turns this into a
weekly irrigation estimate for the crop in the field: FAO-56
ETc = Kc x ET0 minus 80 % of forecast rain.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests

FORECAST_API = "https://api.open-meteo.com/v1/forecast"

CLASSES = [
    (10, "Very dry", "dry2"),
    (25, "Drier than usual", "dry1"),
    (75, "Near normal", "normal"),
    (90, "Wetter than usual", "wet1"),
    (101, "Very wet", "wet2"),
]


def ordinal(n):
    n = int(round(n))
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def classify(pct):
    for limit, label, key in CLASSES:
        if pct < limit:
            return label, key
    return CLASSES[-1][1], CLASSES[-1][2]


def percentile_rank(value, history):
    history = np.asarray([h for h in history if h is not None and not np.isnan(h)])
    if len(history) == 0 or value is None or np.isnan(value):
        return None
    return float((history < value).mean() * 100 + (history == value).mean() * 50)


def rain_anomalies(record, recent, windows=(30, 60, 90)):
    """Percentile of recent N-day rain vs the same window in each past year."""
    if recent is None or "PRECTOTCORR" not in recent:
        return [], None
    r = recent["PRECTOTCORR"].dropna()
    if r.empty:
        return [], None
    end = r.index.max()
    combined = pd.concat([record["PRECTOTCORR"], r]).groupby(level=0).last().sort_index()
    out = []
    for n in windows:
        start = end - pd.Timedelta(days=n - 1)
        current = combined.loc[start:end]
        if len(current) < n * 0.9:
            continue
        total = float(current.sum())
        hist = []
        for y in range(record.index.year.min(), end.year):
            try:
                e = end.replace(year=y)
            except ValueError:  # 29 Feb
                e = end.replace(year=y, day=28)
            s = e - pd.Timedelta(days=n - 1)
            if s < record.index.min():
                continue
            hist.append(float(record["PRECTOTCORR"].loc[s:e].sum()))
        pct = percentile_rank(total, hist)
        if pct is None:
            continue
        label, key = classify(pct)
        out.append({"days": n, "total_mm": total, "normal_mm": float(np.median(hist)),
                    "percentile": pct, "label": label, "key": key, "years": len(hist)})
    return out, end


def soil_anomaly(record, recent, column="GWETROOT"):
    if recent is None or column not in recent or column not in record:
        return None
    r = recent[column].dropna()
    if r.empty:
        return None
    end = r.index.max()
    value = float(r.tail(7).mean())
    doy = record.index.dayofyear
    target = end.dayofyear
    diff = np.minimum(np.abs(doy - target), 365 - np.abs(doy - target))
    hist = record.loc[(diff <= 15) & (record.index.year < end.year), column].groupby(
        record.loc[(diff <= 15) & (record.index.year < end.year)].index.year).mean()
    pct = percentile_rank(value, hist.to_numpy())
    if pct is None:
        return None
    label, key = classify(pct)
    return {"value": value, "normal": float(hist.median()), "percentile": pct, "label": label, "key": key, "date": end}


def dry_spell(recent):
    if recent is None or "PRECTOTCORR" not in recent:
        return None
    r = recent["PRECTOTCORR"].dropna()
    days = 0
    for v in reversed(r.to_numpy()):
        if v < 1.0:
            days += 1
        else:
            break
    return days


def smap_anomaly(series):
    """Latest SMAP value vs the same month in earlier years of the cached record."""
    if series is None or len(series) < 30:
        return None
    s = series.dropna()
    latest_date = s.index.max()
    latest = float(s.loc[latest_date - pd.Timedelta(days=6):].mean())
    same = s[(s.index.month == latest_date.month) & (s.index.year < latest_date.year)]
    if len(same) < 5:
        return {"value": latest, "date": latest_date, "percentile": None}
    pct = percentile_rank(latest, same.groupby(same.index.year).mean().to_numpy())
    label, key = classify(pct) if pct is not None else (None, None)
    return {"value": latest, "date": latest_date, "percentile": pct, "label": label, "key": key,
            "normal": float(same.median())}


def forecast(lat, lon, timeout=15):
    try:
        r = requests.get(FORECAST_API, params={
            "latitude": lat, "longitude": lon, "forecast_days": 7, "timezone": "auto",
            "daily": "precipitation_sum,et0_fao_evapotranspiration,temperature_2m_max",
        }, timeout=timeout)
        r.raise_for_status()
        d = r.json()["daily"]
        return pd.DataFrame({
            "date": pd.to_datetime(d["time"]), "rain_mm": d["precipitation_sum"],
            "et0_mm": d["et0_fao_evapotranspiration"], "tmax": d["temperature_2m_max"],
        })
    except Exception:  # noqa: BLE001
        return None


def weekly_irrigation(fc, kc):
    """mm of irrigation needed over the forecast week for a crop with coefficient kc."""
    if fc is None or kc is None:
        return None
    etc = float((fc["et0_mm"] * kc).sum())
    eff_rain = float((fc["rain_mm"] * 0.8).sum())
    return {"etc_mm": etc, "rain_mm": float(fc["rain_mm"].sum()), "need_mm": max(0.0, etc - eff_rain)}


def irrigation_need_from_climate(et0_month_mm, rain_month_mm, kc, days=7):
    """Fallback when no forecast: use this month's normals."""
    daily = (kc * et0_month_mm - 0.8 * rain_month_mm) / 30.4
    return {"etc_mm": kc * et0_month_mm / 30.4 * days, "rain_mm": rain_month_mm / 30.4 * days,
            "need_mm": max(0.0, daily * days)}


def cumulative_envelope(record, recent, days=90):
    """Cumulative rain over the last `days` vs the 10th-50th-90th percentile of past years."""
    if recent is None or "PRECTOTCORR" not in recent:
        return None
    r = recent["PRECTOTCORR"].dropna()
    if r.empty:
        return None
    end = r.index.max()
    start = end - pd.Timedelta(days=days - 1)
    combined = pd.concat([record["PRECTOTCORR"], r]).groupby(level=0).last().sort_index()
    cur = combined.loc[start:end].cumsum().to_numpy()
    curves = []
    for y in range(record.index.year.min(), end.year):
        try:
            e = end.replace(year=y)
        except ValueError:
            e = end.replace(year=y, day=28)
        s = e - pd.Timedelta(days=days - 1)
        seg = record["PRECTOTCORR"].loc[s:e]
        if len(seg) == days:
            curves.append(seg.cumsum().to_numpy())
    if not curves:
        return None
    arr = np.vstack(curves)
    out = pd.DataFrame({
        "day": np.arange(days),
        "date": pd.date_range(start, periods=days, freq="D"),
        "p10": np.percentile(arr, 10, axis=0),
        "p50": np.percentile(arr, 50, axis=0),
        "p90": np.percentile(arr, 90, axis=0),
    })
    out["this_year"] = np.nan
    out.loc[: len(cur) - 1, "this_year"] = cur
    return out


def crop_stress(et, pet):
    """MODIS evaporative stress: actual ET / potential ET for the latest 8-day
    composite, against the same time of year in the other cached years.
    ~1 = plants transpire freely; below ~0.5 = water-limited."""
    if et is None or pet is None:
        return None
    d = pd.concat({"et": et, "pet": pet}, axis=1).dropna()
    d = d[d["pet"] > 1]
    if len(d) < 6:
        return None
    d["ratio"] = (d["et"] / d["pet"]).clip(0, 1.2)
    latest_date = d.index.max()
    latest = float(d.loc[latest_date, "ratio"])
    doy = d.index.dayofyear
    near = (abs(doy - latest_date.dayofyear) <= 12) & (d.index.year < latest_date.year)
    normal = float(d.loc[near, "ratio"].mean()) if near.any() else None
    return {"date": latest_date, "ratio": latest, "normal": normal,
            "et_mm": float(d.loc[latest_date, "et"]), "pet_mm": float(d.loc[latest_date, "pet"]),
            "label": "water-limited" if latest < 0.5 else ("some stress" if latest < 0.7 else "unstressed")}


def rootzone_status(series, lookback=30):
    """Latest week of SMAP L4 root-zone moisture and its change over `lookback` days."""
    if series is None or len(series.dropna()) < 10:
        return None
    s = series.dropna()
    end = s.index.max()
    now = float(s.loc[end - pd.Timedelta(days=6):].mean())
    before = s.loc[end - pd.Timedelta(days=lookback + 6): end - pd.Timedelta(days=lookback)]
    change = now - float(before.mean()) if len(before) else None
    return {"date": end, "value": now, "change": change, "lookback": lookback}
