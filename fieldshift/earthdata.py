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


def imerg_giovanni(lat, lon, start, end, timeout=120, token=None):
    """IMERG through the Giovanni Time Series API (one request for a long window)."""
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
        except Exception as error:  # noqa: BLE001
            tried.append(f"{data_id}: {str(error)[:100]}")
            continue
        if r.status_code != 200:
            tried.append(f"{data_id}: HTTP {r.status_code} {r.text[:150]!r}")
            continue
        headers, s = parse_timeseries(r.text)
        if s is None:
            tried.append(f"{data_id}: no rows {r.text[:150]!r}")
            continue
        if "hr" in headers.get("unit", "").lower() or "HH" in data_id:
            s = s * 0.5
        return s.resample("D").sum().rename("imerg_mm"), {"source": f"Giovanni {data_id}"}
    return None, {"error": "Giovanni: " + "; ".join(tried)}


# Daily IMERG files on GES DISC, read one grid cell at a time through OPeNDAP.
# Final (gauge-adjusted) lags ~3.5 months; Late is ready ~14 hours after the day.
OPENDAP = "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3"
IMERG_RUNS = {
    "final": ("GPM_3IMERGDF.07", "3B-DAY.MS.MRG.3IMERG.{d:%Y%m%d}-S000000-E235959.V07B.nc4"),
    "late": ("GPM_3IMERGDL.07", "3B-DAY-L.MS.MRG.3IMERG.{d:%Y%m%d}-S000000-E235959.V07B.nc4"),
}
ASCII_VALUE = re.compile(r"\[.*?\]\s*,\s*(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*$")


def imerg_cell(lat, lon):
    """Index of the 0.1 degree IMERG cell (lon -179.95..179.95, lat -89.95..89.95)."""
    return int(round((lon + 179.95) / 0.1)), int(round((lat + 89.95) / 0.1))


def parse_opendap_value(text):
    for line in text.splitlines():
        m = ASCII_VALUE.search(line.strip())
        if m:
            return float(m.group(1))
    return None


def imerg_day(session, lat, lon, day, run):
    collection, name = IMERG_RUNS[run]
    i, j = imerg_cell(lat, lon)
    url = (f"{OPENDAP}/{collection}/{day:%Y}/{day:%m}/{name.format(d=day)}.ascii"
           f"?precipitation[0:0][{i}:{i}][{j}:{j}]")
    r = session.get(url, timeout=60)
    if r.status_code == 404:
        return None, "missing"
    r.raise_for_status()
    v = parse_opendap_value(r.text)
    if v is None:
        raise ValueError(f"unparsed OPeNDAP reply {r.text[:150]!r}")
    return (v if v >= 0 else None), run


def imerg_daily(lat, lon, start, end, token=None, workers=8):
    """Daily IMERG rain (mm/day) at a point: Final where it exists, else Late.
    Returns (Series or None, info)."""
    from concurrent.futures import ThreadPoolExecutor

    start, end = max(pd.Timestamp(start), IMERG_START), pd.Timestamp(end)
    if start > end:
        return None, {"error": "before IMERG starts (June 2000)"}
    creds = credentials()
    if not creds:
        return None, {"error": "No Earthdata credentials"}
    days = list(pd.date_range(start, end, freq="D"))
    final_cutoff = pd.Timestamp.today().normalize() - pd.DateOffset(months=5)

    errors, values = [], {}
    with EarthdataSession(creds) as session:
        adapter = requests.adapters.HTTPAdapter(pool_connections=workers, pool_maxsize=workers)
        session.mount("https://", adapter)

        def one(day):
            runs = ["final", "late"] if day <= final_cutoff else ["late", "final"]
            for run in runs:
                try:
                    v, tag = imerg_day(session, lat, lon, day, run)
                except Exception as error:  # noqa: BLE001
                    errors.append(f"{day:%Y-%m-%d} {run}: {str(error)[:160]}")
                    continue
                if tag != "missing":
                    return day, v, run
            return day, None, None

        # One request first, so a login problem fails fast instead of 700 times.
        first = one(days[0])
        if first[2] is None and errors:
            return None, {"error": "OPeNDAP: " + errors[0]}
        results = [first]
        with ThreadPoolExecutor(workers) as pool:
            results += list(pool.map(one, days[1:]))
    runs = {}
    for day, v, run in results:
        if run:
            runs[run] = runs.get(run, 0) + 1
            if v is not None:
                values[day] = v
    if not values:
        return None, {"error": "OPeNDAP: no values" + (f" ({errors[0]})" if errors else "")}
    s = pd.Series(values).sort_index().rename("imerg_mm")
    return s, {"source": "GES DISC OPeNDAP", "runs": runs, "errors": errors[:3]}


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


def _find_layer(session, product, *needles, suffix=None):
    """First layer whose name contains every needle; prefer one ending in `suffix`."""
    r = session.get(APPEEARS + f"product/{product}", timeout=60)
    r.raise_for_status()
    hits = [layer for layer in r.json() if all(n.lower() in layer.lower() for n in needles)]
    if suffix:
        exact = [h for h in hits if h.lower().endswith(suffix.lower())]
        hits = exact or hits
    if not hits:
        raise RuntimeError(f"No layer matching {needles} in {product}")
    return hits[0]


# AppEEARS request groups. Each is its own task so a slow product never holds
# back the others; long records are refreshed weekly, root-zone moisture often.
#   group: (days of history, [(product short name, needles, preferred suffix)])
APPEEARS_GROUPS = {
    "core": (3 * 365, [("SPL3SMP_E", ("AM_soil_moisture",), "AM_soil_moisture"),  # SMAP surface (~5 cm), 9 km
                       ("MOD13Q1", ("NDVI",), "NDVI")]),                          # MODIS greenness, 250 m
    "et": (3 * 365, [("MOD16A2", ("ET_500m",), "ET_500m"),                        # MODIS actual ET, 8-day, 500 m
                     ("MOD16A2", ("PET_500m",), "PET_500m")]),                    # MODIS potential ET
    "rootzone": (180, [("SPL4SMGP", ("sm_rootzone",), "sm_rootzone")]),           # SMAP L4 root zone (0-100 cm), 9 km
}


def layers_for(session, group):
    _, wanted = APPEEARS_GROUPS[group]
    layers = []
    for short, needles, suffix in wanted:
        product = _latest_product(session, short)
        layers.append({"product": product, "layer": _find_layer(session, product, *needles, suffix=suffix)})
    return layers


def default_layers(session):
    return layers_for(session, "core")


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
    return clean_points(out)


def clean_points(out):
    """Drop fill values, apply scale factors if AppEEARS gave raw integers,
    and average sub-daily products (SMAP L4 is 3-hourly) to one value a day."""
    out = out.copy()
    out["date"] = pd.to_datetime(out["date"], format="mixed").dt.normalize()
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out[out["value"] > -9000]
    ndvi = out["layer"].str.contains("NDVI")
    out.loc[ndvi & (out["value"].abs() > 1.5), "value"] *= 0.0001
    et = out["layer"].str.contains("ET_500m")
    out = out[~(et & (out["value"] >= 3276))]  # MOD16 fill: 32761-32767 raw, 3276.1+ scaled (urban, water, bare)
    for layer in out.loc[et, "layer"].unique():
        rows = out["layer"] == layer
        if out.loc[rows, "value"].median() > 100:  # raw 0.1 kg/m2 units
            out.loc[rows, "value"] *= 0.1
    out = out.groupby(["id", "date", "product", "layer"], as_index=False)["value"].mean()
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
