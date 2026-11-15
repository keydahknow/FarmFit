"""Pre-fetch real data for the demo farms so the deployed app opens instantly.

Run once from the repository root on any computer with internet:
    python scripts/cache_demo_sites.py

It writes JSON files to data/cache/ (NASA POWER daily 30-year record,
the NASA POWER window around each demo storm, SoilGrids soil and SRTM
terrain). Commit those files so the demo works even if an API is slow
during judging.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fieldshift import power, soil_terrain  # noqa: E402

SITES = {
    "St Elizabeth, Jamaica": (18.05, -77.72, date(2025, 10, 28)),
    "Caroni plains, Trinidad": (10.60, -61.38, date(1993, 8, 7)),
}


def main():
    for name, (lat, lon, storm_day) in SITES.items():
        print(f"\n== {name} ({lat}, {lon})")
        df, meta = power.fetch_daily(lat, lon)
        print("  NASA POWER daily:", meta.get("origin"), meta.get("file"), meta.get("error", ""))
        if df is not None:
            print(f"    {df.index.min():%Y-%m-%d} to {df.index.max():%Y-%m-%d}, columns: {', '.join(df.columns)}")
        win, wmeta = power.fetch_window(lat, lon, end_date=storm_day + timedelta(days=3), days=17)
        print("  NASA POWER storm window:", wmeta.get("origin"), wmeta.get("error", ""))
        soil = soil_terrain.get_soil(lat, lon)
        print("  SoilGrids:", {k: soil.get(k) for k in ("origin", "ph", "texture", "organic_matter_pct", "error")} if soil else None)
        terrain = soil_terrain.get_terrain(lat, lon)
        print("  SRTM:", {k: terrain.get(k) for k in ("origin", "elevation_m", "slope_pct", "source", "error")} if terrain else None)
    print("\nDone. Commit data/cache/*.json")


if __name__ == "__main__":
    main()
