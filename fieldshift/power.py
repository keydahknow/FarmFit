"""NASA POWER (MERRA-2 / CERES based) daily climate for a farm.

One API call returns 30 years of daily data. From it FarmFit derives:
- monthly climate normals (rain, temperature, humidity, wind, soil wetness)
- heavy-rain statistics per month (share of years with a >= 50 mm day)
- a "then vs now" comparison between the first and second 15 years
- reference evapotranspiration (ET0) with the FAO-56 Hargreaves equation

Every fetch is cached to data/cache so the demo sites work offline.
"""

import json
import math
import os
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

API = "https://power.larc.nasa.gov/api/temporal/daily/point"
CACHE_DIR = Path(os.environ.get("FIELDSHIFT_CACHE_DIR", Path(__file__).resolve().parents[1] / "data" / "cache"))

FULL_PARAMS = [
    "T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M",
    "WS2M", "WS10M_MAX", "GWETTOP", "GWETROOT", "ALLSKY_SFC_SW_DWN",
]
CORE_PARAMS = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "WS2M"]

PARAM_INFO = {
    "T2M": ("Mean air temperature at 2 m", "°C", "MERRA-2"),
    "T2M_MAX": ("Daily maximum temperature", "°C", "MERRA-2"),
    "T2M_MIN": ("Daily minimum temperature", "°C", "MERRA-2"),
    "PRECTOTCORR": ("Precipitation (bias corrected)", "mm/day", "MERRA-2 corrected"),
    "RH2M": ("Relative humidity at 2 m", "%", "MERRA-2"),
    "WS2M": ("Wind speed at 2 m", "m/s", "MERRA-2"),
    "WS10M_MAX": ("Maximum wind speed at 10 m", "m/s", "MERRA-2"),
    "GWETTOP": ("Surface soil wetness (0-5 cm)", "0-1", "MERRA-2"),
    "GWETROOT": ("Root-zone soil wetness", "0-1", "MERRA-2"),
    "ALLSKY_SFC_SW_DWN": ("Solar radiation at surface", "MJ/m²/day", "CERES"),
}

HEAVY_RAIN_MM = 50.0
HOT_DAY_C = 32.0
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def default_period():
    end = date.today().year - 1
    return end - 29, end


def _cache_path(kind, lat, lon, start, end):
    return CACHE_DIR / f"power_{kind}_{lat:.2f}_{lon:.2f}_{start}_{end}.json"


def _request(lat, lon, start, end, params, timeout=60):
    response = requests.get(
        API,
        params={
            "parameters": ",".join(params),
            "community": "AG",
            "longitude": round(lon, 4),
            "latitude": round(lat, 4),
            "start": start,
            "end": end,
            "format": "JSON",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    return {
        "parameter": payload["properties"]["parameter"],
        "fill_value": payload.get("header", {}).get("fill_value", -999),
        "source": response.url,
    }


def _to_frame(raw):
    fill = raw.get("fill_value", -999)
    df = pd.DataFrame(raw["parameter"])
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df.mask(df <= fill + 1e-6)
    df.index.name = "date"
    return df.sort_index()


def nearest_cache(kind, lat, lon, tolerance=0.3):
    """Find a cached file for a nearby point (POWER cells are ~0.5 deg)."""
    if not CACHE_DIR.exists():
        return None
    best, best_d = None, tolerance
    for path in CACHE_DIR.glob(f"power_{kind}_*.json"):
        try:
            _, _, plat, plon, *_ = path.stem.split("_")
            d = math.hypot(float(plat) - lat, float(plon) - lon)
        except ValueError:
            continue
        if d <= best_d:
            best, best_d = path, d
    return best


def fetch_daily(lat, lon, start_year=None, end_year=None, allow_network=True):
    """Return (DataFrame, meta). meta['origin'] is 'live', 'cache' or None."""
    if start_year is None or end_year is None:
        start_year, end_year = default_period()
    path = _cache_path("daily", lat, lon, start_year, end_year)
    if path.exists():
        raw = json.loads(path.read_text())
        return _to_frame(raw), {"origin": "cache", "source": raw.get("source"), "file": path.name}

    if allow_network:
        for params in (FULL_PARAMS, CORE_PARAMS):
            try:
                raw = _request(lat, lon, f"{start_year}0101", f"{end_year}1231", params)
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(raw))
                return _to_frame(raw), {"origin": "live", "source": raw["source"], "file": path.name}
            except Exception as error:  # noqa: BLE001 - fall through to next option
                last_error = str(error)
        nearby = nearest_cache("daily", lat, lon)
        if nearby:
            raw = json.loads(nearby.read_text())
            return _to_frame(raw), {"origin": "cache-nearby", "source": raw.get("source"), "file": nearby.name, "error": last_error}
        return None, {"origin": None, "error": last_error}

    nearby = nearest_cache("daily", lat, lon)
    if nearby:
        raw = json.loads(nearby.read_text())
        return _to_frame(raw), {"origin": "cache-nearby", "source": raw.get("source"), "file": nearby.name}
    return None, {"origin": None, "error": "offline"}


def fetch_window(lat, lon, end_date=None, days=21, allow_network=True):
    """Daily rain / soil wetness for the days around a storm (POWER lags a few days)."""
    end = min(end_date or date.today(), date.today())
    start = end - timedelta(days=days)
    key = _cache_path("window", lat, lon, start.isoformat(), end.isoformat())
    if key.exists():
        return _to_frame(json.loads(key.read_text())), {"origin": "cache"}
    if allow_network:
        try:
            raw = _request(lat, lon, start.strftime("%Y%m%d"), end.strftime("%Y%m%d"),
                           ["PRECTOTCORR", "GWETTOP", "GWETROOT", "T2M_MAX"], timeout=30)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            key.write_text(json.dumps(raw))
            return _to_frame(raw), {"origin": "live", "source": raw["source"]}
        except Exception as error:  # noqa: BLE001
            return None, {"origin": None, "error": str(error)}
    return None, {"origin": None, "error": "offline"}


# ---------------------------------------------------------------------------
# Derived indicators
# ---------------------------------------------------------------------------

def extraterrestrial_radiation_mm(lat_deg, doy):
    """FAO-56 eq. 21, returned as equivalent evaporation (mm/day)."""
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi / 365 * doy)
    delta = 0.409 * np.sin(2 * np.pi / 365 * doy - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1, 1))
    ra_mj = (24 * 60 / np.pi) * 0.0820 * dr * (
        ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws)
    )
    return 0.408 * ra_mj


def add_et0(df, lat):
    """FAO-56 Hargreaves ET0 (eq. 52): 0.0023 Ra (Tmean + 17.8) sqrt(Tmax - Tmin)."""
    if not {"T2M", "T2M_MAX", "T2M_MIN"} <= set(df.columns):
        return df
    ra = extraterrestrial_radiation_mm(lat, df.index.dayofyear.to_numpy())
    tr = (df["T2M_MAX"] - df["T2M_MIN"]).clip(lower=0)
    df = df.copy()
    df["ET0"] = 0.0023 * ra * (df["T2M"] + 17.8) * np.sqrt(tr)
    return df


def monthly_climate(df):
    """Monthly normals. Rain/ET0 are monthly totals (mean over years)."""
    d = df.copy()
    d["year"], d["month"] = d.index.year, d.index.month
    years = d["year"].nunique()
    out = pd.DataFrame({"month": range(1, 13), "label": MONTHS})

    totals = d.groupby(["year", "month"])["PRECTOTCORR"].sum().groupby("month").mean()
    out["rain_mm"] = out["month"].map(totals)
    if "ET0" in d:
        et0 = d.groupby(["year", "month"])["ET0"].sum().groupby("month").mean()
        out["et0_mm"] = out["month"].map(et0)
    for col, name in [("T2M", "t_mean"), ("T2M_MAX", "t_max"), ("T2M_MIN", "t_min"),
                      ("RH2M", "rh"), ("WS2M", "wind2m"), ("WS10M_MAX", "wind10m_max"),
                      ("GWETTOP", "soil_wet_top"), ("GWETROOT", "soil_wet_root")]:
        if col in d:
            out[name] = out["month"].map(d.groupby("month")[col].mean())

    heavy = d[d["PRECTOTCORR"] >= HEAVY_RAIN_MM]
    out["p_heavy_rain"] = out["month"].map(heavy.groupby("month")["year"].nunique() / years).fillna(0.0)
    out["max_day_rain_mm"] = out["month"].map(d.groupby("month")["PRECTOTCORR"].max())
    p95 = d["PRECTOTCORR"].quantile(0.95)
    out["wet_days_p95"] = out["month"].map(
        d[d["PRECTOTCORR"] >= p95].groupby("month").size() / years
    ).fillna(0.0)
    if "T2M_MAX" in d:
        hot = d[d["T2M_MAX"] >= HOT_DAY_C]
        out["hot_days"] = out["month"].map(hot.groupby("month").size() / years).fillna(0.0)
    out.attrs["years"] = years
    out.attrs["period"] = f"{d['year'].min()}-{d['year'].max()}"
    return out


def _longest_dry_spell(series, threshold=1.0):
    dry = (series < threshold).astype(int).to_numpy()
    best = run = 0
    for v in dry:
        run = run + 1 if v else 0
        best = max(best, run)
    return best


def _ols_per_decade(years, values):
    years, values = np.asarray(years, float), np.asarray(values, float)
    mask = ~np.isnan(values)
    years, values = years[mask], values[mask]
    if len(years) < 5:
        return None, None
    x = years - years.mean()
    slope = (x * (values - values.mean())).sum() / (x ** 2).sum()
    resid = values - (values.mean() + slope * x)
    se = math.sqrt((resid ** 2).sum() / (len(x) - 2) / (x ** 2).sum())
    t = slope / se if se > 0 else 0.0
    return slope * 10, t


def climate_shift(df):
    """Compare first vs second half of the record (Field Shift)."""
    d = df.copy()
    d["year"] = d.index.year
    years = sorted(d["year"].unique())
    mid = years[len(years) // 2]
    annual = d.groupby("year").agg(
        rain=("PRECTOTCORR", "sum"),
        t_mean=("T2M", "mean"),
        heavy_days=("PRECTOTCORR", lambda s: int((s >= HEAVY_RAIN_MM).sum())),
        max_day=("PRECTOTCORR", "max"),
    )
    if "T2M_MAX" in d:
        annual["hot_days"] = d.groupby("year")["T2M_MAX"].apply(lambda s: int((s >= HOT_DAY_C).sum()))
    annual["dry_spell"] = d.groupby("year")["PRECTOTCORR"].apply(_longest_dry_spell)

    then = annual[annual.index < mid]
    now = annual[annual.index >= mid]
    rows = []
    labels = {
        "rain": ("Annual rainfall", "mm"),
        "t_mean": ("Mean temperature", "°C"),
        "heavy_days": ("Days with ≥ 50 mm rain", "days/yr"),
        "hot_days": ("Days above 32 °C", "days/yr"),
        "dry_spell": ("Longest dry spell", "days"),
        "max_day": ("Wettest day of the year", "mm"),
    }
    for key, (label, unit) in labels.items():
        if key not in annual:
            continue
        slope, t = _ols_per_decade(annual.index, annual[key])
        rows.append(
            {
                "indicator": label,
                "unit": unit,
                "then": then[key].mean(),
                "now": now[key].mean(),
                "change": now[key].mean() - then[key].mean(),
                "trend_per_decade": slope,
                "t_stat": t,
                "signal": "clear" if t is not None and abs(t) >= 2 else "weak / within natural variation",
            }
        )
    shift = pd.DataFrame(rows)
    shift.attrs["then"] = f"{then.index.min()}-{then.index.max()}"
    shift.attrs["now"] = f"{now.index.min()}-{now.index.max()}"

    # Monthly rain then vs now (for the season-shift chart)
    d["month"] = d.index.month
    monthly = d.groupby(["year", "month"])["PRECTOTCORR"].sum().reset_index()
    monthly["period"] = np.where(monthly["year"] < mid, shift.attrs["then"], shift.attrs["now"])
    season = monthly.groupby(["period", "month"])["PRECTOTCORR"].mean().reset_index()
    season["label"] = season["month"].map(lambda m: MONTHS[m - 1])
    return shift, annual, season


def wet_season_onset(df, threshold_mm=60.0):
    """Typical month when the rains set in: first month after the driest month with mean rain >= threshold."""
    clim = monthly_climate(df)
    driest = int(clim.loc[clim["rain_mm"].idxmin(), "month"])
    for k in range(12):
        m = (driest - 1 + k) % 12 + 1
        if clim.loc[clim["month"] == m, "rain_mm"].iloc[0] >= threshold_mm and k > 0:
            return m
    return None
