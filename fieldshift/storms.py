"""Historical tropical-cyclone exposure at a farm, from NOAA HURDAT2.

Method (documented in the README):
1. Interpolate every storm track to 15-minute positions.
2. Estimate sustained wind at the farm from each position with a
   modified Rankine vortex: inside the radius of maximum wind (RMW) wind
   grows linearly; outside it decays as (RMW / r) ** X with X = 0.6.
   RMW comes from HURDAT2 where reported, otherwise a 40 km climatological
   value. A 0.85 factor converts open-water best-track winds to rough
   land exposure.
3. Keep each storm's peak estimated wind at the farm and the time it
   happened.
4. Count, for each calendar month, the share of years since START_YEAR
   that had at least one storm bringing tropical-storm-force (>= 34 kt) or
   hurricane-force (>= 64 kt) wind to the farm.

This is an exposure screen, not a forecast and not a wind-field model.
It ignores storm asymmetry, terrain and gusts.
"""

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "hurdat2_caribbean.csv"
START_YEAR = 1971  # satellite era: aircraft + geostationary imagery
END_YEAR = 2025
STEP_HOURS = 0.25  # 15-minute steps so the eyewall is not skipped
DEFAULT_RMW_KM = 40.0
DECAY_X = 0.6
LAND_FACTOR = 0.85
SEARCH_RADIUS_KM = 500.0
NM_TO_KM = 1.852

TS_KT = 34
HU_KT = 64
MAJOR_KT = 96

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def category(wind_kt):
    if wind_kt is None or np.isnan(wind_kt):
        return "Unknown"
    if wind_kt >= 137:
        return "Cat 5"
    if wind_kt >= 113:
        return "Cat 4"
    if wind_kt >= 96:
        return "Cat 3"
    if wind_kt >= 83:
        return "Cat 2"
    if wind_kt >= 64:
        return "Cat 1"
    if wind_kt >= 34:
        return "Tropical storm"
    return "Below storm force"


@lru_cache(maxsize=1)
def load_tracks():
    df = pd.read_csv(DATA_FILE, parse_dates=["time"])
    df["rmw_km"] = df["rmw_nm"] * NM_TO_KM
    return df


@lru_cache(maxsize=1)
def hourly_tracks():
    """Interpolate every storm to 1-hour steps (vectorised per storm)."""
    df = load_tracks().dropna(subset=["wind_kt"])
    pieces = []
    for storm_id, g in df.groupby("storm_id", sort=False):
        g = g.drop_duplicates("time").sort_values("time")
        if len(g) < 2:
            continue
        t = g["time"].to_numpy().astype("datetime64[s]").astype("int64") / 3600.0  # hours since epoch
        grid = np.arange(t[0], t[-1] + 1e-9, STEP_HOURS)
        rmw = g["rmw_km"].fillna(DEFAULT_RMW_KM).to_numpy()
        pieces.append(
            pd.DataFrame(
                {
                    "storm_id": storm_id,
                    "name": g["name"].iloc[0],
                    "year": int(g["year"].iloc[0]),
                    "hour": grid,
                    "lat": np.interp(grid, t, g["lat"].to_numpy()),
                    "lon": np.interp(grid, t, g["lon"].to_numpy()),
                    "wind_kt": np.interp(grid, t, g["wind_kt"].to_numpy()),
                    "rmw_km": np.interp(grid, t, rmw),
                }
            )
        )
    out = pd.concat(pieces, ignore_index=True)
    out["time"] = pd.to_datetime(np.round(out["hour"] * 3600).astype("int64"), unit="s")
    return out


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def wind_at_distance(vmax_kt, dist_km, rmw_km):
    """Modified Rankine vortex estimate of sustained wind at the farm (kt)."""
    rmw_km = np.maximum(rmw_km, 5.0)
    inner = vmax_kt * (dist_km / rmw_km)
    outer = vmax_kt * (rmw_km / np.maximum(dist_km, 1e-6)) ** DECAY_X
    return np.where(dist_km <= rmw_km, inner, outer) * LAND_FACTOR


IMPACT_COLUMNS = [
    "storm_id", "name", "year", "time", "month", "site_wind_kt", "closest_km",
    "storm_wind_kt", "site_category", "storm_category",
]


def _empty_impacts():
    return pd.DataFrame(columns=IMPACT_COLUMNS)


def storm_impacts(lat, lon, start_year=1950):
    """One row per storm that came within SEARCH_RADIUS_KM of the farm."""
    tracks = hourly_tracks()
    tracks = tracks[tracks["year"] >= start_year]
    # cheap bounding-box pre-filter (~5 degrees)
    box = tracks[(tracks["lat"].between(lat - 5, lat + 5)) & (tracks["lon"].between(lon - 6, lon + 6))]
    if box.empty:
        return _empty_impacts()
    dist = haversine_km(lat, lon, box["lat"].to_numpy(), box["lon"].to_numpy())
    site_wind = wind_at_distance(box["wind_kt"].to_numpy(), dist, box["rmw_km"].to_numpy())
    box = box.assign(dist_km=dist, site_wind_kt=site_wind)
    box = box[box["dist_km"] <= SEARCH_RADIUS_KM]
    if box.empty:
        return _empty_impacts()
    idx = box.groupby("storm_id")["site_wind_kt"].idxmax()
    peak = box.loc[idx].copy()
    closest = box.groupby("storm_id")["dist_km"].min()
    peak["closest_km"] = peak["storm_id"].map(closest)
    peak = peak.rename(columns={"wind_kt": "storm_wind_kt"})
    peak["site_category"] = peak["site_wind_kt"].apply(category)
    peak["storm_category"] = peak["storm_wind_kt"].apply(category)
    peak["month"] = peak["time"].dt.month
    peak = peak.sort_values("site_wind_kt", ascending=False)
    return peak[IMPACT_COLUMNS].reset_index(drop=True)


def monthly_exposure(impacts, start_year=START_YEAR, end_year=END_YEAR):
    """Share of years with at least one storm-force / hurricane-force event, per month."""
    years = end_year - start_year + 1
    period = impacts[(impacts["year"] >= start_year) & (impacts["year"] <= end_year)]
    rows = []
    for m in range(1, 13):
        sub = period[period["month"] == m]
        ts_years = sub[sub["site_wind_kt"] >= TS_KT]["year"].nunique()
        hu_years = sub[sub["site_wind_kt"] >= HU_KT]["year"].nunique()
        major_years = sub[sub["site_wind_kt"] >= MAJOR_KT]["year"].nunique()
        near = sub[sub["closest_km"] <= 300]["year"].nunique()
        rows.append(
            {
                "month": m,
                "label": MONTHS[m - 1],
                "p_storm_force": ts_years / years,
                "p_hurricane_force": hu_years / years,
                "p_major": major_years / years,
                "p_within_300km": near / years,
                "events_storm_force": int((sub["site_wind_kt"] >= TS_KT).sum()),
            }
        )
    out = pd.DataFrame(rows)
    out.attrs["years"] = years
    out.attrs["period"] = f"{start_year}-{end_year}"
    return out


def exposure_summary(impacts, start_year=START_YEAR, end_year=END_YEAR):
    years = end_year - start_year + 1
    period = impacts[(impacts["year"] >= start_year) & (impacts["year"] <= end_year)]
    ts = period[period["site_wind_kt"] >= TS_KT]
    hu = period[period["site_wind_kt"] >= HU_KT]
    return {
        "years": years,
        "period": f"{start_year}-{end_year}",
        "storm_force_events": len(ts),
        "hurricane_force_events": len(hu),
        "return_period_storm_force": (years / len(ts)) if len(ts) else None,
        "return_period_hurricane_force": (years / len(hu)) if len(hu) else None,
        "annual_p_storm_force": ts["year"].nunique() / years,
        "annual_p_hurricane_force": hu["year"].nunique() / years,
        "peak_months": [MONTHS[m - 1] for m in ts["month"].value_counts().index[:3]],
        "decade_counts": (
            ts.assign(decade=(ts["year"] // 10) * 10).groupby("decade").size().to_dict()
        ),
    }


def storm_track(storm_id):
    df = load_tracks()
    return df[df["storm_id"] == storm_id].sort_values("time")
