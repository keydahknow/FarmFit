"""NASA Earthdata access: GPM IMERG point rain (Giovanni Time Series API) and
SMAP soil moisture / MODIS NDVI point time series (LP DAAC AppEEARS).

Both need a free NASA Earthdata Login (https://urs.earthdata.nasa.gov).
Credentials are read from environment variables or Streamlit secrets:

    EARTHDATA_USERNAME, EARTHDATA_PASSWORD

Nothing here runs without them; the app falls back to NASA POWER.
"""

import io
import os
import re
import time
import zipfile

import pandas as pd
import requests

URS_HOST = "urs.earthdata.nasa.gov"
APPEEARS = "https://appeears.earthdatacloud.nasa.gov/api/"
# GES DISC retired Hydrology Data Rods (Oct 2025); its replacement is the
# "Giovanni in the Cloud" Time Series API, which takes an Earthdata bearer token.
GIOVANNI_TS = "https://api.giovanni.earthdata.nasa.gov/timeseries"
EDL_TOKEN = "https://urs.earthdata.nasa.gov/api/users/find_or_create_token"
# Giovanni data ids: IMERG Final V07 daily (mm/day), then half-hourly (mm/hr).
IMERG_DATA_IDS = [v for v in os.environ.get("IMERG_GIOVANNI_DATA", "").split(",") if v] or [
    "GPM_3IMERGDF_07_precipitation",
    "GPM_3IMERGHH_07_precipitation",
]
IMERG_START = pd.Timestamp("2000-06-01")  # first IMERG day


def credentials():
    user = os.environ.get("EARTHDATA_USERNAME")
    pwd = os.environ.get("EARTHDATA_PASSWORD")
    if not (user and pwd):
        try:
            import streamlit as st
            user = user or st.secrets.get("EARTHDATA_USERNAME")
            pwd = pwd or st.secrets.get("EARTHDATA_PASSWORD")
        except Exception:  # noqa: BLE001 - no Streamlit or no secrets file
            pass
    return (user, pwd) if user and pwd else None


class EarthdataSession(requests.Session):
    """Keeps the Earthdata credentials only for the login host across redirects."""

    def __init__(self, auth):
        super().__init__()
        self.auth = auth

    def rebuild_auth(self, prepared_request, response):
        headers = prepared_request.headers
        if "Authorization" in headers:
            original = requests.utils.urlparse(response.request.url).hostname
            target = requests.utils.urlparse(prepared_request.url).hostname
            if original != target and target != URS_HOST and original != URS_HOST:
                del headers["Authorization"]


# ---------------------------------------------------------------------------
# GPM IMERG via the Giovanni Time Series API
# ---------------------------------------------------------------------------

ROW = re.compile(r"^(\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?)Z?\s*,\s*(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*$")


def edl_token(timeout=60):
    """An Earthdata Login bearer token (valid for weeks) from username + password."""
    creds = credentials()
    if not creds:
        raise RuntimeError("No Earthdata credentials")
    r = requests.post(EDL_TOKEN, auth=creds, timeout=timeout)
    r.raise_for_status()
    return r.json()["access_token"]


def parse_timeseries(text):
    """Giovanni CSV -> (header dict, Series). Header lines are 'key,value'."""
    headers, rows = {}, []
    for line in text.splitlines():
        line = line.strip()
        m = ROW.match(line)
        if m:
            v = float(m.group(2))
            if 0 <= v < 1e4:  # drop fill values
                rows.append((pd.Timestamp(m.group(1)), v))
        elif line.count(",") == 1 and not rows:
            key, value = line.split(",")
            headers[key.strip()] = value.strip()
    series = pd.Series(dict(rows), dtype=float).sort_index() if rows else None
    return headers, series


def imerg_daily(lat, lon, start, end, timeout=120, token=None):
    """Daily IMERG Final rain (mm/day) at a point. Returns (Series or None, info)."""
    start, end = max(pd.Timestamp(start), IMERG_START), pd.Timestamp(end)
    if start > end:
        return None, {"error": "before IMERG starts (June 2000)"}
    try:
        token = token or edl_token()
    except Exception as error:  # noqa: BLE001
        return None, {"error": f"token: {error}"}
    tried = []
    for data_id in IMERG_DATA_IDS:
        params = {"data": data_id, "location": f"[{lat:.4f},{lon:.4f}]",
                  "time": f"{start:%Y-%m-%dT00:00:00}/{end:%Y-%m-%dT23:59:59}"}
        try:
            r = requests.get(GIOVANNI_TS, params=params, timeout=timeout,
                             headers={"Authorization": f"Bearer {token}"})
            text = r.text
            r.raise_for_status()
        except Exception as error:  # noqa: BLE001
            tried.append(f"{data_id}: {str(error)[:120]}")
            continue
        headers, s = parse_timeseries(text)
        if s is None:
            tried.append(f"{data_id}: no rows ({text[:120]!r})")
            continue
        unit = headers.get("unit", "").lower()
        if "hr" in unit or "HH" in data_id:
            s = s * 0.5  # half-hourly mm/hr -> mm per half hour
        daily = s.resample("D").sum()
        return daily.rename("imerg_mm"), {"source": data_id, "unit": unit, "n": len(s)}
    return None, {"error": "; ".join(tried)}


# ---------------------------------------------------------------------------
# AppEEARS point samples (SMAP, MODIS)
# ---------------------------------------------------------------------------

def _appeears_token(session):
    creds = credentials()
    if not creds:
        raise RuntimeError("No Earthdata credentials")
    r = session.post(APPEEARS + "login", auth=creds, timeout=60)
    r.raise_for_status()
    return r.json()["token"]


def _latest_product(session, short_name):
    r = session.get(APPEEARS + "product", timeout=60)
    r.raise_for_status()
    versions = [p["ProductAndVersion"] for p in r.json() if p["ProductAndVersion"].split(".")[0] == short_name]
    if not versions:
        raise RuntimeError(f"{short_name} not offered by AppEEARS")
    return sorted(versions)[-1]


def _find_layer(session, product, *needles):
    r = session.get(APPEEARS + f"product/{product}", timeout=60)
    r.raise_for_status()
    for layer in r.json():
        if all(n.lower() in layer.lower() for n in needles):
            return layer
    raise RuntimeError(f"No layer matching {needles} in {product}")


def default_layers(session):
    smap = _latest_product(session, "SPL3SMP_E")
    modis = _latest_product(session, "MOD13Q1")
    return [
        {"product": smap, "layer": _find_layer(session, smap, "AM_soil_moisture")},
        {"product": modis, "layer": _find_layer(session, modis, "NDVI")},
    ]


def _session():
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {_appeears_token(session)}"
    return session


def submit_points(points, start, end, name="FarmFit refresh", layers=None, log=print):
    """Submit an AppEEARS point task; returns (task_id, layers)."""
    session = _session()
    layers = layers or default_layers(session)
    task = {
        "task_type": "point",
        "task_name": name,
        "params": {
            "dates": [{"startDate": f"{pd.Timestamp(start):%m-%d-%Y}", "endDate": f"{pd.Timestamp(end):%m-%d-%Y}"}],
            "layers": layers,
            "coordinates": [{"id": p["id"], "latitude": p["lat"], "longitude": p["lon"]} for p in points],
        },
    }
    r = session.post(APPEEARS + "task", json=task, timeout=60)
    r.raise_for_status()
    task_id = r.json()["task_id"]
    log(f"AppEEARS task {task_id} submitted ({', '.join(l['product'] for l in layers)})")
    return task_id, layers


def task_status(task_id):
    session = _session()
    return session.get(APPEEARS + f"task/{task_id}", timeout=60).json().get("status")


def download_points(task_id, layers):
    """Download a finished task's CSVs and return a tidy DataFrame (id, date, product, layer, value)."""
    session = _session()
    bundle = session.get(APPEEARS + f"bundle/{task_id}", timeout=60).json()
    frames = []
    for f in bundle.get("files", []):
        if not f["file_name"].endswith((".csv", ".zip")):
            continue
        content = session.get(APPEEARS + f"bundle/{task_id}/{f['file_id']}", timeout=300, allow_redirects=True).content
        if f["file_name"].endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                content = z.read([n for n in z.namelist() if n.endswith(".csv")][0])
        df = pd.read_csv(io.BytesIO(content))
        if "ID" not in df.columns or "Date" not in df.columns:
            continue
        for layer in layers:
            col = layer["product"].replace(".", "_") + "_" + layer["layer"]
            if col not in df.columns:
                continue
            part = df[["ID", "Date", col]].rename(columns={"ID": "id", "Date": "date", col: "value"})
            part["product"], part["layer"] = layer["product"], layer["layer"]
            frames.append(part)
    if not frames:
        raise RuntimeError("AppEEARS bundle had no usable CSV columns")
    out = pd.concat(frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"])
    out = out[out["value"] > -9000]
    ndvi = out["layer"].str.contains("NDVI")
    out.loc[ndvi & (out["value"].abs() > 1.5), "value"] *= 0.0001
    return out.sort_values(["id", "product", "date"]).reset_index(drop=True)


def appeears_points(points, start, end, name="FarmFit refresh", layers=None, max_wait_s=600, poll_s=30, log=print):
    """Submit and wait (up to max_wait_s). Prefer submit_points + download_points across runs."""
    task_id, layers = submit_points(points, start, end, name, layers, log)
    waited = 0
    while waited < max_wait_s:
        status = task_status(task_id)
        if status == "done":
            return download_points(task_id, layers)
        if status in ("error", "expired"):
            raise RuntimeError(f"AppEEARS task {task_id} ended with status {status}")
        time.sleep(poll_s)
        waited += poll_s
    raise TimeoutError(f"AppEEARS task {task_id} still running after {waited}s")
