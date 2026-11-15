"""Engine tests. Run: pytest -q  (uses the synthetic fixture, no internet)."""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["FIELDSHIFT_CACHE_DIR"] = str(ROOT / "tests" / "fixtures" / "cache")

from fieldshift import planner, power, recovery, soil_terrain, storms  # noqa: E402

JAM = (18.05, -77.72)
TT = (10.60, -61.38)


@pytest.fixture(scope="module", autouse=True)
def fixtures():
    if not (ROOT / "tests" / "fixtures" / "cache").exists():
        import subprocess
        subprocess.run([sys.executable, str(ROOT / "tests" / "make_fixture.py")], check=True)


def site_for(lat, lon, soil=None):
    df, _ = power.fetch_daily(lat, lon, 1996, 2025, allow_network=False)
    df = power.add_et0(df, lat)
    clim = power.monthly_climate(df)
    exposure = storms.monthly_exposure(storms.storm_impacts(lat, lon))
    return planner.Site(clim, exposure, soil=soil or {"ph": 6.3, "drainage": "Moderate"})


def test_melissa_is_top_storm_for_st_elizabeth():
    imp = storms.storm_impacts(*JAM)
    top = imp.iloc[0]
    assert top["name"] == "MELISSA" and top["year"] == 2025
    assert top["time"].month == 10 and top["site_wind_kt"] >= 64


def test_trinidad_rarely_sees_hurricane_force_wind():
    summ = storms.exposure_summary(storms.storm_impacts(*TT))
    assert summ["hurricane_force_events"] == 0
    assert summ["storm_force_events"] <= 6


def test_rankine_wind_profile():
    assert storms.wind_at_distance(100, 40, 40) == pytest.approx(85, rel=1e-6)
    assert storms.wind_at_distance(100, 0.0, 40) == pytest.approx(0, abs=1e-6)
    assert storms.wind_at_distance(100, 160, 40) < storms.wind_at_distance(100, 80, 40)


def test_hargreaves_et0_is_physical():
    df, _ = power.fetch_daily(*JAM, 1996, 2025, allow_network=False)
    et0 = power.add_et0(df, JAM[0])["ET0"]
    assert 2.0 < et0.mean() < 7.0


def test_usda_texture():
    assert soil_terrain.usda_texture(40, 40, 20) == "Loam"
    assert soil_terrain.usda_texture(20, 20, 60) == "Clay"
    assert soil_terrain.usda_texture(90, 5, 5) == "Sand"


def test_storm_smart_beats_exposed_current_rotation():
    site = site_for(*JAM)
    crops = planner.load_crops()
    plans = planner.generate_strategies(site, crops, planner.allowed_crops(crops))
    plans.pop("_meta")
    current = planner.evaluate_current(site, crops, [planner.Planting("Watermelon", 6, 3), planner.Planting("Sweet Pepper", 9, 4)])
    assert set(plans) == {"storm", "soil", "water"}
    assert plans["storm"].metrics["expected_loss"] < current.metrics["expected_loss"]
    assert plans["soil"].metrics["bare_months"] <= current.metrics["bare_months"]


def test_plans_cover_twelve_months_and_respect_rotation_rules():
    site = site_for(*TT)
    crops = planner.load_crops()
    plans = planner.generate_strategies(site, crops, planner.allowed_crops(crops, wet_field=True), irrigation="No irrigation")
    plans.pop("_meta")
    for plan in plans.values():
        months = [m for p in plan.plantings for m in p.month_list()]
        assert len(months) == len(set(months)) and len(months) >= 11
        fams = [crops.loc[p.crop, "family"] for p in plan.plantings]
        assert all(a != b for a, b in zip(fams, fams[1:]))


def test_wet_crops_need_wet_field():
    crops = planner.load_crops()
    assert "Rice" not in planner.allowed_crops(crops, wet_field=False)
    assert "Dasheen" in planner.allowed_crops(crops, wet_field=True)


def test_monte_carlo_is_reproducible_and_bounded():
    site = site_for(*JAM)
    crops = planner.load_crops()
    cur = planner.evaluate_current(site, crops, [planner.Planting("Tomato", 8, 4)])
    a = planner.monte_carlo(site, {"c": cur}, crops, n_years=2000, seed=1)["c"]
    b = planner.monte_carlo(site, {"c": cur}, crops, n_years=2000, seed=1)["c"]
    assert a["expected_loss"] == b["expected_loss"]
    assert 0 <= a["expected_loss"] <= 1
    more = planner.monte_carlo(site, {"c": cur}, crops, n_years=2000, seed=1, storm_multiplier=2.0)["c"]
    assert more["expected_loss"] >= a["expected_loss"]


def test_flood_contact_blocks_food_and_flags_contamination():
    state = recovery.field_state({"standing_water": "widespread"},
                                 {"standing_water_days": 5, "water_source": "Sewage / septic", "flood_touched_edible": "Yes"})
    assert {"edible_contact", "contamination_risk", "prolonged_flooding"} <= set(state["flags"])
    stages = recovery.recovery_stages(state, 10)
    assert "Do not harvest" in stages[0]["actions"][0]
    assert "Pak Choi" not in stages[2]["crops"]


def test_datarods_line_parser():
    from fieldshift.earthdata import LINE
    for line in ("2025-10-28T00:00:00\t1.25", "2025-10-28 00Z 1.25", "2025-10-28T00:30 1.25e0"):
        m = LINE.match(line)
        assert m and float(m.group(4)) == 1.25
    assert LINE.match("Location: lat 18.05") is None
