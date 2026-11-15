"""Streamlit views for FarmFit · Hurricane to Harvest."""

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import altair as alt
import folium
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from . import planner, power, recovery, soil_terrain, storms

MONTHS = planner.MONTHS
CACHE_DIR = power.CACHE_DIR


def manifest():
    try:
        return json.loads((CACHE_DIR / "manifest.json").read_text())
    except Exception:  # noqa: BLE001
        return {}


def freshness(name):
    """'refreshed 3 days ago' for a dataset in the manifest, or None."""
    entry = manifest().get("datasets", {}).get(name)
    if not entry or entry.get("status") not in ("ok", "partial"):
        return None
    try:
        then = datetime.fromisoformat(entry["updated"])
        days = (datetime.now(timezone.utc) - then).days
        return "refreshed today" if days == 0 else f"refreshed {days} day{'s' if days != 1 else ''} ago"
    except Exception:  # noqa: BLE001
        return None


def satellite_pulse(farm_id):
    """Cached SMAP / NDVI (AppEEARS) and IMERG series for a watched farm."""
    out = {}
    path = CACHE_DIR / "appeears_points.csv"
    if path.exists():
        df = pd.read_csv(path, parse_dates=["date"])
        df = df[df["id"] == farm_id]
        for key, needle in (("smap", "soil_moisture"), ("ndvi", "NDVI")):
            part = df[df["layer"].str.contains(needle, case=False)]
            if len(part):
                out[key] = part.set_index("date")["value"].sort_index()
    ip = CACHE_DIR / f"imerg_{farm_id}.csv"
    if ip.exists():
        out["imerg"] = pd.read_csv(ip, parse_dates=["date"]).set_index("date")["imerg_mm"]
    return out

DEMO_SITES = {
    "jamaica": {
        "label": "St Elizabeth, Jamaica",
        "story": "Jamaica's breadbasket parish, crossed by Category 5 Hurricane Melissa on 28 Oct 2025.",
        "lat": 18.05, "lon": -77.72, "icon": "🌀",
        "current": [("Watermelon", 6, 3), ("Sweet Pepper", 9, 4)],
        "storm": "MELISSA 2025", "storm_date": date(2025, 10, 28),
        "wet_field": False, "irrigation": "Limited irrigation",
    },
    "trinidad": {
        "label": "Caroni plains, Trinidad",
        "story": "Low-lying farmland where the main storm threat is rain and flooding, not wind.",
        "lat": 10.60, "lon": -61.38, "icon": "🌧️",
        "current": [("Corn", 6, 3), ("Tomato", 9, 4)],
        "storm": "BRET 1993", "storm_date": date(1993, 8, 7),
        "wet_field": True, "irrigation": "No irrigation",
    },
}

GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{layer}/default/{date}/GoogleMapsCompatible_Level{level}/{{z}}/{{y}}/{{x}}.{ext}"
GIBS_LAYERS = [
    ("MODIS_Terra_CorrectedReflectance_TrueColor", "MODIS true colour (Terra)", 9, "jpg"),
    ("MODIS_Terra_NDVI_8Day", "MODIS NDVI 8-day (vegetation)", 9, "png"),
    ("SMAP_L4_Analyzed_Surface_Soil_Moisture", "SMAP L4 surface soil moisture", 6, "png"),
    ("IMERG_Precipitation_Rate", "GPM IMERG precipitation rate", 6, "png"),
]

CATEGORY_COLORS = {
    "Cat 5": "#7b2cbf", "Cat 4": "#c1121f", "Cat 3": "#e85d04", "Cat 2": "#f48c06",
    "Cat 1": "#ffba08", "Tropical storm": "#3a86ff", "Below storm force": "#8d99ae", "Unknown": "#8d99ae",
}

CSS = """
<style>
.fs-hero{border-radius:26px;padding:1.4rem 1.6rem;margin:.4rem 0 1rem 0;color:#fff;
  background:linear-gradient(120deg,#0b2545 0%,#13315c 40%,#1d6f5f 100%);box-shadow:0 18px 50px rgba(11,37,69,.18);
  position:relative;overflow:hidden}
.fs-hero:after{content:"";position:absolute;right:-60px;top:-60px;width:260px;height:260px;border-radius:50%;
  background:radial-gradient(circle,rgba(255,209,102,.35),transparent 65%)}
.fs-hero h2{color:#fff !important;margin:.1rem 0 .3rem 0;font-size:1.65rem}
.fs-hero p{color:#dbe7f3;margin:0;max-width:760px}
.fs-kicker{font-size:.75rem;letter-spacing:.12em;text-transform:uppercase;color:#ffd166;font-weight:700}
.fs-chip{display:inline-block;padding:.18rem .6rem;border-radius:999px;font-size:.75rem;font-weight:600;
  background:rgba(255,255,255,.14);color:#fff;margin:.5rem .35rem 0 0}
.fs-card{background:#fff;border:1px solid rgba(24,58,34,.10);border-radius:20px;padding:1rem 1.1rem;
  box-shadow:0 10px 30px rgba(25,49,31,.06);height:100%}
.fs-card h4{margin:.1rem 0 .35rem 0}
.fs-stat{font-size:1.6rem;font-weight:800;color:#143122;line-height:1.1}
.fs-label{font-size:.78rem;color:#617064;text-transform:uppercase;letter-spacing:.06em;font-weight:600}
.fs-sub{font-size:.85rem;color:#617064}
.fs-cal{display:grid;grid-template-columns:150px repeat(12,1fr);gap:4px;align-items:stretch;margin:.2rem 0}
.fs-cal .hdr{font-size:.72rem;font-weight:700;color:#617064;text-align:center;padding:.15rem 0}
.fs-cal .name{font-size:.82rem;font-weight:700;color:#143122;display:flex;align-items:center;gap:.35rem}
.fs-cal .risk{height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:.7rem;font-weight:700}
.fs-cal .bare{height:42px;border-radius:10px;background:repeating-linear-gradient(45deg,#f3eee6,#f3eee6 6px,#ebe3d6 6px,#ebe3d6 12px);
  border:1px dashed #cdbfa8}
.fs-cal .crop{height:42px;border-radius:10px;color:#102a1c;font-size:.78rem;font-weight:700;display:flex;align-items:center;
  padding:0 .5rem;overflow:hidden;white-space:nowrap;box-shadow:inset 0 -3px 0 rgba(0,0,0,.08)}
.fs-cal .storm{outline:3px solid #c1121f;outline-offset:-3px}
.fs-score{display:flex;align-items:center;gap:.5rem;margin:.18rem 0;font-size:.8rem}
.fs-score .bar{flex:1;height:8px;border-radius:99px;background:#eef2ec;overflow:hidden}
.fs-score .fill{height:100%;border-radius:99px}
.fs-badge{display:inline-block;padding:.15rem .55rem;border-radius:999px;font-size:.72rem;font-weight:700;margin-right:.3rem}
.fs-best{background:#ffd166;color:#4a3500}
.fs-cur{background:#e9ecef;color:#343a40}
.fs-stage{border-left:4px solid #2F7D32;padding:.4rem .9rem;margin:.5rem 0;background:#fff;border-radius:0 14px 14px 0;
  box-shadow:0 6px 18px rgba(25,49,31,.05)}
.fs-stage .gate{font-size:.8rem;color:#2F7D32;font-weight:700;margin-top:.3rem}
.fs-note{font-size:.8rem;color:#617064;border-top:1px dashed rgba(24,58,34,.15);margin-top:.6rem;padding-top:.5rem}
.fs-warn{background:#fff4e5;border:1px solid #ffd8a8;border-radius:14px;padding:.6rem .9rem;font-size:.85rem}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data bundle
# ---------------------------------------------------------------------------

@st.cache_data(ttl=86400, show_spinner=False)
def load_site(lat, lon):
    lat, lon = round(lat, 3), round(lon, 3)
    bundle = {"lat": lat, "lon": lon}
    df, meta = power.fetch_daily(lat, lon)
    bundle["power_meta"] = meta
    if df is not None:
        df = power.add_et0(df, lat)
        bundle["climate"] = power.monthly_climate(df)
        shift, annual, season = power.climate_shift(df)
        bundle["shift"], bundle["annual"], bundle["season"] = shift, annual, season
        bundle["shift_periods"] = (shift.attrs["then"], shift.attrs["now"])
        bundle["climate_period"] = bundle["climate"].attrs["period"]
        bundle["power_params"] = [c for c in df.columns if c in power.PARAM_INFO]
    impacts = storms.storm_impacts(lat, lon)
    bundle["impacts"] = impacts
    bundle["exposure"] = storms.monthly_exposure(impacts)
    bundle["storm_summary"] = storms.exposure_summary(impacts)
    bundle["soil"] = soil_terrain.get_soil(lat, lon)
    bundle["terrain"] = soil_terrain.get_terrain(lat, lon)
    return bundle


def build_site(bundle, soil_override=None):
    soil = dict(bundle.get("soil") or {})
    if soil_override:
        soil.update({k: v for k, v in soil_override.items() if v is not None})
    terrain = dict(bundle.get("terrain") or {})
    terrain["s_factor"] = soil_terrain.erosion_slope_factor(terrain.get("slope_pct"))
    return planner.Site(bundle["climate"], bundle["exposure"], soil=soil, terrain=terrain)


# ---------------------------------------------------------------------------
# Small render helpers
# ---------------------------------------------------------------------------

def stat_card(label, value, sub="", icon=""):
    st.markdown(
        f'<div class="fs-card"><div class="fs-label">{icon} {label}</div>'
        f'<div class="fs-stat">{value}</div><div class="fs-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def risk_color(p):
    # p in 0..~0.6
    t = min(1.0, p / 0.35)
    r = int(255 - (255 - 193) * t)
    g = int(243 - (243 - 18) * t)
    b = int(224 - (224 - 31) * t)
    text = "#fff" if t > 0.55 else "#5c3d00"
    return f"background:rgb({r},{g},{b});color:{text}"


def calendar_html(plans, site, crops, storm_month=None):
    risk = site.p_hu + site.p_ts + 0.5 * site.p_flood
    head = '<div class="hdr"></div>' + "".join(f'<div class="hdr">{m}</div>' for m in MONTHS)
    risk_row = '<div class="name">⚠️ Storm + flood risk</div>' + "".join(
        f'<div class="risk" style="{risk_color(p)}" title="storm-force wind {site.p_hu[i] + site.p_ts[i]:.0%}, waterlogging {site.p_flood[i]:.0%}">{p:.0%}</div>'
        for i, p in enumerate(risk)
    )
    rows = [head, risk_row]
    for plan in plans:
        cells = []
        segments = []
        for p in plan.plantings:
            months = p.month_list()
            run = [months[0]]
            for m in months[1:]:
                if m == run[-1] + 1:
                    run.append(m)
                else:
                    segments.append((p.crop, run))
                    run = [m]
            segments.append((p.crop, run))
        covered = {m for _, run in segments for m in run}
        for crop, run in segments:
            row = crops.loc[crop] if crop in crops.index else None
            color = row.color if row is not None else "#ccc"
            emoji = row.emoji if row is not None else ""
            storm_cls = " storm" if storm_month and storm_month in run else ""
            cells.append((run[0], len(run), f'<div class="crop{storm_cls}" style="background:{color}cc;grid-column:span {len(run)}" title="{crop}">{emoji}&nbsp;{crop}</div>'))
        for m in range(1, 13):
            if m not in covered:
                storm_cls = " storm" if storm_month == m else ""
                cells.append((m, 1, f'<div class="bare{storm_cls}" title="bare soil"></div>'))
        cells.sort(key=lambda c: c[0])
        rows.append(f'<div class="name">{plan.icon} {plan.title}</div>' + "".join(c[2] for c in cells))
    return '<div class="fs-cal">' + "".join(rows) + "</div>"


SCORE_LABELS = {
    "storm": ("Storm & flood safety", "#c1121f"),
    "soil": ("Soil health", "#8C6A43"),
    "water": ("Water saving", "#1d70b8"),
    "suitability": ("Climate fit", "#2F7D32"),
    "food": ("Food & income months", "#e09f3e"),
}


def score_bars(scores):
    html = ""
    for key, (label, color) in SCORE_LABELS.items():
        v = scores.get(key, 0)
        html += (f'<div class="fs-score"><div style="width:150px">{label}</div><div class="bar">'
                 f'<div class="fill" style="width:{v}%;background:{color}"></div></div><b>{v}</b></div>')
    return html


def data_passport(bundle):
    meta = bundle.get("power_meta", {})
    soil = bundle.get("soil") or {}
    terr = bundle.get("terrain") or {}
    origin = {"live": "✅ live", "cache": "✅ cached", "cache-nearby": "🟡 nearby cache", None: "⚠️ unavailable"}
    synthetic = "SYNTHETIC" in str(meta.get("source", ""))
    rows = [
        ["NASA POWER (MERRA-2, CERES)", "Daily rain, temperature, humidity, wind, soil wetness, radiation", "≈ 0.5° × 0.625° (≈ 55 km)",
         bundle.get("climate_period", "-"), ("🧪 TEST FIXTURE" if synthetic else origin.get(meta.get("origin"), "⚠️"))],
        ["NOAA HURDAT2 best track", "Storm positions and intensity every 6 h", "Track points, wind estimated at farm",
         "1971-2025 (tracks 1950+)", "✅ bundled"],
        ["ISRIC SoilGrids 2.0", "pH, organic carbon, clay / sand / silt", "250 m", "Static model", origin.get(soil.get("origin"), "⚠️")],
        ["NASA SRTM GL1", "Elevation and slope (RUSLE S factor)", "30 m", "Feb 2000", origin.get(terr.get("origin"), "⚠️")],
        ["NASA GIBS: SMAP, GPM IMERG, MODIS", "Map overlays for soil moisture, rain, vegetation", "9 km / 0.1° / 250 m", "Pick a date", "🗺️ map layer"],
        ["FAO ECOCROP + FAO-56", "Crop climate ranges and crop water coefficients", "Crop level", "-", "✅ bundled"],
    ]
    fresh = {0: "NASA POWER", 1: "NOAA IBTrACS (current season)", 2: "ISRIC SoilGrids", 3: "NASA SRTM"}
    for i, name in fresh.items():
        f = freshness(name)
        if f:
            rows[i][4] = f"{rows[i][4]} · {f}"
    for name, label, use, res in [
        ("GPM IMERG", "NASA GPM IMERG Final (data rods)", "Daily rain at the farm, storm windows", "0.1° (≈ 11 km)"),
        ("SMAP + MODIS NDVI (AppEEARS)", "NASA SMAP L3 + MODIS NDVI (AppEEARS)", "Soil-moisture and greenness time series", "9 km / 250 m"),
    ]:
        f = freshness(name)
        rows.append([label, use, res, "last 2-3 years", f"✅ {f}" if f else "⏳ needs Earthdata login"])
    return pd.DataFrame(rows, columns=["Dataset", "Used for", "Resolution", "Period", "Status"])


def make_map(lat, lon, impacts=None, date_str=None, height=420, top_storms=6, key="fs_map", show_layer=None):
    m = folium.Map(location=[lat, lon], zoom_start=7, control_scale=True, tiles=None)
    folium.TileLayer("OpenStreetMap", name="Street map").add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery", name="Satellite (Esri)",
    ).add_to(m)
    date_str = date_str or (date.today() - timedelta(days=3)).isoformat()
    for layer, title, level, ext in GIBS_LAYERS:
        folium.TileLayer(
            tiles=GIBS.format(layer=layer, date=date_str, level=level, ext=ext),
            attr="NASA GIBS / EOSDIS",
            name=f"{title} · {date_str}",
            overlay=True,
            show=(layer == show_layer),
            opacity=0.75,
            max_native_zoom=level,
            max_zoom=18,
        ).add_to(m)
    if impacts is not None and len(impacts):
        group = folium.FeatureGroup(name="Storm tracks (NOAA HURDAT2)", show=True)
        for _, s in impacts.head(top_storms).iterrows():
            track = storms.storm_track(s["storm_id"])
            color = CATEGORY_COLORS.get(s["site_category"], "#8d99ae")
            folium.PolyLine(
                track[["lat", "lon"]].to_numpy().tolist(),
                color=color, weight=3, opacity=0.85,
                tooltip=f"{s['name'].title()} {s['year']}: ≈ {s['site_wind_kt']:.0f} kt at the farm ({s['site_category']})",
            ).add_to(group)
        group.add_to(m)
    folium.Marker([lat, lon], tooltip="Your farm", icon=folium.Icon(color="green", icon="leaf")).add_to(m)
    folium.Circle([lat, lon], radius=100_000, color="#13315c", weight=1, fill=False, dash_array="6").add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    return st_folium(m, height=height, width=None, key=key, returned_objects=["last_clicked"])


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def ensure_state():
    ss = st.session_state
    ss.setdefault("fs_demo", "jamaica")
    ss.setdefault("fs_current", list(DEMO_SITES["jamaica"]["current"]))
    ss.setdefault("fs_wet_field", DEMO_SITES["jamaica"]["wet_field"])
    ss.setdefault("fs_irrigation", DEMO_SITES["jamaica"]["irrigation"])


def demo_picker():
    ss = st.session_state
    cols = st.columns(len(DEMO_SITES) + 1)
    for col, (key, site) in zip(cols, DEMO_SITES.items()):
        with col:
            if st.button(f"{site['icon']} {site['label']}", key=f"demo_{key}", use_container_width=True,
                         type="primary" if ss.get("fs_demo") == key else "secondary"):
                ss.fs_demo = key
                ss.farm_latitude, ss.farm_longitude = site["lat"], site["lon"]
                ss.fs_current = list(site["current"])
                ss.fs_wet_field = site["wet_field"]
                ss.fs_irrigation = site["irrigation"]
                ss.pop("fs_plans", None)
                st.rerun()
    with cols[-1]:
        st.caption("Or tap the map below to use your own farm.")


def current_demo():
    key = st.session_state.get("fs_demo")
    site = DEMO_SITES.get(key)
    if site and abs(site["lat"] - st.session_state.farm_latitude) < 0.05 and abs(site["lon"] - st.session_state.farm_longitude) < 0.05:
        return key, site
    return None, None


# ---------------------------------------------------------------------------
# VIEW: Storm-ready plan
# ---------------------------------------------------------------------------

def render_storm_plan():
    inject_css()
    ensure_state()
    ss = st.session_state
    st.markdown(
        """<div class="fs-hero"><div class="fs-kicker">Hurricane to Harvest · NASA Space Apps 2026 · Field Shift</div>
        <h2>Plan a rotation that survives the storm season and rebuilds the soil</h2>
        <p>Pick a farm. FarmFit reads 30 years of NASA climate data, 55 years of NOAA hurricane tracks,
        the soil map and the terrain. It then compares your current rotation with three alternatives, month by month.</p>
        <span class="fs-chip">🛰️ NASA POWER · SMAP · GPM IMERG · MODIS · SRTM</span>
        <span class="fs-chip">🌀 NOAA HURDAT2</span><span class="fs-chip">🌱 SoilGrids · FAO ECOCROP · FAO-56</span></div>""",
        unsafe_allow_html=True,
    )
    demo_picker()

    lat, lon = ss.farm_latitude, ss.farm_longitude
    with st.spinner("Reading NASA climate history, storm tracks, soil and terrain…"):
        bundle = load_site(lat, lon)

    if "climate" not in bundle:
        st.error("NASA POWER could not be reached for this location and no cached copy exists. "
                 f"Details: {bundle.get('power_meta', {}).get('error', 'unknown')}. Try a demo farm or retry in a minute.")
        return
    if "SYNTHETIC" in str(bundle["power_meta"].get("source", "")):
        st.warning("Running on a synthetic test fixture, not NASA data (offline development mode).")

    tabs = st.tabs(["① Farm profile", "② Field shift", "③ Compare rotations", "④ Hurricane stress test", "⑤ Storm water bank"])
    with tabs[0]:
        render_profile(bundle)
    with tabs[1]:
        render_shift(bundle)
    with tabs[2]:
        render_strategies(bundle)
    with tabs[3]:
        render_stress(bundle)
    with tabs[4]:
        render_water_bank(bundle)


def render_profile(bundle):
    ss = st.session_state
    lat, lon = bundle["lat"], bundle["lon"]
    clim, summ = bundle["climate"], bundle["storm_summary"]
    soil, terr = bundle.get("soil") or {}, bundle.get("terrain") or {}
    key, demo = current_demo()
    if demo:
        st.markdown(f"**{demo['label']}**: {demo['story']}")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("Rain per year", f"{clim['rain_mm'].sum():,.0f} mm",
                  f"Wettest month {clim.loc[clim['rain_mm'].idxmax(), 'label']} · NASA POWER {bundle['climate_period']}", "🌧️")
    with c2:
        rp = summ["return_period_storm_force"]
        stat_card("Storm-force wind at farm", f"1 in {rp:.0f} yrs" if rp else "Not since 1971",
                  f"{summ['storm_force_events']} events {summ['period']} · peak {', '.join(summ['peak_months']) or '-'}", "🌀")
    with c3:
        ph = soil.get("ph")
        stat_card("Topsoil", f"pH {ph:.1f}" if ph else "No soil data",
                  f"{soil.get('texture') or 'texture n/a'} · OM {soil.get('organic_matter_pct') or '-'}% · drainage {soil.get('drainage') or '-'}", "🪨")
    with c4:
        sl = terr.get("slope_pct")
        elev = terr.get("elevation_m")
        stat_card("Terrain", f"{elev:.0f} m" if elev is not None else "No terrain data",
                  f"Slope {sl if sl is not None else '-'}% · {soil_terrain.slope_class(sl)}", "⛰️")

    st.markdown("#### Where the storms came from")
    left, right = st.columns([1.6, 1])
    with left:
        storm_dates = {f"{r['name'].title()} {r['year']}": r["time"].date().isoformat() for _, r in bundle["impacts"].head(6).iterrows()}
        choice = st.selectbox("Satellite layer date (open the layer menu on the map to switch NASA layers)",
                              ["3 days ago"] + list(storm_dates.keys()), key="profile_map_date")
        date_str = None if choice == "3 days ago" else storm_dates[choice]
        clicked = make_map(lat, lon, bundle["impacts"], date_str=date_str, key="profile_map",
                           show_layer="IMERG_Precipitation_Rate" if date_str else None)
        if clicked and clicked.get("last_clicked"):
            nl, ng = round(clicked["last_clicked"]["lat"], 4), round(clicked["last_clicked"]["lng"], 4)
            if abs(nl - lat) > 1e-3 or abs(ng - lon) > 1e-3:
                ss.farm_latitude, ss.farm_longitude = nl, ng
                ss.fs_demo = None
                ss.pop("fs_plans", None)
                st.rerun()
    with right:
        top = bundle["impacts"].head(8).copy()
        if len(top):
            top["Storm"] = top["name"].str.title() + " " + top["year"].astype(str)
            top["Wind at farm"] = top["site_wind_kt"].round(0).astype(int).astype(str) + " kt"
            top["Category at farm"] = top["site_category"]
            top["Closest"] = top["closest_km"].round(0).astype(int).astype(str) + " km"
            st.dataframe(top[["Storm", "Wind at farm", "Category at farm", "Closest"]], hide_index=True, use_container_width=True)
        st.caption("Wind at the farm is estimated from the NOAA track with a modified Rankine vortex "
                   "(radius of maximum wind from HURDAT2, 0.6 decay, ×0.85 land factor). It is an exposure screen, not a forecast.")

    st.markdown("#### Month by month: when is this farm exposed?")
    ex = bundle["exposure"].copy()
    ex["Storm-force wind (≥ 34 kt)"] = ex["p_storm_force"]
    ex["Hurricane-force wind (≥ 64 kt)"] = ex["p_hurricane_force"]
    ex["Day with ≥ 50 mm rain"] = clim["p_heavy_rain"].to_numpy()
    long = ex.melt(id_vars=["label", "month"], value_vars=["Storm-force wind (≥ 34 kt)", "Hurricane-force wind (≥ 64 kt)", "Day with ≥ 50 mm rain"],
                   var_name="Hazard", value_name="Chance in a given year")
    chart = alt.Chart(long).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("label:N", sort=MONTHS, title=None, axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("Hazard:N", sort=["Storm-force wind (≥ 34 kt)", "Hurricane-force wind (≥ 64 kt)", "Day with ≥ 50 mm rain"]),
        y=alt.Y("Chance in a given year:Q", axis=alt.Axis(format="%")),
        color=alt.Color("Hazard:N", scale=alt.Scale(
            domain=["Storm-force wind (≥ 34 kt)", "Hurricane-force wind (≥ 64 kt)", "Day with ≥ 50 mm rain"],
            range=["#3a86ff", "#c1121f", "#2a9d8f"]), legend=alt.Legend(orient="bottom", labelLimit=260)),
        tooltip=["label", "Hazard", alt.Tooltip("Chance in a given year:Q", format=".0%")],
    ).properties(height=260)
    st.altair_chart(chart, use_container_width=True)

    with st.expander("🛂 Data passport: every dataset behind this profile"):
        st.dataframe(data_passport(bundle), hide_index=True, use_container_width=True)
        st.caption("Satellite and reanalysis cells are much larger than a farm. Treat these as the regional backdrop "
                   "and correct the soil values below if you have a soil test.")

    key, _ = current_demo()
    pulse = satellite_pulse(key) if key else {}
    if pulse:
        st.markdown("#### Satellite pulse: the last few years at this farm")
        cols = st.columns(len(pulse))
        specs = {
            "smap": ("SMAP soil moisture (m³/m³)", "#8C6A43"),
            "ndvi": ("MODIS NDVI (greenness)", "#2F7D32"),
            "imerg": ("GPM IMERG daily rain (mm)", "#1d70b8"),
        }
        for col, (k, series) in zip(cols, pulse.items()):
            title, color = specs[k]
            d = series.reset_index()
            d.columns = ["date", "value"]
            mark = alt.Chart(d).mark_bar(color=color) if k == "imerg" else alt.Chart(d).mark_line(color=color, strokeWidth=1.6)
            with col:
                st.altair_chart(mark.encode(x=alt.X("date:T", title=None), y=alt.Y("value:Q", title=None),
                                            tooltip=["date:T", alt.Tooltip("value:Q", format=".2f")])
                                .properties(height=170, title=title), use_container_width=True)


def render_shift(bundle):
    shift, season = bundle["shift"], bundle["season"]
    then, now = bundle["shift_periods"]
    st.markdown(f"#### Your grandparents' calendar vs today's: {then} compared with {now}")
    st.caption("Same farm, same NASA POWER grid cell, two 15-year windows. 'Clear' means the 30-year trend is at least twice its standard error.")
    cols = st.columns(3)
    for i, row in shift.reset_index(drop=True).iterrows():
        arrow = "▲" if row["change"] > 0 else "▼"
        fmt = "{:,.1f}" if abs(row["now"]) < 100 else "{:,.0f}"
        with cols[i % 3]:
            stat_card(row["indicator"], f"{fmt.format(row['now'])} {row['unit']}",
                      f"{arrow} {fmt.format(abs(row['change']))} vs {fmt.format(row['then'])} · trend {row['signal']}")
            st.write("")

    chart = alt.Chart(season).mark_line(point=True, strokeWidth=3).encode(
        x=alt.X("label:N", sort=MONTHS, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("PRECTOTCORR:Q", title="Mean monthly rain (mm)"),
        color=alt.Color("period:N", title="Period", scale=alt.Scale(range=["#adb5bd", "#1d6f5f"])),
        tooltip=["period", "label", alt.Tooltip("PRECTOTCORR:Q", format=".0f")],
    ).properties(height=280)
    st.altair_chart(chart, use_container_width=True)

    dec = bundle["storm_summary"]["decade_counts"]
    decades = list(range(1970, 2030, 10))
    d = pd.DataFrame({"Decade": [f"{k}s" for k in decades], "Events": [int(dec.get(k, 0)) for k in decades]})
    st.altair_chart(
        alt.Chart(d, title="NOAA HURDAT2: storm-force wind events at this farm, by decade").mark_bar(
            color="#13315c", cornerRadiusTopLeft=5, cornerRadiusTopRight=5, size=46).encode(
            x=alt.X("Decade:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Events:Q", title="Events", axis=alt.Axis(tickMinStep=1)),
            tooltip=["Decade", "Events"]).properties(height=220),
        use_container_width=True)
    st.markdown('<div class="fs-note">Why this matters: rotations handed down between generations were tuned to the old pattern. '
                'When heavy-rain days, hot days or storm months shift, the same calendar leaves crops at their most fragile stage in the riskiest weeks.</div>',
                unsafe_allow_html=True)


def rotation_editor(crops):
    ss = st.session_state
    st.markdown("##### 🧑🏾‍🌾 Your current rotation")
    st.caption("The demo farms load a typical example. Change it to match what you actually grow.")
    rows = list(ss.fs_current)
    new_rows = []
    crop_names = list(crops.index)
    for i in range(4):
        default = rows[i] if i < len(rows) else None
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            crop = st.selectbox(f"Crop {i + 1}", ["(none)"] + crop_names,
                                index=(crop_names.index(default[0]) + 1) if default and default[0] in crop_names else 0,
                                key=f"cur_crop_{i}_{ss.get('fs_demo')}")
        with c2:
            start = st.selectbox("Plant in", MONTHS, index=(default[1] - 1) if default else 0, key=f"cur_start_{i}_{ss.get('fs_demo')}")
        with c3:
            months = st.number_input("Months", 1, 12, value=default[2] if default else int(crops.loc[crop, "months"]) if crop != "(none)" else 3,
                                     key=f"cur_len_{i}_{ss.get('fs_demo')}")
        if crop != "(none)":
            new_rows.append((crop, MONTHS.index(start) + 1, int(months)))
    if new_rows != rows:
        ss.fs_current = new_rows
        ss.pop("fs_plans", None)
    return [planner.Planting(c, s, m) for c, s, m in ss.fs_current]


@st.cache_data(show_spinner=False, ttl=3600)
def cached_strategies(lat, lon, wet_field, irrigation, exclude, ph_override, drainage_override):
    bundle = load_site(lat, lon)
    site = build_site(bundle, {"ph": ph_override, "drainage": drainage_override})
    crops = planner.load_crops()
    allowed = planner.allowed_crops(crops, wet_field=wet_field, exclude=list(exclude))
    plans = planner.generate_strategies(site, crops, allowed, irrigation=irrigation)
    meta = plans.pop("_meta", {})
    return plans, meta


def get_plans(bundle):
    ss = st.session_state
    crops = planner.load_crops()
    ov = ss.get("fs_soil_override", {})
    plans, meta = cached_strategies(bundle["lat"], bundle["lon"], ss.fs_wet_field, ss.fs_irrigation,
                                    tuple(sorted(ss.get("fs_exclude", []))), ov.get("ph"), ov.get("drainage"))
    site = build_site(bundle, ov)
    current = planner.evaluate_current(site, crops, [planner.Planting(c, s, m) for c, s, m in ss.fs_current])
    return site, crops, current, plans, meta


PRIORITY_TO_KEY = {"Survive storms": "storm", "Rebuild my soil": "soil", "Save water": "water"}


def render_strategies(bundle):
    ss = st.session_state
    crops = planner.load_crops()
    with st.container(border=True):
        left, right = st.columns([1.35, 1])
        with left:
            rotation_editor(crops)
        with right:
            st.markdown("##### 🎯 Your priorities and limits")
            ss.fs_priority = st.radio("What matters most this year?", list(PRIORITY_TO_KEY), horizontal=True,
                                      index=list(PRIORITY_TO_KEY).index(ss.get("fs_priority", "Survive storms")))
            ss.fs_irrigation = st.selectbox("Water for irrigation", list(planner.IRRIGATION_LIMITS),
                                            index=list(planner.IRRIGATION_LIMITS).index(ss.fs_irrigation))
            ss.fs_wet_field = st.toggle("I have a low-lying field with managed water (allows rice and dasheen)", value=ss.fs_wet_field)
            ss.fs_exclude = st.multiselect("Crops I can't grow or sell", list(crops.index), default=ss.get("fs_exclude", []))
            with st.expander("Correct the soil (from a soil test)"):
                soil = bundle.get("soil") or {}
                ph = st.number_input("Soil pH", 3.5, 9.5, value=float(soil.get("ph") or 6.5), step=0.1)
                drainage = st.selectbox("Drainage", ["Fast", "Good", "Moderate", "Slow", "Very slow"],
                                        index=["Fast", "Good", "Moderate", "Slow", "Very slow"].index(soil.get("drainage") or "Moderate"))
                ss.fs_soil_override = {"ph": ph, "drainage": drainage}

    with st.spinner("Searching every 12-month rotation of up to four crops…"):
        site, crops, current, plans, meta = get_plans(bundle)
    if not plans:
        st.warning("No rotation fits these limits. Allow more crops or more irrigation.")
        return
    pick = PRIORITY_TO_KEY[ss.fs_priority]
    ordered = [current] + [plans[k] for k in ("storm", "soil", "water") if k in plans]

    st.markdown(f"#### Four calendars, same rules · {meta.get('candidates', 0):,} rotations searched")
    key, demo = current_demo()
    storm_month = None
    if demo:
        hit = bundle["impacts"][(bundle["impacts"]["name"] + " " + bundle["impacts"]["year"].astype(str)) == demo["storm"]]
        if len(hit):
            storm_month = int(hit.iloc[0]["month"])
    st.markdown(calendar_html(ordered, site, crops, storm_month=storm_month), unsafe_allow_html=True)
    st.caption("Striped = bare soil. Top row = chance per year of storm-force wind or a waterlogging rain day (NOAA HURDAT2 + NASA POWER). "
               + (f"Red outline = month {demo['storm'].title()} struck." if storm_month else ""))

    cols = st.columns(len(ordered))
    for col, plan in zip(cols, ordered):
        with col:
            badge = ""
            if plan.key == pick:
                badge = '<span class="fs-badge fs-best">★ Best for your priority</span>'
            elif plan.key == "current":
                badge = '<span class="fs-badge fs-cur">Today</span>'
            m = plan.metrics
            st.markdown(
                f'<div class="fs-card"><h4>{plan.icon} {plan.title}</h4>{badge}'
                f'<div class="fs-sub" style="margin:.35rem 0 .6rem 0">{plan.tagline}</div>'
                f'{score_bars(plan.scores)}'
                f'<div class="fs-note">Expected storm/flood harvest loss <b>{m["expected_loss"]:.0%}</b> · '
                f'bare months <b>{m["bare_months"]}</b> · legume months <b>{m["legume_months"]}</b> · '
                f'irrigation ≈ <b>{m["irrigation_mm"]:.0f} mm</b></div></div>',
                unsafe_allow_html=True,
            )
            ex = planner.explain(plan, site, crops, current=current)
            with st.expander("Why · evidence · gaps"):
                st.markdown(f"**Why suggested.** {ex['why']}")
                st.markdown("**Benefits**\n" + "\n".join(f"- {b}" for b in ex["benefits"]))
                st.markdown("**Evidence**\n" + "\n".join(f"- {b}" for b in ex["evidence"]))
                st.markdown("**Information gaps**\n" + "\n".join(f"- {b}" for b in ex["gaps"]))
                st.markdown("**Check locally before planting**\n" + "\n".join(f"- {b}" for b in ex["review"]))

    best = plans.get(pick)
    if best:
        st.markdown("#### Take the plan with you")
        lines = [f"FarmFit · Hurricane to Harvest. {best.title} rotation for {bundle['lat']:.3f}, {bundle['lon']:.3f}"]
        for p in best.plantings:
            months = p.month_list()
            lines.append(f"- {p.crop}: plant {MONTHS[months[0] - 1]}, harvest about {MONTHS[months[-1] - 1]}")
        lines.append(f"Expected storm/flood harvest loss {best.metrics['expected_loss']:.0%} vs {current.metrics['expected_loss']:.0%} for my current rotation.")
        lines.append("Built with NASA POWER, NOAA HURDAT2, SoilGrids, FAO data. Check with your extension officer before planting.")
        text = "\n".join(lines)
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("⬇️ Download plan (text, works offline)", text, file_name="farmfit_storm_plan.txt", use_container_width=True)
        with d2:
            st.link_button("📲 Share on WhatsApp", f"https://wa.me/?text={quote(text)}", use_container_width=True)


def render_stress(bundle):
    ss = st.session_state
    site, crops, current, plans, _ = get_plans(bundle)
    if not plans:
        st.info("Build the rotations in tab ③ first.")
        return
    allplans = {"current": current, **plans}
    impacts = bundle["impacts"]
    key, demo = current_demo()

    st.markdown("#### Replay a real storm on each calendar")
    named = impacts[impacts["site_wind_kt"] >= 25].head(15)
    if named.empty:
        st.info("No storm since 1950 brought strong wind to this farm in the NOAA record. Heavy rain is the main hazard here; see the simulation below.")
    else:
        labels = [f"{r['name'].title()} {r['year']} · ≈{r['site_wind_kt']:.0f} kt at farm ({r['site_category']})" for _, r in named.iterrows()]
        default = 0
        if demo:
            for i, (_, r) in enumerate(named.iterrows()):
                if f"{r['name']} {r['year']}" == demo["storm"]:
                    default = i
        choice = st.selectbox("Storm", labels, index=default)
        storm = named.iloc[labels.index(choice)]
        st.markdown(f"**{storm['name'].title()}** reached this farm on **{storm['time']:%d %b %Y}**: "
                    f"about **{storm['site_wind_kt']:.0f} kt** sustained wind ({storm['site_category']}), "
                    f"closest approach {storm['closest_km']:.0f} km while the storm itself was {storm['storm_category']}.")
        cols = st.columns(len(allplans))
        for col, (k, plan) in zip(cols, allplans.items()):
            r = planner.replay_storm(plan, crops, storm["time"], storm["site_wind_kt"])
            with col:
                if r["bare"]:
                    body = "Field was <b>bare</b>: no harvest at risk, but bare soil erodes in storm rain."
                    big = "–"
                elif r.get("cover_crop"):
                    body = f"<b>{r['crop']}</b> cover crop ({r['stage']}): no harvest at risk; it holds the soil."
                    big = "0%"
                else:
                    body = f"<b>{r['crop']}</b> at the <b>{r['stage']}</b> stage."
                    big = f"{r['loss']:.0%}"
                st.markdown(f'<div class="fs-card"><div class="fs-label">{plan.icon} {plan.title}</div>'
                            f'<div class="fs-stat">{big}</div><div class="fs-sub">estimated loss of that crop</div>'
                            f'<div class="fs-note">{body}</div></div>', unsafe_allow_html=True)
        st.markdown("")
        st.markdown(calendar_html(list(allplans.values()), site, crops, storm_month=int(storm["month"])), unsafe_allow_html=True)

    st.markdown("#### Simulate 5,000 storm seasons")
    st.caption("Each simulated year draws storms and heavy-rain days month by month from this farm's own history "
               "(NOAA HURDAT2 1971-2025, NASA POWER). Use the sliders to test a stormier or wetter future.")
    s1, s2 = st.columns(2)
    with s1:
        storm_mult = st.slider("Storm frequency vs history", 0.5, 2.0, 1.0, 0.1, format="%.1f×")
    with s2:
        rain_mult = st.slider("Heavy-rain days vs history", 0.5, 2.0, 1.0, 0.1, format="%.1f×")
    mc = planner.monte_carlo(site, allplans, crops, n_years=5000, storm_multiplier=storm_mult, rain_multiplier=rain_mult)
    rows = []
    for k, plan in allplans.items():
        r = mc[k]
        rows.append({"Rotation": f"{plan.icon} {plan.title}", "Average loss": r["expected_loss"],
                     "Bad year (1 in 10)": r["bad_year_loss"], "Chance of losing > half": r["p_loss_over_50"]})
    df = pd.DataFrame(rows)
    long = df.melt(id_vars="Rotation", var_name="Measure", value_name="Share of harvest")
    st.altair_chart(
        alt.Chart(long).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("Rotation:N", title=None, sort=None, axis=alt.Axis(labelAngle=0)),
            xOffset="Measure:N",
            y=alt.Y("Share of harvest:Q", axis=alt.Axis(format="%")),
            color=alt.Color("Measure:N", scale=alt.Scale(range=["#f4a261", "#c1121f", "#6d597a"]), legend=alt.Legend(orient="bottom")),
            tooltip=["Rotation", "Measure", alt.Tooltip("Share of harvest:Q", format=".1%")],
        ).properties(height=300),
        use_container_width=True,
    )
    best = min(plans.values(), key=lambda p: mc[p.key]["expected_loss"])
    cur = mc["current"]
    st.success(f"In {5000:,} simulated seasons, **{best.title}** loses on average **{mc[best.key]['expected_loss']:.0%}** of its harvest "
               f"vs **{cur['expected_loss']:.0%}** for your current rotation. In a bad (1-in-10) year that is "
               f"**{mc[best.key]['bad_year_loss']:.0%}** vs **{cur['bad_year_loss']:.0%}**.")
    st.markdown('<div class="fs-note">This is an exposure model: it shows which calendars put fragile crop stages in risky months. '
                'It does not predict when the next storm will hit. Vulnerability values are heuristics to be validated with local agronomists.</div>',
                unsafe_allow_html=True)


def render_water_bank(bundle):
    """Link to the IFRS project: harvest storm rain in tanks, release before storms."""
    clim = bundle["climate"]
    site, crops, current, plans, _ = get_plans(bundle)
    st.markdown("#### Storm water bank: catch the wet-season rain, use it in the dry season")
    st.caption("From our IFRS flood-resilience project: rooftop or shed tanks with a slow-release valve. "
               "They cut runoff during storms and feed drip irrigation when the rains stop.")
    c1, c2, c3 = st.columns(3)
    with c1:
        roof = st.number_input("Catchment area (roof / shed / tunnel), m²", 10, 5000, 150, 10)
    with c2:
        field_m2 = st.number_input("Field area to irrigate, m²", 50, 50000, 2000, 50)
    with c3:
        plan_key = st.selectbox("Rotation", ["current"] + [k for k in ("storm", "soil", "water") if k in plans],
                                format_func=lambda k: "Your current rotation" if k == "current" else plans[k].title)
    plan = current if plan_key == "current" else plans[plan_key]
    catch = clim["rain_mm"].to_numpy() * roof * 0.8 / 1000  # m3 per month
    need = np.zeros(12)
    for opt in plan.metrics.get("option_rows", []):
        # monthly deficit for this planting = Kc*ET0 - 0.8 P over its months
        row = crops.loc[opt["crop"]]
        for k, mth in enumerate(planner.Planting(opt["crop"], opt["start"], opt["months"]).month_list()):
            stage = planner.stage_for(k, opt["months"])
            kc = {"seedling": row.kc_ini, "vegetative": (row.kc_ini + row.kc_mid) / 2,
                  "reproductive": row.kc_mid, "mature": row.kc_end}[stage]
            need[mth - 1] += max(0.0, kc * site.et0[mth - 1] - 0.8 * site.rain[mth - 1]) * field_m2 / 1000 / 0.9
    storage, peak = 0.0, 0.0
    for _ in range(2):  # two passes to settle the cycle
        storage = 0.0
        series = []
        for m in range(12):
            storage = max(0.0, storage + catch[m] - need[m])
            series.append(storage)
        peak = max(series)
    supplied = np.minimum(need, catch + np.roll(np.array(series), 1))
    share = supplied.sum() / need.sum() if need.sum() > 0 else 1.0
    m1, m2, m3 = st.columns(3)
    with m1:
        stat_card("Rain you could catch", f"{catch.sum():,.0f} m³/yr", "80% runoff coefficient", "🛢️")
    with m2:
        stat_card("Irrigation need", f"{need.sum():,.0f} m³/yr", "FAO-56 Kc × ET0 minus effective rain, 90% drip efficiency", "💧")
    with m3:
        stat_card("Tank size to bank it", f"{min(peak, need.sum()):,.0f} m³", f"covers ≈ {min(share, 1):.0%} of the need", "🏗️")
    d = pd.DataFrame({"label": MONTHS, "Rain caught (m³)": catch, "Irrigation need (m³)": need})
    st.altair_chart(
        alt.Chart(d.melt("label", var_name="Flow", value_name="m³")).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("label:N", sort=MONTHS, title=None, axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("Flow:N", sort=["Rain caught (m³)", "Irrigation need (m³)"]), y="m³:Q",
            color=alt.Color("Flow:N", scale=alt.Scale(domain=["Rain caught (m³)", "Irrigation need (m³)"], range=["#1d70b8", "#e76f51"]),
                            legend=alt.Legend(orient="bottom"))
        ).properties(height=240), use_container_width=True)
    st.markdown('<div class="fs-note">IFRS release rule, adapted: when a storm or ≥ 50 mm day is forecast, open the slow-release valve '
                'early to free space. Never release while the downstream drain is already high.</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# VIEW: After the storm
# ---------------------------------------------------------------------------

def gemini_key():
    try:
        key = st.secrets.get("GEMINI_API_KEY")
    except Exception:  # noqa: BLE001 - no secrets file
        key = None
    return key or os.environ.get("GEMINI_API_KEY")


def gemini_model():
    try:
        return st.secrets.get("GEMINI_MODEL")
    except Exception:  # noqa: BLE001
        return os.environ.get("GEMINI_MODEL")


def render_after_storm():
    inject_css()
    ensure_state()
    ss = st.session_state
    st.markdown(
        """<div class="fs-hero" style="background:linear-gradient(120deg,#3d1f0b 0%,#7f4f24 45%,#386641 100%)">
        <div class="fs-kicker">After the storm</div>
        <h2>Photograph the field. Get a safe, staged path back to harvest.</h2>
        <p>AI describes what the photo shows. NASA rain and soil-moisture data add context. Clear rules decide what is safe,
        and the farmer confirms anything a photo cannot show.</p></div>""",
        unsafe_allow_html=True,
    )
    demo_picker()
    lat, lon = ss.farm_latitude, ss.farm_longitude
    bundle = load_site(lat, lon)

    left, right = st.columns([1, 1])
    with left:
        st.markdown("##### 1 · Field photo")
        src = st.radio("Photo source", ["Upload", "Camera"], horizontal=True, label_visibility="collapsed")
        photo = st.camera_input("Take a field photo") if src == "Camera" else st.file_uploader("Upload a field photo", type=["jpg", "jpeg", "png", "webp"])
        ai = ss.get("fs_ai")
        if photo is not None:
            st.image(photo, use_container_width=True)
            key = gemini_key()
            if st.button("🔎 Analyse photo with AI", type="primary", use_container_width=True, disabled=not key):
                with st.spinner("Gemini is describing the visible field conditions…"):
                    res = recovery.assess_photo(photo.getvalue(), photo.type, key, model=gemini_model())
                ss.fs_ai = res if res.get("ok") else None
                if not res.get("ok"):
                    st.error(f"AI analysis unavailable: {res.get('error')}. Use the checklist on the right.")
                ai = ss.get("fs_ai")
            if not key:
                st.caption("Add GEMINI_API_KEY to Streamlit secrets to enable AI photo analysis. The checklist works without it.")
        if ai:
            r = ai["result"]
            st.markdown(
                f'<div class="fs-card"><div class="fs-label">AI sees ({ai["model"]}, confidence {r.get("confidence", 0):.0%})</div>'
                f'<div class="fs-sub">Standing water: <b>{r.get("standing_water")}</b> · bare soil <b>{r.get("bare_soil_percent")}%</b> · '
                f'erosion <b>{r.get("erosion")}</b> · debris <b>{r.get("sediment_or_debris")}</b> · plants lodged/broken <b>{r.get("plants_lodged_or_broken")}</b></div>'
                f'<div class="fs-note">{r.get("visible_notes", "")}<br/>Can\'t tell from the photo: {", ".join(r.get("cannot_tell_from_photo", [])) or "-"}</div></div>',
                unsafe_allow_html=True)

    with right:
        st.markdown("##### 2 · Confirm what a photo can't show")
        ai_r = (ai or {}).get("result", {})
        days = st.slider("Days water stood on the field", 0, 14, 2 if ai_r.get("standing_water") in ("puddles", "widespread") else 0)
        source = st.selectbox("Where did the water come from?", ["Rain only", "River or drain overflow", "Sewage / septic", "Livestock area", "Industrial / unknown"])
        contact = st.radio("Did floodwater touch the part of the crop you eat?", ["No", "Yes", "Not sure"], horizontal=True)
        washed = st.checkbox("Soil washed away / gullies formed", value=ai_r.get("erosion") in ("rills", "gullies"))
        debris = st.checkbox("Heavy debris or silt deposited", value=ai_r.get("sediment_or_debris") == "heavy")
        _, demo = current_demo()
        default_date = demo["storm_date"] if demo else date.today() - timedelta(days=5)
        storm_date = st.date_input("When did the storm pass?", value=default_date, key=f"storm_date_{ss.get('fs_demo')}")

    recent, rmeta = power.fetch_window(lat, lon, end_date=storm_date + timedelta(days=3), days=17)
    rain14 = wet = None
    if recent is not None and "PRECTOTCORR" in recent:
        r = recent.dropna(subset=["PRECTOTCORR"])
        rain14 = float(r["PRECTOTCORR"].tail(14).sum()) if len(r) else None
        if "GWETROOT" in recent and recent["GWETROOT"].notna().any():
            wet = float(recent["GWETROOT"].dropna().iloc[-1])

    st.markdown("##### 3 · Satellite context")
    c1, c2 = st.columns([1, 1.4])
    with c1:
        stat_card("Rain in the 14 days to the storm", f"{rain14:.0f} mm" if rain14 is not None else "n/a", "NASA POWER daily (3 days after included)", "🌧️")
        st.write("")
        stat_card("Root-zone wetness", f"{wet:.2f}" if wet is not None else "n/a", "0 = dry, 1 = saturated · MERRA-2 via POWER", "🟫")
    with c2:
        make_map(lat, lon, bundle.get("impacts"), date_str=storm_date.isoformat(), height=300, top_storms=3,
                 key="after_map", show_layer="IMERG_Precipitation_Rate")
        st.caption("NASA GIBS layers for the storm date: GPM IMERG rain, SMAP soil moisture, MODIS true colour and NDVI. Switch layers with the menu.")

    state = recovery.field_state(ai_r, {"standing_water_days": days, "water_source": source, "flood_touched_edible": contact,
                                        "soil_washed": washed, "debris": debris},
                                 recent_rain_mm=rain14, soil_wet_root=wet, drainage=(bundle.get("soil") or {}).get("drainage"))
    flag_text = {
        "waterlogged": "💧 Waterlogged", "prolonged_flooding": "🌊 Prolonged flooding", "eroded": "🏜️ Erosion",
        "debris": "🪵 Debris / silt", "crop_damaged": "🥀 Crop damaged", "bare": "🟫 Mostly bare",
        "edible_contact": "⛔ Floodwater on edible crop", "contamination_risk": "☣️ Possible contamination",
        "unknown_contact": "❓ Unsure about flood contact",
    }
    st.markdown("##### 4 · Field condition")
    st.markdown(" ".join(f'<span class="fs-badge" style="background:#f1f3f5">{flag_text.get(f, f)}</span>' for f in state["flags"]) or "No major concerns detected.",
                unsafe_allow_html=True)
    for n in state["notes"]:
        st.caption(n)

    st.markdown("##### 5 · Recovery path")
    stages = recovery.recovery_stages(state, storm_date.month, wet_field=ss.fs_wet_field)
    cols = st.columns(len(stages))
    for col, stg in zip(cols, stages):
        with col:
            actions = "".join(f"<li>{a}</li>" for a in stg["actions"])
            st.markdown(f'<div class="fs-stage"><div class="fs-label">{stg["weeks"]}</div><h4>{stg["icon"]} {stg["title"]}</h4>'
                        f'<ul style="padding-left:1.1rem;font-size:.85rem">{actions}</ul><div class="gate">Move on when: {stg["gate"]}</div></div>',
                        unsafe_allow_html=True)

    if "climate" in bundle:
        start_month = (storm_date.month + 1) % 12 + 1  # about 2 months after the storm
        site = build_site(bundle)
        crops = planner.load_crops()
        allowed = planner.allowed_crops(crops, wet_field=ss.fs_wet_field and "contamination_risk" not in state["flags"])
        if "contamination_risk" in state["flags"] or "edible_contact" in state["flags"]:
            allowed = [c for c in allowed if c not in ("Pak Choi", "Callaloo", "Cabbage")]
        plans = planner.generate_strategies(site, crops, allowed, fixed_start=start_month, irrigation=ss.fs_irrigation)
        plans.pop("_meta", None)
        rec = plans.get("storm") or plans.get("soil")
        if rec:
            rec.title, rec.icon = "Recovery calendar", "🔁"
            st.markdown(f"**Recovery rotation starting {MONTHS[start_month - 1]}** (after drainage and a cover crop), "
                        "ranked Storm-smart so harvests land before the next peak months:")
            st.markdown(calendar_html([rec], site, crops), unsafe_allow_html=True)
            st.markdown(score_bars(rec.scores), unsafe_allow_html=True)
    st.markdown('<div class="fs-warn">⚠️ FarmFit supports, not replaces, local expertise. Food-safety decisions after flooding '
                'should be confirmed with your Ministry of Agriculture extension officer.</div>', unsafe_allow_html=True)
