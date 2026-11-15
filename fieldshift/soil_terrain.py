"""Soil (ISRIC SoilGrids 250 m) and terrain (NASA SRTM 30 m) for a farm point.

Both services are free and keyless. Both can be slow or unavailable, so
every call has a cache and a graceful fallback: the farmer can always
correct or enter values by hand.
"""

import json
import math
import os
from pathlib import Path

import requests

CACHE_DIR = Path(os.environ.get("FIELDSHIFT_CACHE_DIR", Path(__file__).resolve().parents[1] / "data" / "cache"))

SOILGRIDS = "https://rest.isric.org/soilgrids/v2.0/properties/query"
OPENTOPO = "https://api.opentopodata.org/v1/srtm30m"
OPEN_METEO_ELEVATION = "https://api.open-meteo.com/v1/elevation"

SOIL_PROPS = ["phh2o", "soc", "clay", "sand", "silt", "nitrogen", "bdod"]
DEPTHS = ["0-5cm", "5-15cm", "15-30cm"]


def _cache(name):
    return CACHE_DIR / name


def _read_cache(name):
    path = _cache(name)
    if path.exists():
        return json.loads(path.read_text())
    return None


def _write_cache(name, payload):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache(name).write_text(json.dumps(payload))


def usda_texture(sand, silt, clay):
    """USDA soil texture class from percentages."""
    if None in (sand, silt, clay):
        return None
    if clay >= 40 and silt < 40 and sand <= 45:
        return "Clay"
    if clay >= 40 and silt >= 40:
        return "Silty clay"
    if clay >= 35 and sand > 45:
        return "Sandy clay"
    if 27 <= clay < 40 and sand <= 20:
        return "Silty clay loam"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "Clay loam"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "Sandy clay loam"
    if silt >= 80 and clay < 12:
        return "Silt"
    if silt >= 50 and (clay < 27):
        return "Silt loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "Loam"
    if sand >= 85 and (silt + 1.5 * clay) < 15:
        return "Sand"
    if sand >= 70 and (silt + 2 * clay) < 30:
        return "Loamy sand"
    return "Sandy loam"


DRAINAGE_BY_TEXTURE = {
    "Sand": "Fast", "Loamy sand": "Fast", "Sandy loam": "Good",
    "Loam": "Moderate", "Silt loam": "Moderate", "Silt": "Moderate",
    "Sandy clay loam": "Moderate", "Clay loam": "Slow", "Silty clay loam": "Slow",
    "Sandy clay": "Slow", "Silty clay": "Very slow", "Clay": "Very slow",
}


def get_soil(lat, lon, allow_network=True):
    """Top-soil (0-30 cm, depth-weighted) properties from SoilGrids."""
    key = f"soil_{lat:.3f}_{lon:.3f}.json"
    cached = _read_cache(key)
    if cached:
        return {**cached, "origin": "cache"}
    if not allow_network:
        return None
    try:
        params = [("lon", round(lon, 5)), ("lat", round(lat, 5)), ("value", "mean")]
        params += [("property", p) for p in SOIL_PROPS] + [("depth", d) for d in DEPTHS]
        response = requests.get(SOILGRIDS, params=params, timeout=25)
        response.raise_for_status()
        layers = response.json()["properties"]["layers"]
    except Exception as error:  # noqa: BLE001
        return {"origin": None, "error": str(error)}

    weights = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}
    values = {}
    for layer in layers:
        factor = layer.get("unit_measure", {}).get("d_factor", 1) or 1
        total = weight = 0.0
        for depth in layer.get("depths", []):
            mean = depth.get("values", {}).get("mean")
            if mean is None:
                continue
            w = weights.get(depth["label"], 0)
            total += (mean / factor) * w
            weight += w
        values[layer["name"]] = round(total / weight, 2) if weight else None

    if all(v is None for v in values.values()):
        return {"origin": None, "error": "SoilGrids has no data for this pixel (water, urban or island edge)."}

    result = {
        "ph": values.get("phh2o"),
        "soc_g_kg": values.get("soc"),
        "organic_matter_pct": round(values["soc"] * 1.724 / 10, 2) if values.get("soc") else None,
        "clay_pct": values.get("clay"),
        "sand_pct": values.get("sand"),
        "silt_pct": values.get("silt"),
        "nitrogen_g_kg": values.get("nitrogen"),
        "bulk_density": values.get("bdod"),
        "source": "ISRIC SoilGrids 2.0 (250 m), 0-30 cm depth-weighted mean",
    }
    result["texture"] = usda_texture(result["sand_pct"], result["silt_pct"], result["clay_pct"])
    result["drainage"] = DRAINAGE_BY_TEXTURE.get(result["texture"])
    _write_cache(key, result)
    return {**result, "origin": "live"}


def get_terrain(lat, lon, allow_network=True):
    """Elevation and slope from SRTM 30 m (3x3 stencil, 30 m spacing)."""
    key = f"terrain_{lat:.4f}_{lon:.4f}.json"
    cached = _read_cache(key)
    if cached:
        return {**cached, "origin": "cache"}
    if not allow_network:
        return None
    step_m = 30.0
    dlat = step_m / 111_320.0
    dlon = step_m / (111_320.0 * max(math.cos(math.radians(lat)), 0.1))
    grid = [(lat + i * dlat, lon + j * dlon) for i in (1, 0, -1) for j in (-1, 0, 1)]
    try:
        response = requests.get(
            OPENTOPO,
            params={"locations": "|".join(f"{a:.6f},{b:.6f}" for a, b in grid)},
            timeout=20,
        )
        response.raise_for_status()
        z = [r["elevation"] for r in response.json()["results"]]
        if any(v is None for v in z):
            raise ValueError("SRTM void")
        # Horn's method
        z1, z2, z3, z4, z5, z6, z7, z8, z9 = z
        dzdx = ((z3 + 2 * z6 + z9) - (z1 + 2 * z4 + z7)) / (8 * step_m)
        dzdy = ((z1 + 2 * z2 + z3) - (z7 + 2 * z8 + z9)) / (8 * step_m)
        slope_pct = math.hypot(dzdx, dzdy) * 100
        result = {
            "elevation_m": round(z5, 1),
            "slope_pct": round(slope_pct, 1),
            "source": "NASA SRTM GL1 30 m via OpenTopoData",
        }
    except Exception as error:  # noqa: BLE001
        try:
            response = requests.get(OPEN_METEO_ELEVATION, params={"latitude": lat, "longitude": lon}, timeout=15)
            response.raise_for_status()
            result = {
                "elevation_m": round(response.json()["elevation"][0], 1),
                "slope_pct": None,
                "source": "Copernicus DEM 90 m via Open-Meteo (SRTM unavailable: slope not computed)",
                "error": str(error),
            }
        except Exception as error2:  # noqa: BLE001
            return {"origin": None, "error": f"{error}; {error2}"}
    _write_cache(key, result)
    return {**result, "origin": "live"}


def slope_class(slope_pct):
    if slope_pct is None:
        return "Unknown"
    if slope_pct < 2:
        return "Flat (0-2%)"
    if slope_pct < 5:
        return "Gentle (2-5%)"
    if slope_pct < 10:
        return "Moderate (5-10%)"
    if slope_pct < 20:
        return "Steep (10-20%)"
    return "Very steep (>20%)"


def erosion_slope_factor(slope_pct):
    """RUSLE-style slope steepness factor S (McCool et al., 1987), relative to 9 % slope = 1."""
    if slope_pct is None:
        return 1.0
    theta = math.atan(slope_pct / 100)
    if slope_pct < 9:
        return 10.8 * math.sin(theta) + 0.03
    return 16.8 * math.sin(theta) - 0.50
