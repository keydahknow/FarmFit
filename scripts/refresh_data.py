"""Scheduled data refresh for FarmFit · Hurricane to Harvest.

Runs on GitHub Actions (.github/workflows/refresh-data.yml) or by hand:
    python scripts/refresh_data.py            # everything available
    python scripts/refresh_data.py --quick    # skip the slow AppEEARS task

For every farm in data/farms.json it refreshes:
  - NASA POWER daily, 30 complete years                 (no key)
  - NASA POWER last 45 days (recent rain, soil wetness)  (no key)
  - ISRIC SoilGrids + NASA SRTM, only if missing         (no key)
  - GPM IMERG Final daily rain, last 2 years + storm dates  (Earthdata login)
  - SMAP soil moisture + MODIS NDVI via AppEEARS         (Earthdata login)
Plus, once for the whole basin:
  - NOAA IBTrACS current-season storm tracks             (no key)

It writes data/cache/manifest.json so the app can show when each
dataset was last refreshed. Each source fails independently.
"""

import argparse
import json
import sys
import time
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import requests  # noqa: E402

from fieldshift import earthdata, power, soil_terrain  # noqa: E402

CACHE = power.CACHE_DIR  # honours FIELDSHIFT_CACHE_DIR
FARMS = ROOT / "data" / "farms.json"
IBTRACS_URL = ("https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/"
               "v04r01/access/csv/ibtracs.last3years.list.v04r01.csv")
RECENT_TRACKS = ROOT / "data" / "ibtracs_recent.csv"
HURDAT = ROOT / "data" / "hurdat2_caribbean.csv"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def status_of(ok, total):
    return "ok" if ok == total else ("partial" if ok else "failed")


def record(manifest, name, status, **extra):
    manifest["datasets"][name] = {"updated": now(), "status": status, **extra}
    print(f"[{status:>7}] {name} {extra if extra else ''}")


def refresh_power(farms, manifest):
    ok = 0
    for f in farms:
        start, end = power.default_period()
        df, meta = power.fetch_daily(f["lat"], f["lon"], start, end, refresh=True)
        if df is not None and meta.get("origin") == "live":  # never count or clean up on a fallback
            ok += 1
            # remove caches of older 30-year windows for this point
            for old in CACHE.glob(f"power_daily_{f['lat']:.2f}_{f['lon']:.2f}_*.json"):
                if old.name != meta["file"]:
                    old.unlink()
        recent, _ = power.fetch_window(f["lat"], f["lon"], end_date=date.today(), days=45)
        for d in f.get("storm_dates", []):
            day = date.fromisoformat(d)
            power.fetch_window(f["lat"], f["lon"], end_date=day + timedelta(days=3), days=17)
    record(manifest, "NASA POWER", status_of(ok, len(farms)),
           farms=ok, period=f"{power.default_period()[0]}-{power.default_period()[1]} + last 45 days")


def refresh_soil_terrain(farms, manifest):
    soil_ok = terr_ok = 0
    soil_errors = []
    for f in farms:
        s = soil_terrain.get_soil(f["lat"], f["lon"])
        t = soil_terrain.get_terrain(f["lat"], f["lon"])
        soil_ok += bool(s and s.get("origin") in ("live", "cache"))
        if s and s.get("error"):
            soil_errors.append(f"{f['id']}: {s['error'][:250]}")
        terr_ok += bool(t and t.get("origin") in ("live", "cache") and "Copernicus" not in t.get("source", ""))
    record(manifest, "ISRIC SoilGrids", status_of(soil_ok, len(farms)), farms=soil_ok, errors=soil_errors)
    record(manifest, "NASA SRTM", status_of(terr_ok, len(farms)), farms=terr_ok)


def refresh_imerg(farms, manifest):
    if not earthdata.credentials():
        record(manifest, "GPM IMERG", "skipped", reason="no Earthdata credentials")
        return
    try:
        token = earthdata.edl_token()
    except Exception:  # noqa: BLE001 - OPeNDAP uses the password login instead
        token = None
    ok = 0
    errors = []
    for f in farms:
        # Recent 120 days (Water watch) + each storm window; ~2 small requests a day.
        windows = [(date.today() - timedelta(days=120), date.today() - timedelta(days=1))]
        windows += [(date.fromisoformat(d) - timedelta(days=14), date.fromisoformat(d) + timedelta(days=3))
                    for d in f.get("storm_dates", [])]
        parts = []
        for a, b in windows:
            if pd.Timestamp(b) < earthdata.IMERG_START:
                continue  # e.g. Trinidad 1993: IMERG starts June 2000, POWER covers it
            s, info = earthdata.imerg_daily(f["lat"], f["lon"], a, b)
            if s is None:  # fall back to Giovanni, report both reasons
                s2, info2 = earthdata.imerg_giovanni(f["lat"], f["lon"], pd.Timestamp(a), pd.Timestamp(b), token=token)
                if s2 is not None:
                    s, info = s2, info2
                else:
                    info = {"error": f"{info.get('error')} || {info2.get('error')}"}
            else:
                print(f"  IMERG {f['id']} {a}..{b}: {len(s)} days {info.get('runs')}")
            if s is not None:
                parts.append(s)
            else:
                errors.append(f"{f['id']} {a}..{b}: {info.get('error')}")
        if parts:
            out = pd.concat(parts).groupby(level=0).max().sort_index()
            out.to_frame().to_csv(CACHE / f"imerg_{f['id']}.csv", index_label="date")
            ok += 1
    record(manifest, "GPM IMERG", status_of(ok, len(farms)), farms=ok,
           note="IMERG V07 daily: Final (gauge-adjusted) where available, else Late (~1 day behind)",
           errors=[e[:600] for e in errors[:4]])


def refresh_appeears(farms, manifest, max_wait_s):
    """SMAP + NDVI via AppEEARS without long waits.

    A task submitted in one run is collected in a later run (AppEEARS can queue
    requests for a long time). The pending task id lives in the manifest.
    """
    name = "SMAP + MODIS NDVI (AppEEARS)"
    if not earthdata.credentials():
        record(manifest, name, "skipped", reason="no Earthdata credentials")
        return
    pending = manifest.get("appeears_pending")
    try:
        if pending:
            status = earthdata.task_status(pending["task_id"])
            print(f"AppEEARS pending task {pending['task_id']}: {status}")
            if status == "done":
                df = earthdata.download_points(pending["task_id"], pending["layers"])
                df.to_csv(CACHE / "appeears_points.csv", index=False)
                manifest.pop("appeears_pending", None)
                record(manifest, name, "ok", rows=len(df), products=sorted(df["product"].unique().tolist()))
                return
            if status in ("error", "expired"):
                manifest.pop("appeears_pending", None)
            else:
                prev = manifest["datasets"].get(name, {})
                manifest["datasets"][name] = {**prev, "pending": pending["task_id"], "pending_status": status}
                print("Still processing; will collect on the next run.")
                return
        task_id, layers = earthdata.submit_points(
            [{"id": f["id"], "lat": f["lat"], "lon": f["lon"]} for f in farms],
            start=date.today() - timedelta(days=3 * 365), end=date.today())
        manifest["appeears_pending"] = {"task_id": task_id, "layers": layers, "submitted": now()}
        waited = 0
        while waited < max_wait_s:  # short wait: small requests often finish quickly
            time.sleep(30)
            waited += 30
            status = earthdata.task_status(task_id)
            if status == "done":
                df = earthdata.download_points(task_id, layers)
                df.to_csv(CACHE / "appeears_points.csv", index=False)
                manifest.pop("appeears_pending", None)
                record(manifest, name, "ok", rows=len(df), products=sorted(df["product"].unique().tolist()))
                return
        prev = manifest["datasets"].get(name, {})
        manifest["datasets"][name] = {**prev, "pending": task_id}
        print(f"AppEEARS task {task_id} submitted; it will be collected on the next run.")
    except Exception as error:  # noqa: BLE001
        traceback.print_exc()
        record(manifest, name, "failed", error=str(error)[:300])


def refresh_ibtracs(manifest):
    """Add this season's storms (provisional) that HURDAT2 does not have yet."""
    try:
        hurdat_last = int(pd.read_csv(HURDAT, usecols=["year"])["year"].max())
        r = requests.get(IBTRACS_URL, timeout=120)
        r.raise_for_status()
        # keep_default_na=False: IBTrACS writes the North Atlantic basin as "NA",
        # which pandas would otherwise read as a missing value.
        df = pd.read_csv(pd.io.common.StringIO(r.text), skiprows=[1], low_memory=False,
                         keep_default_na=False, na_values=["", " "],
                         usecols=lambda c: c in {"SID", "SEASON", "BASIN", "NAME", "ISO_TIME", "LAT", "LON",
                                                 "USA_WIND", "WMO_WIND", "USA_PRES", "USA_RMW", "NATURE"})
        counts = {"rows": len(df), "latest_season": int(pd.to_numeric(df["SEASON"], errors="coerce").max())}
        df = df[(df["BASIN"] == "NA") & (pd.to_numeric(df["SEASON"], errors="coerce") > hurdat_last)]
        counts["atlantic_new"] = len(df)
        for col in ("LAT", "LON", "USA_WIND", "WMO_WIND", "USA_PRES", "USA_RMW"):
            if col in df:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df[df["LAT"].between(0, 32) & df["LON"].between(-100, -45)]
        wind = df["USA_WIND"].fillna(df.get("WMO_WIND"))
        out = pd.DataFrame({
            "storm_id": df["SID"], "name": df["NAME"].str.upper(), "year": df["SEASON"].astype(int),
            "time": pd.to_datetime(df["ISO_TIME"]).dt.strftime("%Y-%m-%dT%H:%M"), "record": "",
            "status": df.get("NATURE", ""), "lat": df["LAT"], "lon": df["LON"], "wind_kt": wind,
            "pressure_mb": df.get("USA_PRES"), "rmw_nm": df.get("USA_RMW"),
        }).dropna(subset=["wind_kt"])
        out.to_csv(RECENT_TRACKS, index=False)
        record(manifest, "NOAA IBTrACS (current season)", "ok",
               storms=int(out["storm_id"].nunique()), seasons_after=hurdat_last,
               names=sorted(out["name"].dropna().unique().tolist())[:30], **counts)
    except Exception as error:  # noqa: BLE001
        record(manifest, "NOAA IBTrACS (current season)", "failed", error=str(error)[:300])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="skip the AppEEARS task")
    parser.add_argument("--appeears-wait", type=int, default=480, help="seconds to wait before leaving the AppEEARS task for the next run")
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    farms = json.loads(FARMS.read_text())["farms"]
    CACHE.mkdir(parents=True, exist_ok=True)
    manifest_path = CACHE / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"datasets": {}}
    manifest["farms"] = [f["id"] for f in farms]

    for step in (refresh_power, refresh_soil_terrain, refresh_imerg):
        try:
            step(farms, manifest)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
    if not args.quick:
        refresh_appeears(farms, manifest, args.appeears_wait)
    refresh_ibtracs(manifest)

    manifest["generated"] = now()
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str))
    print("\nManifest written:", manifest_path)


if __name__ == "__main__":
    main()
