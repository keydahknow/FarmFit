"""Build the compact storm-track file bundled with FarmFit.

Source: NOAA National Hurricane Center, Atlantic best track (HURDAT2),
release of 23 Sep 2026 covering 1851-2025:
https://www.nhc.noaa.gov/data/hurdat/hurdat2-1851-2025-092326.txt

Usage:
    python scripts/build_hurdat2.py path/to/hurdat2.txt

Keeps fixes from 1950 onward inside a Caribbean / Gulf / western Atlantic
box and writes data/hurdat2_caribbean.csv (one row per 6-hourly fix).
"""

import csv
import sys
from pathlib import Path

BOX = {"lat_min": 0.0, "lat_max": 32.0, "lon_min": -100.0, "lon_max": -45.0}
START_YEAR = 1950


def parse_coord(text):
    value = float(text[:-1])
    return -value if text[-1] in "SW" else value


def parse(path):
    rows = []
    storm_id = name = None
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            parts = [p.strip() for p in line.strip().split(",")]
            if not parts or not parts[0]:
                continue
            if parts[0].startswith("AL") and len(parts) <= 4:
                storm_id, name = parts[0], parts[1]
                continue
            date, time, record, status = parts[0], parts[1], parts[2], parts[3]
            year = int(date[:4])
            if year < START_YEAR:
                continue
            lat, lon = parse_coord(parts[4]), parse_coord(parts[5])
            if not (BOX["lat_min"] <= lat <= BOX["lat_max"]):
                continue
            if not (BOX["lon_min"] <= lon <= BOX["lon_max"]):
                continue
            wind = int(parts[6])
            pressure = int(parts[7])
            rmw = int(parts[20]) if len(parts) > 20 and parts[20] not in ("", "-999") else None
            rows.append(
                {
                    "storm_id": storm_id,
                    "name": name,
                    "year": year,
                    "time": f"{date[:4]}-{date[4:6]}-{date[6:8]}T{time[:2]}:{time[2:]}",
                    "record": record,
                    "status": status,
                    "lat": lat,
                    "lon": lon,
                    "wind_kt": wind if wind > 0 else None,
                    "pressure_mb": pressure if pressure > 0 else None,
                    "rmw_nm": rmw,
                }
            )
    return rows


def main():
    source = Path(sys.argv[1] if len(sys.argv) > 1 else "hurdat2.txt")
    out = Path(__file__).resolve().parents[1] / "data" / "hurdat2_caribbean.csv"
    rows = parse(source)
    with open(out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    storms = len({r["storm_id"] for r in rows})
    print(f"Wrote {len(rows)} fixes from {storms} storms to {out}")


if __name__ == "__main__":
    main()
