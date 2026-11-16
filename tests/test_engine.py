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


def test_giovanni_timeseries_parser():
    from fieldshift.earthdata import parse_timeseries
    text = "\n".join([
        "prod_name,GPM_3IMERGDF", "param_short_name,precipitation", "param_name,Daily mean precipitation",
        "unit,mm/day", "lat,18.05", "lon,-77.75", "",
        "Timestamp (UTC),Data",
        "2025-10-27T00:00:00,12.5", "2025-10-28T00:00:00,210.25", "2025-10-29T00:00:00,-9999.9",
    ])
    headers, s = parse_timeseries(text)
    assert headers["unit"] == "mm/day"
    assert list(s.values) == [12.5, 210.25]  # fill value dropped
    assert parse_timeseries("<html>error</html>")[1] is None


def test_imerg_opendap_cell_and_parser():
    from fieldshift.earthdata import imerg_cell, parse_opendap_value
    assert imerg_cell(-89.95, -179.95) == (0, 0)
    assert imerg_cell(89.95, 179.95) == (3599, 1799)
    assert imerg_cell(18.05, -77.72) == (1022, 1080)
    for reply in ("Dataset: 3B-DAY.nc4\nprecipitation.precipitation[0][0][0], 212.37\n",
                  "Dataset: x\nprecipitation[1][1][1]\n[0][0], 212.37\n"):
        assert parse_opendap_value(reply) == 212.37
    assert parse_opendap_value("<html>Earthdata Login</html>") is None


def test_ibtracs_north_atlantic_is_not_read_as_missing():
    import io
    import pandas as pd
    csv = "SID,SEASON,BASIN\n,Year,\nX1,2026,NA\nX2,2026,EP\n"
    naive = pd.read_csv(io.StringIO(csv), skiprows=[1])
    fixed = pd.read_csv(io.StringIO(csv), skiprows=[1], keep_default_na=False, na_values=["", " "])
    assert (naive["BASIN"] == "NA").sum() == 0   # the bug
    assert (fixed["BASIN"] == "NA").sum() == 1   # the fix


def test_soilgrids_falls_back_to_wcs(tmp_path, monkeypatch):
    import io
    import numpy as np
    import tifffile
    from fieldshift import soil_terrain as st

    monkeypatch.setattr(st, "CACHE_DIR", tmp_path)
    raw = {"phh2o": 65, "soc": 150, "clay": 450, "sand": 250, "silt": 300, "nitrogen": 180, "bdod": 130}

    class Resp:
        def __init__(self, content):
            self.content = content
            self.text = ""

        def raise_for_status(self):
            pass

    def fake_get(url, params=None, timeout=None):
        if url == st.SOILGRIDS:
            raise ConnectionError("REST paused")
        prop = dict(params)["COVERAGEID"].split("_")[0]
        grid = np.full((4, 4), raw[prop], dtype="int16")
        grid[0, 0] = -32768  # nodata pixel
        buf = io.BytesIO()
        tifffile.imwrite(buf, grid)
        return Resp(buf.getvalue())

    monkeypatch.setattr(st.requests, "get", fake_get)
    soil = st.get_soil(18.05, -77.72)
    assert soil["origin"] == "live" and "WCS" in soil["source"]
    assert soil["ph"] == 6.5 and soil["clay_pct"] == 45.0 and soil["bulk_density"] == 1.3
    assert soil["texture"] == "Clay"


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


def test_enso_outlook_splits_the_farms_own_rain_by_phase():
    import numpy as np
    import pandas as pd
    from fieldshift import enso
    # 30 years where Dec-Feb rain is high in El Nino years and low in La Nina years
    days = pd.date_range("1996-01-01", "2025-12-31")
    oni_rows, rain = [], pd.Series(1.0, index=days)
    for y in range(1995, 2027):
        a = [1.2, 0.0, -1.2][y % 3]
        for i, sname in enumerate(enso.SEASONS):
            oni_rows.append(f"  {sname} {y}  27.0  {a:.2f}")
        window = (days >= pd.Timestamp(y, 12, 1)) & (days < pd.Timestamp(y + 1, 3, 1))
        rain[window] = {1.2: 3.0, 0.0: 2.0, -1.2: 1.0}[a]
    oni = enso.parse_oni("\n".join(oni_rows))
    oni = oni[oni["date"] <= "2026-10-01"]
    o = enso.outlook(pd.DataFrame({"PRECTOTCORR": rain}), oni, today="2026-11-15")
    assert o["window_months"] == [12, 1, 2]
    assert o["now"]["season"] == "SON" and o["now"]["year"] == 2026
    bp = o["by_phase"]
    assert bp["El Niño"]["pct_normal"] > bp["Neutral"]["pct_normal"] > bp["La Niña"]["pct_normal"]
    assert o["r"] > 0.9
    assert enso.phase(0.5) == "El Niño" and enso.phase(-0.5) == "La Niña" and enso.phase(0.2) == "Neutral"


def test_appeears_cleaning_scales_et_and_averages_smap_l4():
    import pandas as pd
    from fieldshift.earthdata import clean_points
    raw = pd.DataFrame([
        {"id": "j", "date": "2026-10-01", "product": "MOD16A2.061", "layer": "ET_500m", "value": 250},
        {"id": "j", "date": "2026-10-09", "product": "MOD16A2.061", "layer": "ET_500m", "value": 32762},  # fill
        {"id": "j", "date": "2026-10-01", "product": "MOD16A2.061", "layer": "PET_500m", "value": 400},
        {"id": "j", "date": "2026-10-01 01:30", "product": "SPL4SMGP.007", "layer": "Geophysical_Data_sm_rootzone", "value": 0.30},
        {"id": "j", "date": "2026-10-01 04:30", "product": "SPL4SMGP.007", "layer": "Geophysical_Data_sm_rootzone", "value": 0.20},
        {"id": "j", "date": "2026-10-01", "product": "MOD13Q1.061", "layer": "_250m_16_days_NDVI", "value": 7000},
    ])
    out = clean_points(raw).set_index("layer")["value"]
    assert out["ET_500m"] == 25.0 and out["PET_500m"] == 40.0
    assert abs(out["Geophysical_Data_sm_rootzone"] - 0.25) < 1e-9
    assert abs(out["_250m_16_days_NDVI"] - 0.7) < 1e-9


def test_crop_stress_ratio():
    import pandas as pd
    from fieldshift import water
    idx = pd.date_range("2024-01-01", periods=120, freq="8D")
    et = pd.Series(30.0, index=idx)
    et.iloc[-1] = 10.0
    pet = pd.Series(40.0, index=idx)
    s = water.crop_stress(et, pet)
    assert s["ratio"] == 0.25 and s["label"] == "water-limited"
    assert abs(s["normal"] - 0.75) < 1e-9


def test_planting_window_and_pest_cycle():
    import numpy as np
    import pandas as pd
    from fieldshift import planner
    crops = planner.load_crops()
    clim = pd.DataFrame({"month": range(1, 13), "rain_mm": 100.0, "et0_mm": 120.0, "t_mean": 27.0, "t_max": 31.0,
                         "p_heavy_rain": 0.05, "soil_wet_root": 0.7})
    calm = pd.DataFrame({"month": range(1, 13), "p_storm_force": 0.0, "p_hurricane_force": 0.0})
    stormy = calm.assign(p_storm_force=np.where(calm["month"].isin([9, 10]), 0.5, 0.0),
                         p_hurricane_force=np.where(calm["month"].isin([9, 10]), 0.3, 0.0))
    w_calm = planner.planting_window(planner.Site(clim, calm, {"ph": 6.5}), crops, "Tomato", "Reliable irrigation")
    w_storm = planner.planting_window(planner.Site(clim, stormy, {"ph": 6.5}), crops, "Tomato", "Reliable irrigation")
    assert len(w_calm) == 12 and all(0 <= w["p_good"] <= 1 for w in w_calm)
    # a tomato planted in July is in the field through Sep-Oct: storms must cut its chances
    jul = 6
    assert w_storm[jul]["p_safe"] < w_calm[jul]["p_safe"] - 0.2
    plan = planner.Plan("x", [planner.Planting("Tomato", 1, 4), planner.Planting("Sweet Pepper", 6, 4)])
    rep = planner.pest_cycle(plan)
    assert rep and rep[0][2] == "Solanaceae"


def test_market_index_from_wide_table():
    import pandas as pd
    from fieldshift import market
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    wide = pd.DataFrame({"Commodity": ["Tomato (kg)", "Patchoi"], **{m: [10 + i, 5] for i, m in enumerate(months)}})
    idx = market.price_index(market.tidy(wide), "Tomato")
    assert idx[12] > 1 > idx[1]
    plan = __import__("fieldshift.planner", fromlist=["x"]).Plan("x", [__import__("fieldshift.planner", fromlist=["x"]).Planting("Tomato", 9, 4)])
    mk = market.plan_market(plan, market.tidy(wide))
    assert mk[0]["harvest"] == 12 and mk[0]["best"] == 12


def test_satellite_series_with_text_dates_and_few_years():
    import pandas as pd
    from fieldshift import water
    idx = [d.strftime("%Y-%m-%d") for d in pd.date_range("2023-11-01", "2026-11-12", freq="3D")]
    sm = pd.Series([0.5] * len(idx), index=idx)
    sm.iloc[-4:] = 0.3
    out = water.smap_anomaly(sm)
    assert out["percentile"] is None and out["rank_text"].startswith("driest of 4")
    et = pd.Series(20.0, index=[d.strftime("%Y-%m-%d") for d in pd.date_range("2024-01-01", periods=60, freq="8D")])
    assert water.crop_stress(et, et * 2)["ratio"] == 0.5


def test_profile_link_round_trip_and_rotation():
    from fieldshift import planner, profile
    p = profile.new("farm")
    p.update({"name": "Test", "lat": 10.6, "lon": -61.38, "crops": ["Corn", "Tomato"], "water": profile.WATER[1],
              "soil_type": profile.SOIL_TYPES[1], "ph": 5.8})
    back = profile.decode(profile.encode(p))
    assert back["lat"] == 10.6 and back["crops"] == ["Corn", "Tomato"] and back["ph"] == 5.8
    assert profile.decode("not-a-profile") is None
    assert profile.irrigation(p) == "Limited irrigation"
    assert profile.soil_override(p) == {"ph": 5.8, "drainage": "Slow"}
    rows = profile.rotation_from_crops(["Corn", "Tomato"], 11, planner.load_crops())
    assert rows[0][0] == "Corn" and rows[0][1] == 11 and rows[1][1] == (11 - 1 + rows[0][2]) % 12 + 1


def test_community_reports_are_blurred_unverified_and_clustered(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from fieldshift import community
    monkeypatch.setattr(community, "DIR", tmp_path)
    r = community.add(10.6123, -61.3876, "insects", "high", "armyworm in corn", crop="Corn")
    assert r["status"] == "unverified"
    assert (r["lat"], r["lon"]) != (10.6123, -61.3876)
    assert abs(r["lat"] - 10.6123) <= community.GRID and abs(r["lon"] + 61.3876) <= community.GRID
    for _ in range(2):
        community.add(10.62, -61.39, "insects", "medium", "more armyworm")
    community.update(r["id"], status="verified", guidance="Scout twice a week")
    rs = community.load()
    assert any(x["status"] == "verified" and x["guidance"] for x in rs)
    near = community.nearby(rs, 10.6, -61.38, km=10)
    assert len(near) == 3 and near[0]["km"] < 10
    hs = community.hotspots(rs)
    assert hs and hs[0]["category"] == "insects" and hs[0]["count"] == 3
    assert all(x["simulated"] for x in community.example_reports(10.6, -61.38))


def test_restoration_only_suggests_rice_where_it_can_grow():
    from fieldshift import restore
    caroni = restore.field_facts({"clay_pct": 49, "drainage": "Very slow"}, {"slope_pct": 0.8}, "No irrigation", True)
    dry_slope = restore.field_facts({"clay_pct": 20, "drainage": "Moderate"}, {"slope_pct": 9}, "No irrigation", False)
    rice = lambda f: next(r for r in restore.recommend("waterlogged", f) if r["name"] == "Rice")
    assert rice(caroni)["suits"] is True
    assert rice(dry_slope)["suits"] is False and rice(dry_slope)["caveat"]
    assert "Rice is also" in restore.CONDITIONS["salt"]["avoid"]


def test_news_rss_parser():
    from fieldshift import news
    xml = """<rss><channel><item><title>Farmers count losses - Newsday</title><link>https://example.org/a</link>
    <source>Newsday</source><pubDate>Sat, 14 Nov 2026 10:00:00 GMT</pubDate></item></channel></rss>"""
    items = news.parse_rss(xml)
    assert items == [{"title": "Farmers count losses", "link": "https://example.org/a", "source": "Newsday", "date": "2026-11-14"}]


def test_merge_points_handles_three_hourly_time_zones(tmp_path, monkeypatch):
    import pandas as pd
    from scripts import refresh_data
    monkeypatch.setattr(refresh_data, "POINTS", tmp_path / "p.csv")
    df = pd.DataFrame({"id": ["a"] * 3, "product": ["SPL4SMGP.008"] * 3, "layer": ["sm_rootzone"] * 3,
                       "date": ["2026-11-14T01:30:00+00:00", "2026-11-14T04:30:00Z", "2026-11-15"],
                       "value": [0.30, 0.34, 0.40]})
    refresh_data.merge_points(df)
    out = pd.read_csv(tmp_path / "p.csv")
    assert list(out["date"]) == ["2026-11-14", "2026-11-15"]
    assert abs(out["value"].iloc[0] - 0.32) < 1e-9
