"""Create SYNTHETIC POWER-shaped files for offline tests only.

These are NOT NASA data. They exist so the engine and UI can be exercised
in environments without internet. The app labels them as synthetic.
Run: python tests/make_fixture.py  -> tests/fixtures/cache/
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "fixtures" / "cache"

SITES = {
    # lat, lon, monthly rain mm (Jan..Dec), mean T, diurnal range
    "jamaica": (18.05, -77.72, [30, 30, 35, 70, 150, 110, 70, 110, 160, 210, 100, 45], 26.5, 8.5),
    "trinidad": (10.60, -61.38, [60, 40, 35, 50, 110, 250, 260, 250, 210, 220, 230, 140], 26.8, 8.0),
}


def build(lat, lon, monthly, t_mean, dtr, start=1996, end=2025, seed=1):
    rng = np.random.default_rng(seed)
    days = pd.date_range(f"{start}-01-01", f"{end}-12-31", freq="D")
    m = days.month.to_numpy() - 1
    mean_daily = np.array(monthly)[m] / days.days_in_month.to_numpy()
    wet_prob = np.clip(np.array(monthly)[m] / 300, 0.1, 0.75)
    wet = rng.random(len(days)) < wet_prob
    amount = rng.gamma(0.7, mean_daily / wet_prob / 0.7)
    trend = 1 + 0.004 * (days.year.to_numpy() - start)
    rain = np.where(wet, amount * trend, 0.0)
    seasonal_t = 1.2 * np.sin((m - 2) / 12 * 2 * np.pi)
    warming = 0.025 * (days.year.to_numpy() - start)
    t = t_mean + seasonal_t + warming + rng.normal(0, 0.6, len(days))
    gw = np.clip(0.45 + np.array(monthly)[m] / 600 + rng.normal(0, 0.05, len(days)), 0.2, 0.98)

    def series(arr):
        return {d.strftime("%Y%m%d"): round(float(v), 2) for d, v in zip(days, arr)}

    return {
        "parameter": {
            "T2M": series(t),
            "T2M_MAX": series(t + dtr / 2),
            "T2M_MIN": series(t - dtr / 2),
            "PRECTOTCORR": series(rain),
            "RH2M": series(np.clip(70 + np.array(monthly)[m] / 15, 60, 92)),
            "WS2M": series(np.clip(rng.normal(3, 0.6, len(days)), 0.5, 8)),
            "WS10M_MAX": series(np.clip(rng.normal(7, 1.5, len(days)), 2, 20)),
            "GWETTOP": series(gw),
            "GWETROOT": series(np.clip(gw + 0.05, 0.2, 0.99)),
            "ALLSKY_SFC_SW_DWN": series(np.clip(rng.normal(20, 3, len(days)), 8, 28)),
        },
        "fill_value": -999,
        "source": "SYNTHETIC TEST FIXTURE - not NASA data",
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for i, (name, (lat, lon, monthly, t, dtr)) in enumerate(SITES.items()):
        raw = build(lat, lon, monthly, t, dtr, seed=i + 1)
        path = OUT / f"power_daily_{lat:.2f}_{lon:.2f}_1996_2025.json"
        path.write_text(json.dumps(raw))
        print("wrote", path)


if __name__ == "__main__":
    main()
