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


def test_water_watch_percentiles_and_ordinals():
    from fieldshift import water
    assert water.ordinal(3) == "3rd" and water.ordinal(11) == "11th" and water.ordinal(22) == "22nd"
    assert water.percentile_rank(5, [1, 2, 3, 4]) == 100.0
    assert water.classify(5)[1] == "dry2" and water.classify(50)[1] == "normal" and water.classify(95)[1] == "wet2"


def test_storm_threat_levels():
    from fieldshift import stormwatch
    near = {"lat": 17.0, "lon": -76.0, "dir": 280, "speed_mph": 10}
    far = {"lat": 30.0, "lon": -50.0, "dir": 45, "speed_mph": 15}
    assert stormwatch.threat(near, 18.05, -77.72)["level"] == "act now"
    assert stormwatch.threat(far, 18.05, -77.72)["level"] == "monitor"
    steps = stormwatch.render_steps(stormwatch.checklist("Plantain", "mature", drainage="Slow"))
    es = stormwatch.render_steps(stormwatch.checklist("Plantain", "mature", drainage="Slow"), "es")
    assert any("madurez" in s for s in es)
    assert any("prop" in s for s in steps) and any("drains slowly" in s for s in steps)


def test_assistant_briefing_and_request(monkeypatch):
    from fieldshift import assistant
    text = assistant.build_briefing({"Farm": "Test farm", "Climate": ["Jan: rain 30 mm"], "Empty": None})
    assert "Test farm" in text and "Jan: rain 30 mm" in text and "Empty" not in text
    captured = {}

    class R:
        ok = True
        def raise_for_status(self): pass
        def json(self): return {"candidates": [{"content": {"parts": [{"text": "Plant cowpea."}]}}]}

    def fake_post(url, params=None, json=None, timeout=None):
        captured.update(url=url, body=json)
        return R()

    monkeypatch.setattr(assistant.requests, "post", fake_post)
    answer, info = assistant.ask("k", [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}],
                                 "What now?", text, lang="es")
    assert answer == "Plant cowpea." and "Spanish" in captured["body"]["system_instruction"]["parts"][0]["text"]
    assert [c["role"] for c in captured["body"]["contents"]] == ["user", "model", "user"]


def test_alert_rules_and_topic():
    from fieldshift import alerts
    topic = alerts.topic_for("jamaica", 18.05, -77.72, "St Elizabeth, Jamaica")
    assert topic.startswith("farmfit-st-elizabeth-jamaica-") and topic == alerts.topic_for("jamaica", 18.05, -77.72, "St Elizabeth, Jamaica")
    storm = {"name": "Test", "classification": "Hurricane", "intensity_kt": 100, "lat": 17.5, "lon": -76.5, "dir": 280, "speed_mph": 10, "id": "al99"}
    out = alerts.evaluate(18.05, -77.72, "St Elizabeth", active=[storm])
    assert out and out[0]["level"] == "act now" and "Test" in out[0]["title"]
    assert "<svg" in alerts.qr_svg("https://ntfy.sh/" + topic)


def test_sensor_parse_and_compare():
    import io
    from fieldshift import sensor
    days = pd.date_range("2026-01-01", periods=40, freq="6h")
    raw = 2100 + 300 * np.sin(np.arange(len(days)) / 8)
    csv = pd.DataFrame({"ts": days.strftime("%Y-%m-%dT%H:%M:%SZ"), "soil_raw": raw}).to_csv(index=False).encode()
    s = sensor.parse_csv(csv)
    assert 0 <= s.min() and s.max() <= 100 and len(s) == 40
    ref = pd.Series(-raw, index=days)  # wetter probe -> lower raw -> higher pct, so -raw tracks pct
    z, stats = sensor.compare(s, {"ref": ref})
    assert stats[0]["r"] > 0.9


def test_poster_renders():
    from fieldshift import poster
    site = site_for(*JAM)
    crops = planner.load_crops()
    plans = planner.generate_strategies(site, crops, planner.allowed_crops(crops)); plans.pop("_meta")
    cur = planner.evaluate_current(site, crops, [planner.Planting("Tomato", 8, 4)])
    html = poster.build("Test farm", plans["storm"], cur, site, crops, "<div>cal</div>",
                        {"return_period_storm_force": 4, "peak_months": ["Aug"]}, ["Clear drains"], "https://ntfy.sh/x", "<svg></svg>", "fr")
    assert html.startswith("<!DOCTYPE html>") and "Test farm" in html and "Clear drains" in html and "Planter" not in html
