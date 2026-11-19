"""Multi-page app: onboarding first, then one page per job.

Commercial farm pages: Home, My farm, Weather, Crops & market, Planner,
Storms & recovery, Pest watch, News & learning, Data & method.
Home garden pages: a lighter set built for small spaces and beginners.
Every page reuses the engine and the sections that already existed in ui.py.
"""

import copy
from datetime import date, datetime, timezone

import altair as alt
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from . import art, community, garden, journey, market, news, planner, profile, restore, stormwatch, water
from . import ui
from .i18n import LANGS

MONTHS = planner.MONTHS
TODAY = date.today

DEMO_PROFILES = {
    "jamaica": {"mode": "farm", "name": "Example farm, St Elizabeth", "lat": 18.05, "lon": -77.72, "place": "St Elizabeth, Jamaica",
                "size": 5, "size_unit": "acres", "crops": ["Watermelon", "Sweet Pepper"], "soil_type": profile.SOIL_TYPES[0],
                "water": profile.WATER[1], "equipment": ["Hand tools only", "Smartphone camera"], "wet_field": False},
    "trinidad": {"mode": "farm", "name": "Example farm, Caroni plains", "lat": 10.60, "lon": -61.38, "place": "Caroni, Trinidad",
                 "size": 3, "size_unit": "acres", "crops": ["Corn", "Tomato"], "soil_type": profile.SOIL_TYPES[1],
                 "water": profile.WATER[0], "equipment": ["Hand tools only", "Water pump", "Smartphone camera"], "wet_field": True},
}


# ---------------------------------------------------------------------------
# Profile <-> session
# ---------------------------------------------------------------------------

def P():
    return st.session_state.get("fs_profile")


def apply_profile(p):
    """Write the profile into the session keys the engine already uses."""
    ss = st.session_state
    old = ss.get("fs_profile") or {}
    ss.fs_profile = p
    ss.farm_latitude, ss.farm_longitude = round(float(p["lat"]), 4), round(float(p["lon"]), 4)
    demo = next((k for k, f in ui.FARMS.items() if abs(f["lat"] - p["lat"]) < .05 and abs(f["lon"] - p["lon"]) < .05), None)
    ss.fs_demo = demo
    ss.fs_located = True
    ss.fs_irrigation = profile.irrigation(p)
    ss.fs_wet_field = bool(p.get("wet_field"))
    ss.fs_soil_override = profile.soil_override(p)
    if p.get("crops") != old.get("crops") or "fs_current" not in ss or old.get("lat") != p.get("lat"):
        crops = planner.load_crops()
        rows = profile.rotation_from_crops(p.get("crops") or [], TODAY().month, crops)
        if demo and p.get("crops") == DEMO_PROFILES.get(demo, {}).get("crops"):
            rows = list(ui.FARMS[demo]["current"])
        ss.fs_current = rows or []
    try:
        st.query_params["p"] = profile.encode(p)
        for k in ("farm", "lat", "lon"):
            if k in st.query_params:
                del st.query_params[k]
    except Exception:  # noqa: BLE001
        pass


def restore_profile():
    """From ?p= (bookmarked link) or ?farm=jamaica|trinidad (demo links)."""
    if P():
        return True
    q = st.query_params
    if q.get("p"):
        p = profile.decode(q.get("p"))
        if p:
            apply_profile(p)
            return True
    if q.get("farm") in DEMO_PROFILES:
        p = profile.new()
        p.update(DEMO_PROFILES[q.get("farm")])
        apply_profile(p)
        return True
    return False


def bundle():
    ss = st.session_state
    return ui.load_site(ss.farm_latitude, ss.farm_longitude)


def badge(kind):
    label = {"data": "Measured data", "model": "Model estimate", "yours": "Your numbers", "sim": "Simulated example"}[kind]
    return f'<span class="fs-badge {kind}">{label}</span>'


# ---------------------------------------------------------------------------
# Shell: world, display settings, top bar
# ---------------------------------------------------------------------------

def shell(depth, key):
    """Common page frame. Returns the farm bundle (or None for pages that need none)."""
    ss = st.session_state
    journey.install_static(st, depth, dark=ss.get("fs_dark", False), zoom=ss.get("fs_zoom", 1.0))
    st.markdown(journey.EXTRA_CSS, unsafe_allow_html=True)
    p = P()
    with st.container(key="topbar"):
        c1, c2, c3 = st.columns([3.2, 1, 1])
        mode = profile.MODES[p["mode"]]
        caribbean = p.get("lat") is not None and news.region_of(p["lat"], p["lon"]) == "Caribbean"
        c1.markdown(f'<div class="al-kicker">FarmFit · {"Caribbean farm" if caribbean else "Farm"} resilience · {mode}</div>'
                    f'<div style="font:600 1.2rem Fraunces,serif;color:{art.INK}">{p.get("name") or p.get("place") or "My farm"}'
                    f'<span style="font:400 .85rem InterVar,sans-serif;color:{art.INK2}"> · {p["lat"]:.3f}°, {p["lon"]:.3f}°</span></div>',
                    unsafe_allow_html=True)
        with c2.popover("Display", use_container_width=True):
            display_settings()
        c3.page_link(ss.fs_pages["myfarm"], label="Edit farm", icon=":material/edit:", use_container_width=True)
    return key


def display_settings():
    ss = st.session_state
    lang = st.selectbox("Language", list(LANGS), index=list(LANGS).index(ss.fs_lang), format_func=LANGS.get)
    zoom = st.select_slider("Text size", options=[0.9, 1.0, 1.15, 1.3], value=ss.get("fs_zoom", 1.0),
                            format_func=lambda z: {0.9: "Small", 1.0: "Normal", 1.15: "Large", 1.3: "Largest"}[z])
    dark = st.toggle("Dark mode", value=ss.get("fs_dark", False))
    if (lang, zoom, dark) != (ss.fs_lang, ss.get("fs_zoom", 1.0), ss.get("fs_dark", False)):
        ss.fs_lang, ss.fs_zoom, ss.fs_dark = lang, zoom, dark
        st.rerun()


def hero(kicker, head, dek=""):
    st.markdown(f'<div class="fs-hero2"><div class="k">{kicker}</div><div class="h">{head}</div>'
                + (f'<div class="d">{dek}</div>' if dek else "") + "</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

STEPS = ["Who it's for", "Location", "Your land", "Crops & water", "Done"]


def onboarding():
    ss = st.session_state
    journey.install_static(st, "sky", dark=ss.get("fs_dark", False), zoom=ss.get("fs_zoom", 1.0))
    st.markdown(journey.EXTRA_CSS, unsafe_allow_html=True)
    step = ss.setdefault("ob_step", 0)
    draft = ss.setdefault("ob_draft", profile.new())
    hero("NASA Space Apps 2026 · Field Shift", "Hurricane to Harvest",
         "Farm intelligence for the Caribbean: plan the year around storms and drought, recover faster, and share what you "
         "see with farmers nearby. Let's set up your farm or garden first: it takes about a minute.")
    with st.container(key="onboard"):
        left, right = st.columns([1, 4.2], gap="medium")
        with left:
            st.markdown(f'<div style="text-align:center">{journey.growth_tree(step + (1 if step == 4 else 0))}</div>',
                        unsafe_allow_html=True)
        with right:
            st.markdown('<div class="fs-steps">' + "".join(
                f'<span class="{"on" if i == step else "done" if i < step else ""}">{i + 1} · {s}</span>' for i, s in enumerate(STEPS))
                + "</div>", unsafe_allow_html=True)
            [ob_who, ob_where, ob_land, ob_crops, ob_done][step](draft)


def _nav(back=True, next_label="Next", disabled=False):
    ss = st.session_state
    c1, c2, _ = st.columns([1, 1.3, 3])
    if back and c1.button("Back", use_container_width=True):
        ss.ob_step -= 1
        st.rerun()
    if c2.button(next_label, type="primary", use_container_width=True, disabled=disabled):
        ss.ob_step += 1
        st.rerun()


def ob_who(d):
    ss = st.session_state
    st.markdown("### Who is FarmFit for today?")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="fs-demo">{journey.ICON_FARM}<div><b>A farm</b><div class="s">Fields, crops for sale, livestock. Full planning, '
                    'storm, market and recovery tools.</div></div></div>', unsafe_allow_html=True)
        if st.button("Set up a farm", use_container_width=True, type="primary" if d["mode"] == "farm" else "secondary"):
            d["mode"] = "farm"
            ss.ob_step = 1
            st.rerun()
    with c2:
        st.markdown(f'<div class="fs-demo">{journey.ICON_GARDEN}<div><b>A home garden</b><div class="s">Pots, a backyard bed or a balcony. Simple, '
                    'beginner-friendly guidance.</div></div></div>', unsafe_allow_html=True)
        if st.button("Set up a home garden", use_container_width=True, type="primary" if d["mode"] == "garden" else "secondary"):
            d["mode"] = "garden"
            ss.ob_step = 1
            st.rerun()
    st.markdown("**Just looking?** Open an example farm (example values, not a real farm's records):")
    e1, e2, e3 = st.columns([1, 1, 1.4])
    for col, key, label in ((e1, "jamaica", "St Elizabeth, Jamaica"), (e2, "trinidad", "Caroni plains, Trinidad")):
        if col.button(label, use_container_width=True, key=f"ex_{key}"):
            p = profile.new()
            p.update(DEMO_PROFILES[key])
            apply_profile(p)
            st.rerun()
    with e3.popover("Load a saved farm file", use_container_width=True):
        up = st.file_uploader("FarmFit farm file (.json)", type=["json"], label_visibility="collapsed")
        if up:
            p = profile.from_json(up.getvalue().decode("utf-8", "ignore"))
            if p:
                apply_profile(p)
                st.rerun()
            st.error("That file is not a FarmFit farm file.")
    lang = st.selectbox("Language", list(LANGS), index=list(LANGS).index(ss.fs_lang), format_func=LANGS.get)
    if lang != ss.fs_lang:
        ss.fs_lang = lang
        st.rerun()


def ob_where(d):
    ss = st.session_state
    noun = "farm" if d["mode"] == "farm" else "garden"
    st.markdown(f"### Where is your {noun}?")
    d["name"] = st.text_input(f"{noun.title()} name (optional)", value=d.get("name", ""), placeholder="e.g. Ramdass family farm")
    q = st.text_input("Search for your village, district or town", placeholder="e.g. Penal, Trinidad · Santa Cruz, Jamaica")
    hits = ui.geocode(q) if q and len(q) > 2 else []
    if hits:
        pick = st.radio("Matches", range(len(hits)), format_func=lambda i: hits[i]["label"], label_visibility="collapsed")
        if (hits[pick]["lat"], hits[pick]["lon"]) != (d.get("lat"), d.get("lon")):
            d["lat"], d["lon"], d["place"] = hits[pick]["lat"], hits[pick]["lon"], hits[pick]["label"]
    elif q and len(q) > 2:
        st.caption("No match found. Try a nearby town, or tap the map.")
    centre = [d["lat"], d["lon"]] if d.get("lat") is not None else [14.5, -68.0]
    m = folium.Map(location=centre, zoom_start=12 if d.get("lat") is not None else 5, tiles=None, control_scale=True)
    folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                     attr="Esri World Imagery", name="Satellite").add_to(m)
    folium.TileLayer("OpenStreetMap", name="Street map").add_to(m)
    if d.get("lat") is not None:
        folium.Marker(centre, icon=folium.Icon(color="green", icon="leaf")).add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    out = st_folium(m, height=320, width=None, key="ob_map", returned_objects=["last_clicked"])
    if out and out.get("last_clicked"):
        new = (round(out["last_clicked"]["lat"], 4), round(out["last_clicked"]["lng"], 4))
        if new != (d.get("lat"), d.get("lon")):
            d["lat"], d["lon"], d["place"] = new[0], new[1], d.get("place") or ""
            st.rerun()
    with st.expander("Or type your coordinates (from your phone's map app)"):
        c1, c2, c3 = st.columns([1, 1, 1])
        la = c1.number_input("Latitude", -90.0, 90.0, float(d.get("lat") or 10.6), format="%.4f", key="ob_lat")
        lo = c2.number_input("Longitude", -180.0, 180.0, float(d.get("lon") or -61.4), format="%.4f", key="ob_lon")
        if c3.button("Use these", use_container_width=True):
            d["lat"], d["lon"] = round(la, 4), round(lo, 4)
            st.rerun()
    st.caption("Tap your field on the map for the best results. Your exact location stays in your browser link and is never "
               "shown to other farmers.")
    if d.get("lat") is not None:
        st.success(f"Location set: {d['lat']:.4f}, {d['lon']:.4f} {('· ' + d['place']) if d.get('place') else ''}")
    _nav(disabled=d.get("lat") is None)


def ob_land(d):
    if d["mode"] == "farm":
        st.markdown("### Your land")
        c1, c2 = st.columns([1, 1])
        d["size"] = c1.number_input("Farm size (optional)", min_value=0.0, value=float(d["size"] or 0), step=0.5) or None
        d["size_unit"] = c2.selectbox("Unit", list(profile.SIZE_UNITS), index=list(profile.SIZE_UNITS).index(d.get("size_unit", "acres")))
        d["wet_field"] = st.toggle("My field is low-lying and I can hold water on it (e.g. for rice or dasheen)", value=d.get("wet_field", False))
    else:
        st.markdown("### Your growing space")
        d["garden_space"] = st.multiselect("Where will you grow?", profile.GARDEN_SPACES, default=d.get("garden_space", []))
        d["sun_hours"] = st.select_slider("Direct sun on the spot", options=["Under 3 hours", "3-6 hours", "6+ hours"],
                                          value=d.get("sun_hours") or "6+ hours")
    d["soil_type"] = st.radio("What is your soil like? (skip if unsure)", profile.SOIL_TYPES,
                              index=profile.SOIL_TYPES.index(d.get("soil_type", profile.SOIL_TYPES[0])), horizontal=True)
    know_ph = st.checkbox("I have a soil test with pH", value=bool(d.get("ph")))
    d["ph"] = st.slider("Soil pH", 4.0, 9.0, float(d.get("ph") or 6.5), 0.1) if know_ph else None
    st.caption("Not sure? That's fine. FarmFit uses ISRIC SoilGrids satellite-based soil maps until you know more.")
    _nav()


def ob_crops(d):
    crops = planner.load_crops()
    if d["mode"] == "farm":
        st.markdown("### What you grow, and your water")
        names = [c for c in crops.index if crops.loc[c, "harvest_value"] > 0]
        d["crops"] = st.multiselect("Crops you grow now or plan to grow (up to 4)", names, default=d.get("crops", []), max_selections=4)
    else:
        st.markdown("### What you'd like to grow, and your water")
        names = [c[0] for c in garden.CROPS]
        d["crops"] = st.multiselect("Plants you grow or would like to try", names, default=[c for c in d.get("crops", []) if c in names])
    d["water"] = st.radio("Water for your plants", profile.WATER, index=profile.WATER.index(d.get("water", profile.WATER[0])))
    d["equipment"] = st.multiselect("Equipment you have (optional)", profile.EQUIPMENT, default=d.get("equipment", []))
    d["notes"] = st.text_area("Anything else we should know? (optional)", value=d.get("notes", ""),
                              placeholder="e.g. goats on the farm, field floods every October, organic only")
    _nav(next_label="Finish")


def ob_done(d):
    ss = st.session_state
    noun = "farm" if d["mode"] == "farm" else "garden"
    st.markdown(f"### Your {noun} is set up")
    st.markdown(f"**{d.get('name') or d.get('place') or 'My ' + noun}** · {d['lat']:.3f}, {d['lon']:.3f}"
                + (f" · {d['size']} {d['size_unit']}" if d.get("size") else "")
                + (f" · {', '.join(d['crops'])}" if d.get("crops") else ""))
    st.markdown("FarmFit will now pull 30 years of NASA climate data, every storm since 1971 and the soil for this spot. "
                "You can change anything later from **Edit farm**.")
    c1, c2, _ = st.columns([1, 1.6, 2.5])
    if c1.button("Back", use_container_width=True):
        ss.ob_step -= 1
        st.rerun()
    if c2.button(f"Open my {noun} dashboard", type="primary", use_container_width=True):
        apply_profile(dict(d))
        ss.ob_step = 0
        st.rerun()


# ---------------------------------------------------------------------------
# Shared computations
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def windows(lat, lon, irrigation, ov_ph, ov_drain, crops_key):
    b = ui.load_site(lat, lon)
    site = ui.build_site(b, {"ph": ov_ph, "drainage": ov_drain})
    crops = planner.load_crops()
    return {c: planner.planting_window(site, crops, c, irrigation, n_years=2500) for c in crops_key}


def harvest_crops():
    """Food and cash crops this farm can grow: wet-field crops (rice, dasheen) only where water can be held."""
    ss = st.session_state
    crops = planner.load_crops()
    ok = planner.allowed_crops(crops, wet_field=ss.get("fs_wet_field", False), exclude=ss.get("fs_exclude", []))
    return [c for c in ok if crops.loc[c, "harvest_value"] > 0]


def crop_windows(names):
    ss = st.session_state
    ov = ss.get("fs_soil_override", {})
    return windows(ss.farm_latitude, ss.farm_longitude, ss.fs_irrigation, ov.get("ph"), ov.get("drainage"), tuple(sorted(names)))


def verdict(w, month):
    now = w[month - 1]["p_good"]
    best = max(w, key=lambda x: x["p_good"])
    if best["p_good"] < 0.3:
        return "Poor fit here", "#9aa3ad", f"Even its best month ({MONTHS[best['start'] - 1]}) scores only {journey.pct(best['p_good'])}."
    if now >= 0.5 and now >= best["p_good"] - 0.08:
        return "Plant now", art.LEAF, f"{journey.pct(now)} chance of a good harvest this month, close to its best."
    if now >= 0.4 and now >= best["p_good"] - 0.2:
        return "OK now", art.OCHRE, f"{journey.pct(now)} now; {MONTHS[best['start'] - 1]} is better ({journey.pct(best['p_good'])})."
    return f"Wait for {MONTHS[best['start'] - 1]}", art.TERRA, (
        f"Only {journey.pct(now)} now: harvest would land in risky weeks. {MONTHS[best['start'] - 1]} gives {journey.pct(best['p_good'])}.")


def crop_card(name, w, month, why=None):
    word, colour, reason = verdict(w, month)
    return (f'<div class="fs-card"><div class="c">{name}</div><span class="v" style="background:{colour}">{word}</span>'
            f'{journey.spark([x["p_good"] for x in w], highlight=month - 1)}'
            f'<div class="w">{reason}{(" " + why) if why else ""}</div></div>')


def risk_levels(b):
    """Four plain risk gauges for this month: storm, drought, flood, heat."""
    m = TODAY().month
    clim = b["climate"].set_index("month")
    exp = b["exposure"].set_index("month")
    out = []
    p_storm = float(exp.loc[m, "p_storm_force"])
    live, _ = ui.load_active_storms(datetime.now().strftime("%Y%m%d%H"))
    threats = [stormwatch.threat(s, b["lat"], b["lon"]) for s in (live or [])]
    worst = max(threats, key=lambda x: {"act now": 3, "get ready": 2, "monitor": 1}.get(x.get("level"), 0), default=None)
    if worst and worst.get("level") in ("act now", "get ready"):
        out.append(("Storm", 0.9 if worst["level"] == "act now" else 0.65, "high" if worst["level"] == "act now" else "medium",
                    f"Live storm: {worst.get('level')}. See Storms."))
    else:
        lvl = "high" if p_storm >= 0.1 else "medium" if p_storm >= 0.03 else "low"
        out.append(("Storm", min(1, p_storm / 0.15), lvl, f"{p_storm:.0%} chance of storm-force wind in {MONTHS[m - 1]} (NOAA, since 1971)."))
    recent = ui.load_recent(b["lat"], b["lon"], TODAY().isoformat())
    an = water.rain_anomalies(b["daily"], recent)[0] if recent is not None and "daily" in b else []
    a60 = next((a for a in an if a["days"] == 60), None)
    if a60 and a60.get("percentile") is not None:
        pct = a60["percentile"]
        lvl = "high" if pct < 15 else "medium" if pct < 33 else "low"
        out.append(("Drought", 1 - pct / 100, lvl, f"Last 60 days: {water.ordinal(int(pct))} percentile of rain for the time of year."))
    else:
        o = ui.season_outlook(b)
        if o and o["now"]["phase"] != "Neutral" and o["by_phase"].get(o["now"]["phase"]):
            pc = o["by_phase"][o["now"]["phase"]]["pct_normal"]
            lvl = "high" if pc < 75 else "medium" if pc < 90 else "low"
            out.append(("Drought", max(0, min(1, (110 - pc) / 60)), lvl,
                        f"{o['now']['phase']} now; such years brought {pc:.0f}% of normal rain here next 3 months."))
        else:
            out.append(("Drought", None, "unknown", "Recent rain data not reachable right now."))
    p_heavy = float(clim.loc[m, "p_heavy_rain"])
    drain = (b.get("soil") or {}).get("drainage") or "Moderate"
    f = p_heavy * {"Fast": .6, "Good": .8, "Moderate": 1, "Slow": 1.25, "Very slow": 1.4}.get(drain, 1)
    lvl = "high" if f >= 0.12 else "medium" if f >= 0.05 else "low"
    out.append(("Flooding", min(1, f / 0.2), lvl, f"{p_heavy:.0%} of {MONTHS[m - 1]} days bring very heavy rain; soil drains {drain.lower()}."))
    tmax = float(clim.loc[m, "t_max"])
    lvl = "high" if tmax >= 33 else "medium" if tmax >= 31.5 else "low"
    out.append(("Heat", max(0, min(1, (tmax - 28) / 8)), lvl, f"Average daytime high in {MONTHS[m - 1]}: {tmax:.0f} °C."))
    return out


def forecast_chart(fc, height=190):
    d = fc.assign(day=fc["date"].dt.strftime("%a %d"))
    rain = alt.Chart(d).mark_bar(color=art.SEA, opacity=.85).encode(
        x=alt.X("day:N", sort=None, title=None, axis=alt.Axis(labelAngle=0, labelFontSize=9)),
        y=alt.Y("rain_mm:Q", title="rain mm"),
        tooltip=["day", alt.Tooltip("rain_mm:Q", title="rain (mm)", format=".1f"),
                 alt.Tooltip("rain_chance:Q", title="chance of rain (%)"), alt.Tooltip("tmax:Q", title="high °C", format=".0f"),
                 alt.Tooltip("tmin:Q", title="low °C", format=".0f"), alt.Tooltip("rh:Q", title="humidity %", format=".0f")])
    band = alt.Chart(d).mark_area(color=art.TERRA, opacity=.18).encode(x=alt.X("day:N", sort=None), y=alt.Y("tmin:Q", title="°C",
                                                                             scale=alt.Scale(zero=False)), y2="tmax:Q")
    hi = alt.Chart(d).mark_line(color=art.TERRA, point=True).encode(x=alt.X("day:N", sort=None), y="tmax:Q")
    return alt.layer(rain, alt.layer(band, hi)).resolve_scale(y="independent").properties(height=height)


# ---------------------------------------------------------------------------
# Home dashboard (farm)
# ---------------------------------------------------------------------------

def page_home():
    shell("home", "home")
    p, b = P(), bundle()
    if "climate" not in b:
        st.error("NASA POWER could not be reached for this point and no saved copy exists. Try again in a minute.")
        return
    m = TODAY().month
    hero(f"{MONTHS[m - 1]} {TODAY().year} · {p.get('place') or 'your farm'}", "Plant now, or wait?",
         "What this month means for your crops, the risks to watch, and the next two weeks of weather, worked out for this "
         "exact field from NASA and NOAA records.")
    with st.container(key="layer_home"):
        crops = planner.load_crops()
        mine = [c for c in (p.get("crops") or []) if c in crops.index][:4]
        others = [c for c in harvest_crops() if c not in mine]
        W = crop_windows(mine + others)
        st.markdown(art.heading("Your crops this month") + badge("model"), unsafe_allow_html=True)
        if mine:
            cols = st.columns(len(mine))
            for col, c in zip(cols, mine):
                col.markdown(crop_card(c, W[c], m), unsafe_allow_html=True)
        else:
            st.info("Add the crops you grow under **Edit farm** to see a verdict for each.")
        top = sorted(others, key=lambda c: -W[c][m - 1]["p_good"])[:4]
        st.markdown(art.heading("Good to plant in " + MONTHS[m - 1]), unsafe_allow_html=True)
        cols = st.columns(4)
        for col, c in zip(cols, top):
            col.markdown(crop_card(c, W[c], m), unsafe_allow_html=True)
        st.caption("Bars show each planting month, January to December; the outlined bar is this month. Chance of a good harvest = "
                   "simulated seasons from this farm's own storm and heavy-rain records × climate fit × whether your water covers "
                   "the crop's needs. Pests and prices are not included, so it is a guide, not a guarantee.")

        st.markdown(art.heading("Risks right now"), unsafe_allow_html=True)
        cols = st.columns(4)
        for col, (label, v, lvl, sub) in zip(cols, risk_levels(b)):
            col.markdown(journey.gauge(v, label, lvl, sub), unsafe_allow_html=True)
        st.markdown('<div class="al-note">Green = low, amber = watch, red = high. Each gauge says what it is based on.</div>',
                    unsafe_allow_html=True)

        st.markdown(art.heading("The next 16 days"), unsafe_allow_html=True)
        fc = ui.load_forecast(b["lat"], b["lon"], TODAY().isoformat())
        if fc is not None:
            st.altair_chart(forecast_chart(fc), use_container_width=True, theme=None)
            wet = int((fc["rain_mm"] >= 10).sum())
            st.caption(f"Rain (blue bars) and daytime high / night low (red band). {wet} day(s) with 10 mm or more of rain "
                       f"expected. Forecast from Open-Meteo (ECMWF and GFS models); confidence drops after about 7 days.")
        else:
            clim = b["climate"].set_index("month")
            st.info(f"Forecast not reachable right now. Normal for {MONTHS[m - 1]}: {clim.loc[m, 'rain_mm']:.0f} mm of rain, "
                    f"highs near {clim.loc[m, 't_max']:.0f} °C (NASA POWER, 30 years).")
        c1, c2 = st.columns([1.2, 1], gap="large")
        with c1:
            ui.render_season_ahead(b)
        with c2:
            st.markdown(art.heading("Near you"), unsafe_allow_html=True)
            near = community.nearby(community.load(), b["lat"], b["lon"], km=25, days=30)
            if near:
                st.markdown(f"**{len(near)}** pest or disease report(s) within 25 km in the last 30 days.")
                for r in near[:3]:
                    st.markdown(f"- {community.CATEGORIES[r['category']][0]} · {r['km']:.0f} km · {community.STATUS[r['status']]}")
            else:
                st.markdown("No pest or disease reports within 25 km in the last 30 days.")
            st.page_link(st.session_state.fs_pages["pests"], label="Open the pest & disease map", icon=":material/bug_report:")
            st.page_link(st.session_state.fs_pages["planner"], label="Plan the year", icon=":material/calendar_month:")
            st.page_link(st.session_state.fs_pages["storms"], label="Storm checklist", icon=":material/cyclone:")
        report_download(b)


def report_download(b):
    p = P()
    m = TODAY().month
    crops = [c for c in (p.get("crops") or []) if c in planner.load_crops().index]
    W = crop_windows(crops) if crops else {}
    rows = "".join(f"<tr><td>{c}</td><td>{verdict(W[c], m)[0]}</td><td>{verdict(W[c], m)[2]}</td></tr>" for c in crops)
    risks = "".join(f"<tr><td>{label}</td><td>{ {'low': 'Low', 'medium': 'Watch', 'high': 'High', 'unknown': 'No data'}[lvl]}</td>"
                    f"<td>{sub}</td></tr>" for label, _, lvl, sub in risk_levels(b))
    clim = b["climate"]
    normals = "".join(f"<td>{MONTHS[i]}<br><b>{r.rain_mm:.0f}</b> mm<br>{r.t_max:.0f} °C</td>" for i, r in enumerate(clim.itertuples()))
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>FarmFit summary</title>
<style>body{{font-family:Georgia,serif;max-width:820px;margin:2rem auto;color:#1F2B3A}} table{{border-collapse:collapse;width:100%;margin:.6rem 0 1.2rem 0}}
td,th{{border-bottom:1px solid #ccc;padding:.35rem .4rem;font:13px Arial;text-align:left;vertical-align:top}} h1{{margin-bottom:0}}
.k{{font:600 11px Arial;letter-spacing:.15em;text-transform:uppercase;color:#C2502F}} @media print{{button{{display:none}}}}</style></head>
<body><button onclick="print()">Print or save as PDF</button><div class="k">FarmFit · Hurricane to Harvest</div>
<h1>{p.get('name') or 'My farm'}</h1><p>{p.get('place', '')} ({p['lat']:.3f}, {p['lon']:.3f}) · {profile.MODES[p['mode']]}
{(' · ' + str(p['size']) + ' ' + p['size_unit']) if p.get('size') else ''} · Water: {p.get('water')} · Summary for {MONTHS[m - 1]} {TODAY().year}</p>
<h2>Plant now, or wait?</h2><table><tr><th>Crop</th><th>Verdict</th><th>Why</th></tr>{rows or '<tr><td colspan=3>No crops entered</td></tr>'}</table>
<h2>Risks this month</h2><table><tr><th>Risk</th><th>Level</th><th>Based on</th></tr>{risks}</table>
<h2>Normal rain and daytime highs (NASA POWER, 30 years)</h2><table><tr>{normals}</tr></table>
<p style="font:12px Arial">Chances are model estimates from this farm's NOAA storm and NASA rain records, climate fit and water access; they leave out pests,
prices and luck. Check plans with your extension officer. Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC.</p></body></html>"""
    st.download_button("Download my farm summary (printable)", html, file_name="farmfit_summary.html", mime="text/html",
                       icon=":material/download:")


# ---------------------------------------------------------------------------
# My farm
# ---------------------------------------------------------------------------

def page_myfarm():
    shell("soil", "myfarm")
    ss = st.session_state
    p, b = P(), bundle()
    hero("My farm" if p["mode"] == "farm" else "My garden", "What we know about this place",
         "Your answers, plus what satellites and maps say. Anything you tell us replaces the satellite estimate.")
    with st.container(key="layer_myfarm"):
        st.markdown(art.heading("Hazard profile of this location"), unsafe_allow_html=True)
        hazard_profile(b)
        with st.expander("Edit my details", expanded=False):
            d = dict(p)
            c1, c2 = st.columns(2)
            d["name"] = c1.text_input("Name", value=d.get("name", ""))
            d["mode"] = c2.radio("Type", list(profile.MODES), format_func=profile.MODES.get, index=list(profile.MODES).index(d["mode"]),
                                 horizontal=True)
            c1, c2, c3 = st.columns(3)
            d["lat"] = c1.number_input("Latitude", value=float(d["lat"]), format="%.4f")
            d["lon"] = c2.number_input("Longitude", value=float(d["lon"]), format="%.4f")
            d["size"] = c3.number_input(f"Size ({d.get('size_unit', 'acres')})", min_value=0.0, value=float(d.get("size") or 0)) or None
            crops = planner.load_crops()
            names = [c for c in crops.index if crops.loc[c, "harvest_value"] > 0] + [c[0] for c in garden.CROPS if not c[1]]
            d["crops"] = st.multiselect("Crops", names, default=[c for c in d.get("crops", []) if c in names], max_selections=6)
            c1, c2 = st.columns(2)
            d["soil_type"] = c1.selectbox("Soil type", profile.SOIL_TYPES, index=profile.SOIL_TYPES.index(d.get("soil_type", profile.SOIL_TYPES[0])))
            ph_known = c2.checkbox("I know my soil pH", value=bool(d.get("ph")))
            d["ph"] = c2.slider("pH", 4.0, 9.0, float(d.get("ph") or 6.5), .1) if ph_known else None
            d["water"] = st.radio("Water", profile.WATER, index=profile.WATER.index(d.get("water", profile.WATER[0])), horizontal=True)
            d["wet_field"] = st.toggle("Low-lying field where I can hold water", value=bool(d.get("wet_field")))
            d["equipment"] = st.multiselect("Equipment and sensors", profile.EQUIPMENT, default=d.get("equipment", []))
            d["notes"] = st.text_area("Notes", value=d.get("notes", ""))
            if st.button("Save changes", type="primary"):
                apply_profile(d)
                st.success("Saved. Every page now uses these details.")
                st.rerun()
        c1, c2, c3 = st.columns(3)
        c1.download_button("Download my farm file", profile.to_json(p), file_name="farmfit_farm.json", mime="application/json",
                           use_container_width=True, icon=":material/save:")
        c2.markdown(f"[Bookmark this link to come back]({'?p=' + profile.encode(p)})")
        if c3.button("Start over with a new farm", use_container_width=True):
            for k in ("fs_profile", "ob_draft", "ob_step"):
                ss.pop(k, None)
            st.query_params.clear()
            st.rerun()
        ui.render_soil(b)


def hazard_profile(b):
    soil, terr = b.get("soil") or {}, b.get("terrain") or {}
    clim = b["climate"].set_index("month")
    summ = b["storm_summary"]
    drain = soil.get("drainage") or "unknown"
    slope = float(terr.get("slope_pct") or 0)
    elev = float(terr.get("elevation_m") or 0)
    wettest = clim["p_heavy_rain"].idxmax()
    flood = ("high" if drain in ("Slow", "Very slow") and slope < 2 and elev < 30 else
             "medium" if drain in ("Slow", "Very slow") or (slope < 1 and elev < 15) else "low")
    dry = clim[clim["rain_mm"] < 60]
    drought = "high" if len(dry) >= 4 else "medium" if len(dry) >= 2 else "low"
    rp = summ.get("return_period_storm_force")
    storm = "high" if rp and rp <= 5 else "medium" if rp and rp <= 12 else "low"
    erosion = "high" if slope > 12 else "medium" if slope > 5 else "low"
    items = [
        ("Flooding and waterlogging", flood, f"Soil drains {drain.lower()}, slope {slope:.1f}%, {elev:.0f} m above sea level. "
         f"Heaviest-rain month: {MONTHS[wettest - 1]}."),
        ("Drought and dry spells", drought, f"{len(dry)} month(s) a year get under 60 mm of rain"
         + (f" ({', '.join(MONTHS[i - 1] for i in dry.index)})." if len(dry) else ".")),
        ("Storms and hurricanes", storm, f"Storm-force wind about 1 year in {rp:.0f} (NOAA, 1971-2025)." if rp else "No storm-force wind since 1971."),
        ("Soil erosion", erosion, f"Slope {slope:.1f}% (NASA SRTM 30 m)."),
    ]
    cols = st.columns(4)
    advice = {"Flooding and waterlogging": "Raised beds, open drains before the rains, flood-tolerant crops in wet months.",
              "Drought and dry spells": "Mulch, store water, plant drought-tolerant crops for the dry season.",
              "Storms and hurricanes": "Harvest before Aug-Oct where you can; keep low, sturdy crops in the field then.",
              "Soil erosion": "Plant across the slope, keep the ground covered, hedgerows of pigeon peas or vetiver."}
    for col, (label, lvl, why) in zip(cols, items):
        v = {"low": .2, "medium": .52, "high": .85}[lvl]
        col.markdown(journey.gauge(v, label, lvl, why), unsafe_allow_html=True)
        col.caption(advice[label])
    st.caption("Based on NASA POWER rainfall, ISRIC SoilGrids drainage, NASA SRTM terrain and NOAA storm tracks. Flood risk here is "
               "about drainage and terrain; it is not an official flood-zone map, so check with your local drainage authority.")


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------

def monthly_history(daily):
    d = daily[["PRECTOTCORR"]].copy()
    d["year"], d["month"] = d.index.year, d.index.month
    tot = d.groupby(["year", "month"])["PRECTOTCORR"].sum().reset_index()
    q = tot.groupby("month")["PRECTOTCORR"].quantile([.1, .5, .9]).unstack()
    q.columns = ["p10", "p50", "p90"]
    return q.reset_index()


def page_weather():
    shell("sky", "weather")
    p, b = P(), bundle()
    hero("Weather intelligence", "Rain, heat and humidity on this farm",
         "Next 16 days from weather models; 30 years of NASA history to show what is normal and what is not.")
    with st.container(key="layer_weather"):
        st.markdown(art.heading("Next 16 days") + badge("model"), unsafe_allow_html=True)
        fc = ui.load_forecast(b["lat"], b["lon"], TODAY().isoformat())
        if fc is not None:
            st.altair_chart(forecast_chart(fc, 220), use_container_width=True, theme=None)
            c = st.columns(4)
            c[0].metric("Rain, next 7 days", f"{fc['rain_mm'].head(7).sum():.0f} mm")
            c[1].metric("Rain, days 8-16", f"{fc['rain_mm'].iloc[7:].sum():.0f} mm")
            c[2].metric("Hottest day", f"{fc['tmax'].max():.0f} °C")
            if fc["rh"].notna().any():
                c[3].metric("Average humidity", f"{fc['rh'].mean():.0f}%")
            hum = fc.assign(day=fc["date"].dt.strftime("%a %d"))
            if fc["rh"].notna().any():
                st.altair_chart(alt.Chart(hum).mark_line(color=art.SEA, point=True).encode(
                    x=alt.X("day:N", sort=None, title=None, axis=alt.Axis(labelAngle=0, labelFontSize=9)),
                    y=alt.Y("rh:Q", title="humidity %", scale=alt.Scale(domain=[40, 100])),
                    tooltip=["day", alt.Tooltip("rh:Q", format=".0f")]).properties(height=120,
                    title="Humidity: above about 85% for days on end favours fungal disease"), use_container_width=True, theme=None)
            st.caption("Open-Meteo (ECMWF and GFS models). Confidence drops after about a week; for official warnings use the "
                       "Trinidad and Tobago Meteorological Service or your national met service.")
        else:
            st.info("The forecast service is not reachable right now; the 30-year normals below still apply.")

        st.markdown(art.heading("Rain through the year: normal range and this year") + badge("data"), unsafe_allow_html=True)
        hist = monthly_history(b["daily"])
        hist["mon"] = [MONTHS[i - 1] for i in hist["month"]]
        band = alt.Chart(hist).mark_area(color=art.SEA, opacity=.18).encode(
            x=alt.X("mon:N", sort=MONTHS, title=None), y=alt.Y("p10:Q", title="mm per month"), y2="p90:Q")
        med = alt.Chart(hist).mark_line(color=art.SEA, strokeWidth=2.5, point=True).encode(
            x=alt.X("mon:N", sort=MONTHS), y="p50:Q",
            tooltip=[alt.Tooltip("mon:N", title="month"), alt.Tooltip("p50:Q", title="typical (mm)", format=".0f"),
                     alt.Tooltip("p10:Q", title="dry year (mm)", format=".0f"), alt.Tooltip("p90:Q", title="wet year (mm)", format=".0f")])
        layers = [band, med]
        recent = ui.load_recent(b["lat"], b["lon"], TODAY().isoformat())
        if recent is not None and len(recent):
            r = recent["PRECTOTCORR"].resample("MS").sum()
            r = r[r.index.month != TODAY().month] if len(r) > 1 else r
            rr = pd.DataFrame({"mon": [MONTHS[d.month - 1] for d in r.index], "mm": r.values})
            layers.append(alt.Chart(rr).mark_point(shape="diamond", size=110, filled=True, color=art.TERRA).encode(
                x=alt.X("mon:N", sort=MONTHS), y="mm:Q", tooltip=["mon", alt.Tooltip("mm:Q", format=".0f")]))
        st.altair_chart(alt.layer(*layers).properties(height=230), use_container_width=True, theme=None)
        st.caption("Blue line: typical month; shaded band: from a dry year (1 in 10) to a wet year (1 in 10), NASA POWER 1996-2025. "
                   "Red diamonds: recent months this year.")

        clim = b["climate"].copy()
        clim["mon"] = [MONTHS[i - 1] for i in clim["month"]]
        rh = b["daily"]["RH2M"].groupby(b["daily"].index.month).mean() if "RH2M" in b["daily"] else None
        if rh is not None:
            clim["rh"] = rh.values
        c1, c2 = st.columns(2)
        t_band = alt.Chart(clim).mark_area(color=art.TERRA, opacity=.2).encode(
            x=alt.X("mon:N", sort=MONTHS, title=None), y=alt.Y("t_min:Q", title="°C", scale=alt.Scale(zero=False)), y2="t_max:Q")
        t_hi = alt.Chart(clim).mark_line(color=art.TERRA, point=True).encode(x=alt.X("mon:N", sort=MONTHS), y="t_max:Q",
                                                                            tooltip=["mon", alt.Tooltip("t_max:Q", format=".1f")])
        c1.altair_chart(alt.layer(t_band, t_hi).properties(height=200, title="Day highs and night lows (normal)"),
                        use_container_width=True, theme=None)
        if rh is not None:
            c2.altair_chart(alt.Chart(clim).mark_bar(color=art.SEA, opacity=.8).encode(
                x=alt.X("mon:N", sort=MONTHS, title=None), y=alt.Y("rh:Q", title="%", scale=alt.Scale(domain=[50, 100])),
                tooltip=["mon", alt.Tooltip("rh:Q", format=".0f")]).properties(height=200, title="Humidity (normal)"),
                use_container_width=True, theme=None)
        heavy = clim.assign(days=clim["p_heavy_rain"] * 30.4)
        st.altair_chart(alt.Chart(heavy).mark_bar(color=art.TERRA, opacity=.75).encode(
            x=alt.X("mon:N", sort=MONTHS, title=None), y=alt.Y("days:Q", title="days"),
            tooltip=["mon", alt.Tooltip("days:Q", format=".1f", title="days per month")]).properties(
            height=150, title="Very heavy rain days per month (waterlogging and erosion risk)"), use_container_width=True, theme=None)
    with st.container(key="layer_water"):
        ui.render_water(b)


# ---------------------------------------------------------------------------
# Crops & market
# ---------------------------------------------------------------------------

def page_crops():
    shell("field", "crops")
    p, b = P(), bundle()
    hero("Crops & market", "Which crop, when, and is it worth it?",
         "Weather suitability is only half the decision. Compare crops on growing conditions, risk, water, time to harvest and "
         "market prices: each number is labelled by where it comes from.")
    crops = planner.load_crops()
    names = harvest_crops()
    W = crop_windows(names)
    with st.container(key="layer_crops"):
        st.markdown(art.heading("Chance of a good harvest, by crop and planting month") + badge("model"), unsafe_allow_html=True)
        rows = [{"crop": c, "month": MONTHS[w["start"] - 1], "m": w["start"], "chance": w["p_good"], "safe": w["p_safe"],
                 "fit": w["fit"], "water": w["water_need"]} for c in names for w in W[c]]
        df = pd.DataFrame(rows)
        order = df.groupby("crop")["chance"].max().sort_values(ascending=False).index.tolist()
        heat = alt.Chart(df).mark_rect(stroke="#F3EEE3", strokeWidth=1.5).encode(
            x=alt.X("month:N", sort=MONTHS, title="planting month", axis=alt.Axis(labelAngle=0, orient="top")),
            y=alt.Y("crop:N", sort=order, title=None),
            color=alt.Color("chance:Q", title="chance", scale=alt.Scale(domain=[0, .5, .95], range=["#E9D9C4", "#D99A2B", "#3F7A4C"]),
                            legend=alt.Legend(format=".0%", orient="bottom")),
            tooltip=["crop", "month", alt.Tooltip("chance:Q", format=".0%", title="good harvest"),
                     alt.Tooltip("safe:Q", format=".0%", title="safe from storms/floods"), alt.Tooltip("fit:Q", format=".2f", title="climate fit"),
                     alt.Tooltip("water:Q", format=".0f", title="irrigation need (mm)")])
        now_rule = alt.Chart(pd.DataFrame({"month": [MONTHS[TODAY().month - 1]]})).mark_rect(fill=None, stroke=art.INK, strokeWidth=2).encode(
            x=alt.X("month:N", sort=MONTHS))
        st.altair_chart((heat + now_rule).properties(height=max(320, 22 * len(order))), use_container_width=True, theme=None)
        st.caption("Dark green = good bet, ochre = mixed, pale = poor. The outlined column is this month. Hover any square for "
                   "the reasons. Rice and dasheen only appear for low-lying fields that can hold water. Same model as the home page: storm and heavy-rain records for this farm, FAO climate ranges, "
                   "and your water.")

        st.markdown(art.heading("Compare crops side by side"), unsafe_allow_html=True)
        default = [c for c in (p.get("crops") or []) if c in names][:2] + order[:2]
        pick = st.multiselect("Choose 2 to 4 crops", names, default=list(dict.fromkeys(default))[:4], max_selections=4)
        prices = ui.PRICES()
        if pick:
            compare_crops(pick, W, crops, prices)
        profit_calculator(pick, prices, p)
        market_trends(pick, prices)


def compare_crops(pick, W, crops, prices):
    m = TODAY().month
    rows = []
    for c in pick:
        w = W[c]
        best = max(w, key=lambda x: x["p_good"])
        idx = market.price_index(prices, c) if prices is not None else None
        rows.append({
            "Crop": c,
            "Chance if planted now": w[m - 1]["p_good"],
            "Best month": f"{MONTHS[best['start'] - 1]} ({journey.pct(best['p_good'])})",
            "Storm & flood safety (best month)": best["p_safe"],
            "Climate fit": best["fit"],
            "Irrigation need, best month (mm)": round(best["water_need"]),
            "Days to harvest": int(crops.loc[c, "days_to_harvest"]),
            "Nitrogen": "Makes its own" if crops.loc[c, "n_fixing"] else "Needs fertiliser",
            "Price at harvest vs yearly average": (f"{idx[best['harvest']]:.2f}×" if idx and best["harvest"] in idx else "no price data"),
        })
    df = pd.DataFrame(rows).set_index("Crop")
    st.dataframe(df, use_container_width=True, column_config={
        "Chance if planted now": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
        "Storm & flood safety (best month)": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
        "Climate fit": st.column_config.ProgressColumn(format="%.2f", min_value=0, max_value=1)})
    st.markdown(f'<div class="al-note">{badge("model")} chance, safety, fit and irrigation need are FarmFit model estimates from '
                f'NASA POWER, NOAA storm tracks and FAO crop ranges. {badge("data")} days to harvest are FAO / CARDI reference '
                f'values and prices are NAMDEVCO wholesale records. Labour and fertiliser costs are not in any open dataset we '
                f'could verify, so enter your own below.</div>', unsafe_allow_html=True)


def profit_calculator(pick, prices, p):
    if not pick:
        return
    st.markdown(art.heading("Will it pay? Your own numbers") + badge("yours"), unsafe_allow_html=True)
    area_ha = profile.hectares(p) or 0.4
    unit = p.get("size_unit", "acres") if p.get("size") else "acres"
    st.caption(f"FarmFit does not guess yields or costs. Enter what you usually get and spend; the price starts at the NAMDEVCO "
               f"wholesale median where we have it. Area used: {area_ha / profile.SIZE_UNITS.get(unit, 1):.2f} {unit}.")
    rows = []
    for c in pick:
        med = None
        if prices is not None:
            for word in market.ALIASES.get(c, []):
                sub = prices[prices["commodity"].str.lower().str.contains(word, regex=False)]
                if len(sub):
                    med = float(sub["price"].median())
                    break
        rows.append({"Crop": c, "Yield per acre (kg)": None, "Price per kg ($)": round(med, 2) if med else None,
                     "Costs per acre ($)": None})
    ed = st.data_editor(pd.DataFrame(rows), hide_index=True, use_container_width=True, key="profit_ed",
                        disabled=["Crop"], column_config={"Price per kg ($)": st.column_config.NumberColumn(help="NAMDEVCO median if available")})
    acres = area_ha / profile.SIZE_UNITS["acres"]
    out = []
    for r in ed.itertuples():
        y, pr, cost = r[2], r[3], r[4]
        if pd.notna(y) and pd.notna(pr):
            rev = y * pr * acres
            out.append({"crop": r[1], "Revenue": rev, "Margin": rev - (cost if pd.notna(cost) else 0) * acres})
    if out:
        d = pd.DataFrame(out).melt("crop", var_name="what", value_name="dollars")
        st.altair_chart(alt.Chart(d).mark_bar().encode(
            x=alt.X("dollars:Q", title="$ for your area"), y=alt.Y("crop:N", title=None), yOffset="what:N",
            color=alt.Color("what:N", title=None, scale=alt.Scale(domain=["Revenue", "Margin"], range=[art.SEA, art.LEAF])),
            tooltip=["crop", "what", alt.Tooltip("dollars:Q", format=",.0f")]).properties(height=60 + 46 * len(out)),
            use_container_width=True, theme=None)
        st.caption("Your estimate from your own yield, price and cost figures; not a forecast.")


def market_trends(pick, prices):
    st.markdown(art.heading("When prices are usually high") + badge("data"), unsafe_allow_html=True)
    if prices is None:
        st.info("NAMDEVCO wholesale prices (Trinidad and Tobago open data) are downloaded by the scheduled data refresh and "
                "have not arrived yet. Run 'Refresh NASA data' in GitHub Actions to fetch them.")
        return
    rows = []
    for c in pick or []:
        idx = market.price_index(prices, c)
        if idx:
            rows += [{"crop": c, "month": MONTHS[k - 1], "index": v} for k, v in idx.items()]
    if not rows:
        st.caption("None of the chosen crops has enough NAMDEVCO price history yet.")
        return
    d = pd.DataFrame(rows)
    st.altair_chart(alt.Chart(d).mark_line(point=True).encode(
        x=alt.X("month:N", sort=MONTHS, title=None), y=alt.Y("index:Q", title="price ÷ yearly average", scale=alt.Scale(zero=False)),
        color=alt.Color("crop:N", title=None), tooltip=["crop", "month", alt.Tooltip("index:Q", format=".2f")]).properties(height=220),
        use_container_width=True, theme=None)
    st.caption("Above 1 = that month usually sells above the crop's yearly average at the Norris Deonarine Northern Wholesale "
               "Market (NAMDEVCO). Jamaica's Ministry of Agriculture publishes weekly farmgate prices for local checks.")


# ---------------------------------------------------------------------------
# Planner: four horizons
# ---------------------------------------------------------------------------

def page_planner():
    shell("field", "planner")
    p, b = P(), bundle()
    hero("Planning calendar", "Plan the next month, the year, five years and beyond",
         "Short-term plans use forecasts and this season's records. Longer plans use 30-year history and clearly labelled "
         "climate scenarios: nobody can forecast the weather years ahead, so those are what-ifs, not predictions.")
    with st.container(key="layer_planner"):
        horizon = st.segmented_control("Horizon", ["Next 3 months", "1 year", "5 years", "Beyond 5 years"], default="Next 3 months",
                                       label_visibility="collapsed", key="horizon")
        if horizon == "1 year":
            ui.render_plan(b)
        elif horizon == "5 years":
            five_year(b, p)
        elif horizon == "Beyond 5 years":
            long_term(b)
        else:
            next_months(b)


def next_months(b):
    m0 = TODAY().month
    clim = b["climate"].set_index("month")
    exp = b["exposure"].set_index("month")
    names = harvest_crops()
    W = crop_windows(names)
    o = ui.season_outlook(b)
    st.markdown(art.heading("The next three months") + badge("data") + badge("model"), unsafe_allow_html=True)
    cols = st.columns(3)
    drain = (b.get("soil") or {}).get("drainage") or "Moderate"
    for k, col in enumerate(cols):
        m = (m0 - 1 + k) % 12 + 1
        rain, heavy, storm = clim.loc[m, "rain_mm"], clim.loc[m, "p_heavy_rain"], exp.loc[m, "p_storm_force"]
        best = sorted(names, key=lambda c: -W[c][m - 1]["p_good"])[:3]
        tasks = []
        if storm >= 0.05:
            tasks.append("Storm season: keep fragile crops out, stake and tie, clear drains.")
        if rain < 60:
            tasks.append("Dry month: mulch, water early, plant drought-tolerant crops.")
        if heavy >= 0.08 or (rain > 180 and drain in ("Slow", "Very slow")):
            tasks.append("Wet month: raised beds and open drains before planting.")
        if not tasks:
            tasks.append("Good working month: prepare beds and plant.")
        with col:
            st.markdown(f"#### {MONTHS[m - 1]}")
            st.markdown(journey.gauge(min(1, storm / 0.15), "Storm", "high" if storm >= .1 else "medium" if storm >= .03 else "low",
                                     f"{storm:.0%} chance of storm-force wind"), unsafe_allow_html=True)
            st.metric("Normal rain", f"{rain:.0f} mm", help="NASA POWER 30-year average for this month")
            st.markdown("**Best to plant:** " + ", ".join(f"{c} ({journey.pct(W[c][m - 1]['p_good'])})" for c in best))
            for tk in tasks:
                st.markdown(f"- {tk}")
    if o:
        st.caption(f"This season: {o['now']['phase']} (ONI {o['now']['anom']:+.1f}). In past {o['now']['phase']} years this farm got "
                   f"{o['by_phase'].get(o['now']['phase'], {}).get('pct_normal', 100):.0f}% of normal rain over the next three months; "
                   "a tendency, not a forecast.")


def five_year(b, p):
    site, crops, current, plans, _ = ui.get_plans(b)
    soil, terr = b.get("soil") or {}, b.get("terrain") or {}
    summ = b["storm_summary"]
    rp = summ.get("return_period_storm_force")
    st.markdown(art.heading("A five-year roadmap for this farm"), unsafe_allow_html=True)
    seq = ["storm", "soil", "water", "soil", "storm"] if (rp and rp <= 8) else ["soil", "water", "soil", "storm", "water"]
    rows = []
    for y, key in enumerate(seq, start=1):
        plan = plans.get(key)
        if plan:
            for pl in plan.plantings:
                for k, mo in enumerate(pl.month_list()):
                    rows.append({"year": f"Year {y}", "month": MONTHS[mo - 1], "crop": pl.crop, "plan": plan.title,
                                 "group": crops.loc[pl.crop, "group"] if pl.crop in crops.index else ""})
    if rows:
        d = pd.DataFrame(rows)
        st.altair_chart(alt.Chart(d).mark_rect(stroke="#F3EEE3", strokeWidth=1).encode(
            x=alt.X("month:N", sort=MONTHS, title=None, axis=alt.Axis(orient="top", labelAngle=0)),
            y=alt.Y("year:N", title=None),
            color=alt.Color("group:N", title="crop type", legend=alt.Legend(orient="bottom")),
            tooltip=["year", "month", "crop", "plan", "group"]).properties(height=230), use_container_width=True, theme=None)
        st.caption("Each year alternates FarmFit's best plans for this farm (" + ", ".join(dict.fromkeys(r["plan"] for r in rows))
                   + ") so no crop family follows itself year after year, which breaks pest and disease cycles and builds soil.")
    milestones = [("Year 1", "Soil test (pH and nutrients) at your extension office; lime only if the test says so.")]
    if (soil.get("drainage") or "") in ("Slow", "Very slow"):
        milestones.append(("Year 1", f"Drainage: open field drains and raised beds (soil drains {soil['drainage'].lower()})."))
    if rp and rp <= 10:
        milestones.append(("Year 1-2", f"Windbreaks: plant rows of gliricidia, pigeon peas or vetiver on the windward side; storm-force "
                                       f"wind arrives about 1 year in {rp:.0f} here."))
    if float(terr.get("slope_pct") or 0) > 5:
        milestones.append(("Year 1-2", f"Contour hedgerows on the {terr['slope_pct']:.0f}% slope."))
    if profile.irrigation(p) != "Reliable irrigation":
        milestones.append(("Year 2", "Rain tank and drip lines sized with the storm water bank (Weather page)."))
    milestones += [("Every year", "A legume or cover crop in every rotation; keep crop and cost records."),
                   ("Year 3 and 5", "Repeat the soil test and compare."),
                   ("Year 5", "Review: which crops paid, which failed, and what the climate did. Adjust the next five years.")]
    st.markdown(art.heading("Land, water and protection milestones"), unsafe_allow_html=True)
    for when, what in milestones:
        st.markdown(f"- **{when}:** {what}")
    st.caption("Milestones come from this farm's drainage (ISRIC SoilGrids), slope (NASA SRTM), storm record (NOAA) and your water "
               "access. Weather beyond the next season cannot be forecast; the roadmap is built to cope with the range of years the "
               "farm has already seen.")


def long_term(b):
    st.markdown(art.heading("What has already changed here") + badge("data"), unsafe_allow_html=True)
    ui.render_shift(b)
    st.markdown(art.heading("What if it gets hotter? Crop fit at +1 °C and +2 °C") + badge("model"), unsafe_allow_html=True)
    site = ui.build_site(b, st.session_state.get("fs_soil_override"))
    crops = planner.load_crops()
    rows = []
    for dt in (0, 1, 2):
        s2 = copy.copy(site)
        s2.t_mean = site.t_mean + dt
        for c in crops.index:
            if crops.loc[c, "harvest_value"] <= 0:
                continue
            best = max(planner.planting_metrics(s2, crops.loc[c], st_, max(1, round(crops.loc[c, "days_to_harvest"] / 30.4)))["suitability"]
                       for st_ in range(1, 13))
            rows.append({"crop": c, "warming": f"+{dt} °C" if dt else "today", "fit": best})
    d = pd.DataFrame(rows)
    piv = d.pivot(index="crop", columns="warming", values="fit")
    piv["change"] = piv["+2 °C"] - piv["today"]
    order = piv.sort_values("change").index.tolist()
    st.altair_chart(alt.Chart(d).mark_line(point=True).encode(
        x=alt.X("warming:N", sort=["today", "+1 °C", "+2 °C"], title=None), y=alt.Y("fit:Q", title="best-month climate fit (0-1)"),
        color=alt.Color("crop:N", sort=order, title=None, legend=alt.Legend(columns=2, orient="right")),
        tooltip=["crop", "warming", alt.Tooltip("fit:Q", format=".2f")]).properties(height=300), use_container_width=True, theme=None)
    losers = [c for c in order if piv.loc[c, "change"] < -0.05][:5]
    gainers = [c for c in order[::-1] if piv.loc[c, "change"] > 0.02][:5]
    st.markdown(("**Lose fit as it warms:** " + ", ".join(losers) + ". ") if losers else "No crop loses much fit at +2 °C. ")
    if gainers:
        st.markdown("**Hold up or gain:** " + ", ".join(gainers) + ".")
    st.caption("A what-if, not a forecast: the farm's 30-year temperatures are raised by 1 and 2 °C and checked against FAO ECOCROP "
               "temperature ranges. IPCC AR6 projects continued warming across the Caribbean this century; how much depends on global "
               "emissions. Rain changes are too uncertain at farm scale to include honestly.")
    st.markdown(art.heading("Long-term resilience choices"), unsafe_allow_html=True)
    st.markdown("- Diversify: no more than about half the land in one crop family.\n"
                "- Tree crops and windbreaks (breadfruit, citrus, gliricidia hedges) take years to establish: start early.\n"
                "- Build organic matter every year: it holds water in drought and drains better in floods.\n"
                "- Store water: every dry season the tank pays for itself in crops not lost.")


# ---------------------------------------------------------------------------
# Storms & recovery: prepare, respond, recover, resilience
# ---------------------------------------------------------------------------

def page_storms():
    shell("sky", "storms")
    p, b = P(), bundle()
    hero("Storms & recovery", "Prepare. Respond. Restore. Build back stronger.",
         "Hurricanes can't be stopped, but how much a farm loses depends on what is in the field, how the soil is held and how "
         "fast it recovers. This is the full cycle for this farm.")
    with st.container(key="layer_storms"):
        stage = st.segmented_control("Stage", ["1 · Prepare", "2 · Respond & recover", "3 · Restore the soil", "4 · Build resilience"],
                                     default="1 · Prepare", label_visibility="collapsed", key="storm_stage")
        if stage == "2 · Respond & recover":
            st.fragment(ui.render_after)(b)
        elif stage == "3 · Restore the soil":
            restoration(b, p)
        elif stage == "4 · Build resilience":
            resilience(b)
        else:
            ui.render_storm(b)


def restoration(b, p):
    st.markdown(art.heading("Restore damaged land: pick what your field looks like"), unsafe_allow_html=True)
    key = st.radio("Condition", list(restore.CONDITIONS), format_func=lambda k: restore.CONDITIONS[k]["label"], horizontal=True,
                   label_visibility="collapsed")
    c = restore.CONDITIONS[key]
    clim = b["climate"]
    facts = restore.field_facts(b.get("soil"), b.get("terrain"), profile.irrigation(p), bool(p.get("wet_field")),
                                float(clim["rain_mm"].min()))
    st.markdown(f"*How to recognise it:* {c['sign']}")
    left, right = st.columns([1, 1.4], gap="large")
    with left:
        st.markdown("**First steps**")
        for s in c["first"]:
            st.markdown(f"- {s}")
        st.markdown(f"**Avoid for now:** {c['avoid']}")
    with right:
        st.markdown("**Crops that restore this kind of land, checked against your farm**")
        for r in restore.recommend(key, facts):
            tag = ('<span class="fs-fit ok">Suits this farm</span>' if r["suits"]
                   else '<span class="fs-fit no">Not a good match here</span>')
            note = "" if r["suits"] else f"<br><span class='fs-fit-note'>{r['caveat']}</span>"
            st.markdown(f"{tag} <b>{r['name']}</b>: {r['why']}{note}", unsafe_allow_html=True)
    soil = b.get("soil") or {}
    st.caption(f"Checked against this farm: clay {facts['clay']:.0f}% (SoilGrids), drainage {soil.get('drainage', 'unknown')}, "
               f"{'flat' if facts['flat'] else 'sloping'} land (SRTM), water: {p.get('water')}"
               f"{', low-lying field you can flood' if p.get('wet_field') else ''}. Sources: {c['source']}.")


def resilience(b):
    crops = planner.load_crops()
    st.markdown(art.heading("Crops that stand up to wind best") + badge("model"), unsafe_allow_html=True)
    d = crops[crops["harvest_value"] > 0].copy()
    d["wind"] = d[["wind_seedling", "wind_vegetative", "wind_reproductive", "wind_mature"]].mean(axis=1)
    # the crop table is indexed by crop *and* keeps a crop column, so drop the index rather than insert it again
    d = d.reset_index(drop=True) if "crop" in d.columns else d.rename_axis("crop").reset_index()
    d = d.sort_values("wind")
    st.altair_chart(alt.Chart(d).mark_bar().encode(
        x=alt.X("wind:Q", title="share of the crop a hurricane typically destroys (FarmFit estimate)", axis=alt.Axis(format="%")),
        y=alt.Y("crop:N", sort=None, title=None),
        color=alt.Color("wind:Q", scale=alt.Scale(range=[art.LEAF, art.OCHRE, art.TERRA]), legend=None),
        tooltip=["crop", alt.Tooltip("wind:Q", format=".0%")]).properties(height=22 * len(d)), use_container_width=True, theme=None)
    st.caption("Low, below-ground and flexible crops (sweet potato, cassava, dasheen) survive wind best; tall, top-heavy crops "
               "(corn, plantain, staked tomatoes) worst. Values are transparent FarmFit estimates from crop shape and growth stage, "
               "to be validated with CARDI and extension officers.")
    rp = b["storm_summary"].get("return_period_storm_force")
    st.markdown(art.heading("Structural protection and money"), unsafe_allow_html=True)
    st.markdown("- **Windbreaks** on the windward side cut wind speed for several times their height downwind.\n"
                "- **Ground cover** in August-October: cover crops hold soil when the heavy rain comes.\n"
                "- **Seed and planting material** stored off the ground and dry, ready to replant fast.\n"
                "- **Records and photos** of the field before the season: they speed up damage reports and insurance.")
    st.markdown("**Insurance that pays fast.** CCRIF's Livelihood Protection Policy is parametric micro-insurance: it pays when "
                "measured wind or rain passes a set level, with no loss adjuster. It launched in Jamaica in December 2025 and is "
                "being extended to other Caribbean countries, including Trinidad and Tobago."
                + (f" Storm-force wind reaches this farm about 1 year in {rp:.0f}, the kind of risk it is designed for." if rp else ""))
    st.page_link(st.session_state.fs_pages["planner"], label="Build these into a five-year plan", icon=":material/calendar_month:")


# ---------------------------------------------------------------------------
# Pest & disease watch
# ---------------------------------------------------------------------------

def page_pests():
    shell("field", "pests")
    p, b = P(), bundle()
    ss = st.session_state
    hero("Community pest & disease watch", "See it. Report it. Warn your neighbours.",
         "Like a traffic app for crop threats: farmers report what they see, everyone nearby gets a heads-up, and agricultural "
         "officers confirm or correct each report. Locations are blurred to about 2 km.")
    with st.container(key="layer_pests"):
        tab_map, tab_report, tab_follow, tab_officer = st.tabs(["Map", "Report a problem", "Follow my area", "Officer dashboard"])
        with tab_report:
            report_form(p)
        reports = community.load()
        with tab_map:
            show_examples = st.toggle("Show simulated example reports (for demonstration)", value=ss.get("pest_examples", False),
                                      key="pest_examples")
            if show_examples:
                reports = reports + community.example_reports(b["lat"], b["lon"])
            pest_map(reports, b)
        with tab_follow:
            follow_area(b)
        with tab_officer:
            officer_dashboard(community.load())


def report_form(p):
    ss = st.session_state
    st.markdown("Your report is anonymous. It appears as **Unverified** until an agricultural officer reviews it.")
    photo = st.file_uploader("Photo of the problem (optional but very helpful)", type=["jpg", "jpeg", "png", "webp"], key="pest_photo")
    ai = None
    if photo is not None:
        st.image(photo, width=260)
        key = ui.secret("GEMINI_API_KEY")
        if key and st.button("Ask AI what it might be"):
            with st.spinner("Looking at the photo…"):
                res = community.ai_triage(photo.getvalue(), photo.type, key)
            ss.pest_ai = res
        res = ss.get("pest_ai")
        if res and res.get("ok"):
            r = res["result"]
            ai = r
            st.info(f"**AI suggestion, not a diagnosis:** {r.get('likely', 'unclear')} "
                    f"({community.CATEGORIES[r['category']][0].lower()}, confidence {r['confidence']:.0%}). {r.get('visible', '')} "
                    f"{r.get('next_step', '')}")
        elif res and not res.get("ok"):
            st.caption(f"AI check unavailable: {res.get('error', '')[:160]}")
        elif not key:
            st.caption("AI photo suggestions turn on when a Gemini API key is configured (see docs/GEMINI.md).")
    c1, c2 = st.columns(2)
    default_cat = list(community.CATEGORIES).index(ai["category"]) if ai else 0
    cat = c1.selectbox("What kind of problem?", list(community.CATEGORIES), index=default_cat,
                       format_func=lambda k: community.CATEGORIES[k][0])
    c1.caption(community.CATEGORIES[cat][2])
    sev = c2.radio("How bad?", list(community.SEVERITY), format_func=community.SEVERITY.get, horizontal=False)
    crops = planner.load_crops()
    crop = st.selectbox("Crop affected", ["—"] + [c for c in crops.index if crops.loc[c, "harvest_value"] > 0] + ["Other"])
    desc = st.text_area("What did you see?", placeholder="e.g. holes in leaves, caterpillars in the funnel, started 3 days ago")
    where = st.radio("Location", ["My farm (blurred to about 2 km)", "Somewhere else"], horizontal=True)
    lat, lon = p["lat"], p["lon"]
    if where == "Somewhere else":
        c1, c2 = st.columns(2)
        lat = c1.number_input("Latitude", value=float(p["lat"]), format="%.4f")
        lon = c2.number_input("Longitude", value=float(p["lon"]), format="%.4f")
    area = st.text_input("Village or district name (optional, shown to others)")
    if st.button("Send report", type="primary", disabled=not desc.strip()):
        r = community.add(lat, lon, cat, sev, desc, crop=None if crop == "—" else crop, area_name=area,
                          photo=photo.getvalue() if photo is not None else None, ai=ai)
        sent = community.notify_area(r)
        ss.pop("pest_ai", None)
        st.success("Thank you. Your report is on the map as Unverified" + (" and farmers following this area were alerted." if sent else "."))
        with st.expander("What you can do now", expanded=True):
            for tip in community.PREVENT[cat]:
                st.markdown(f"- {tip}")


def pest_map(reports, b):
    c1, c2, c3, c4 = st.columns([1.6, 1, 1, 1])
    cats = c1.multiselect("Threat type", list(community.CATEGORIES), default=list(community.CATEGORIES),
                          format_func=lambda k: community.CATEGORIES[k][0])
    sev = c2.multiselect("Severity", list(community.SEVERITY), default=list(community.SEVERITY))
    km = c3.select_slider("Within", options=[10, 25, 50, 100, 500], value=50, format_func=lambda x: f"{x} km")
    days = c4.select_slider("Last", options=[7, 14, 30, 90, 365], value=30, format_func=lambda x: f"{x} days")
    show = [r for r in community.nearby(reports, b["lat"], b["lon"], km=km, days=days)
            if r["category"] in cats and r["severity"] in sev]
    m = folium.Map(location=[b["lat"], b["lon"]], zoom_start=10 if km <= 50 else 8, tiles="OpenStreetMap", control_scale=True)
    folium.Circle([b["lat"], b["lon"]], radius=km * 1000, color=art.INK, weight=1, fill=False, dash_array="6").add_to(m)
    folium.Marker([b["lat"], b["lon"]], tooltip="Your farm (only you see this)", icon=folium.Icon(color="green", icon="home")).add_to(m)
    for r in show:
        label, colour, _ = community.CATEGORIES[r["category"]]
        radius = {"low": 7, "medium": 10, "high": 14}[r["severity"]]
        sim = " · SIMULATED EXAMPLE" if r.get("simulated") else ""
        popup = (f"<b>{label}</b>{sim}<br>{community.SEVERITY[r['severity']]}<br>{r.get('crop') or ''}<br><i>{r['description']}</i><br>"
                 f"{r['age_days']:.0f} day(s) ago · {community.STATUS[r['status']]}"
                 + (f"<br><b>Officer:</b> {r['guidance']}" if r.get("guidance") else ""))
        folium.CircleMarker([r["lat"], r["lon"]], radius=radius, color=colour, weight=3 if r["status"] == "verified" else 1.5,
                            dash_array=None if r["status"] == "verified" else "4", fill=True, fill_color=colour, fill_opacity=.55,
                            tooltip=f"{label} · {community.STATUS[r['status']]}", popup=folium.Popup(popup, max_width=260)).add_to(m)
    st_folium(m, height=420, width=None, key="pest_map", returned_objects=[])
    st.markdown(" ".join(f'<span style="display:inline-block;margin:.1rem .5rem .1rem 0"><span style="display:inline-block;width:11px;'
                         f'height:11px;border-radius:50%;background:{c[1]};vertical-align:middle"></span> {c[0]}</span>'
                         for c in community.CATEGORIES.values()), unsafe_allow_html=True)
    st.caption("Solid outline = verified by an officer; dashed = unverified. Bigger circle = more severe. Every point is the centre "
               "of a ~2 km square, never a farm's exact location.")
    if show:
        df = pd.DataFrame([{"type": community.CATEGORIES[r["category"]][0], "severity": r["severity"], "km away": round(r["km"], 1),
                            "days ago": round(r["age_days"]), "status": community.STATUS[r["status"]],
                            "example": "simulated" if r.get("simulated") else ""} for r in show])
        st.dataframe(df, hide_index=True, use_container_width=True)
        kinds = sorted({r["category"] for r in show})
        st.markdown(art.heading("What to do"), unsafe_allow_html=True)
        for k in kinds:
            with st.expander(f"{community.CATEGORIES[k][0]}: prevention and first steps"):
                for tip in community.PREVENT[k]:
                    st.markdown(f"- {tip}")
                st.caption("General integrated pest management guidance (FAO, CABI PlantwisePlus). Your extension officer can confirm "
                           "the exact pest and the right treatment.")
    else:
        st.info("No reports match these filters. When a farmer nearby reports a problem, it will appear here.")


def follow_area(b):
    from . import alerts
    topic = community.area_topic(b["lat"], b["lon"])
    url = f"{community.NTFY}/{topic}"
    st.markdown("Get a phone notification when someone reports a pest or disease within about 25 km of your farm. Free, no "
                "account, no phone number: install the **ntfy** app and subscribe to your area.")
    c1, c2 = st.columns([1, 2.5])
    c1.markdown(f'<div class="keep-colour">{alerts.qr_svg(url)}</div>', unsafe_allow_html=True)
    c2.markdown(f"**Your area channel:** `{topic}`\n\n1. Install ntfy (Android or iPhone).\n2. Scan the code or open "
                f"[{url}]({url}).\n3. Tap Subscribe. Alerts show only the type, severity and approximate area.")


def officer_dashboard(reports):
    ss = st.session_state
    code = ui.secret("AUTHORITY_PASSCODE")
    if not code:
        st.info("For agricultural officers. Turn it on by adding AUTHORITY_PASSCODE to the app's secrets (see docs/GEMINI.md, "
                "'Secrets'); officers then sign in here to verify reports and add guidance.")
        return
    if not ss.get("officer_ok"):
        entered = st.text_input("Officer passcode", type="password")
        if st.button("Sign in") and entered == code:
            ss.officer_ok = True
            st.rerun()
        return
    st.success("Signed in as an agricultural officer.")
    if not reports:
        st.caption("No reports yet.")
        return
    df = pd.DataFrame(reports)
    df["created"] = pd.to_datetime(df["created"])
    df["week"] = df["created"].dt.to_period("W").dt.start_time
    df["type"] = df["category"].map(lambda k: community.CATEGORIES[k][0])
    c1, c2, c3 = st.columns(3)
    c1.metric("Reports", len(df))
    c2.metric("Awaiting review", int((df["status"] == "unverified").sum()))
    c3.metric("Verified", int((df["status"] == "verified").sum()))
    st.altair_chart(alt.Chart(df).mark_bar().encode(x=alt.X("week:T", title=None), y=alt.Y("count():Q", title="reports"),
                                                    color=alt.Color("type:N", title=None)).properties(height=180),
                    use_container_width=True, theme=None)
    hs = community.hotspots(reports)
    if hs:
        st.warning("Possible outbreaks (3+ reports of the same kind within ~28 km in 14 days): " +
                   "; ".join(f"{community.CATEGORIES[h['category']][0]} near {h['lat']:.2f}, {h['lon']:.2f} ({h['count']})" for h in hs))
    for r in sorted(reports, key=lambda r: r["created"], reverse=True)[:30]:
        if r["status"] != "unverified":
            continue
        with st.expander(f"{community.CATEGORIES[r['category']][0]} · {r['severity']} · {r['created'][:10]} · {r.get('area') or ''}"):
            img = community.photo_bytes(r)
            if img:
                st.image(img, width=280)
            st.write(r["description"])
            if r.get("ai"):
                st.caption(f"AI suggestion (not a diagnosis): {r['ai'].get('likely')} · confidence {r['ai'].get('confidence', 0):.0%}")
            g = st.text_input("Guidance for farmers", key=f"g_{r['id']}")
            c1, c2 = st.columns(2)
            if c1.button("Verify", key=f"v_{r['id']}", type="primary"):
                community.update(r["id"], status="verified", reviewer="officer", guidance=g)
                st.rerun()
            if c2.button("Dismiss", key=f"d_{r['id']}"):
                community.update(r["id"], status="dismissed", reviewer="officer", guidance=g)
                st.rerun()


# ---------------------------------------------------------------------------
# News & learning (+ assistant)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=7 * 86400, show_spinner=False)
def farm_location(lat, lon, place):
    return news.locate(lat, lon, place)


@st.cache_data(ttl=1800, show_spinner=False)
def load_news(scopes):
    return news.news_for(list(scopes))


def page_news():
    shell("water", "news")
    p, b = P(), bundle()
    loc = farm_location(round(b["lat"], 2), round(b["lon"], 2), p.get("place") or "")
    country, region = loc["country"], loc["region"]
    where = country or region
    hero("News & learning", f"What's happening in farming in {where}, and who to ask")
    with st.container(key="layer_news"):
        left, right = st.columns([1.3, 1], gap="large")
        with left:
            st.markdown(art.heading("Agriculture news"), unsafe_allow_html=True)
            tabs = [x for x in dict.fromkeys([country, region, "World"]) if x]
            pick = st.segmented_control("Region", tabs, default=tabs[0], label_visibility="collapsed") or tabs[0]
            chain = tabs[tabs.index(pick):]  # if nothing for the country, fall back to the region, then the world
            scopes = tuple((k, news.query_for("world" if k == "World" else "place", k)) for k in chain)
            with st.spinner("Finding the latest farming news…"):
                res = load_news(scopes)
            if res:
                if res["key"] != pick:
                    st.caption(f"No recent farming headlines for {pick}; showing {res['key']}.")
                for it in res["items"]:
                    st.markdown(f"**[{it['title']}]({it['link']})**  \n<span style='font-size:.8rem;color:{art.INK2}'>"
                                f"{' · '.join(x for x in (it['source'], it['date']) if x)}</span>", unsafe_allow_html=True)
                if res["how"] == "live":
                    st.caption("Latest headlines via Google News or Bing News; each links to the original publisher.")
                else:
                    st.caption(f"Most recent saved headlines (updated {res['fetched']}). Each links to the original publisher.")
            else:
                st.markdown("Worth reading while we fetch the latest headlines:")
                for name, url, what in news.FURTHER_READING:
                    st.markdown(f"**[{name}]({url})**  \n<span style='font-size:.82rem;color:{art.INK2}'>{what}</span>",
                                unsafe_allow_html=True)
        with right:
            st.markdown(art.heading("Official sources"), unsafe_allow_html=True)
            for name, url, what in news.official_for(country, region, b["lat"], b["lon"]):
                st.markdown(f"[{name}]({url})  \n<span style='font-size:.82rem;color:{art.INK2}'>{what}</span>", unsafe_allow_html=True)
        if p["mode"] == "garden":
            st.markdown(art.heading("Beginner guides"), unsafe_allow_html=True)
            for title, tips in garden.GUIDES:
                with st.expander(title):
                    for tip in tips:
                        st.markdown(f"- {tip}")
        st.caption("Questions about your own farm? Use Ask FarmFit at the bottom right of any page.")


def page_data():
    shell("bedrock", "data")
    b = bundle()
    with st.container(key="layer_data"):
        ui.render_data(b)


# ---------------------------------------------------------------------------
# Home garden pages
# ---------------------------------------------------------------------------

def page_garden_home():
    shell("home", "ghome")
    p, b = P(), bundle()
    m = TODAY().month
    hero(f"{MONTHS[m - 1]} in your garden", "What to plant and how to look after it",
         "Simple advice for pots, beds and backyards, based on this spot's weather and 30 years of NASA records.")
    with st.container(key="layer_ghome"):
        table = [c for c in garden.CROPS if c[1]]
        W = crop_windows([c[0] for c in table])
        mine = [c for c in table if c[0] in (p.get("crops") or [])] or table[:4]
        st.markdown(art.heading("Plant now, or wait?") + badge("model"), unsafe_allow_html=True)
        cols = st.columns(min(4, len(mine)))
        for col, c in zip(cols, mine[:4]):
            col.markdown(crop_card(c[0], W[c[0]], m, why=f"Container: {c[3]}."), unsafe_allow_html=True)
        herbs = [c for c in garden.CROPS if not c[1]]
        st.markdown("**Herbs you can start any month:** " + ", ".join(h[0] for h in herbs) + ".")
        st.markdown(art.heading("Watering this week"), unsafe_allow_html=True)
        fc = ui.load_forecast(b["lat"], b["lon"], TODAY().isoformat())
        if fc is not None:
            wk = fc.head(7)
            rain, et0 = float(wk["rain_mm"].sum()), float(wk["et0_mm"].sum())
            need = max(0.0, 0.9 * et0 - 0.8 * rain)
            msg = ("Rain should cover your beds this week; containers still dry out fast, so check them daily."
                   if need < 5 else f"Expect to water: plants will use about {et0 * .9:.0f} mm and rain gives about {rain:.0f} mm. "
                   f"For each square metre of bed that is about {need:.0f} litres this week; water pots whenever the top 2-3 cm is dry.")
            st.markdown(msg)
            st.altair_chart(forecast_chart(fc), use_container_width=True, theme=None)
        else:
            st.markdown("Forecast unavailable: water when the top 2-3 cm of soil is dry.")
        st.markdown(art.heading("Risks right now"), unsafe_allow_html=True)
        cols = st.columns(4)
        for col, (label, v, lvl, sub) in zip(cols, risk_levels(b)):
            col.markdown(journey.gauge(v, label, lvl, sub), unsafe_allow_html=True)
        report_download(b)


def page_garden_grow():
    shell("field", "ggrow")
    p = P()
    hero("Grow guide", "Small spaces, big harvests", "Crops that do well in containers, raised beds and on walls, with beginner steps.")
    with st.container(key="layer_ggrow"):
        spaces = st.multiselect("My space", profile.GARDEN_SPACES, default=p.get("garden_space") or profile.GARDEN_SPACES[:1])
        shown = [c for c in garden.CROPS if not spaces or set(spaces) & set(c[2])]
        cols = st.columns(3)
        for i, (name, _, sp, cont, days, sun, tip) in enumerate(shown):
            cols[i % 3].markdown(f'<div class="fs-card"><div class="c">{name}</div><div class="w"><b>Container:</b> {cont}<br>'
                                 f'<b>First harvest:</b> about {days} days<br><b>Sun:</b> {sun}<br>{tip}</div></div>',
                                 unsafe_allow_html=True)
            cols[i % 3].write("")
        st.caption("Starting points from common extension guidance (e.g. University of Florida IFAS container vegetable guide); "
                   "local varieties may differ.")
        st.markdown(art.heading("Beginner guides"), unsafe_allow_html=True)
        for title, tips in garden.GUIDES:
            with st.expander(title, expanded=title == "Start with good soil"):
                for tip in tips:
                    st.markdown(f"- {tip}")


def page_garden_storm():
    shell("sky", "gstorm")
    b = bundle()
    hero("Storm ready", "Protect your garden before the wind and rain")
    with st.container(key="layer_gstorm"):
        live, err = ui.load_active_storms(datetime.now().strftime("%Y%m%d%H"))
        if live:
            for s in live:
                th = stormwatch.threat(s, b["lat"], b["lon"])
                st.warning(f"{s.get('name')}: {th['level']} · {th['distance_km']:.0f} km away"
                           + (f", could arrive in about {th['eta_h']:.0f} hours" if th.get("eta_h") else ""))
        elif err:
            st.caption("Live storm feed not reachable; check your national met service.")
        else:
            st.success("No active Atlantic storms right now.")
        for title, tips in garden.GUIDES:
            if title == "Before a storm":
                for tip in tips:
                    st.markdown(f"- {tip}")
        rp = b["storm_summary"].get("return_period_storm_force")
        if rp:
            st.markdown(f"Storm-force wind reaches this area about **1 year in {rp:.0f}** (NOAA records since 1971), mostly August to October.")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def render():
    ui.setup_page()
    ss = st.session_state
    if not restore_profile():
        pg = st.navigation([st.Page(onboarding, title="Set up", icon=":material/eco:", url_path="setup")], position="hidden")
        pg.run()
        return
    p = P()
    if p["mode"] == "garden":
        spec = [("home", page_garden_home, "Home", ":material/home:"), ("grow", page_garden_grow, "Grow guide", ":material/potted_plant:"),
                ("weather", page_weather, "Weather", ":material/partly_cloudy_day:"), ("pests", page_pests, "Pest watch", ":material/bug_report:"),
                ("storms", page_garden_storm, "Storm ready", ":material/cyclone:"), ("news", page_news, "Learn", ":material/school:"),
                ("myfarm", page_myfarm, "My garden", ":material/person:")]
    else:
        spec = [("home", page_home, "Home", ":material/home:"), ("myfarm", page_myfarm, "My farm", ":material/agriculture:"),
                ("weather", page_weather, "Weather", ":material/partly_cloudy_day:"), ("crops", page_crops, "Crops & market", ":material/storefront:"),
                ("planner", page_planner, "Planner", ":material/calendar_month:"), ("storms", page_storms, "Storms & recovery", ":material/cyclone:"),
                ("pests", page_pests, "Pest watch", ":material/bug_report:"), ("news", page_news, "News", ":material/newspaper:"),
                ("data", page_data, "Data", ":material/dataset:")]
    pages = {k: st.Page(fn, title=title, icon=icon, url_path=k, default=(k == "home")) for k, fn, title, icon in spec}
    pages.setdefault("planner", pages.get("home"))
    pages.setdefault("storms", pages.get("home"))
    ss.fs_pages = pages
    pg = st.navigation(list({id(v): v for v in pages.values()}.values()), position="top")
    pg.run()
    ask_fab()


def ask_fab():
    """Floating Ask FarmFit button, bottom right of every page."""
    with st.container(key="fs_fab"):
        with st.popover("Ask FarmFit", icon=":material/forum:", key="fs_fab_pop"):
            st.fragment(ui.render_ask)(bundle())
