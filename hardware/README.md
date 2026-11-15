# FarmFit soil probe

A low-cost ground-truth station for comparing a field with NASA SMAP and NASA POWER soil wetness.

| Part | Approx. cost |
|---|---|
| ESP32 dev board | US$5-8 |
| Capacitive soil moisture sensor v1.2 | US$2-4 |
| 18650 cell, TP4056 charger, 5 V solar panel (optional) | US$6-10 |

**Wiring:**
- sensor AOUT → GPIO34
- sensor VCC → 3V3
- GND → GND
- optional battery divider (2 × 100 kΩ) → GPIO35

**Calibrate:**
1. Read `soil_raw` in dry air and put it in `DRY_RAW`.
2. Read it with the probe in water up to the line and put it in `WET_RAW`.

**Publish:** the sketch posts JSON to an ntfy topic every 30 minutes and deep-sleeps in between. The format is the IFRS sensor contract with `soil_raw` / `soil_pct` added.

**Use in FarmFit:** go to Water watch → Ground truth and enter the topic name to see recent readings, or upload a CSV with columns `ts, soil_raw` (or `soil_pct`).

**What the comparison means:** a probe measures one spot; SMAP averages about 9 km and POWER about 55 km. FarmFit therefore compares standardised anomalies (z-scores) and reports the correlation r, not absolute water content.
