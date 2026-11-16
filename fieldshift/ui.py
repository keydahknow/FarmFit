"""Streamlit views for FarmFit · Hurricane to Harvest (almanac edition).

Five sections, one farm picker:
  Plan my season   rotation comparison
  Water watch      drought / rain vs normal, 7-day outlook, water bank, field shift
  Storm ready      live storm watch + checklist, exposure, stress test
  After a storm    photo assessment and staged recovery
  Data & method    every dataset, how it is used, limits
"""

import json
import os
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

import altair as alt
import folium
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from . import alerts, art, assistant, enso, journey, market, planner, poster, power, recovery, sensor, soil_terrain, storms, stormwatch, water
from .i18n import LANGS, month as mname, t

MONTHS = planner.MONTHS
CACHE_DIR = power.CACHE_DIR

FARMS = {
    "jamaica": {
        "label": "St Elizabeth, Jamaica",
        "story": "Jamaica's breadbasket parish. Category 5 Hurricane Melissa crossed it on 28 Oct 2025.",
        "lat": 18.05, "lon": -77.72,
        "current": [("Watermelon", 6, 3), ("Sweet Pepper", 9, 4)],
        "storm": "MELISSA 2025", "storm_date": date(2025, 10, 28),
        "wet_field": False, "irrigation": "Limited irrigation",
    },
    "trinidad": {
        "label": "Caroni plains, Trinidad",
        "story": "Low-lying farmland where rain, flooding and dry-season drought matter more than wind.",
        "lat": 10.60, "lon": -61.38,
        "current": [("Corn", 6, 3), ("Tomato", 9, 4)],
        "storm": "BRET 1993", "storm_date": date(1993, 8, 7),
        "wet_field": True, "irrigation": "No irrigation",
    },
}
CUSTOM = "custom"

GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{layer}/default/{date}/GoogleMapsCompatible_Level{level}/{{z}}/{{y}}/{{x}}.{ext}"
GIBS_LAYERS = [
    ("MODIS_Terra_CorrectedReflectance_TrueColor", "MODIS true colour", 9, "jpg"),
    ("MODIS_Terra_NDVI_8Day", "MODIS NDVI (greenness)", 9, "png"),
    ("SMAP_L4_Analyzed_Surface_Soil_Moisture", "SMAP soil moisture", 6, "png"),
    ("IMERG_Precipitation_Rate", "GPM IMERG rain rate", 6, "png"),
    ("MODIS_Combined_Flood_2-Day", "MODIS flood water (2-day)", 9, "png"),
    ("OPERA_L3_Dynamic_Surface_Water_Extent-Sentinel-1", "OPERA surface water (Sentinel-1 radar, sees through cloud)", 12, "png"),
]
CAT_COLORS = {"Cat 5": "#6b1d0f", "Cat 4": "#9b2f17", "Cat 3": art.TERRA, "Cat 2": "#d9743b",
              "Cat 1": art.OCHRE, "Tropical storm": art.SEA, "Below storm force": "#9aa3ad", "Unknown": "#9aa3ad"}


def setup_page():
    st.markdown(art.CSS, unsafe_allow_html=True)
    art.register_chart_theme()
    ss = st.session_state
    ss.setdefault("fs_demo", "jamaica")
    ss.setdefault("farm_latitude", FARMS["jamaica"]["lat"])
    ss.setdefault("farm_longitude", FARMS["jamaica"]["lon"])
    ss.setdefault("fs_current", list(FARMS["jamaica"]["current"]))
    ss.setdefault("fs_wet_field", FARMS["jamaica"]["wet_field"])
    ss.setdefault("fs_irrigation", FARMS["jamaica"]["irrigation"])
    ss.setdefault("fs_priority", "Survive storms")
    if "fs_lang" not in ss and st.query_params.get("lang") in LANGS:
        ss.fs_lang = st.query_params.get("lang")
    ss.setdefault("fs_lang", "en")
    ss.setdefault("fs_chat", [])


def L():
    return st.session_state.get("fs_lang", "en")


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def manifest():
    try:
        return json.loads((CACHE_DIR / "manifest.json").read_text())
    except Exception:  # noqa: BLE001
        return {}


def freshness(name):
    entry = manifest().get("datasets", {}).get(name)
    if not entry or entry.get("status") not in ("ok", "partial"):
        return None
    try:
        days = (datetime.now(timezone.utc) - datetime.fromisoformat(entry["updated"])).days
        return "refreshed today" if days == 0 else f"refreshed {days} day{'s' if days != 1 else ''} ago"
    except Exception:  # noqa: BLE001
        return None


def satellite_pulse(farm_id):
    out = {}
    path = CACHE_DIR / "appeears_points.csv"
    if farm_id and path.exists():
        df = pd.read_csv(path)
        df["date"] = pd.to_datetime(df["date"], format="mixed")
        df = df[df["id"] == farm_id]
        for key, pattern in (("smap", "AM_soil_moisture"), ("rootzone", "sm_rootzone$"), ("ndvi", "NDVI"),
                             ("et", r"(?:^|_)ET_500m$"), ("pet", "PET_500m")):
            part = df[df["layer"].str.contains(pattern, case=False, regex=True)]
            if len(part):
                out[key] = part.set_index("date")["value"].sort_index()
    ip = CACHE_DIR / f"imerg_{farm_id}.csv"
    if farm_id and ip.exists():
        im = pd.read_csv(ip)
        im["date"] = pd.to_datetime(im["date"], format="mixed")
        out["imerg"] = im.set_index("date")["imerg_mm"].sort_index()
    return out


@st.cache_data(ttl=86400, show_spinner=False)
def load_site(lat, lon):
    lat, lon = round(lat, 3), round(lon, 3)
    bundle = {"lat": lat, "lon": lon}
    df, meta = power.fetch_daily(lat, lon)
    bundle["power_meta"] = meta
    if df is not None:
        df = power.add_et0(df, lat)
        bundle["daily"] = df
        bundle["climate"] = power.monthly_climate(df)
        shift, annual, season = power.climate_shift(df)
        bundle["shift"], bundle["season"] = shift, season
        bundle["shift_periods"] = (shift.attrs["then"], shift.attrs["now"])
        bundle["climate_period"] = bundle["climate"].attrs["period"]
    impacts = storms.storm_impacts(lat, lon)
    bundle["impacts"] = impacts
    bundle["exposure"] = storms.monthly_exposure(impacts)
    bundle["storm_summary"] = storms.exposure_summary(impacts)
    bundle["soil"] = soil_terrain.get_soil(lat, lon)
    bundle["terrain"] = soil_terrain.get_terrain(lat, lon)
    return bundle


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def load_recent(lat, lon, day_key):
    df, _ = power.fetch_window(round(lat, 3), round(lon, 3), end_date=date.fromisoformat(day_key), days=120)
    return df


@st.cache_data(ttl=3 * 3600, show_spinner=False)
def load_forecast(lat, lon, day_key):
    return water.forecast(lat, lon)


@st.cache_data(ttl=900, show_spinner=False)
def load_active_storms(slot):
    return stormwatch.active_storms()


def build_site(bundle, soil_override=None):
    soil = dict(bundle.get("soil") or {})
    if soil_override:
        soil.update({k: v for k, v in soil_override.items() if v is not None})
    terrain = dict(bundle.get("terrain") or {})
    terrain["s_factor"] = soil_terrain.erosion_slope_factor(terrain.get("slope_pct"))
    return planner.Site(bundle["climate"], bundle["exposure"], soil=soil, terrain=terrain)


def current_farm():
    ss = st.session_state
    f = FARMS.get(ss.get("fs_demo"))
    if f and abs(f["lat"] - ss.farm_latitude) < 0.05 and abs(f["lon"] - ss.farm_longitude) < 0.05:
        return ss.fs_demo, f
    return None, None


def farm_label(bundle):
    _, f = current_farm()
    return f["label"] if f else f"{bundle['lat']:.3f}, {bundle['lon']:.3f}"


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


def in_field(plan, month):
    slot = plan.occupancy()[month - 1]
    return slot if slot else (None, None)


# ---------------------------------------------------------------------------
# Landing: pick the farm first
# ---------------------------------------------------------------------------

GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"


@st.cache_data(ttl=86400, show_spinner=False)
def geocode(name):
    try:
        import requests
        r = requests.get(GEOCODE, params={"name": name, "count": 6, "language": "en", "format": "json"}, timeout=10)
        r.raise_for_status()
        return [{"label": ", ".join(x for x in (g.get("name"), g.get("admin1"), g.get("country")) if x),
                 "lat": g["latitude"], "lon": g["longitude"]} for g in r.json().get("results", [])]
    except Exception:  # noqa: BLE001
        return []


def choose_farm(key=None, lat=None, lon=None):
    ss = st.session_state
    if key in FARMS:
        f = FARMS[key]
        ss.fs_demo = key
        ss.farm_latitude, ss.farm_longitude = f["lat"], f["lon"]
        ss.fs_current = list(f["current"])
        ss.fs_wet_field, ss.fs_irrigation = f["wet_field"], f["irrigation"]
    else:
        ss.fs_demo = None
        ss.farm_latitude, ss.farm_longitude = round(float(lat), 4), round(float(lon), 4)
    ss.fs_located = True


def located():
    ss = st.session_state
    if ss.get("fs_located"):
        return True
    q = st.query_params
    if q.get("farm") in FARMS:
        choose_farm(q.get("farm"))
        return True
    try:
        if q.get("lat") and q.get("lon"):
            choose_farm(lat=float(q.get("lat")), lon=float(q.get("lon")))
            return True
    except ValueError:
        pass
    return False


def language_select(key):
    ss = st.session_state
    lang = st.selectbox("Language", list(LANGS), index=list(LANGS).index(ss.fs_lang), format_func=LANGS.get,
                        label_visibility="collapsed", key=key)
    if lang != ss.fs_lang:
        ss.fs_lang = lang
        st.rerun()


def render_landing():
    ss = st.session_state
    lg = L()
    st.markdown(f"""<div class="fs-hero"><div class="k">NASA Space Apps 2026 · Field Shift</div>
        <div class="t">Hurricane<br/>to Harvest</div>
        <div class="d">{t("A farmer's almanac, redrawn with satellite data: what to plant, when to water, and how to get through the storm season with your soil and your harvest intact.", lg)}</div></div>""",
                unsafe_allow_html=True)
    with st.container(key="landing"):
        top = st.columns([3, 1])
        top[0].markdown(f"### {t('Where is your farm?', lg)}")
        with top[1]:
            language_select("lang_landing")
        st.caption("Everything that follows is worked out for that exact spot: 30 years of NASA rain, every storm since 1971, "
                   "the soil under it and the satellites watching it now.")
        d1, d2 = st.columns(2, gap="medium")
        for col, (key, f) in zip((d1, d2), FARMS.items()):
            with col:
                st.markdown(f'<div class="fs-demo"><b>{f["label"]}</b><div class="s">{f["story"]}</div></div>', unsafe_allow_html=True)
                if st.button(f"Start with {f['label'].split(',')[0]}", key=f"demo_{key}", use_container_width=True):
                    choose_farm(key)
                    st.rerun()
        st.markdown("**Or find your own farm.** Search a district or village, or tap the map.")
        q = st.text_input("Search a place", placeholder="e.g. Santa Cruz, Jamaica  ·  Penal, Trinidad  ·  Les Cayes, Haiti",
                          label_visibility="collapsed")
        hits = geocode(q) if q and len(q) > 2 else []
        if q and not hits:
            st.caption("No match. Try a nearby town, or tap the map.")
        if hits:
            pick = st.radio("Matches", range(len(hits)), format_func=lambda i: hits[i]["label"], label_visibility="collapsed",
                            horizontal=False)
            ss.fs_pin = (hits[pick]["lat"], hits[pick]["lon"])
        pin = ss.get("fs_pin", (18.05, -77.72))
        m = folium.Map(location=list(pin), zoom_start=9 if "fs_pin" in ss else 6, tiles=None, control_scale=True)
        folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                         attr="Esri World Imagery", name="Satellite").add_to(m)
        folium.TileLayer("OpenStreetMap", name="Street map").add_to(m)
        folium.Marker(list(pin), icon=folium.Icon(color="green", icon="leaf")).add_to(m)
        folium.LayerControl(collapsed=True).add_to(m)
        out = st_folium(m, height=330, width=None, key="landing_map", returned_objects=["last_clicked"])
        if out and out.get("last_clicked"):
            new = (round(out["last_clicked"]["lat"], 4), round(out["last_clicked"]["lng"], 4))
            if new != tuple(pin):
                ss.fs_pin = new
                st.rerun()
        if st.button(f"Begin the journey at {pin[0]:.3f}, {pin[1]:.3f}", type="primary", use_container_width=True,
                     disabled="fs_pin" not in ss):
            choose_farm(lat=pin[0], lon=pin[1])
            st.rerun()


def topbar(bundle):
    ss = st.session_state
    with st.container(key="topbar"):
        c1, c2, c3 = st.columns([3, 1, 1])
        _, farm = current_farm()
        c1.markdown(f'<div class="al-kicker">FarmFit · Hurricane to Harvest</div>'
                    f'<div style="font:600 1.25rem Fraunces,serif;color:{art.INK}">{farm_label(bundle)}</div>', unsafe_allow_html=True)
        with c2:
            language_select("lang_top")
        if c3.button("Change farm", use_container_width=True):
            ss.fs_located = False
            for k in ("farm", "lat", "lon"):
                if k in st.query_params:
                    del st.query_params[k]
            st.rerun()


def intro_beat(bundle):
    _, farm = current_farm()
    imp = bundle["impacts"]
    summ = bundle["storm_summary"]
    place = farm["label"] if farm else f"{bundle['lat']:.3f}°, {bundle['lon']:.3f}°"
    if farm:
        hit = imp[(imp["name"] + " " + imp["year"].astype(str)) == farm["storm"]]
        kt = f" with about {hit.iloc[0]['site_wind_kt']:.0f} knots of wind" if len(hit) else ""
        head = f"On {farm['storm_date']:%-d %B %Y}, {farm['storm'].split()[0].title()} reached this field{kt}."
    elif len(imp):
        top = imp.iloc[0]
        head = f"The worst storm here since 1971 was {top['name'].title()} {top['year']}, about {top['site_wind_kt']:.0f} knots at the farm."
    else:
        head = "Few storms have reached this field since 1971. Rain and drought are the bigger story."
    rp = summ.get("return_period_storm_force")
    dek = (("Storm-force wind reaches it about 1 year in " + f"{rp:.0f}. " if rp else "")
           + "Scroll down, from the sky above the farm to the rock beneath it, and plan the year so the next storm "
             "takes as little as possible.")
    st.markdown(journey.beat(place, head, dek), unsafe_allow_html=True)


def render():
    setup_page()
    journey.install(st)
    if not located():
        render_landing()
        return
    lat, lon = st.session_state.farm_latitude, st.session_state.farm_longitude
    with st.spinner("Reading 30 years of NASA climate, storm tracks, soil and terrain for this farm…"):
        bundle = load_site(lat, lon)
    topbar(bundle)
    if "climate" not in bundle:
        st.error("NASA POWER could not be reached for this point and no saved copy exists. "
                 f"Details: {bundle.get('power_meta', {}).get('error', 'unknown')}. Try again in a minute or pick a demo farm.")
        return
    if "SYNTHETIC" in str(bundle.get("power_meta", {}).get("source", "")):
        st.warning("Offline development mode: climate numbers come from a synthetic test fixture, not NASA data.")
    lg = L()
    intro_beat(bundle)
    with st.container(key="layer_sky"):
        render_storm(bundle)
    st.markdown(journey.beat("The field", t("When the sky clears, the field decides.", lg),
                             "What is in the ground in the storm months matters more than anything done after them."),
                unsafe_allow_html=True)
    with st.container(key="layer_field"):
        render_plan(bundle)
    st.markdown(journey.beat("After the storm", "If it still comes, recover fast and safely.",
                             "A photo, two minutes of questions and the satellite record give a staged path back to harvest."),
                unsafe_allow_html=True)
    with st.container(key="layer_recover"):
        st.fragment(render_after)(bundle)
    st.markdown(journey.beat("Under the surface", "Most of a farm's water is out of sight.",
                             "Rain gauges in orbit, soil moisture from microwaves, and plants breathing out water: "
                             "together they say whether this field is heading into drought."), unsafe_allow_html=True)
    with st.container(key="layer_water"):
        render_water(bundle)
    st.markdown(journey.beat("Deeper", "Clay that holds water. Roots that hold soil.",
                             "The ground under this farm, and the questions only you can ask about it."), unsafe_allow_html=True)
    with st.container(key="layer_soil"):
        render_soil(bundle)
        st.fragment(render_ask)(bundle)
    st.markdown(journey.beat("Bedrock", "Every number traces back to an open dataset.",
                             "NASA, NOAA, FAO, ISRIC and local open data. Here is what each one does, and where it stops."),
                unsafe_allow_html=True)
    with st.container(key="layer_bedrock"):
        render_data(bundle)
        st.markdown('<hr class="al-rule"/><div class="al-note">'
                    + t("FarmFit supports farmers' judgment; it never replaces it. Check plans with your extension officer.", lg)
                    + ' Built with NASA POWER, SMAP, GPM IMERG, MODIS, SRTM, OPERA, NOAA HURDAT2 / IBTrACS / ENSO, ISRIC SoilGrids, '
                      'FAO and NAMDEVCO data.</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:30vh"></div>', unsafe_allow_html=True)


def render_soil(bundle):
    lg = L()
    soil, terr = bundle.get("soil") or {}, bundle.get("terrain") or {}
    st.markdown(art.section("data", t("Soil and roots", lg),
                            "What the ground under this farm is made of, and what that means for drainage, crops and storms."),
                unsafe_allow_html=True)
    if not soil.get("texture"):
        st.info("SoilGrids has no reading for this point yet. A soil test from your extension office gives better numbers anyway.")
    else:
        st.markdown(art.figures([
            ("Texture (0-30 cm)", soil["texture"], f"clay {soil.get('clay_pct', 0):.0f}% · sand {soil.get('sand_pct', 0):.0f}% · silt {soil.get('silt_pct', 0):.0f}%", "clay"),
            ("Drainage", soil.get("drainage") or "?", "from texture (USDA)", "terra" if soil.get("drainage") in ("Slow", "Very slow") else None),
            ("pH", f"{soil.get('ph', 0):.1f}", "most vegetables like 6.0-7.0", "terra" if (soil.get("ph") or 7) < 6 else None),
            ("Organic matter", f"{soil.get('organic_matter_pct', 0):.1f}%", "from soil organic carbon", "leaf"),
            ("Slope", f"{terr.get('slope_pct', 0):.1f}%", f"elevation {terr.get('elevation_m', 0):.0f} m · NASA SRTM", None),
        ]), unsafe_allow_html=True)
        notes = []
        if soil.get("drainage") in ("Slow", "Very slow"):
            notes.append("**Water sits on this soil.** Raised or cambered beds and open drains before the rainy season protect roots; "
                         "crops that hate wet feet (tomato, pepper, watermelon) belong in the drier months.")
        if (soil.get("ph") or 7) < 6:
            notes.append(f"**Slightly acid (pH {soil['ph']:.1f}).** Cabbage, beans and tomatoes do better near 6.5; a lime rate should come from a soil test.")
        if (terr.get("slope_pct") or 0) > 8:
            notes.append("**Sloping land.** Contour rows, grass strips or pigeon-pea hedges slow runoff in heavy rain.")
        notes.append("**Living roots all year** (cover crops between cash crops) hold this soil in place in storms and add organic matter.")
        for n in notes:
            st.markdown(n)
        st.caption(f"Source: {soil.get('source', 'ISRIC SoilGrids')}. 250 m cells average over many fields; your own soil test wins.")
    render_ground_truth(bundle)


# ---------------------------------------------------------------------------
# Calendar + cards
# ---------------------------------------------------------------------------

def _segment_style(row):
    color = row.color if row is not None else "#cccccc"
    fill = f"color-mix(in srgb, {color} 58%, {art.PAPER})"
    texture = art.CROP_TEXTURE.get(row.group) if row is not None else None
    return f"background:{texture + ', ' if texture else ''}{fill}"


def calendar_html(plans, site, crops, storm_month=None, storm_label=None, risk=True):
    head = '<div></div>' + "".join(
        f'<div class="mh{" hit" if storm_month == i + 1 else ""}">{"🌀 " if storm_month == i + 1 else ""}{mname(i + 1, L())}</div>'
        for i in range(12))
    rows = [head]
    if risk:
        wind = site.p_hu + site.p_ts
        flood = 0.5 * site.p_flood
        top = max(0.05, float((wind + flood).max()))
        cells = "".join(
            f'<div class="risk" title="{MONTHS[i]}: storm-force wind in {wind[i]:.0%} of years, waterlogging rain in {site.p_flood[i]:.0%}">'
            f'<i style="height:{28 * wind[i] / top:.1f}px;background:{art.TERRA}"></i>'
            f'<i style="height:{28 * flood[i] / top:.1f}px;background:{art.SEA}"></i></div>'
            for i in range(12))
        rows.append('<div class="rl">Risk<small>wind · flood</small></div>' + cells)
    for plan in plans:
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
        covered = {m for _, r in segments for m in r}
        cells = []
        for crop, run in segments:
            row = crops.loc[crop] if crop in crops.index else None
            hit = " hit" if storm_month in run else ""
            cells.append((run[0], f'<div class="seg{hit}" title="{crop}" style="grid-column:span {len(run)};{_segment_style(row)}">{crop}</div>'))
        for m in range(1, 13):
            if m not in covered:
                cells.append((m, f'<div class="bare{" hit" if storm_month == m else ""}" title="bare soil"></div>'))
        cells.sort(key=lambda c: c[0])
        sub = "today" if plan.key == "current" else ("suggested" if plan.key in ("storm", "soil", "water") else "")
        rows.append(f'<div class="rl">{t(plan.title, L())}<small>{sub}</small></div>' + "".join(c[1] for c in cells))
    legume = art.CROP_TEXTURE["Legume"].split(" 0 0")[0]
    cover = art.CROP_TEXTURE["Cover crop"].split(", repeating")[0]
    key = (f'<div class="al-key"><span><b style="background:{art.TERRA}"></b>storm-force wind</span>'
           f'<span><b style="background:{art.SEA}"></b>waterlogging rain</span>'
           f'<span><b style="border-style:dashed;background:transparent"></b>bare soil</span>'
           f'<span><b style="background:{legume}"></b>legume</span>'
           f'<span><b style="background:{cover}"></b>cover crop</span>'
           + (f'<span>🌀 {storm_label}</span>' if storm_label else "") + '</div>')
    return '<div class="al-cal">' + "".join(rows) + "</div>" + key


METERS = [("storm", "Storm & flood safety", art.TERRA), ("soil", "Soil health", art.CLAY), ("water", "Water saving", art.SEA),
          ("suitability", "Climate fit", art.LEAF), ("food", "Food & income", art.OCHRE)]


def card_html(plan, best=False):
    m = plan.metrics
    lg = L()
    meters = "".join(f'<div class="al-meter"><span>{t(label, lg)}</span><span class="t"><i style="width:{plan.scores.get(k, 0)}%;background:{c}"></i></span>'
                     f'<b>{plan.scores.get(k, 0)}</b></div>' for k, label, c in METERS)
    tag = "Best for your priority" if best else ("What you plant now" if plan.key == "current" else "Alternative")
    return (f'<div class="al-card{" best" if best else ""}"><div class="tag">{t(tag, lg)}</div><h4>{t(plan.title, lg)}</h4>'
            f'<div class="dek">{plan.tagline}</div>{meters}'
            f'<div class="al-facts">{t("Harvest lost to storms and floods, average year", lg)} <b>{m["expected_loss"]:.0%}</b><br/>'
            f'{t("Bare months", lg)} <b>{m["bare_months"]}</b> · {t("legume months", lg)} <b>{m["legume_months"]}</b><br/>'
            f'{t("Irrigation", lg)} ≈ <b>{m["irrigation_mm"]:.0f} mm</b> {t("a year", lg)}</div></div>')


# ---------------------------------------------------------------------------
# PLAN MY SEASON
# ---------------------------------------------------------------------------

PRIORITY_TO_KEY = {"Survive storms": "storm", "Rebuild my soil": "soil", "Save water": "water"}


def rotation_editor(crops):
    ss = st.session_state
    rows = list(ss.fs_current)
    names = list(crops.index)
    new_rows = []
    hdr = st.columns([2.2, 1, 1])
    hdr[0].caption("Crop")
    hdr[1].caption("Planted in")
    hdr[2].caption("Months in field")
    for i in range(4):
        d = rows[i] if i < len(rows) else None
        c1, c2, c3 = st.columns([2.2, 1, 1])
        k = f"{ss.get('fs_demo')}_{i}"
        crop = c1.selectbox(f"Crop {i + 1}", ["—"] + names, index=(names.index(d[0]) + 1) if d and d[0] in names else 0,
                            key=f"cc_{k}", label_visibility="collapsed")
        start = c2.selectbox("Start", MONTHS, index=(d[1] - 1) if d else 0, key=f"cs_{k}", label_visibility="collapsed")
        months = c3.number_input("Months", 1, 12, value=d[2] if d else 3, key=f"cm_{k}", label_visibility="collapsed")
        if crop != "—":
            new_rows.append((crop, MONTHS.index(start) + 1, int(months)))
    if new_rows != rows:
        ss.fs_current = new_rows


def PRICES():
    return market.load(CACHE_DIR / "namdevco_prices.csv")


def render_orchard(site, crops, current):
    ss = st.session_state
    lg = L()
    st.markdown(art.heading(t("When should I plant?", lg)), unsafe_allow_html=True)
    grown = [p.crop for p in current.plantings if p.crop in crops.index and crops.loc[p.crop, "harvest_value"] > 0]
    options = [c for c in crops.index if crops.loc[c, "harvest_value"] > 0]
    default = grown[-1] if grown else "Sweet Potato"
    c1, c2 = st.columns([1, 2.4])
    crop = c1.selectbox("Crop", options, index=options.index(default), key="orchard_crop")
    window = planner.planting_window(site, crops, crop, ss.fs_irrigation)
    best = max(window, key=lambda w: w["p_good"])
    worst = min(window, key=lambda w: w["p_good"])
    c2.markdown(f'<div class="al-note" style="margin-top:1.7rem">Each tree is a planting month. More blossom and fruit means a better '
                f'chance of a good harvest. Best: <b>{MONTHS[best["start"] - 1]}</b> ({journey.pct(best["p_good"])}); '
                f'riskiest: <b>{MONTHS[worst["start"] - 1]}</b> ({journey.pct(worst["p_good"])}). A swirl marks months where storms '
                f'or floods often cost more than a fifth of the crop.</div>', unsafe_allow_html=True)
    st.markdown(journey.orchard_html(window, [mname(i + 1, lg) for i in range(12)], crop), unsafe_allow_html=True)
    st.caption("Chance of a good harvest = share of 4,000 simulated seasons (this farm's own NOAA storm and NASA heavy-rain odds) "
               "where storms and floods take less than 20% of the crop × climate fit (FAO ECOCROP, NASA POWER) × how much of the "
               "irrigation need your water covers. It leaves out pests, prices and luck, so it never shows more than 95%. "
               "Hover a tree for the parts.")


def render_plan(bundle):
    ss = st.session_state
    lg = L()
    st.markdown(art.section("plan", t("Plan my season", lg),
                            t("Tell us what you grow now. We search every 12-month rotation of up to four crops and show the three "
                              "that best protect your harvest, your soil and your water, next to your own.", lg)), unsafe_allow_html=True)
    crops = planner.load_crops()
    with st.container(border=True):
        left, right = st.columns([1.35, 1], gap="large")
        with left:
            st.markdown(f"**{t('What you grow now', lg)}**")
            rotation_editor(crops)
        with right:
            st.markdown(f"**{t('What matters most', lg)}**")
            ss.fs_priority = st.radio("Priority", list(PRIORITY_TO_KEY), horizontal=True, label_visibility="collapsed",
                                      index=list(PRIORITY_TO_KEY).index(ss.fs_priority), format_func=lambda x: t(x, lg))
            ss.fs_irrigation = st.selectbox(t("Water for irrigation", lg), list(planner.IRRIGATION_LIMITS),
                                            index=list(planner.IRRIGATION_LIMITS).index(ss.fs_irrigation))
            with st.expander(t("More options", lg)):
                ss.fs_wet_field = st.toggle("Low-lying field with managed water (allows rice, dasheen)", value=ss.fs_wet_field)
                ss.fs_exclude = st.multiselect("Crops I can't grow or sell", list(crops.index), default=ss.get("fs_exclude", []))
                soil = bundle.get("soil") or {}
                c1, c2 = st.columns(2)
                ph = c1.number_input("Soil pH (from a soil test)", 3.5, 9.5, value=float(soil.get("ph") or 6.5), step=0.1)
                drains = ["Fast", "Good", "Moderate", "Slow", "Very slow"]
                drainage = c2.selectbox("Drainage", drains, index=drains.index(soil.get("drainage") or "Moderate"))
                ss.fs_soil_override = {"ph": ph, "drainage": drainage}

    with st.spinner("Comparing every rotation…"):
        site, crops, current, plans, meta = get_plans(bundle)
    if not plans:
        st.warning("No rotation fits these limits. Allow more crops or more irrigation.")
        return
    pick = PRIORITY_TO_KEY[ss.fs_priority]
    ordered = [current] + [plans[k] for k in ("storm", "soil", "water") if k in plans]
    _, farm = current_farm()
    storm_month = storm_label = None
    if farm:
        hit = bundle["impacts"][(bundle["impacts"]["name"] + " " + bundle["impacts"]["year"].astype(str)) == farm["storm"]]
        if len(hit):
            storm_month = int(hit.iloc[0]["month"])
            storm_label = f"{farm['storm'].title()} struck this month"

    st.markdown(art.heading(f"{t('Your year, four ways', lg)} · {meta.get('candidates', 0):,} {t('rotations compared', lg)}"), unsafe_allow_html=True)
    st.markdown(calendar_html(ordered, site, crops, storm_month, storm_label), unsafe_allow_html=True)
    st.markdown('<div class="al-note">The top row shows how often each month brings storm-force wind (NOAA HURDAT2, 1971-2025) '
                'or a waterlogging rain day (NASA POWER). Hover a bar for the numbers.</div>', unsafe_allow_html=True)
    render_orchard(site, crops, current)

    st.write("")
    cols = st.columns(len(ordered), gap="small")
    for col, plan in zip(cols, ordered):
        with col:
            st.markdown(card_html(plan, best=plan.key == pick), unsafe_allow_html=True)
            ex = planner.explain(plan, site, crops, current=current)
            with st.expander(t("Why · evidence · gaps", lg)):
                st.markdown(f"**Why.** {ex['why']}")
                st.markdown("**Benefits**\n" + "\n".join(f"- {b}" for b in ex["benefits"]))
                st.markdown("**Evidence**\n" + "\n".join(f"- {b}" for b in ex["evidence"]))
                mk = market.plan_market(plan, PRICES())
                if mk:
                    proxy = "" if bundle["lat"] < 11.5 else " (Trinidad prices, used as a regional guide)"
                    st.markdown(f"**Market timing** · NAMDEVCO wholesale{proxy}\n" + "\n".join(
                        f"- {x['crop']} harvested in {MONTHS[x['harvest'] - 1]} sells at {x['index']:.2f}× its yearly average; "
                        f"best month {MONTHS[x['best'] - 1]} ({x['best_index']:.2f}×)" for x in mk if x["index"]))
                st.markdown("**Gaps**\n" + "\n".join(f"- {b}" for b in ex["gaps"]))
                st.markdown("**Check locally**\n" + "\n".join(f"- {b}" for b in ex["review"]))

    best = plans.get(pick)
    if best:
        lines = [f"FarmFit · {best.title} rotation for {farm_label(bundle)}"]
        for p in best.plantings:
            ms = p.month_list()
            lines.append(f"- {p.crop}: plant {MONTHS[ms[0] - 1]}, harvest about {MONTHS[ms[-1] - 1]}")
        lines.append(f"Expected storm/flood harvest loss {best.metrics['expected_loss']:.0%} (mine today: {current.metrics['expected_loss']:.0%}).")
        lines.append("Built with NASA and NOAA data. Check with your extension officer before planting.")
        text = "\n".join(lines)
        st.markdown(art.heading(t("Take the plan with you", lg)), unsafe_allow_html=True)
        key, _ = current_farm()
        topic = alerts.topic_for(key, bundle["lat"], bundle["lon"], farm_label(bundle))
        url = alerts.subscribe_url(topic)
        peak = int(np.argmax(site.p_hu + site.p_ts)) + 1
        pcrop, pstage = in_field(best, peak)
        steps = stormwatch.render_steps(stormwatch.checklist(pcrop, pstage, (bundle.get("soil") or {}).get("drainage"),
                                                             (bundle.get("terrain") or {}).get("slope_pct"), True), lg)
        page = poster.build(farm_label(bundle), best, current, site, crops,
                            calendar_html([best], site, crops), bundle["storm_summary"], steps, url, alerts.qr_svg(url, 3), lg)
        c1, c2, c3 = st.columns(3)
        c1.download_button(t("Printable almanac (A4)", lg), page, file_name="farmfit_almanac.html", mime="text/html",
                           use_container_width=True, type="primary")
        c2.download_button(t("Download (works offline)", lg), text, file_name="farmfit_plan.txt", use_container_width=True)
        c3.link_button(t("Share on WhatsApp", lg), f"https://wa.me/?text={quote(text)}", use_container_width=True)


# ---------------------------------------------------------------------------
# WATER WATCH
# ---------------------------------------------------------------------------

def render_water(bundle):
    lat, lon = bundle["lat"], bundle["lon"]
    lg = L()
    st.markdown(art.section("water", t("Water watch", lg),
                            t("Is the farm drier or wetter than normal right now? Recent NASA rain and soil moisture are ranked "
                              "against the same weeks in each of the last 30 years, then turned into this week's watering advice.", lg)),
                unsafe_allow_html=True)
    record = bundle["daily"]
    recent = load_recent(lat, lon, date.today().isoformat())
    anomalies, last_day = water.rain_anomalies(record, recent)
    soil_now = water.soil_anomaly(record, recent)
    spell = water.dry_spell(recent)
    key, _ = current_farm()
    pulse = satellite_pulse(key)
    smap_now = water.smap_anomaly(pulse.get("smap"))
    root_now = water.rootzone_status(pulse.get("rootzone"))
    stress = water.crop_stress(pulse.get("et"), pulse.get("pet"))

    items = []
    if anomalies:
        main = next((a for a in anomalies if a["days"] == 60), anomalies[0])
        st.markdown(f'{art.stamp(t(main["label"], lg), main["key"])} &nbsp;<span class="al-farm">Last {main["days"]} days to '
                    f'{last_day:%d %b %Y} · NASA POWER, a few days behind real time</span>', unsafe_allow_html=True)
        items += [(f"Rain, last {a['days']} days", f"{a['total_mm']:.0f} mm",
                  f"normal ≈ {a['normal_mm']:.0f} mm · {water.ordinal(a['percentile'])} percentile",
                  "terra" if a["key"].startswith("dry") else ("sea" if a["key"].startswith("wet") else "leaf")) for a in anomalies]
        if soil_now:
            items.append(("Root-zone soil wetness", f"{soil_now['value']:.2f}",
                          f"0 dry, 1 saturated · normal {soil_now['normal']:.2f} · {water.ordinal(soil_now['percentile'])} percentile", None))
        if spell is not None:
            items.append(("Days since ≥ 1 mm rain", f"{spell}", "current dry spell", "terra" if spell >= 10 else None))
    else:
        st.info("Recent NASA POWER data is not reachable right now, so only long-term normals are shown below.")
    if smap_now:
        sub = f"m³/m³ on {smap_now['date']:%d %b}"
        if smap_now.get("percentile") is not None:
            sub += f" · {water.ordinal(smap_now['percentile'])} percentile for the month"
        elif smap_now.get("rank_text"):
            sub += f" · {smap_now['rank_text']} (usual {smap_now['normal']:.2f})"
        items.append(("NASA SMAP soil moisture", f"{smap_now['value']:.2f}", sub, None))
    if root_now:
        sub = f"m³/m³, top 1 m, week to {root_now['date']:%d %b}"
        if root_now["change"] is not None:
            sub += f" · {root_now['change']:+.2f} in {root_now['lookback']} days"
        items.append(("SMAP root-zone moisture", f"{root_now['value']:.2f}", sub,
                      "terra" if (root_now["change"] or 0) < -0.03 else None))
    if stress:
        sub = f"MODIS ET {stress['et_mm']:.0f} of a possible {stress['pet_mm']:.0f} mm, 8 days to {stress['date']:%d %b}"
        if stress["normal"] is not None:
            sub += f" · usual {stress['normal']:.2f}"
        items.append(("Plant water stress (ET ÷ PET)", f"{stress['ratio']:.2f}", f"{stress['label']} · {sub}",
                      "terra" if stress["ratio"] < 0.5 else ("leaf" if stress["ratio"] >= 0.7 else None)))
    if items:
        st.markdown(art.figures(items[:3]) + (art.figures(items[3:6]) if len(items) > 3 else "")
                    + (art.figures(items[6:]) if len(items) > 6 else ""), unsafe_allow_html=True)

    env = water.cumulative_envelope(record, recent, days=90)
    if env is not None:
        band = alt.Chart(env).mark_area(color=art.SEA, opacity=0.18).encode(
            x=alt.X("date:T", title=None), y=alt.Y("p10:Q", title="rain since day 1 (mm)"), y2="p90:Q")
        med = alt.Chart(env).mark_line(color=art.SEA, strokeDash=[4, 3]).encode(x="date:T", y="p50:Q")
        now = alt.Chart(env.dropna(subset=["this_year"])).mark_line(color=art.TERRA, strokeWidth=2.6).encode(
            x="date:T", y="this_year:Q", tooltip=[alt.Tooltip("date:T"), alt.Tooltip("this_year:Q", title="this year (mm)", format=".0f")])
        st.altair_chart((band + med + now).properties(height=240, title="The last 90 days: this year (red) against the usual range (blue)"),
                        use_container_width=True, theme=None)

    render_season_ahead(bundle)
    st.caption("Regional check: the Caribbean Institute for Meteorology and Hydrology (CIMH) publishes a monthly Caribbean Drought "
               "Bulletin and drought outlook (SPI maps): rcc.cimh.edu.bb. Your national met service has the official word.")

    st.markdown(art.heading(t("This week", lg)), unsafe_allow_html=True)
    site, crops, current, plans, _ = get_plans(bundle)
    month = date.today().month
    crop, stage = in_field(current, month)
    fc = load_forecast(lat, lon, date.today().isoformat())
    left, right = st.columns([1.3, 1], gap="large")
    with left:
        if fc is not None:
            fc2 = fc.head(7).assign(day=fc["date"].head(7).dt.strftime("%a %d"))
            bars = alt.Chart(fc2).mark_bar(color=art.SEA, width=26).encode(
                x=alt.X("day:N", sort=None, title=None), y=alt.Y("rain_mm:Q", title="mm"),
                tooltip=["day", alt.Tooltip("rain_mm:Q", title="rain", format=".1f"), alt.Tooltip("et0_mm:Q", title="ET₀", format=".1f")])
            line = alt.Chart(fc2).mark_line(color=art.TERRA, point=True).encode(x=alt.X("day:N", sort=None), y="et0_mm:Q")
            st.altair_chart((bars + line).properties(height=200, title="Next 7 days: rain (bars) and crop water demand ET₀ (line)"),
                            use_container_width=True, theme=None)
            st.caption("Forecast from Open-Meteo (ECMWF / GFS); not a NASA dataset, used only for the week ahead.")
        else:
            st.caption("Forecast unavailable; advice uses this month's 30-year normals instead.")
    with right:
        if crop:
            row = crops.loc[crop]
            kc = {"seedling": row.kc_ini, "vegetative": (row.kc_ini + row.kc_mid) / 2, "reproductive": row.kc_mid, "mature": row.kc_end}[stage]
            clim = bundle["climate"]
            need = water.weekly_irrigation(fc, kc) if fc is not None else water.irrigation_need_from_climate(
                float(clim.loc[month - 1, "et0_mm"]), float(clim.loc[month - 1, "rain_mm"]), kc)
            verdict = t("No watering needed", lg) if need["need_mm"] < 3 else t("Water about {mm} mm this week", lg, mm=f"{need['need_mm']:.0f}")
            st.markdown(f'<div class="al-storm"><div class="al-kicker">{t("in the field", lg)}: {crop} · {t(stage, lg)}</div>'
                        f'<h4 style="margin:.3rem 0">{verdict}</h4>'
                        f'<div class="al-note">The crop uses ≈ {need["etc_mm"]:.0f} mm (K<sub>c</sub> {kc:.2f} × ET₀); about '
                        f'{need["rain_mm"]:.0f} mm of rain is expected, of which 80% counts. That is roughly '
                        f'<b>{need["need_mm"] * 1000:,.0f} litres per 1,000 m²</b>.</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="al-storm"><div class="al-kicker">In the field now</div><h4 style="margin:.3rem 0">' + t("Nothing planted this month", lg) + '</h4>'
                        '<div class="al-note">Bare soil dries out and washes away. A short cover crop holds both water and soil.</div></div>',
                        unsafe_allow_html=True)

    if pulse:
        st.markdown(art.heading("Satellite pulse at this farm"), unsafe_allow_html=True)
        specs = {"imerg": ("GPM IMERG daily rain (mm)", art.SEA), "smap": ("SMAP surface soil moisture (m³/m³)", art.CLAY),
                 "rootzone": ("SMAP L4 root-zone moisture, top 1 m (m³/m³)", art.CLAY),
                 "ndvi": ("MODIS NDVI: how green the land is", art.LEAF)}
        panels = []
        for k in ("imerg", "smap", "rootzone", "ndvi"):
            if k in pulse:
                d = pulse[k].reset_index()
                d.columns = ["date", "value"]
                title, color = specs[k]
                mark = alt.Chart(d).mark_bar(color=color, strokeWidth=0) if k == "imerg" else alt.Chart(d).mark_line(color=color, strokeWidth=1.5)
                panels.append(mark.encode(x=alt.X("date:T", title=None), y=alt.Y("value:Q", title=None)).properties(height=160, title=title))
        if "et" in pulse and "pet" in pulse:
            d = pd.concat({"Actual (ET)": pulse["et"], "Possible (PET)": pulse["pet"]}, axis=1).reset_index().rename(columns={"index": "date"})
            d = d.rename(columns={d.columns[0]: "date"}).melt("date", var_name="series", value_name="mm").dropna()
            panels.append(alt.Chart(d).mark_line(strokeWidth=1.5).encode(
                x=alt.X("date:T", title=None), y=alt.Y("mm:Q", title=None),
                color=alt.Color("series:N", title=None, legend=alt.Legend(orient="bottom"),
                                scale=alt.Scale(domain=["Actual (ET)", "Possible (PET)"], range=[art.LEAF, art.OCHRE]))
            ).properties(height=160, title="MODIS water use, mm per 8 days"))
        for i in range(0, len(panels), 3):
            row = panels[i:i + 3]
            for col, chart in zip(st.columns(3), row):
                col.altair_chart(chart, use_container_width=True, theme=None)

    render_water_bank(bundle, site, crops, current, plans)
    render_shift(bundle)


def season_outlook(bundle):
    return enso.outlook(bundle.get("daily"), enso.load_oni(CACHE_DIR / "oni.csv"))


def render_season_ahead(bundle):
    o = season_outlook(bundle)
    if not o:
        return
    win = f"{MONTHS[o['window_months'][0] - 1]}–{MONTHS[o['window_months'][-1] - 1]}"
    now, bp = o["now"], o["by_phase"]
    st.markdown(art.heading(f"Season ahead: what El Niño and La Niña have meant here for {win}"), unsafe_allow_html=True)
    tone = {"El Niño": "terra", "La Niña": "sea", "Neutral": None}
    items = [("Pacific now (NOAA ENSO index)", now["phase"],
              f"ONI {now['anom']:+.1f} °C for {now['season']} {now['year']}", tone[now["phase"]])]
    for ph in ("El Niño", "Neutral", "La Niña"):
        if ph in bp:
            v = bp[ph]
            items.append((f"{win} rain in {ph} years", f"{v['pct_normal']:.0f}% of normal",
                          f"{v['n']} years · {v['dry_share']:.0%} of them below 80%", tone[ph] if ph == now["phase"] else None))
    st.markdown(art.figures(items), unsafe_allow_html=True)
    r = o["r"]
    if abs(r) < 0.2:
        verdict = (f"At this farm, ENSO has told us little about {win} rain (r = {r:+.2f}), "
                   "so plan on the normals and watch the 60-day status above.")
    else:
        wetter = "El Niño" if r > 0 else "La Niña"
        drier = "La Niña" if r > 0 else "El Niño"
        verdict = (f"Here {drier} years have tended to be drier and {wetter} years wetter in {win} (r = {r:+.2f}). "
                   + ("This year is " + now["phase"] + ", so " + ("bank water and favour drought-tolerant crops."
                      if now["phase"] == drier else "expect more rain than usual and keep drains clear."
                      if now["phase"] == wetter else "the signal is neutral.")))
    st.caption(verdict + f" Normal {win} rain here is {o['normal_mm']:.0f} mm (NASA POWER). "
               "These are tendencies from about 30 years, not a forecast.")
    st.markdown(enso_svg(o, win), unsafe_allow_html=True)


def enso_svg(o, win):
    """One dot per year: the Pacific before the season (x) and rain at this farm (y)."""
    d = o["years"]
    W, H, l, r, top, b = 900, 250, 56, 16, 18, 42
    xmin, xmax = min(-2.0, d["oni"].min()), max(2.5, d["oni"].max())
    ymax = max(200.0, d["pct_normal"].max() * 1.05)
    X = lambda v: l + (v - xmin) / (xmax - xmin) * (W - l - r)
    Y = lambda v: top + (1 - v / ymax) * (H - top - b)
    col = {"El Niño": art.TERRA, "Neutral": "#9aa3ad", "La Niña": art.SEA}
    grid = "".join(f'<line x1="{l}" x2="{W - r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="rgba(31,43,58,{.35 if v == 100 else .1})" '
                   f'stroke-dasharray="{"4 3" if v == 100 else ""}"/><text x="{l - 8}" y="{Y(v) + 4:.1f}" text-anchor="end">{v}%</text>'
                   for v in range(0, int(ymax) + 1, 50))
    xt = "".join(f'<text x="{X(v):.1f}" y="{H - b + 18}" text-anchor="middle">{v:+.1f}</text>' for v in (-2, -1, 0, 1, 2))
    bands = (f'<rect x="{X(0.5):.1f}" y="{top}" width="{X(xmax) - X(0.5):.1f}" height="{H - top - b}" fill="{art.TERRA}" opacity=".06"/>'
             f'<rect x="{X(xmin):.1f}" y="{top}" width="{X(-0.5) - X(xmin):.1f}" height="{H - top - b}" fill="{art.SEA}" opacity=".06"/>')
    dots = "".join(f'<circle cx="{X(row.oni):.1f}" cy="{Y(row.pct_normal):.1f}" r="7" fill="{col[row.phase]}" opacity=".9">'
                   f'<title>{row.year}: ONI {row.oni:+.1f}, {win} rain {row.pct_normal:.0f}% of normal</title></circle>' for row in d.itertuples())
    now = o["now"]["anom"]
    marker = (f'<line x1="{X(now):.1f}" x2="{X(now):.1f}" y1="{top}" y2="{H - b}" stroke="{art.INK}" stroke-width="2" stroke-dasharray="5 4"/>'
              f'<text x="{X(now) - 6:.1f}" y="{top + 12}" text-anchor="end" style="font-weight:600;fill:{art.INK}">this year</text>'
              if xmin <= now <= xmax else "")
    return (f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;font:11px InterVar,sans-serif;fill:{art.INK2}" '
            f'xmlns="http://www.w3.org/2000/svg">{bands}{grid}{xt}{marker}{dots}'
            f'<text x="{(W + l) / 2}" y="{H - 6}" text-anchor="middle">Pacific before the season (ONI, °C): La Niña ← · → El Niño</text>'
            f'<text x="{l}" y="{top - 4}" style="font-weight:600;fill:{art.INK}">{win} rain at this farm, % of normal · one dot per year since 1996</text></svg>')


def render_water_bank(bundle, site, crops, current, plans):
    clim = bundle["climate"]
    st.markdown(art.heading("Storm water bank: catch the wet season, spend it in the dry"), unsafe_allow_html=True)
    st.caption("From our IFRS flood-resilience project: a roof or shed tank with a slow-release valve cuts runoff in storms "
               "and feeds drip irrigation when the rains stop.")
    c1, c2, c3 = st.columns(3)
    roof = c1.number_input("Roof or shed area (m²)", 10, 5000, 150, 10)
    field_m2 = c2.number_input("Field to irrigate (m²)", 50, 50000, 2000, 50)
    plan_key = c3.selectbox("Rotation", ["current"] + [k for k in ("storm", "soil", "water") if k in plans],
                            format_func=lambda k: "Your current rotation" if k == "current" else plans[k].title)
    plan = current if plan_key == "current" else plans[plan_key]
    catch = clim["rain_mm"].to_numpy() * roof * 0.8 / 1000
    need = np.zeros(12)
    for opt in plan.metrics.get("option_rows", []):
        row = crops.loc[opt["crop"]]
        for k, mth in enumerate(planner.Planting(opt["crop"], opt["start"], opt["months"]).month_list()):
            stg = planner.stage_for(k, opt["months"])
            kc = {"seedling": row.kc_ini, "vegetative": (row.kc_ini + row.kc_mid) / 2, "reproductive": row.kc_mid, "mature": row.kc_end}[stg]
            need[mth - 1] += max(0.0, kc * site.et0[mth - 1] - 0.8 * site.rain[mth - 1]) * field_m2 / 1000 / 0.9
    storage, series = 0.0, []
    for _ in range(2):
        series = []
        for m in range(12):
            storage = max(0.0, storage + catch[m] - need[m])
            series.append(storage)
    tank = min(max(series), need.sum())
    supplied = np.minimum(need, catch + np.roll(np.array(series), 1))
    share = supplied.sum() / need.sum() if need.sum() > 0 else 1.0
    st.markdown(art.figures([
        ("Rain you could catch", f"{catch.sum():,.0f} m³", "per year, 80% runoff", "sea"),
        ("Irrigation need", f"{need.sum():,.0f} m³", "FAO-56, drip at 90%", "terra"),
        ("Tank to bank it", f"{tank:,.0f} m³", f"covers ≈ {min(share, 1):.0%} of the need", "leaf"),
    ]), unsafe_allow_html=True)
    d = pd.DataFrame({"month": MONTHS, "Rain caught": catch, "Irrigation need": need})
    st.altair_chart(alt.Chart(d.melt("month", var_name="Flow", value_name="m³")).mark_bar().encode(
        x=alt.X("month:N", sort=MONTHS, title=None), xOffset=alt.XOffset("Flow:N", sort=["Rain caught", "Irrigation need"]), y="m³:Q",
        color=alt.Color("Flow:N", scale=alt.Scale(domain=["Rain caught", "Irrigation need"], range=[art.SEA, art.TERRA]), title=None)
    ).properties(height=200), use_container_width=True, theme=None)


def render_shift(bundle):
    shift, season = bundle["shift"], bundle["season"]
    then, now = bundle["shift_periods"]
    st.markdown(art.heading(f"Field shift: {then} against {now}"), unsafe_allow_html=True)
    st.caption("Same NASA POWER grid cell, two 15-year windows. A change is called 'clear' when its 30-year trend is at least twice its standard error.")
    items = []
    for _, r in shift.iterrows():
        arrow = "▲" if r["change"] > 0 else "▼"
        fmt = "{:,.1f}" if abs(r["now"]) < 100 else "{:,.0f}"
        items.append((r["indicator"], fmt.format(r["now"]), f"{r['unit']} · {arrow} {fmt.format(abs(r['change']))} · {r['signal']}",
                      "terra" if r["signal"] == "clear" else None))
    st.markdown(art.figures(items[:3]) + art.figures(items[3:]), unsafe_allow_html=True)
    st.altair_chart(alt.Chart(season).mark_line(point=True).encode(
        x=alt.X("label:N", sort=MONTHS, title=None), y=alt.Y("PRECTOTCORR:Q", title="mm per month"),
        color=alt.Color("period:N", title=None, scale=alt.Scale(range=["#9aa3ad", art.TERRA])),
        tooltip=["period", "label", alt.Tooltip("PRECTOTCORR:Q", format=".0f")]).properties(height=220, title="Monthly rain, then and now"),
        use_container_width=True, theme=None)


# ---------------------------------------------------------------------------
# STORM READY
# ---------------------------------------------------------------------------

def make_map(lat, lon, impacts=None, date_str=None, height=380, top_storms=6, key="map", show_layer=None, live=None, zoom=6):
    m = folium.Map(location=[lat, lon], zoom_start=zoom, control_scale=True, tiles=None)
    folium.TileLayer("OpenStreetMap", name="Street map").add_to(m)
    folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                     attr="Esri World Imagery", name="Satellite").add_to(m)
    date_str = date_str or (date.today() - timedelta(days=3)).isoformat()
    for layer, title, level, ext in GIBS_LAYERS:
        folium.TileLayer(tiles=GIBS.format(layer=layer, date=date_str, level=level, ext=ext), attr="NASA GIBS",
                         name=f"NASA · {title} · {date_str}", overlay=True, show=(layer == show_layer), opacity=0.75,
                         max_native_zoom=level, max_zoom=18).add_to(m)
    if impacts is not None and len(impacts):
        g = folium.FeatureGroup(name="Past storm tracks (NOAA)", show=True)
        for _, s in impacts.head(top_storms).iterrows():
            tr = storms.storm_track(s["storm_id"])
            folium.PolyLine(tr[["lat", "lon"]].to_numpy().tolist(), color=CAT_COLORS.get(s["site_category"], "#9aa3ad"),
                            weight=3, opacity=.9, tooltip=f"{s['name'].title()} {s['year']}: ≈ {s['site_wind_kt']:.0f} kt at the farm").add_to(g)
        g.add_to(m)
    for s in live or []:
        folium.CircleMarker([s["lat"], s["lon"]], radius=10, color=art.TERRA, fill=True, fill_opacity=.8,
                            tooltip=f"{s['name']} ({s['classification']}, {s['intensity_kt'] or '?'} kt) now").add_to(m)
    folium.Marker([lat, lon], tooltip="Your farm", icon=folium.Icon(color="green", icon="leaf")).add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    return st_folium(m, height=height, width=None, key=key, returned_objects=[])


def render_storm(bundle):
    lat, lon = bundle["lat"], bundle["lon"]
    lg = L()
    st.markdown(art.section("storm", t("Storm ready", lg),
                            t("Hurricanes can't be stopped, but a farm can be ready: the right crops in the ground in the risky months, "
                              "and a short checklist when a storm is on the way.", lg)), unsafe_allow_html=True)
    site, crops, current, plans, _ = get_plans(bundle)
    soil, terr = bundle.get("soil") or {}, bundle.get("terrain") or {}

    st.markdown(art.heading(t("Storm watch, live from NOAA's National Hurricane Center", lg)), unsafe_allow_html=True)
    now = datetime.now()
    live, err = load_active_storms(now.strftime("%Y%m%d%H") + str(now.minute // 15))
    st.caption(stormwatch.season_status())
    threats = []
    if live:
        threats = sorted(((s, stormwatch.threat(s, lat, lon)) for s in live), key=lambda x: x[1]["distance_km"])
        for s, th in threats[:3]:
            lvl = {"act now": "act", "get ready": "ready", "monitor": "calm"}[th["level"]]
            eta = f" · could arrive in about {th['eta_h']:.0f} h" if th["eta_h"] and th["toward"] else ""
            heading_txt = " heading toward the farm" if th["toward"] else (" moving away" if th["toward"] is False else "")
            st.markdown(f'<div class="al-storm">{art.stamp(t(th["level"], lg), lvl)} &nbsp;<b>{s["name"]}</b> · {s["classification"]}, '
                        f'{(s["intensity_kt"] or 0):.0f} kt · {th["distance_km"]:,.0f} km away{heading_txt}{eta}'
                        f'<div class="al-note">Updated {s.get("updated") or "recently"}. Follow your national met service for official warnings.</div></div>',
                        unsafe_allow_html=True)
    elif live is None:
        st.markdown(f'<div class="al-storm">{art.stamp("feed unavailable", "ready")} &nbsp;Could not reach the NHC feed. '
                    'Check nhc.noaa.gov and your national met service.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="al-storm">{art.stamp(t("all clear", lg), "calm")} &nbsp;{t("No active tropical storms in the Atlantic right now.", lg)}</div>',
                    unsafe_allow_html=True)

    month = date.today().month
    crop, stage = in_field(current, month)
    heavy = bool(site.p_flood[month - 1] >= np.quantile(site.p_flood, 0.67))
    steps = stormwatch.checklist(crop, stage, soil.get("drainage"), terr.get("slope_pct"), heavy)
    near = any(th["level"] != "monitor" for _, th in threats)
    title = t("Do these now", lg) if near else t("When a storm is forecast: your checklist for {month}", lg, month=mname(month, lg))
    st.markdown(f"**{title}**" + (f" · {t('in the field', lg)}: {crop} ({t(stage, lg)})" if crop else ""))
    st.markdown('<ul class="al-list">' + "".join(f"<li><span>{x}</span></li>" for x in stormwatch.render_steps(steps, lg)) + "</ul>",
                unsafe_allow_html=True)
    alert_block(bundle)

    summ = bundle["storm_summary"]
    imp = bundle["impacts"]
    top = imp.iloc[0] if len(imp) else None
    st.markdown(art.heading(f"{t('How exposed is this farm?', lg)} NOAA, {summ['period']}"), unsafe_allow_html=True)
    rp = summ["return_period_storm_force"]
    st.markdown(art.figures([
        ("Storm-force wind here", f"1 in {rp:.0f} yrs" if rp else "none", f"{summ['storm_force_events']} events since 1971", "terra"),
        ("Hurricane-force wind", f"{summ['hurricane_force_events']}", "events since 1971", None),
        ("Riskiest months", ", ".join(summ["peak_months"]) or "—", "when storm-force wind arrived", None),
        ("Strongest here", f"{top['name'].title()} {top['year']}" if top is not None else "—",
         f"≈ {top['site_wind_kt']:.0f} kt at the farm" if top is not None else "", "terra"),
    ]), unsafe_allow_html=True)
    left, right = st.columns([1.5, 1], gap="large")
    with left:
        make_map(lat, lon, imp, key="storm_map", live=live or [])
    with right:
        t8 = imp.head(8).copy()
        if len(t8):
            prov = t8["provisional"].fillna(False).astype(bool) if "provisional" in t8 else False
            t8["Storm"] = t8["name"].str.title() + " " + t8["year"].astype(str) + np.where(prov, " *", "")
            t8["Wind here"] = t8["site_wind_kt"].round(0).astype(int).astype(str) + " kt"
            t8["Category here"] = t8["site_category"]
            st.dataframe(t8[["Storm", "Wind here", "Category here"]], hide_index=True, use_container_width=True, height=318)
        st.caption("Wind at the farm is estimated from the NOAA track with a modified Rankine vortex. It is an exposure screen, not a forecast. * provisional.")

    st.markdown(art.heading(t("Stress-test your calendar", lg)), unsafe_allow_html=True)
    allplans = {"current": current, **plans}
    named = imp[imp["site_wind_kt"] >= 25].head(15)
    _, farm = current_farm()
    if len(named):
        labels = [f"{r['name'].title()} {r['year']} · ≈{r['site_wind_kt']:.0f} kt here" for _, r in named.iterrows()]
        default = 0
        if farm:
            for i, (_, r) in enumerate(named.iterrows()):
                if f"{r['name']} {r['year']}" == farm["storm"]:
                    default = i
        storm = named.iloc[labels.index(st.selectbox("Replay a real storm", labels, index=default))]
        cols = st.columns(len(allplans))
        for col, (k, plan) in zip(cols, allplans.items()):
            r = planner.replay_storm(plan, crops, storm["time"], storm["site_wind_kt"])
            if r["bare"]:
                big, note = "—", "Field bare: no harvest at risk, but bare soil washes away."
            elif r.get("cover_crop"):
                big, note = "0%", f"{r['crop']} cover crop holding the soil."
            else:
                big, note = f"{r['loss']:.0%}", f"{r['crop']} at the {r['stage']} stage."
            color = art.TERRA if big not in ("—", "0%") else art.LEAF
            col.markdown(f'<div class="al-card"><div class="tag">{t(plan.title, lg)}</div>'
                         f'<div style="font:600 2.1rem Fraunces,serif;color:{color};margin:.2rem 0">{big}</div>'
                         f'<div class="al-note">{note}</div></div>', unsafe_allow_html=True)
        st.caption(f"{storm['name'].title()} reached this farm on {storm['time']:%d %b %Y} with about {storm['site_wind_kt']:.0f} kt "
                   f"sustained wind; the storm itself was {storm['storm_category']}.")
    else:
        st.caption("No storm since 1950 brought strong wind to this farm in the NOAA record; the simulation below still tests heavy rain.")

    s1, s2 = st.columns(2)
    sm = s1.slider("Storms, compared with history", 0.5, 2.0, 1.0, 0.1, format="%.1f×")
    rm = s2.slider("Heavy-rain days, compared with history", 0.5, 2.0, 1.0, 0.1, format="%.1f×")
    mc = planner.monte_carlo(site, allplans, crops, n_years=5000, storm_multiplier=sm, rain_multiplier=rm)
    rows = [{"Rotation": p.title, "Average year": mc[k]["expected_loss"], "Bad year (1 in 10)": mc[k]["bad_year_loss"]}
            for k, p in allplans.items()]
    df = pd.DataFrame(rows).melt("Rotation", var_name="Measure", value_name="Harvest lost")
    st.altair_chart(alt.Chart(df).mark_bar().encode(
        y=alt.Y("Rotation:N", sort=None, title=None), yOffset=alt.YOffset("Measure:N"),
        x=alt.X("Harvest lost:Q", axis=alt.Axis(format="%"), title="share of harvest lost"),
        color=alt.Color("Measure:N", scale=alt.Scale(range=[art.OCHRE, art.TERRA]), title=None),
        tooltip=["Rotation", "Measure", alt.Tooltip("Harvest lost:Q", format=".1%")],
    ).properties(height=230, title="5,000 simulated seasons drawn from this farm's own storm and rain history"),
        use_container_width=True, theme=None)


# ---------------------------------------------------------------------------
# AFTER A STORM
# ---------------------------------------------------------------------------

def secret(name):
    try:
        v = st.secrets.get(name)
    except Exception:  # noqa: BLE001
        v = None
    return v or os.environ.get(name)


def render_after(bundle):
    ss = st.session_state
    lat, lon = bundle["lat"], bundle["lon"]
    lg = L()
    st.markdown(art.section("after", t("After a storm", lg),
                            t("Photograph the field. AI describes what it can see, NASA rain and soil moisture add context, "
                              "and clear food-safety rules set a staged path back to harvest.", lg)), unsafe_allow_html=True)
    _, farm = current_farm()
    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown("**1 · Field photo**")
        photo = st.file_uploader("Field photo", type=["jpg", "jpeg", "png", "webp"], label_visibility="collapsed")
        ai = ss.get("fs_ai")
        if photo is not None:
            st.image(photo, use_container_width=True)
            key = secret("GEMINI_API_KEY")
            if key and st.button("Describe this photo", type="primary", use_container_width=True):
                with st.spinner("Looking at the photo…"):
                    res = recovery.assess_photo(photo.getvalue(), photo.type, key, model=secret("GEMINI_MODEL"))
                ss.fs_ai = res if res.get("ok") else None
                if not res.get("ok"):
                    st.error(f"Photo analysis unavailable ({res.get('error')}). Answer the questions on the right instead.")
                ai = ss.get("fs_ai")
        if ai:
            r = ai["result"]
            st.markdown(f'<div class="al-card"><div class="tag">What the photo shows · confidence {r.get("confidence", 0):.0%}</div>'
                        f'<div class="al-note">Standing water <b>{r.get("standing_water")}</b> · bare soil <b>{r.get("bare_soil_percent")}%</b> · '
                        f'erosion <b>{r.get("erosion")}</b> · debris <b>{r.get("sediment_or_debris")}</b> · plants down <b>{r.get("plants_lodged_or_broken")}</b>'
                        f'<br/>{r.get("visible_notes", "")}</div></div>', unsafe_allow_html=True)
    with right:
        st.markdown("**2 · What a photo can't show**")
        ai_r = (ai or {}).get("result", {})
        days = st.slider("Days water stood on the field", 0, 14, 2 if ai_r.get("standing_water") in ("puddles", "widespread") else 0)
        source = st.selectbox("Where did the water come from?", ["Rain only", "River or drain overflow", "Sewage / septic", "Livestock area", "Industrial / unknown"])
        contact = st.radio("Did floodwater touch the part of the crop you eat?", ["No", "Yes", "Not sure"], horizontal=True)
        washed = st.checkbox("Soil washed away or gullies formed", value=ai_r.get("erosion") in ("rills", "gullies"))
        storm_date = st.date_input("When did the storm pass?", value=farm["storm_date"] if farm else date.today() - timedelta(days=5),
                                   key=f"sd_{ss.get('fs_demo')}")

    recent, _ = power.fetch_window(lat, lon, end_date=storm_date + timedelta(days=3), days=17)
    rain14 = wet = None
    if recent is not None and "PRECTOTCORR" in recent:
        r = recent.dropna(subset=["PRECTOTCORR"])
        rain14 = float(r["PRECTOTCORR"].tail(14).sum()) if len(r) else None
        if "GWETROOT" in recent and recent["GWETROOT"].notna().any():
            wet = float(recent["GWETROOT"].dropna().iloc[-1])
    state = recovery.field_state(ai_r, {"standing_water_days": days, "water_source": source, "flood_touched_edible": contact,
                                        "soil_washed": washed, "debris": ai_r.get("sediment_or_debris") == "heavy"},
                                 recent_rain_mm=rain14, soil_wet_root=wet, drainage=(bundle.get("soil") or {}).get("drainage"))
    st.markdown(art.heading("3 · Satellite context and field condition"), unsafe_allow_html=True)
    flag_text = {"waterlogged": "waterlogged", "prolonged_flooding": "prolonged flooding", "eroded": "erosion", "debris": "debris or silt",
                 "crop_damaged": "crop damaged", "bare": "mostly bare", "edible_contact": "floodwater on edible crop",
                 "contamination_risk": "possible contamination", "unknown_contact": "unsure about flood contact"}
    n = len(state["flags"])
    st.markdown(art.figures([
        ("Rain in the 14 days to the storm", f"{rain14:.0f} mm" if rain14 is not None else "n/a", "NASA POWER daily", "sea"),
        ("Root-zone wetness", f"{wet:.2f}" if wet is not None else "n/a", "0 dry, 1 saturated (MERRA-2)", None),
        ("Field condition", f"{n} flag{'s' if n != 1 else ''}", ", ".join(flag_text.get(f, f) for f in state["flags"]) or "no major concerns",
         "terra" if n else "leaf"),
    ]), unsafe_allow_html=True)
    for note in state["notes"]:
        st.caption(note)

    imerg = satellite_pulse(current_farm()[0]).get("imerg")
    if imerg is not None:
        win = imerg[pd.Timestamp(storm_date) - pd.Timedelta(days=3): pd.Timestamp(storm_date) + pd.Timedelta(days=1)]
        if len(win):
            st.caption(f"GPM IMERG at the farm: {win.sum():.0f} mm in the 5 days around the storm "
                       f"(peak {win.max():.0f} mm on {win.idxmax():%d %b}).")
    with st.expander("Flood water seen from space"):
        flood_day = storm_date + timedelta(days=1)
        st.caption(f"MODIS flood map for the 2 days to {flood_day:%d %b %Y}, shown by default. In the layer menu, OPERA surface "
                   "water from Sentinel-1 radar sees through cloud, which hides MODIS flooding right after a hurricane. "
                   "MODIS starts in 2000 and OPERA in 2023, and both have gaps on some days.")
        make_map(lat, lon, date_str=flood_day.isoformat(), height=340, key=f"flood_{ss.get('fs_demo')}",
                 show_layer="MODIS_Combined_Flood_2-Day", top_storms=0, zoom=9)

    st.markdown(art.heading("4 · " + t("Your path back", lg)), unsafe_allow_html=True)
    stages = recovery.recovery_stages(state, storm_date.month, wet_field=ss.fs_wet_field)
    cols = st.columns(len(stages), gap="medium")
    for col, stg in zip(cols, stages):
        items = "".join(f"<li>{a}</li>" for a in stg["actions"])
        col.markdown(f'<div class="al-stage"><div class="w">{stg["weeks"]}</div><h4>{t(stg["title"], lg)}</h4><ul>{items}</ul>'
                     f'<div class="gate">{t("Move on when", lg)}: {stg["gate"]}</div></div>', unsafe_allow_html=True)

    site = build_site(bundle)
    crops = planner.load_crops()
    start_month = (storm_date.month + 1) % 12 + 1
    allowed = planner.allowed_crops(crops, wet_field=ss.fs_wet_field and "contamination_risk" not in state["flags"])
    if {"contamination_risk", "edible_contact"} & set(state["flags"]):
        allowed = [c for c in allowed if c not in ("Pak Choi", "Callaloo", "Cabbage")]
    plans = planner.generate_strategies(site, crops, allowed, fixed_start=start_month, irrigation=ss.fs_irrigation)
    plans.pop("_meta", None)
    rec = plans.get("storm") or plans.get("soil")
    if rec:
        rec.title = "Recovery"
        st.markdown(art.heading(f"Recovery rotation from {MONTHS[start_month - 1]}"), unsafe_allow_html=True)
        st.markdown(calendar_html([rec], site, crops), unsafe_allow_html=True)
        st.caption("Stagger plantings and mix in a longer crop. After Hurricane Melissa so many farmers replanted fast vegetables "
                   "that by January 2026 prices had fallen sharply (Jamaica Ministry of Agriculture); the second wave of a "
                   "glut pays least.")
    st.markdown(art.heading("Help, and money, after a storm"), unsafe_allow_html=True)
    jam = bundle["lat"] > 15
    summ = bundle["storm_summary"]
    rp = summ.get("return_period_storm_force")
    h1, h2 = st.columns(2, gap="large")
    h1.markdown(("**Report damage.** RADA hotline **888-ASK-RADA** (275-7232) or WhatsApp **876-436-8879**; RADA officers "
                 "use these reports for damage assessments and input support." if jam else
                 "**Report damage.** Contact your Ministry of Agriculture extension office and register with the County "
                 "agricultural office so you are counted for relief inputs. Follow ODPM for official warnings.")
                + " Keep dated photos of the field: FarmFit's photo check gives you a record.")
    h2.markdown("**Insurance that pays fast.** CCRIF's **Livelihood Protection Policy** is parametric micro-insurance for "
                "small farmers: it pays out when measured wind or rain passes a set level, with no loss adjuster. It launched in "
                "Jamaica in December 2025 and is being rolled out in other Caribbean countries."
                + (f" At this farm storm-force wind arrives about 1 year in {rp:.0f}, which is the kind of risk it covers." if rp else ""))
    st.markdown('<div class="al-note">Food-safety decisions after flooding follow U.S. FDA guidance and should be confirmed with your '
                'Ministry of Agriculture extension officer.</div>', unsafe_allow_html=True)



# ---------------------------------------------------------------------------
# Alerts, assistant, ground truth
# ---------------------------------------------------------------------------

def alert_block(bundle, topic=None):
    lg = L()
    key, _ = current_farm()
    topic = topic or alerts.topic_for(key, bundle["lat"], bundle["lon"], farm_label(bundle))
    url = alerts.subscribe_url(topic)
    with st.expander(t("Get storm and drought alerts on your phone", lg)):
        c1, c2 = st.columns([1, 3])
        c1.markdown(f'<div style="max-width:150px">{alerts.qr_svg(url, 4)}</div>', unsafe_allow_html=True)
        c2.markdown(f"1. Install the free **ntfy** app (Android or iPhone).\n"
                    f"2. Scan the code or subscribe to **`{topic}`**.\n"
                    f"3. You get a message when a storm is close enough to act, or when the last 60 days are very dry or very wet.\n\n"
                    f"No phone number or sign-up is needed. Extension officers can add farms to the automatic watchlist "
                    f"(`data/farms.json`); SMS by Twilio is optional.")
        if c2.button("Send a test alert", key=f"test_alert_{topic}"):
            try:
                alerts.send_ntfy(topic, {"title": f"FarmFit test for {farm_label(bundle)}",
                                         "message": "Alerts are working. You will hear from us when a storm or drought needs action.",
                                         "priority": "default", "tags": "seedling"})
                c2.success("Sent. Check the ntfy app.")
            except Exception as error:  # noqa: BLE001
                c2.error(f"Could not send: {error}")


def farm_briefing(bundle):
    site, crops, current, plans, _ = get_plans(bundle)
    clim = bundle["climate"]
    summ = bundle["storm_summary"]
    soil, terr = bundle.get("soil") or {}, bundle.get("terrain") or {}
    _, farm = current_farm()
    month = date.today().month
    crop, stage = in_field(current, month)

    def plan_line(p):
        parts = ", ".join(f"{x.crop} {MONTHS[x.start - 1]}-{MONTHS[x.month_list()[-1] - 1]}" for x in p.plantings)
        m = p.metrics
        return (f"{p.title}: {parts}; expected storm/flood harvest loss {m['expected_loss']:.0%}, bare months {m['bare_months']}, "
                f"legume months {m['legume_months']}, irrigation {m['irrigation_mm']:.0f} mm/yr")

    ctx = {
        "Today": date.today().isoformat(),
        "Farm": f"{farm_label(bundle) if current_farm()[1] else 'Farm'} (near {bundle['lat']:.1f}, {bundle['lon']:.1f})" + (f". {farm['story']}" if farm else ""),
        "Soil (ISRIC SoilGrids, 250 m)": ", ".join(f"{k} {v}" for k, v in soil.items() if k in ("ph", "texture", "organic_matter_pct", "drainage") and v) or "unknown",
        "Terrain (NASA SRTM)": f"elevation {terr.get('elevation_m')} m, slope {terr.get('slope_pct')} %" if terr.get("elevation_m") is not None else "unknown",
        "Climate (NASA POWER " + bundle.get("climate_period", "") + ")": [
            f"{r.label}: rain {r.rain_mm:.0f} mm, max temp {r.t_max:.1f} C, ET0 {r.et0_mm:.0f} mm, chance of a >=50 mm day {r.p_heavy_rain:.0%}"
            for r in clim.itertuples()],
        "Storm exposure (NOAA HURDAT2 " + summ["period"] + ")": [
            f"storm-force wind at the farm about 1 year in {summ['return_period_storm_force']:.0f}" if summ["return_period_storm_force"] else "storm-force wind very rare",
            f"hurricane-force events {summ['hurricane_force_events']}; riskiest months {', '.join(summ['peak_months'])}",
        ] + [f"{r.name.title()} {r.year}: about {r.site_wind_kt:.0f} kt at the farm on {r.time:%d %b %Y}" for r in bundle["impacts"].head(5).itertuples()],
        "Field shift (first vs last 15 years)": [f"{r.indicator}: {r.then:.1f} -> {r.now:.1f} {r.unit} ({r.signal})" for r in bundle["shift"].itertuples()],
        "In the field this month": f"{crop} ({stage})" if crop else "nothing planted",
        "Farmer's current rotation": plan_line(current),
        "Suggested rotations": [plan_line(p) for p in plans.values()],
    }
    recent = load_recent(bundle["lat"], bundle["lon"], date.today().isoformat())
    anomalies, end = water.rain_anomalies(bundle["daily"], recent)
    if anomalies:
        ctx["Water status (NASA POWER, to " + f"{end:%d %b %Y})"] = [
            f"last {a['days']} days rain {a['total_mm']:.0f} mm vs normal {a['normal_mm']:.0f} mm ({a['label']}, {a['percentile']:.0f}th percentile of 30 years)"
            for a in anomalies]
    o = season_outlook(bundle)
    if o:
        win = f"{MONTHS[o['window_months'][0] - 1]}-{MONTHS[o['window_months'][-1] - 1]}"
        ctx["Season ahead (NOAA ENSO index tested on this farm's NASA POWER rain)"] = [
            f"now {o['now']['phase']} (ONI {o['now']['anom']:+.1f} for {o['now']['season']} {o['now']['year']})",
            f"correlation of ONI with {win} rain here r = {o['r']:+.2f}",
        ] + [f"{win} rain in {ph} years: {v['pct_normal']:.0f}% of normal ({v['n']} years)" for ph, v in o["by_phase"].items()]
    pulse = satellite_pulse(current_farm()[0])
    sat = []
    root = water.rootzone_status(pulse.get("rootzone"))
    if root:
        sat.append(f"SMAP root-zone moisture {root['value']:.2f} m3/m3 on {root['date']:%d %b}"
                   + (f", {root['change']:+.2f} in {root['lookback']} days" if root["change"] is not None else ""))
    stress = water.crop_stress(pulse.get("et"), pulse.get("pet"))
    if stress:
        sat.append(f"MODIS ET/PET {stress['ratio']:.2f} ({stress['label']}) for 8 days to {stress['date']:%d %b}"
                   + (f", usual {stress['normal']:.2f}" if stress["normal"] is not None else ""))
    if sat:
        ctx["Satellite water status"] = sat
    now = datetime.now()
    live, _ = load_active_storms(now.strftime("%Y%m%d%H") + str(now.minute // 15))
    if live:
        ctx["Active storms (NOAA NHC, live)"] = [
            f"{s['name']} {s['classification']} {s['intensity_kt'] or '?'} kt, {stormwatch.threat(s, bundle['lat'], bundle['lon'])['distance_km']:.0f} km away, "
            f"level {stormwatch.threat(s, bundle['lat'], bundle['lon'])['level']}" for s in live]
    else:
        ctx["Active storms (NOAA NHC, live)"] = "none right now" if live == [] else "feed unavailable"
    ctx["Crops FarmFit knows"] = ", ".join(f"{r.crop} ({r.days_to_harvest} d, {r.family})" for r in crops.itertuples())
    return assistant.build_briefing(ctx)


def render_ask(bundle):
    ss = st.session_state
    lg = L()
    st.markdown(art.section("plan", t("Ask FarmFit", lg),
                            t("Ask anything about your farm, in your language. Answers draw on this farm's NASA climate record, storm history, rotations and water status.", lg)),
                unsafe_allow_html=True)
    key = secret("GEMINI_API_KEY")
    if not key:
        st.info("The assistant needs a Gemini API key in the app's secrets (GEMINI_API_KEY).")
    farm_key = f"{bundle['lat']:.3f},{bundle['lon']:.3f}"
    if ss.get("fs_chat_farm") != farm_key:
        ss.fs_chat, ss.fs_chat_farm = [], farm_key
    for turn in ss.fs_chat:
        with st.chat_message("user" if turn["role"] == "user" else "assistant", avatar="🧑🏾‍🌾" if turn["role"] == "user" else "🌱"):
            st.markdown(turn["content"])
    question = None
    if not ss.fs_chat:
        st.caption(t("Try asking", lg))
        cols = st.columns(3)
        for col, q in zip(cols, assistant.SUGGESTED.get(lg, assistant.SUGGESTED["en"])):
            if col.button(q, use_container_width=True, key=f"sugg_{hash(q)}"):
                question = q
    typed = st.chat_input(t("Ask a question about your farm…", lg), disabled=not key)
    question = typed or question
    if question and key:
        with st.chat_message("user", avatar="🧑🏾‍🌾"):
            st.markdown(question)
        with st.chat_message("assistant", avatar="🌱"):
            with st.spinner("…"):
                briefing = farm_briefing(bundle)
                answer, info = assistant.ask(key, ss.fs_chat, question, briefing, lang=lg, model=secret("GEMINI_MODEL"))
            if answer:
                st.markdown(answer)
                ss.fs_chat += [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
            else:
                st.error(f"The assistant is unavailable right now ({info.get('error')}).")
    with st.expander("What the assistant knows about this farm"):
        st.code(farm_briefing(bundle), language=None)


def render_ground_truth(bundle):
    lg = L()
    st.markdown(art.heading(t("Ground truth: your own soil sensor", lg)), unsafe_allow_html=True)
    st.caption("A US$15 ESP32 probe in the field, compared with NASA SMAP (9 km) and NASA POWER soil wetness (≈ 55 km). "
               "Because the scales differ, we compare patterns (standardised anomalies) and report the correlation r.")
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        upload = st.file_uploader("Upload probe CSV (ts, soil_raw or soil_pct)", type=["csv"], key="probe_csv")
        topic = st.text_input("…or read a live probe by its ntfy topic", placeholder="farmfit-sensor-probe-01")
    with c2:
        fw = (Path(__file__).resolve().parents[1] / "hardware" / "farmfit_soil_probe" / "farmfit_soil_probe.ino")
        if fw.exists():
            st.download_button("Download probe firmware (ESP32, Arduino)", fw.read_text(), file_name="farmfit_soil_probe.ino",
                               use_container_width=True)
        st.markdown('<div class="al-note">Parts: ESP32, capacitive soil sensor v1.2, optional solar + 18650. '
                    'Readings use the same JSON contract as our IFRS flood sensors.</div>', unsafe_allow_html=True)
    series = None
    try:
        if upload is not None:
            series = sensor.parse_csv(upload.getvalue())
        elif topic:
            series = sensor.poll_ntfy(topic.strip())
    except Exception as error:  # noqa: BLE001
        st.error(f"Could not read the probe data: {error}")
    if series is None or series.empty:
        return
    key, _ = current_farm()
    pulse = satellite_pulse(key)
    refs = {}
    if "smap" in pulse:
        refs["NASA SMAP"] = pulse["smap"]
    recent = load_recent(bundle["lat"], bundle["lon"], date.today().isoformat())
    if recent is not None and "GWETTOP" in recent:
        refs["NASA POWER surface wetness"] = pd.concat([bundle["daily"]["GWETTOP"], recent["GWETTOP"]]).groupby(level=0).last()
    elif "GWETTOP" in bundle["daily"]:
        refs["NASA POWER surface wetness"] = bundle["daily"]["GWETTOP"]
    z, stats = sensor.compare(series, refs)
    long = z.melt("date", var_name="Series", value_name="z")
    st.altair_chart(alt.Chart(long.dropna()).mark_line().encode(
        x=alt.X("date:T", title=None), y=alt.Y("z:Q", title="standardised anomaly"),
        color=alt.Color("Series:N", scale=alt.Scale(range=[art.TERRA, art.CLAY, art.SEA]), title=None)
    ).properties(height=220, title="Your probe against NASA, as patterns"), use_container_width=True, theme=None)
    items = [(f"vs {s['reference']}", f"r = {s['r']:.2f}" if s["r"] is not None else "n/a", f"{s['days']} shared days", None) for s in stats]
    if items:
        st.markdown(art.figures(items), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# DATA & METHOD
# ---------------------------------------------------------------------------

APPEEARS = "NASA AppEEARS (SMAP, MODIS NDVI + ET)"


def data_passport(bundle):
    meta = bundle.get("power_meta", {})
    soil, terr = bundle.get("soil") or {}, bundle.get("terrain") or {}
    origin = {"live": "live", "cache": "saved copy", "cache-nearby": "nearby saved copy", None: "unavailable"}
    synthetic = "SYNTHETIC" in str(meta.get("source", ""))
    rows = [
        ["NASA POWER (MERRA-2, CERES)", "30 years of daily rain, temperature, humidity, wind, soil wetness, sun", "≈ 55 km", "live on click",
         "test fixture" if synthetic else origin.get(meta.get("origin"), "?"), freshness("NASA POWER")],
        ["NASA SMAP L3 (via AppEEARS)", "Surface soil moisture at the farm (top ≈ 5 cm)", "9 km", "scheduled", None, freshness(APPEEARS)],
        ["NASA SMAP L4 root zone SPL4SMGP (via AppEEARS)", "Moisture where roots are (top 1 m), every 3 hours", "9 km", "scheduled", None, freshness(APPEEARS)],
        ["NASA MODIS NDVI MOD13Q1 (via AppEEARS)", "How green the crops are", "250 m", "scheduled", None, freshness(APPEEARS)],
        ["NASA MODIS ET MOD16A2 (via AppEEARS)", "Actual vs potential water use: plant water stress", "500 m, 8-day", "scheduled", None, freshness(APPEEARS)],
        ["NASA GPM IMERG V07 Final + Late (GES DISC OPeNDAP)", "Daily rain at the farm: last 120 days and storm windows", "0.1° ≈ 11 km", "scheduled", None, freshness("GPM IMERG")],
        ["NASA SRTM GL1", "Elevation, slope, erosion factor", "30 m", "live on click", origin.get(terr.get("origin"), "?"), freshness("NASA SRTM")],
        ["NASA GIBS (SMAP, IMERG, MODIS)", "Map layers for any date", "9 km to 250 m", "live map tiles", "live", None],
        ["NASA MODIS flood + OPERA DSWx-S1 (GIBS)", "Where flood water stood after a storm", "250 m / 30 m", "live map tiles", "live", None],
        ["NOAA CPC ENSO index (ONI)", "Season-ahead drought signal, tested on the farm's own rain", "Pacific index", "scheduled", None, freshness("NOAA ENSO (ONI)")],
        ["NOAA HURDAT2", "Every Atlantic storm track 1851-2025", "6-hourly", "bundled, yearly", "bundled", None],
        ["NOAA IBTrACS", "This season's storms (provisional)", "3-hourly", "scheduled", None, freshness("NOAA IBTrACS (current season)")],
        ["NOAA NHC CurrentStorms", "Active storms right now", "per advisory", "live, every 15 min", "live", None],
        ["ISRIC SoilGrids 2.0", "pH, carbon, texture, drainage", "250 m", "live on click", origin.get(soil.get("origin"), "?"), freshness("ISRIC SoilGrids")],
        ["FAO ECOCROP + FAO-56", "Crop climate ranges and water use", "per crop", "bundled", "bundled", None],
        ["Open-Meteo forecast", "Next 7 days of rain and ET₀ (not NASA)", "≈ 10 km", "live", "live", None],
        ["Your soil probe (ESP32)", "Ground truth for SMAP and POWER soil wetness", "1 point", "live (ntfy) or CSV", None, None],
        ["Google Gemini", "Farm assistant and photo description (not a data source)", "-", "live", None, None],
    ]
    out = []
    for name, use, res, how, here, fresh in rows:
        status = " · ".join(x for x in (how, here if here and here not in ("live", "bundled") else None, fresh) if x)
        out.append([name, use, res, status])
    return pd.DataFrame(out, columns=["Dataset", "Used for", "Resolution", "Status"])


def render_data(bundle):
    lg = L()
    st.markdown(art.section("data", t("Data & method", lg),
                            t("Every number in FarmFit traces back to an open dataset and a published method. Here is the full list, "
                              "how each one reaches the app, and where human judgment still matters.", lg)), unsafe_allow_html=True)
    st.dataframe(data_passport(bundle), hide_index=True, use_container_width=True, column_config={
        "Dataset": st.column_config.TextColumn(width="medium"), "Used for": st.column_config.TextColumn(width="large"),
        "Resolution": st.column_config.TextColumn(width="small"), "Status": st.column_config.TextColumn(width="medium")})
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown(art.heading("Methods"), unsafe_allow_html=True)
        st.markdown("""
- **Storm exposure.** Every NOAA track is interpolated to 15-minute steps. Wind at the farm uses a modified Rankine vortex,
  V = V<sub>max</sub>(R<sub>m</sub>/r)<sup>0.6</sup>, with R<sub>m</sub> from HURDAT2. Monthly odds use 1971-2025.
- **Water.** FAO-56 Hargreaves reference evapotranspiration, ET₀ = 0.0023·R<sub>a</sub>(T + 17.8)√(T<sub>max</sub> − T<sub>min</sub>);
  crop demand ETc = K<sub>c</sub>·ET₀; irrigation = Σ max(0, ETc − 0.8P).
- **Drought.** Recent 30, 60 and 90-day rain and root-zone wetness are ranked against the same window in each of 30 years (an empirical SPI).
- **Soil.** Living cover weighted by each month's share of rain (RUSLE C×R logic), legume months, crop-family diversity, SRTM slope factor.
- **Rotations.** Every 12-month cycle of up to four crops is scored; three weight profiles pick Storm-smart, Soil builder and Water saver.
- **Stress test.** Real storms are replayed on each calendar, and 5,000 seasons are simulated from the farm's own monthly storm and rain odds.
""", unsafe_allow_html=True)
    with c2:
        st.markdown(art.heading("Limits"), unsafe_allow_html=True)
        st.markdown("""
- Satellite cells are larger than farms: valleys, windbreaks and drains are invisible to them. Soil values can be corrected by hand.
- Crop wind and flood vulnerability values are transparent heuristics and need checking with CARDI and extension officers.
- The wind model screens exposure. It does not forecast storms; always follow official warnings.
- Prices, labour and markets are not modelled.
- Food safety after floods follows FDA guidance and must be confirmed locally.
- Spanish, French and Kreyòl screens were drafted with AI help and need review by native speakers.
- The assistant can be wrong. It is told to quote the farm's data and to defer to extension officers and official warnings.
""")
        m = manifest()
        if m.get("generated"):
            st.caption(f"Last scheduled data refresh: {m['generated']} UTC.")
