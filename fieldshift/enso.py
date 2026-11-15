"""El Nino / La Nina (ENSO) and what it has meant for rain at this farm.

The Oceanic Nino Index (ONI) is NOAA CPC's 3-month running mean of sea-surface
temperature anomalies in the Nino 3.4 region of the Pacific. El Nino years tend
to dry the Caribbean's late wet season; La Nina years tend to wet it. Instead of
quoting that rule of thumb, `outlook` measures it at the farm: it splits the
farm's own 30-year NASA POWER record by ENSO phase and compares the rain that
fell in the coming three months.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import requests

ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
SEASONS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
CACHE = Path(__file__).resolve().parents[1] / "data" / "cache" / "oni.csv"


def parse_oni(text):
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[0] in SEASONS:
            season, year, total, anom = parts
            rows.append({"season": season, "year": int(year), "total": float(total), "anom": float(anom),
                         "month": SEASONS.index(season) + 1})  # centre month of the 3-month season
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
    return df


def fetch_oni(timeout=60):
    r = requests.get(ONI_URL, timeout=timeout)
    r.raise_for_status()
    return parse_oni(r.text)


def load_oni(path=CACHE):
    if Path(path).exists():
        df = pd.read_csv(path, parse_dates=["date"])
        return df if len(df) else None
    return None


def phase(anom):
    if anom >= 0.5:
        return "El Niño"
    if anom <= -0.5:
        return "La Niña"
    return "Neutral"


def outlook(daily, oni, today=None, months=3):
    """Rain in the next `months` months at this farm, by ENSO phase.

    daily: NASA POWER daily frame with PRECTOTCORR. oni: from parse_oni/load_oni.
    Each past year Y is classed by the ONI of the same season as the latest
    reading, and scored by rain in the same calendar window as the one ahead.
    """
    if daily is None or oni is None or not len(oni) or "PRECTOTCORR" not in daily:
        return None
    today = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    latest = oni.iloc[-1]
    anchor = pd.Timestamp(latest["date"])
    start0 = (today + pd.offsets.MonthBegin(1)).normalize()
    rain = daily["PRECTOTCORR"].dropna()
    years = []
    for y in range(rain.index.min().year, rain.index.max().year + 1):
        shift = pd.DateOffset(years=y - today.year)
        start = start0 + shift
        end = start + pd.DateOffset(months=months) - pd.Timedelta(days=1)
        if start < rain.index.min() or end > rain.index.max():
            continue
        row = oni[oni["date"] == anchor + shift]
        if row.empty:
            continue
        years.append({"year": y, "oni": float(row["anom"].iloc[0]), "rain_mm": float(rain[start:end].sum())})
    if len(years) < 8:
        return None
    df = pd.DataFrame(years)
    normal = df["rain_mm"].mean()
    df["pct_normal"] = 100 * df["rain_mm"] / normal
    df["phase"] = df["oni"].map(phase)
    by_phase = {}
    for ph in ("El Niño", "Neutral", "La Niña"):
        part = df[df["phase"] == ph]
        if len(part):
            by_phase[ph] = {"n": int(len(part)), "pct_normal": float(part["pct_normal"].mean()),
                            "years": part["year"].tolist(),
                            "dry_share": float((part["pct_normal"] < 80).mean())}
    r = float(np.corrcoef(df["oni"], df["pct_normal"])[0, 1]) if df["oni"].std() > 0 else 0.0
    window = [((start0.month - 1 + k) % 12) + 1 for k in range(months)]
    return {
        "now": {"season": latest["season"], "year": int(latest["year"]), "anom": float(latest["anom"]),
                "phase": phase(latest["anom"])},
        "window_months": window,
        "normal_mm": float(normal),
        "by_phase": by_phase,
        "r": r,
        "years": df,
    }
