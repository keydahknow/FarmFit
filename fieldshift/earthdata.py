"""NASA Earthdata access: GPM IMERG point rain (GES DISC data rods) and
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
DATARODS = "https://hydro1.gesdisc.eosdis.nasa.gov/daac-bin/access/timeseries.cgi"
# IMERG Final half-hourly V07 (mm/hr). Override if GES DISC renames it.
IMERG_VARIABLE = os.environ.get("IMERG_DATAROD_VARIABLE", "GPM:GPM_3IMERGHH.07:precipitation")


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
# GPM IMERG via Hydrology Data Rods
# ---------------------------------------------------------------------------

LINE = re.compile(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2})(?::?(\d{2}))?\S*\s+(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*$")


def imerg_daily(lat, lon, start, end, timeout=90):
    """Daily IMERG Final rain (mm/day) at a point. Returns (Series or None, info)."""
    creds = credentials()
    if not creds:
        return None, {"error": "No Earthdata credentials"}
    params = {
        "variable": IMERG_VARIABLE,
        "location": f"GEOM:POINT({lon:.4f}, {lat:.4f})",
        "startDate": f"{pd.Timestamp(start):%Y-%m-%dT00}",
        "endDate": f"{pd.Timestamp(end):%Y-%m-%dT23}",
        "type": "asc2",
    }
    try:
        with EarthdataSession(creds) as session:
            response = session.get(DATARODS, params=params, timeout=timeout)
            response.raise_for_status()
            text = response.text
    except Exception as error:  # noqa: BLE001
        return None, {"error": str(error)}

    rows = []
    for line in text.splitlines():
        m = LINE.match(line.strip())
        if m:
            day, hour, minute, value = m.groups()
            v = float(value)
            if v < 0:  # fill value
                continue
            rows.append((pd.Timestamp(f"{day} {hour}:{minute or '00'}"), v))
    if not rows:
        return None, {"error": "Data rods returned no values", "head": text[:300]}
    s = pd.Series(dict(rows)).sort_index()
    daily = (s * 0.5).resample("D").sum()  # half-hourly mm/hr -> mm per day
    return daily.rename("imerg_mm"), {"source": response.url, "n": len(s)}


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


def appeears_points(points, start, end, name="FarmFit refresh", layers=None, max_wait_s=3600, poll_s=30, log=print):
    """Submit one AppEEARS point task for many farms and return a tidy DataFrame.

    points: list of dicts {id, lat, lon}. Returns columns id, date, product, layer, value.
    """
    session = requests.Session()
    token = _appeears_token(session)
    session.headers["Authorization"] = f"Bearer {token}"
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

    waited = 0
    while True:
        status = session.get(APPEEARS + f"task/{task_id}", timeout=60).json().get("status")
        if status == "done":
            break
        if status in ("error", "expired") or waited >= max_wait_s:
            raise RuntimeError(f"AppEEARS task {task_id} ended with status {status} after {waited}s")
        time.sleep(poll_s)
        waited += poll_s
    log(f"AppEEARS task done after ~{waited}s")

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
            prefix = layer["product"].replace(".", "_") + "_" + layer["layer"]
            col = next((c for c in df.columns if c == prefix), None)
            if col is None:
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
    out.loc[ndvi & (out["value"].abs() > 1.5), "value"] *= 0.0001  # unscaled MODIS integers
    return out.sort_values(["id", "product", "date"]).reset_index(drop=True)
