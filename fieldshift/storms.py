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
RECENT_FILE = Path(__file__).resolve().parents[1] / "data" / "ibtracs_recent.csv"  # written by scripts/refresh_data.py
GLOBAL_FILE = Path(__file__).resolve().parents[1] / "data" / "ibtracs_global.csv.gz"  # every basin, 1971+ (refresh_data.py)
# HURDAT2 subset box: farms inside it use the reviewed Atlantic record; everywhere else uses IBTrACS.
ATLANTIC_BOX = (7.5, 32.0, -100.0, -45.0)
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
    """HURDAT2 (final, reviewed) plus any newer provisional IBTrACS storms."""
    df = pd.read_csv(DATA_FILE, parse_dates=["time"])
    df["provisional"] = False
    if RECENT_FILE.exists():
        recent = pd.read_csv(RECENT_FILE, parse_dates=["time"])
        recent = recent[recent["year"] > df["year"].max()]
        if len(recent):
            recent["provisional"] = True
            df = pd.concat([df, recent[df.columns.intersection(recent.columns)]], ignore_index=True)
            df["provisional"] = df["provisional"].fillna(False).astype(bool)
    df["rmw_km"] = df["rmw_nm"] * NM_TO_KM
    return df


def _interpolate(df):
    """Interpolate each storm in df (6-hourly fixes) to STEP_HOURS steps."""
    df = df.dropna(subset=["wind_kt"])
    pieces = []
    for storm_id, g in df.groupby("storm_id", sort=False):
        g = g.drop_duplicates("time").sort_values("time")
        if len(g) < 2:
            continue
        t = g["time"].to_numpy().astype("datetime64[s]").astype("int64") / 3600.0  # hours since epoch
        grid = np.arange(t[0], t[-1] + 1e-9, STEP_HOURS)
        lon = np.unwrap(np.radians(g["lon"].to_numpy()))  # storms crossing the date line
        rmw = g["rmw_km"].fillna(DEFAULT_RMW_KM).to_numpy()
        pieces.append(
            pd.DataFrame(
                {
                    "storm_id": storm_id,
                    "name": g["name"].iloc[0],
                    "year": int(g["year"].iloc[0]),
                    "provisional": bool(g["provisional"].iloc[0]),
                    "hour": grid,
                    "lat": np.interp(grid, t, g["lat"].to_numpy()),
                    "lon": (np.degrees(np.interp(grid, t, lon)) + 180) % 360 - 180,
                    "wind_kt": np.interp(grid, t, g["wind_kt"].to_numpy()),
                    "rmw_km": np.interp(grid, t, rmw),
                }
            )
        )
    if not pieces:
        return pd.DataFrame(columns=["storm_id", "name", "year", "provisional", "hour", "lat", "lon", "wind_kt", "rmw_km", "time"])
    out = pd.concat(pieces, ignore_index=True)
    out["time"] = pd.to_datetime(np.round(out["hour"] * 3600).astype("int64"), unit="s")
    return out


@lru_cache(maxsize=1)
def hourly_tracks():
    """Every Atlantic (HURDAT2) storm at STEP_HOURS steps."""
    return _interpolate(load_tracks())


@lru_cache(maxsize=1)
def load_global():
    """NOAA IBTrACS, every ocean basin since 1971 (6-hourly). Empty if the file hasn't been built yet."""
    if not GLOBAL_FILE.exists():
        return pd.DataFrame(columns=["storm_id", "name", "year", "time", "basin", "lat", "lon", "wind_kt", "rmw_nm", "rmw_km", "provisional"])
    df = pd.read_csv(GLOBAL_FILE, parse_dates=["time"], keep_default_na=False, na_values=["", " "])
    df["rmw_km"] = pd.to_numeric(df["rmw_nm"], errors="coerce") * NM_TO_KM
    df["provisional"] = False
    return df


def in_atlantic_box(lat, lon):
    lo_lat, hi_lat, lo_lon, hi_lon = ATLANTIC_BOX
    return lo_lat <= lat <= hi_lat and lo_lon <= lon <= hi_lon


def source_for(lat, lon):
    """'atlantic' (HURDAT2, reviewed) inside its box, otherwise 'global' (IBTrACS) when available."""
    if in_atlantic_box(lat, lon) or load_global().empty:
        return "atlantic"
    return "global"


def _fixes_near(df, lat, lon, radius_km):
    """Rows of every storm with at least one fix within radius_km of the farm."""
    if df.empty:
        return df
    pad_lat = radius_km / 111.0 + 1
    pad_lon = pad_lat / max(np.cos(np.radians(lat)), 0.2)
    box = df[df["lat"].between(lat - pad_lat, lat + pad_lat) & (((df["lon"] - lon + 180) % 360 - 180).abs() <= pad_lon)]
    if box.empty:
        return box
    d = haversine_km(lat, lon, box["lat"].to_numpy(), box["lon"].to_numpy())
    ids = box.loc[d <= radius_km, "storm_id"].unique()
    return df[df["storm_id"].isin(ids)]


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
    "storm_wind_kt", "site_category", "storm_category", "provisional",
]


def _empty_impacts():
    return pd.DataFrame(columns=IMPACT_COLUMNS)


def storm_impacts(lat, lon, start_year=1950):
    """One row per storm that came within SEARCH_RADIUS_KM of the farm."""
    if source_for(lat, lon) == "global":
        g = load_global()
        tracks = _interpolate(_fixes_near(g[g["year"] >= start_year], lat, lon, SEARCH_RADIUS_KM + 300))
    else:
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
    tr = df[df["storm_id"] == storm_id]
    if tr.empty:
        g = load_global()
        tr = g[g["storm_id"] == storm_id]
    return tr.sort_values("time")


def nearest_storms(lat, lon, n=5, max_km=3000, start_year=START_YEAR):
    """The storms that came closest to the farm, however far: context for farms outside the storm belts.
    One row per storm: name, year, closest_km, peak wind of the storm, basin."""
    frames = [load_tracks().assign(basin="NA")]
    g = load_global()
    if not g.empty:
        frames = [g] if not in_atlantic_box(lat, lon) else frames + [g[g["basin"] != "NA"]]
    df = pd.concat(frames, ignore_index=True)
    df = df[(df["year"] >= start_year) & df["wind_kt"].notna()]
    near = _fixes_near(df, lat, lon, max_km)
    if near.empty:
        return pd.DataFrame(columns=["storm_id", "name", "year", "closest_km", "storm_wind_kt", "storm_category", "basin"])
    d = haversine_km(lat, lon, near["lat"].to_numpy(), near["lon"].to_numpy())
    near = near.assign(dist_km=d)
    rows = near.groupby("storm_id").agg(name=("name", "first"), year=("year", "first"), closest_km=("dist_km", "min"),
                                         storm_wind_kt=("wind_kt", "max"), basin=("basin", "first")).reset_index()
    rows["storm_category"] = rows["storm_wind_kt"].apply(category)
    rows["name"] = rows["name"].fillna("UNNAMED").replace({"NOT_NAMED": "UNNAMED", "": "UNNAMED"})
    return rows.sort_values("closest_km").head(n).reset_index(drop=True)
