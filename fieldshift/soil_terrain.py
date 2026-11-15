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
# Same SoilGrids 2.0 maps through ISRIC's OGC Web Coverage Service. Used when the
# (beta) REST API is paused, which ISRIC has done several times.
SOILGRIDS_WCS = "https://maps.isric.org/mapserv"
# SoilGrids stores integers; divide by these to get conventional units
# (pH, g/kg, %, g/kg, kg/dm3).
SOIL_FACTOR = {"phh2o": 10, "soc": 10, "clay": 10, "sand": 10, "silt": 10, "nitrogen": 100, "bdod": 100}
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
    values, source, errors = None, None, []
    try:
        values = _soilgrids_rest(lat, lon)
        source = "ISRIC SoilGrids 2.0 REST (250 m)"
    except Exception as error:  # noqa: BLE001
        errors.append(f"REST: {str(error)[:150]}")
    if values is None or all(v is None for v in values.values()):
        try:
            values = _soilgrids_wcs(lat, lon)
            source = "ISRIC SoilGrids 2.0 WCS (250 m)"
        except Exception as error:  # noqa: BLE001
            errors.append(f"WCS: {str(error)[:150]}")
    if values is None:
        return {"origin": None, "error": " | ".join(errors)}

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
        "source": f"{source}, 0-30 cm depth-weighted mean",
    }
    result["texture"] = usda_texture(result["sand_pct"], result["silt_pct"], result["clay_pct"])
    result["drainage"] = DRAINAGE_BY_TEXTURE.get(result["texture"])
    _write_cache(key, result)
    return {**result, "origin": "live"}


DEPTH_WEIGHTS = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}


def _weighted(by_depth):
    """Depth-weighted 0-30 cm mean from {depth label: value}."""
    pairs = [(v, DEPTH_WEIGHTS[d]) for d, v in by_depth.items() if v is not None and d in DEPTH_WEIGHTS]
    total = sum(w for _, w in pairs)
    return round(sum(v * w for v, w in pairs) / total, 2) if total else None


def _soilgrids_rest(lat, lon):
    params = [("lon", round(lon, 5)), ("lat", round(lat, 5)), ("value", "mean")]
    params += [("property", p) for p in SOIL_PROPS] + [("depth", d) for d in DEPTHS]
    response = requests.get(SOILGRIDS, params=params, timeout=25)
    response.raise_for_status()
    values = {}
    for layer in response.json()["properties"]["layers"]:
        factor = layer.get("unit_measure", {}).get("d_factor", 1) or 1
        by_depth = {}
        for depth in layer.get("depths", []):
            mean = depth.get("values", {}).get("mean")
            by_depth[depth["label"]] = None if mean is None else mean / factor
        values[layer["name"]] = _weighted(by_depth)
    return values


def _soilgrids_wcs(lat, lon, half=0.004):
    """Read a ~900 m GeoTIFF window around the point for each property and depth,
    and average the valid 250 m pixels."""
    import io

    import numpy as np
    import tifffile

    values = {}
    for prop in SOIL_PROPS:
        by_depth = {}
        for depth in DEPTHS:
            params = [
                ("map", f"/map/{prop}.map"), ("SERVICE", "WCS"), ("VERSION", "2.0.1"),
                ("REQUEST", "GetCoverage"), ("COVERAGEID", f"{prop}_{depth}_mean"),
                ("FORMAT", "image/tiff"),
                ("SUBSET", f"long({lon - half:.5f},{lon + half:.5f})"),
                ("SUBSET", f"lat({lat - half:.5f},{lat + half:.5f})"),
                ("SUBSETTINGCRS", "http://www.opengis.net/def/crs/EPSG/0/4326"),
                ("OUTPUTCRS", "http://www.opengis.net/def/crs/EPSG/0/4326"),
            ]
            response = requests.get(SOILGRIDS_WCS, params=params, timeout=40)
            response.raise_for_status()
            if not response.content[:4] in (b"II*\x00", b"MM\x00*"):
                raise ValueError(f"{prop} {depth}: not a GeoTIFF: {response.text[:120]!r}")
            raster = tifffile.imread(io.BytesIO(response.content)).astype(float)
            valid = raster[(raster > 0) & (raster < 32767)]
            by_depth[depth] = float(valid.mean()) / SOIL_FACTOR[prop] if valid.size else None
        values[prop] = _weighted(by_depth)
    return values


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
