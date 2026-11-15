
import sqlite3
from datetime import datetime

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

from fieldshift import ui as fs_ui


# =========================================================
# PAGE + VISUAL SYSTEM
# =========================================================

st.set_page_config(
    page_title="FarmFit · Hurricane to Harvest",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        :root {
            --ff-bg: #f7fbf3;
            --ff-surface: #ffffff;
            --ff-surface-2: #eef7e9;
            --ff-text: #143122;
            --ff-muted: #617064;
            --ff-border: rgba(24, 58, 34, 0.10);
            --ff-primary: #4CAF50;
            --ff-primary-dark: #2F7D32;
            --ff-secondary: #F4C95D;
            --ff-brown: #8C6A43;
            --ff-accent: #9BE17B;
            --ff-shadow: 0 18px 50px rgba(25, 49, 31, .08);
        }

        .stApp {
            background:
                radial-gradient(circle at 0% 0%, rgba(155,225,123,.18), transparent 22%),
                radial-gradient(circle at 95% 10%, rgba(244,201,93,.13), transparent 20%),
                linear-gradient(180deg, #f8fcf5 0%, #f4faef 100%);
        }

        .block-container {
            max-width: 1200px;
            padding-top: .85rem;
            padding-bottom: 4rem;
        }

        h1, h2, h3, h4 {
            letter-spacing: -0.025em;
            color: var(--ff-text);
        }

        p, li, div, span, label {
            color: inherit;
        }

        /* HERO */
        .ff-hero-wrap {
            animation: ffFadeUp .65s ease both;
            margin: .25rem 0 1.4rem 0;
        }

        .ff-hero {
            position: relative;
            overflow: hidden;
            border-radius: 30px;
            padding: 0;
            background: linear-gradient(135deg, #0f3d20 0%, #24693b 52%, #68b65f 100%);
            color: white;
            box-shadow: 0 22px 60px rgba(21, 66, 34, .14);
        }

        .ff-hero-grid {
            display: grid;
            grid-template-columns: 1.1fr .95fr;
            gap: 1rem;
            align-items: center;
            min-height: 380px;
        }

        .ff-hero-copy {
            padding: 2.4rem 2.4rem 2.4rem 2.5rem;
            position: relative;
            z-index: 2;
        }

        .ff-kicker {
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            border-radius: 999px;
            background: rgba(255,255,255,.12);
            border: 1px solid rgba(255,255,255,.15);
            padding: .4rem .78rem;
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .06em;
            text-transform: uppercase;
            margin-bottom: .95rem;
        }

        .ff-hero h1 {
            margin: 0;
            color: white !important;
            font-size: clamp(2.5rem, 5vw, 4.4rem);
            line-height: .95;
        }

        .ff-hero p {
            margin: .9rem 0 0 0;
            max-width: 620px;
            color: rgba(255,255,255,.90);
            font-size: 1.04rem;
            line-height: 1.65;
        }

        .ff-hero-pills {
            margin-top: 1.2rem;
        }

        .ff-hero-pill {
            display: inline-block;
            text-decoration: none;
            cursor: pointer;
            border-radius: 999px;
            padding: .35rem .72rem;
            margin: .18rem .32rem .18rem 0;
            background: rgba(255,255,255,.14);
            border: 1px solid rgba(255,255,255,.14);
            font-size: .82rem;
            font-weight: 700;
            color: white;
        }

        .ff-hero-cta {
            margin-top: 1.35rem;
            display: flex;
            flex-wrap: wrap;
            gap: .7rem;
        }

        .ff-btn-solid, .ff-btn-ghost {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 46px;
            border-radius: 14px;
            padding: 0 1rem;
            font-weight: 800;
            font-size: .92rem;
            text-decoration: none;
        }

        .ff-btn-solid {
            color: #163823 !important;
            background: var(--ff-secondary);
            box-shadow: 0 10px 28px rgba(244, 201, 93, .25);
        }

        .ff-btn-ghost {
            color: white !important;
            background: rgba(255,255,255,.08);
            border: 1px solid rgba(255,255,255,.16);
        }

        .ff-hero-art {
            padding: 1rem 1.25rem 1rem 0;
            position: relative;
            z-index: 2;
        }

        .ff-hero-glow {
            position: absolute;
            width: 280px;
            height: 280px;
            border-radius: 50%;
            right: -40px;
            top: -20px;
            background: radial-gradient(circle, rgba(255,255,255,.16), transparent 60%);
            animation: ffFloat 5s ease-in-out infinite;
        }

        .ff-farm-scene {
            position: relative;
            width: min(100%, 430px);
            height: 330px;
            margin: 0 auto;
            border-radius: 30px;
            overflow: hidden;
            background:
                linear-gradient(180deg, #c8ecff 0 42%, #dff3bd 42% 54%, #76b85f 54% 100%);
            box-shadow: 0 24px 55px rgba(0,0,0,.18);
            border: 1px solid rgba(255,255,255,.18);
            animation: ffFloat 5.5s ease-in-out infinite;
        }

        .ff-scene-sun {
            position: absolute;
            width: 70px;
            height: 70px;
            right: 34px;
            top: 30px;
            border-radius: 50%;
            background: #ffd76a;
            box-shadow: 0 0 0 12px rgba(255,215,106,.14);
        }

        .ff-hill {
            position: absolute;
            border-radius: 50% 50% 0 0;
            bottom: 0;
        }

        .ff-hill.one {
            width: 340px;
            height: 145px;
            left: -90px;
            background: #5a9e50;
        }

        .ff-hill.two {
            width: 350px;
            height: 130px;
            right: -115px;
            background: #438947;
        }

        .ff-field-row {
            position: absolute;
            left: 46px;
            right: 46px;
            bottom: 42px;
            height: 54px;
            border-radius: 50%;
            border-top: 8px solid rgba(93,65,38,.62);
            transform: skewX(-12deg);
        }

        .ff-field-row.r2 {
            bottom: 68px;
            left: 76px;
            right: 74px;
            opacity: .8;
        }

        .ff-field-row.r3 {
            bottom: 92px;
            left: 112px;
            right: 100px;
            opacity: .62;
        }

        .ff-plant {
            position: absolute;
            bottom: 78px;
            font-size: 2.4rem;
            filter: drop-shadow(0 8px 8px rgba(0,0,0,.10));
        }

        .ff-plant.p1 { left: 95px; transform: rotate(-7deg); }
        .ff-plant.p2 { left: 177px; bottom: 94px; transform: scale(1.12); }
        .ff-plant.p3 { right: 91px; transform: rotate(6deg); }

        .ff-float-card {
            position: absolute;
            z-index: 3;
            min-width: 118px;
            padding: .72rem .82rem;
            border-radius: 16px;
            background: rgba(255,255,255,.92);
            color: #183b26;
            box-shadow: 0 14px 30px rgba(16,52,27,.14);
            border: 1px solid rgba(255,255,255,.68);
            backdrop-filter: blur(8px);
        }

        .ff-float-card strong {
            display: block;
            font-size: .82rem;
            margin-bottom: .1rem;
        }

        .ff-float-card span {
            font-size: .72rem;
            color: #627267;
        }

        .ff-float-card.nasa { left: 18px; top: 23px; }
        .ff-float-card.water { right: 18px; bottom: 24px; }
        .ff-float-card.rotation { left: 22px; bottom: 26px; }

        .ff-signal {
            position: absolute;
            left: 50%;
            top: 38px;
            width: 74px;
            height: 74px;
            transform: translateX(-50%);
            border-radius: 50%;
            border: 2px dashed rgba(27,94,49,.28);
            animation: ffSpin 15s linear infinite;
        }

        .ff-signal:after {
            content: "🛰️";
            position: absolute;
            right: -8px;
            top: 14px;
            font-size: 1.35rem;
            transform: rotate(18deg);
        }

        @keyframes ffSpin {
            to { transform: translateX(-50%) rotate(360deg); }
        }

        /* TOP TILES */
        .ff-tiles {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: .85rem;
            margin: 1rem 0 1.2rem 0;
        }

        .ff-tile {
            background: rgba(255,255,255,.88);
            border: 1px solid var(--ff-border);
            border-radius: 22px;
            padding: 1rem;
            box-shadow: 0 8px 28px rgba(20,49,34,.04);
            transition: transform .2s ease, box-shadow .2s ease;
            animation: ffFadeUp .55s ease both;
        }

        .ff-tile:hover {
            transform: translateY(-3px);
            box-shadow: 0 14px 30px rgba(20,49,34,.08);
        }

        .ff-tile-icon {
            width: 44px;
            height: 44px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 14px;
            font-size: 1.25rem;
            margin-bottom: .7rem;
            background: #edf7e8;
        }

        .ff-tile-title {
            font-weight: 800;
            font-size: .98rem;
            color: var(--ff-text);
        }

        .ff-tile-copy {
            font-size: .87rem;
            color: var(--ff-muted);
            line-height: 1.5;
            margin-top: .25rem;
        }

        /* CARDS / SECTIONS */
        .ff-section-kicker {
            font-size: .8rem;
            font-weight: 800;
            color: var(--ff-primary-dark);
            letter-spacing: .05em;
            text-transform: uppercase;
            margin-top: .2rem;
            margin-bottom: .2rem;
        }

        .ff-subtle {
            color: var(--ff-muted);
            font-size: .92rem;
            line-height: 1.6;
        }

        .ff-weather {
            border: 1px solid rgba(22,56,35,.08);
            border-radius: 18px;
            padding: .9rem .65rem;
            text-align: center;
            min-height: 136px;
            background:
                linear-gradient(180deg, rgba(255,255,255,.95) 0%, rgba(246,250,243,.95) 100%);
            box-shadow: 0 8px 24px rgba(20,49,34,.035);
            transition: transform .18s ease, box-shadow .18s ease;
            animation: ffFadeUp .45s ease-out both;
        }

        .ff-weather:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 25px rgba(20,49,34,.06);
        }

        .ff-weather .icon {
            font-size: 1.65rem;
            margin: .1rem 0 .22rem 0;
        }

        .ff-chip {
            display: inline-block;
            padding: .32rem .68rem;
            margin: .12rem .3rem .12rem 0;
            border-radius: 999px;
            background: rgba(155,225,123,.20);
            border: 1px solid rgba(76,175,80,.12);
            color: #23542f;
            font-size: .78rem;
            font-weight: 760;
        }

        .ff-reason, .ff-warning {
            padding: .72rem .9rem;
            margin: .36rem 0;
            border-radius: 0 14px 14px 0;
            font-size: .93rem;
            line-height: 1.55;
            background: rgba(76,175,80,.06);
            border-left: 4px solid rgba(76,175,80,.65);
        }

        .ff-warning {
            background: rgba(244,201,93,.12);
            border-left: 4px solid rgba(244,201,93,.92);
        }

        .ff-score-row {
            display: grid;
            gap: .55rem;
            margin-top: .7rem;
        }

        .ff-score-label {
            display: flex;
            justify-content: space-between;
            font-size: .87rem;
            color: var(--ff-muted);
            margin-bottom: .22rem;
        }

        .ff-progress {
            width: 100%;
            height: 10px;
            border-radius: 999px;
            background: rgba(25,49,31,.08);
            overflow: hidden;
        }

        .ff-progress-bar {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #6bcf68 0%, #f4c95d 100%);
        }

        .ff-mini-banner {
            border-radius: 22px;
            padding: 1rem 1.1rem;
            background: linear-gradient(135deg, rgba(107,207,104,.11) 0%, rgba(244,201,93,.16) 100%);
            border: 1px solid rgba(22,56,35,.08);
            margin: .6rem 0 1rem 0;
        }

        .ff-stat-box {
            background: rgba(255,255,255,.88);
            border: 1px solid var(--ff-border);
            border-radius: 22px;
            padding: 1rem 1.1rem;
            box-shadow: 0 8px 24px rgba(20,49,34,.03);
        }

        .ff-icon-line {
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            font-weight: 760;
        }

        .ff-timeline-note {
            border-left: 3px solid rgba(76,175,80,.35);
            padding-left: .9rem;
        }

        .ff-hero-pill:hover,
        .ff-btn-solid:hover,
        .ff-btn-ghost:hover {
            transform: translateY(-2px);
            transition: transform .18s ease;
        }

        /* STREAMLIT COMPONENT RESTYLING */
        div[data-testid="stMetric"] {
            background: rgba(255,255,255,.88);
            border: 1px solid var(--ff-border);
            border-radius: 20px;
            padding: .9rem 1rem;
            box-shadow: 0 8px 24px rgba(20,49,34,.03);
        }

        div[data-testid="stMetricValue"] {
            color: var(--ff-text);
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 24px;
            border: 1px solid var(--ff-border);
            background: rgba(255,255,255,.84);
            box-shadow: 0 8px 24px rgba(20,49,34,.03);
        }

        div[data-testid="stExpander"] {
            border-radius: 18px;
            border-color: var(--ff-border);
            background: rgba(255,255,255,.75);
        }

        .stButton > button {
            min-height: 48px;
            border-radius: 16px;
            font-weight: 780;
            border: 1px solid rgba(47,125,50,.10);
            box-shadow: 0 8px 20px rgba(20,49,34,.04);
        }

        div[data-baseweb="select"] > div,
        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea {
            border-radius: 14px !important;
        }

        [data-testid="stTabs"] button {
            font-weight: 760;
            font-size: .95rem;
        }

        [data-testid="stTabs"] {
            margin-top: .3rem;
        }

        @keyframes ffFadeUp {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes ffFloat {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(10px); }
        }

        @media (max-width: 980px) {
            .ff-hero-grid {
                grid-template-columns: 1fr;
            }
            .ff-hero-art {
                padding: 0 1.25rem 1.4rem 1.25rem;
            }
            .ff-tiles {
                grid-template-columns: 1fr 1fr;
            }
        }

        @media (max-width: 720px) {
            .block-container {
                padding-left: .8rem;
                padding-right: .8rem;
            }
            .ff-hero-copy {
                padding: 1.5rem 1.3rem 1rem 1.3rem;
            }
            .ff-tiles {
                grid-template-columns: 1fr;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# DATA
# =========================================================

@st.cache_data
def load_crop_data():
    return pd.read_csv("crops.csv")


@st.cache_data
def load_intercropping_data():
    try:
        return pd.read_csv("intercropping.csv")
    except FileNotFoundError:
        return pd.DataFrame(columns=["crop_1", "crop_2", "status", "reason"])


@st.cache_data
def load_water_data():
    return pd.read_csv("crop_water.csv")


crops = load_crop_data()
intercropping = load_intercropping_data()
water_data = load_water_data()


# =========================================================
# DATABASE
# =========================================================

DB_PATH = "farmfit.db"

EXTRA_COLUMNS = {
    "plant_part": "TEXT",
    "symptoms": "TEXT",
    "severity": "TEXT",
    "pest_evidence": "TEXT",
    "water_observation": "TEXT",
    "pesticide_used": "TEXT",
    "pesticide_type": "TEXT",
    "pesticide_name": "TEXT",
    "days_since_application": "INTEGER",
    "temperature_today": "REAL",
    "rain_today": "REAL",
    "rain_next_3_days": "REAL",
    "rule_assessment": "TEXT",
}


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS crop_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                crop TEXT,
                note TEXT,
                latitude REAL,
                longitude REAL,
                image BLOB,
                ai_analysis TEXT
            )
            """
        )

        existing = {
            row[1]
            for row in conn.execute("PRAGMA table_info(crop_checks)").fetchall()
        }

        for column, kind in EXTRA_COLUMNS.items():
            if column not in existing:
                conn.execute(
                    f"ALTER TABLE crop_checks ADD COLUMN {column} {kind}"
                )


def save_crop_check(record):
    fields = [
        "created_at", "crop", "plant_part", "symptoms", "severity",
        "pest_evidence", "water_observation", "pesticide_used",
        "pesticide_type", "pesticide_name", "days_since_application",
        "note", "latitude", "longitude", "temperature_today",
        "rain_today", "rain_next_3_days", "image", "rule_assessment",
    ]

    values = [record.get(field) for field in fields]

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            f"""
            INSERT INTO crop_checks ({",".join(fields)})
            VALUES ({",".join(["?"] * len(fields))})
            """,
            values,
        )


def load_crop_checks():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            "SELECT * FROM crop_checks ORDER BY id DESC",
            conn,
        )


def update_crop_check(check_id, updates):
    allowed = {
        "crop",
        "plant_part",
        "symptoms",
        "severity",
        "pest_evidence",
        "water_observation",
        "pesticide_used",
        "pesticide_type",
        "pesticide_name",
        "days_since_application",
        "note",
    }

    clean = {
        key: value
        for key, value in updates.items()
        if key in allowed
    }

    if not clean:
        return

    set_clause = ", ".join(f"{column} = ?" for column in clean)
    values = list(clean.values()) + [check_id]

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            f"UPDATE crop_checks SET {set_clause} WHERE id = ?",
            values,
        )


def delete_crop_check(check_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM crop_checks WHERE id = ?",
            (check_id,),
        )


init_db()


# =========================================================
# LOCATION + WEATHER
# =========================================================

@st.cache_data(ttl=86400)
def get_elevation(latitude, longitude):
    url = (
        "https://api.open-meteo.com/v1/elevation"
        f"?latitude={latitude}&longitude={longitude}"
    )
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return round(response.json()["elevation"][0], 1)
    except Exception:
        return None


@st.cache_data(ttl=1800)
def get_weather_forecast(latitude, longitude):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        "&daily="
        "weather_code,"
        "temperature_2m_max,"
        "temperature_2m_min,"
        "precipitation_sum,"
        "precipitation_probability_max,"
        "et0_fao_evapotranspiration"
        "&timezone=auto"
        "&forecast_days=7"
    )

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        daily = response.json()["daily"]

        return pd.DataFrame(
            {
                "Date": pd.to_datetime(daily["time"]),
                "Weather code": daily["weather_code"],
                "High °C": daily["temperature_2m_max"],
                "Low °C": daily["temperature_2m_min"],
                "Rain mm": daily["precipitation_sum"],
                "Rain chance %": daily["precipitation_probability_max"],
                "ETo mm": daily["et0_fao_evapotranspiration"],
            }
        )
    except Exception:
        return None


@st.cache_data(ttl=86400)
def get_nasa_climate(latitude, longitude):
    current_year = datetime.now().year
    start_year = current_year - 5
    end_year = current_year - 1

    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        "?parameters=T2M,PRECTOTCORR"
        "&community=AG"
        f"&longitude={longitude}"
        f"&latitude={latitude}"
        f"&start={start_year}0101"
        f"&end={end_year}1231"
        "&format=JSON"
    )

    try:
        response = requests.get(url, timeout=40)
        response.raise_for_status()
        parameters = response.json()["properties"]["parameter"]

        rows = []

        for day, temp in parameters["T2M"].items():
            rain = parameters["PRECTOTCORR"].get(day)

            if temp is None or rain is None or temp <= -900 or rain <= -900:
                continue

            rows.append(
                {
                    "date": pd.to_datetime(day, format="%Y%m%d"),
                    "temperature": temp,
                    "rainfall": rain,
                }
            )

        if not rows:
            return None

        df = pd.DataFrame(rows)
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month

        annual = df.groupby("year")["rainfall"].sum()

        monthly_rainfall = (
            df.groupby(["year", "month"])["rainfall"]
            .sum()
            .groupby("month")
            .mean()
            .round(1)
            .to_dict()
        )

        monthly_temperature = (
            df.groupby("month")["temperature"]
            .mean()
            .round(1)
            .to_dict()
        )

        return {
            "temperature": round(df["temperature"].mean(), 1),
            "annual_rainfall": round(annual.mean(), 1),
            "annual_rainfall_min": round(annual.min(), 1),
            "annual_rainfall_max": round(annual.max(), 1),
            "monthly_rainfall": monthly_rainfall,
            "monthly_temperature": monthly_temperature,
            "years": f"{start_year}-{end_year}",
        }

    except Exception as error:
        print("NASA POWER error:", error)
        return None


# =========================================================
# UI HELPERS
# =========================================================

def render_hero():
    hero_html = """<div class="ff-hero-wrap">
<div class="ff-hero">
<div class="ff-hero-glow"></div>
<div class="ff-hero-grid">
<div class="ff-hero-copy">
<div class="ff-kicker">🛰️ NASA Space Apps 2026 · Field Shift</div>
<h1>Hurricane to Harvest</h1>
<p style="font-size:1.25rem;font-weight:700;margin:-.2rem 0 .6rem 0;opacity:.95">Crop rotations that weather the storm and rebuild the soil.</p>
<p>FarmFit turns NASA Earth observations, 55 years of NOAA hurricane tracks and crop science into crop-rotation calendars for Caribbean farmers. Each plan protects the harvest from storms, rebuilds the soil and saves water, and comes with a recovery plan for after the storm.</p>
<div class="ff-hero-pills">
<span class="ff-hero-pill">NASA POWER · SMAP · IMERG · SRTM</span>
<span class="ff-hero-pill">Hurricane stress test</span>
<span class="ff-hero-pill">Soil-health rotations</span>
<span class="ff-hero-pill">After-storm recovery</span>
</div>
<div class="ff-hero-cta">
<span class="ff-btn-solid">Build a storm-ready plan</span>
<span class="ff-btn-ghost">Recover after a storm</span>
</div>
</div>
<div class="ff-hero-art">
<div class="ff-farm-scene">
<div class="ff-scene-sun"></div>
<div class="ff-signal"></div>
<div class="ff-hill one"></div>
<div class="ff-hill two"></div>
<div class="ff-field-row"></div>
<div class="ff-field-row r2"></div>
<div class="ff-field-row r3"></div>
<div class="ff-plant p1">🌱</div>
<div class="ff-plant p2">🌿</div>
<div class="ff-plant p3">🌱</div>
<div class="ff-float-card nasa"><strong>NASA POWER</strong><span>30 years of daily climate</span></div>
<div class="ff-float-card rotation"><strong>Storm exposure</strong><span>NOAA HURDAT2 1971-2025</span></div>
<div class="ff-float-card water"><strong>Water check</strong><span>ETc = Kc × ETo</span></div>
</div>
</div>
</div>
</div>
</div>"""
    st.markdown(hero_html, unsafe_allow_html=True)


def render_top_tiles():
    st.markdown(
        """
        <div class="ff-tiles">
          <div class="ff-tile">
            <div class="ff-tile-icon">🗺️</div>
            <div class="ff-tile-title">Map-based field setup</div>
            <div class="ff-tile-copy">Drop a pin and let FarmFit pull the field context automatically.</div>
          </div>
          <div class="ff-tile">
            <div class="ff-tile-icon">💧</div>
            <div class="ff-tile-title">Water-aware recommendations</div>
            <div class="ff-tile-copy">Use ETc = Kc × ETo for near-term water screening and compare shortfalls.</div>
          </div>
          <div class="ff-tile">
            <div class="ff-tile-icon">🩺</div>
            <div class="ff-tile-title">Structured crop checks</div>
            <div class="ff-tile-copy">Record visible symptoms, water observations, pest evidence and pesticide history.</div>
          </div>
          <div class="ff-tile">
            <div class="ff-tile-icon">📚</div>
            <div class="ff-tile-title">Farm memory</div>
            <div class="ff-tile-copy">Save checks over time and identify recurring patterns for the same crop or field.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def weather_icon(code):
    if code == 0:
        return "☀️"
    if code in [1, 2]:
        return "🌤️"
    if code == 3:
        return "☁️"
    if code in [45, 48]:
        return "🌫️"
    if code in [51, 53, 55, 56, 57]:
        return "🌦️"
    if code in [61, 63, 65, 66, 67, 80, 81, 82]:
        return "🌧️"
    if code in [95, 96, 99]:
        return "⛈️"
    return "🌤️"


def show_weather_cards(forecast):
    if forecast is None or forecast.empty:
        st.info("Forecast data is unavailable right now.")
        return

    columns = st.columns(len(forecast))

    for col, row in zip(columns, forecast.itertuples()):
        with col:
            st.markdown(
                f"""
                <div class="ff-weather">
                    <div style="font-size:.82rem; color:#617064;">{row.Date.strftime("%a")}</div>
                    <div class="icon">{weather_icon(row[2])}</div>
                    <div style="font-size:1.05rem; font-weight:800; color:#143122;">{row[3]:.0f}°</div>
                    <div style="font-size:.82rem; color:#617064;">{row[4]:.0f}° low</div>
                    <div style="font-size:.82rem; color:#617064;">💧 {row[5]:.1f} mm</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_score_breakdown(weights):
    labels = [
        ("Environmental fit", weights[0]),
        ("Rotation / soil fit", weights[1]),
        ("Near-term water fit", weights[2]),
    ]

    parts = ['<div class="ff-score-row">']

    for label, weight in labels:
        pct = max(0, min(100, round(weight * 100)))
        parts.append(
            f'<div class="ff-score-item">'
            f'<div class="ff-score-label"><span>{label}</span><span>{pct}%</span></div>'
            f'<div class="ff-progress"><div class="ff-progress-bar" style="width:{pct}%"></div></div>'
            f'</div>'
        )

    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_section_intro(kicker, title, subtitle):
    st.markdown(
        f"""
        <div style="margin-top:.2rem; margin-bottom:.5rem;">
          <div class="ff-section-kicker">{kicker}</div>
          <h3 style="margin:.1rem 0 .25rem 0;">{title}</h3>
          <div class="ff-subtle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# SCIENTIFIC CROP LOGIC
# =========================================================

CLASSIFICATION_SCORES = {
    "Optimal": 100,
    "Tolerable": 60,
    "Outside Range": 0,
}

ROTATION_SCORE = {
    "Caution": 25,
    "Limited history": 55,
    "Good diversity": 80,
    "Potential soil benefit": 85,
    "Strong diversity": 100,
}


def classify_range(value, optimal_min, optimal_max, absolute_min, absolute_max):
    if value is None:
        return "Unknown"

    if optimal_min <= value <= optimal_max:
        return "Optimal"

    if absolute_min <= value <= absolute_max:
        return "Tolerable"

    return "Outside Range"


def status_symbol(status):
    return {
        "Optimal": "✓",
        "Tolerable": "△",
        "Outside Range": "!",
        "Unknown": "?",
    }.get(status, "?")


def calculate_environment_score(evaluation):
    scores = [
        CLASSIFICATION_SCORES[value]
        for value in evaluation.values()
        if value in CLASSIFICATION_SCORES
    ]

    return round(sum(scores) / len(scores)) if scores else None


def evaluate_environment(crop_name, nasa, soil_ph):
    crop = crops[crops["crop"] == crop_name].iloc[0]

    return {
        "Temperature": classify_range(
            nasa["temperature"],
            crop["temp_opt_min"],
            crop["temp_opt_max"],
            crop["temp_abs_min"],
            crop["temp_abs_max"],
        ),
        "Rainfall": classify_range(
            nasa["annual_rainfall"],
            crop["rain_opt_min"],
            crop["rain_opt_max"],
            crop["rain_abs_min"],
            crop["rain_abs_max"],
        ),
        "Soil pH": (
            classify_range(
                soil_ph,
                crop["ph_opt_min"],
                crop["ph_opt_max"],
                crop["ph_abs_min"],
                crop["ph_abs_max"],
            )
            if soil_ph is not None
            else "Unknown"
        ),
    }


def evaluate_rotation(current_crop, next_crop):
    next_data = crops[crops["crop"] == next_crop].iloc[0]

    if current_crop in ["Other", "Nothing / Field is resting"]:
        return {
            "status": (
                "Potential soil benefit"
                if next_data["nitrogen_fixing"] == "Yes"
                else "Limited history"
            ),
            "message": (
                f"{next_crop} is a nitrogen-fixing legume, but the previous "
                "crop family is unknown."
                if next_data["nitrogen_fixing"] == "Yes"
                else "Previous crop family is unknown, so rotation diversity "
                "cannot be fully assessed."
            ),
        }

    current_data = crops[crops["crop"] == current_crop].iloc[0]

    if current_data["family"] == next_data["family"]:
        return {
            "status": "Caution",
            "message": (
                f"{current_crop} and {next_crop} are both in the "
                f"{next_data['family']} family."
            ),
        }

    if next_data["nitrogen_fixing"] == "Yes":
        return {
            "status": "Strong diversity",
            "message": (
                f"{next_crop} adds a different crop family and is a "
                "nitrogen-fixing legume."
            ),
        }

    return {
        "status": "Good diversity",
        "message": f"{next_crop} adds a different crop family.",
    }


def crop_kc(crop_name, stage):
    row = water_data[water_data["crop"] == crop_name]

    if row.empty:
        return None, None

    row = row.iloc[0]

    column = {
        "Initial": "kc_initial",
        "Mid-season": "kc_mid",
        "Late season": "kc_late",
    }[stage]

    return float(row[column]), row["water_basis"]


def calculate_water_profile(crop_name, forecast, stage="Mid-season"):
    if forecast is None or forecast.empty:
        return None

    kc, basis = crop_kc(crop_name, stage)

    if kc is None:
        return None

    eto = float(forecast["ETo mm"].sum())
    rain = float(forecast["Rain mm"].sum())

    # FAO single crop-coefficient method
    etc = kc * eto

    # Screening only
    screening_gap = max(etc - rain, 0)

    return {
        "kc": round(kc, 2),
        "basis": basis,
        "eto_7d": round(eto, 1),
        "etc_7d": round(etc, 1),
        "rain_7d": round(rain, 1),
        "screening_gap": round(screening_gap, 1),
    }


def water_score(profile):
    if profile is None:
        return None

    return max(0, min(100, round(100 - profile["screening_gap"] * 2.5)))


def interpret_water_stress(profile, irrigation_access):
    """
    Prototype farmer-facing interpretation of the 7-day screening gap.

    These thresholds are product heuristics for communication, not published
    crop-stress thresholds and not an irrigation prescription.
    """
    if profile is None:
        return None

    gap = float(profile["screening_gap"])

    if gap <= 0:
        level = "Low near-term water stress signal"
        message = (
            "Forecast rainfall meets or exceeds the crop's estimated 7-day ETc "
            "screening demand."
        )
        actions = [
            "Keep monitoring soil moisture because rainfall may not all become plant-available water.",
            "No extra irrigation amount is prescribed from this screen alone.",
        ]
    elif gap <= 10:
        level = "Watch closely"
        message = (
            f"FarmFit shows an uncovered 7-day water demand of about {gap:.1f} mm."
        )
        actions = [
            "Check soil moisture below the surface before watering.",
            "Watch the forecast and the crop for wilting or heat stress.",
        ]
    else:
        level = "Elevated near-term water stress signal"
        message = (
            f"FarmFit shows an uncovered 7-day water demand of about {gap:.1f} mm."
        )
        actions = [
            "Verify soil moisture and drainage before planting or irrigating.",
            "If the field is not yet planted, compare a lower-demand crop or a later planting window.",
            "If the crop is established, use local irrigation guidance that accounts for soil, root depth and system efficiency.",
        ]

    if irrigation_access == "No irrigation available" and gap > 0:
        actions.insert(
            0,
            "Because irrigation is unavailable, treat this as a stronger planning constraint."
        )
    elif irrigation_access == "Limited irrigation" and gap > 0:
        actions.insert(
            0,
            "Because irrigation is limited, prioritise monitoring and avoid assuming the full gap can be replaced."
        )
    elif irrigation_access == "Reliable irrigation" and gap > 0:
        actions.insert(
            0,
            "Reliable irrigation may reduce the planning risk, but the exact amount still needs local scheduling."
        )

    return {
        "level": level,
        "message": message,
        "actions": actions,
        "gap": gap,
    }


def make_recommendations(
    candidate_crops,
    current_crop,
    nasa,
    forecast,
    soil_ph,
    priority,
    planting_timing,
):
    results = []

    for crop_name in candidate_crops:
        env = evaluate_environment(crop_name, nasa, soil_ph)
        env_score = calculate_environment_score(env)

        rotation = evaluate_rotation(current_crop, crop_name)
        rotation_score = ROTATION_SCORE.get(rotation["status"], 50)

        water = calculate_water_profile(
            crop_name,
            forecast,
            stage="Mid-season",
        )

        w_score = water_score(water)

        if planting_timing == "Later / just exploring":
            weights = {
                "Balanced": (0.70, 0.30, 0.00),
                "Save water": (0.65, 0.35, 0.00),
                "Improve soil / rotation": (0.55, 0.45, 0.00),
            }[priority]
        else:
            weights = {
                "Balanced": (0.55, 0.25, 0.20),
                "Save water": (0.40, 0.20, 0.40),
                "Improve soil / rotation": (0.45, 0.40, 0.15),
            }[priority]

        env_w, rot_w, water_w = weights

        components = [
            (env_score if env_score is not None else 0, env_w),
            (rotation_score, rot_w),
        ]

        if w_score is not None and water_w > 0:
            components.append((w_score, water_w))

        total_weight = sum(weight for _, weight in components)

        score = round(
            sum(value * weight for value, weight in components) / total_weight
        )

        row = crops[crops["crop"] == crop_name].iloc[0]

        results.append(
            {
                "crop": crop_name,
                "crop_type": row["crop_type"],
                "family": row["family"],
                "nitrogen_fixing": row["nitrogen_fixing"],
                "environment": env,
                "environment_score": env_score,
                "rotation": rotation,
                "rotation_score": rotation_score,
                "water": water,
                "water_score": w_score,
                "comparison_score": score,
                "weights": weights,
            }
        )

    return sorted(
        results,
        key=lambda item: item["comparison_score"],
        reverse=True,
    )


def recommendation_reasons(result, priority, timing):
    positive = []
    cautions = []

    for variable, status in result["environment"].items():
        if status == "Optimal":
            positive.append(f"{variable} is within the crop's optimal range.")
        elif status == "Tolerable":
            cautions.append(
                f"{variable} is within the crop's wider tolerance range, "
                "but outside the optimal range."
            )
        elif status == "Outside Range":
            cautions.append(
                f"{variable} falls outside the crop's stored tolerance range."
            )

    if result["rotation"]["status"] in [
        "Strong diversity",
        "Good diversity",
        "Potential soil benefit",
    ]:
        positive.append(result["rotation"]["message"])
    else:
        cautions.append(result["rotation"]["message"])

    if result["nitrogen_fixing"] == "Yes":
        positive.append(
            "This crop is stored as a nitrogen-fixing legume, which is relevant "
            "to the soil/rotation objective."
        )

    if timing == "Soon / next 2 weeks" and result["water"]:
        gap = result["water"]["screening_gap"]

        if gap <= 0:
            positive.append(
                "Forecast rainfall meets or exceeds the 7-day ETc screening demand."
            )
        elif gap <= 10:
            cautions.append(
                f"The 7-day water screening shows a small {gap:.1f} mm gap."
            )
        else:
            cautions.append(
                f"The 7-day water screening shows a {gap:.1f} mm gap between "
                "forecast rainfall and crop ETc."
            )

    return positive, cautions


def find_intercrops(selected_crops):
    output = []

    for _, row in intercropping.iterrows():
        if row["crop_1"] in selected_crops and row["crop_2"] in selected_crops:
            output.append(row.to_dict())

    return output


# =========================================================
# STRUCTURED CROP CHECK
# =========================================================

PLANT_PARTS = [
    "Leaves",
    "Fruit",
    "Stem",
    "Roots",
    "Flowers",
    "Whole plant / general growth",
]

SYMPTOMS = [
    "Yellow leaves",
    "Brown / dry leaf edges",
    "Leaf spots",
    "Holes or chewing damage",
    "Leaf curling",
    "Wilting / drooping",
    "Stunted or slow growth",
    "Fruit cracking / splitting",
    "Fruit rotting / soft patches",
    "Discolouration on fruit",
    "Stem damage",
    "White / powdery growth",
    "Black / sooty-looking coating",
    "Flowers dropping",
    "Plant dying back",
]

PEST_EVIDENCE = [
    "None seen",
    "Small insects",
    "Caterpillars / worms",
    "Beetles",
    "Mites / tiny specks",
    "Eggs",
    "Webbing",
    "Sticky residue",
    "Chewed leaves",
    "Other visible pest evidence",
]

WATER_OBSERVATIONS = [
    "Soil seems normal",
    "Soil is very dry",
    "Soil stays very wet / waterlogged",
    "Crop wilted during hot periods",
    "Heavy rain occurred recently",
    "Watering has been irregular",
    "Not sure",
]


def structured_crop_assessment(
    symptoms,
    pest_evidence,
    water_observation,
    pesticide_used,
    severity,
):
    possibilities = []
    checks = []

    symptom_set = set(symptoms)

    if symptom_set & {
        "Yellow leaves",
        "Brown / dry leaf edges",
        "Wilting / drooping",
        "Stunted or slow growth",
    }:
        possibilities.append(
            "Water or root-zone stress is worth checking because the selected "
            "symptoms can occur when roots cannot access water normally."
        )
        checks.append(
            "Check soil moisture below the surface and whether the soil is "
            "draining or remaining saturated."
        )

    if "Fruit cracking / splitting" in symptom_set:
        possibilities.append(
            "Irregular water supply is one possible contributor to fruit cracking."
        )
        checks.append(
            "Compare recent dry periods, irrigation changes and heavy rainfall "
            "with when cracking began."
        )

    if water_observation in [
        "Soil is very dry",
        "Crop wilted during hot periods",
        "Watering has been irregular",
    ]:
        possibilities.append(
            "The farmer's water observation supports investigating moisture stress."
        )

    if water_observation == "Soil stays very wet / waterlogged":
        possibilities.append(
            "Excess water and poor root-zone aeration are worth investigating."
        )

    if symptom_set & {
        "Leaf spots",
        "Fruit rotting / soft patches",
        "White / powdery growth",
        "Black / sooty-looking coating",
        "Plant dying back",
    }:
        possibilities.append(
            "A disease-related cause is possible, but visual symptoms alone are "
            "not enough to identify a specific disease."
        )
        checks.append(
            "Look at how symptoms are distributed across the field and whether "
            "they expanded after wet/humid conditions."
        )

    if pest_evidence != "None seen" or symptom_set & {
        "Holes or chewing damage",
        "Leaf curling",
    }:
        possibilities.append(
            "Pest pressure is worth investigating because visible pest evidence "
            "or feeding-type damage was recorded."
        )
        checks.append(
            "Inspect the upper and lower leaf surfaces, stems and nearby plants "
            "for insects, eggs, webbing or feeding damage."
        )

    if symptom_set & {
        "Yellow leaves",
        "Stunted or slow growth",
        "Brown / dry leaf edges",
    }:
        possibilities.append(
            "Nutrient availability is another category worth checking; these "
            "symptoms are not nutrient-specific by themselves."
        )
        checks.append(
            "If the problem persists, compare symptoms with a soil or tissue test "
            "rather than diagnosing a nutrient deficiency from colour alone."
        )

    if pesticide_used == "Yes":
        possibilities.append(
            "A pesticide application was recorded. Timing should be considered "
            "when comparing when symptoms appeared or changed."
        )
        checks.append(
            "Review the product label, crop registration, application date and "
            "whether symptoms began before or after application."
        )

    if severity == "Severe / spreading quickly":
        checks.append(
            "Because the issue is severe or spreading quickly, obtain local "
            "agronomic or extension support before making treatment decisions."
        )

    if not possibilities:
        possibilities.append(
            "The selected observations do not point strongly to one screening "
            "category. Continue documenting changes and field conditions."
        )

    possibilities = list(dict.fromkeys(possibilities))
    checks = list(dict.fromkeys(checks))

    return possibilities, checks


def format_assessment(possibilities, checks):
    lines = ["POSSIBLE CATEGORIES TO INVESTIGATE"]
    for item in possibilities:
        lines.append(f"- {item}")

    lines.append("")
    lines.append("WHAT TO CHECK NEXT")
    for item in checks:
        lines.append(f"- {item}")

    return "\n".join(lines)


# =========================================================
# HISTORY INSIGHTS
# =========================================================

def split_saved_list(value):
    if pd.isna(value) or not value:
        return []
    return [item.strip() for item in str(value).split("|") if item.strip()]


def history_insights(history, crop=None):
    if history.empty:
        return []

    df = history.copy()

    if crop and crop != "All crops":
        df = df[df["crop"] == crop]

    if df.empty:
        return []

    insights = []

    all_symptoms = []
    for value in df["symptoms"].dropna():
        all_symptoms.extend(split_saved_list(value))

    if all_symptoms:
        counts = pd.Series(all_symptoms).value_counts()
        top = counts.index[0]
        count = int(counts.iloc[0])

        if count >= 2:
            insights.append(
                f"{top} has been recorded {count} times in the selected history."
            )

    wet = df[df["water_observation"] == "Heavy rain occurred recently"]
    cracks = df[
        df["symptoms"].fillna("").str.contains("Fruit cracking / splitting")
    ]

    if not wet.empty and not cracks.empty:
        overlap = df[
            (df["water_observation"] == "Heavy rain occurred recently")
            & (
                df["symptoms"]
                .fillna("")
                .str.contains("Fruit cracking / splitting")
            )
        ]

        if len(overlap) >= 1:
            insights.append(
                "Your history includes fruit cracking checks recorded with "
                "recent heavy rain. Treat this as a farm-history pattern to "
                "watch, not proof that rain caused the cracking."
            )

    dry = df[df["water_observation"].isin(
        ["Soil is very dry", "Crop wilted during hot periods"]
    )]

    if len(dry) >= 2:
        insights.append(
            f"{len(dry)} checks recorded dry-soil or heat-wilting observations."
        )

    pest_rows = df[df["pest_evidence"].fillna("None seen") != "None seen"]

    if len(pest_rows) >= 2:
        insights.append(
            f"Visible pest evidence was recorded in {len(pest_rows)} checks."
        )

    pesticide_rows = df[df["pesticide_used"] == "Yes"]

    if len(pesticide_rows) >= 1:
        insights.append(
            f"{len(pesticide_rows)} check(s) include a pesticide-use record, "
            "which can be compared with symptom timing."
        )

    return insights


# =========================================================
# STATE
# =========================================================

if "farm_latitude" not in st.session_state:
    st.session_state.farm_latitude = fs_ui.DEMO_SITES["jamaica"]["lat"]

if "farm_longitude" not in st.session_state:
    st.session_state.farm_longitude = fs_ui.DEMO_SITES["jamaica"]["lon"]

if "last_results" not in st.session_state:
    st.session_state.last_results = None


# =========================================================
# LAYOUT START
# =========================================================

render_hero()

# Native Streamlit navigation keeps all movement inside the same app/browser tab.
def go_to_view(view_name):
    st.session_state["requested_view"] = view_name


s1, s2 = st.columns([1, 1])

with s1:
    if st.button(
        "🌀 Build a storm-ready rotation",
        use_container_width=True,
        type="primary",
        key="hero_storm",
    ):
        go_to_view("storm")
        st.rerun()

with s2:
    if st.button(
        "🛰️ Recover after a storm",
        use_container_width=True,
        key="hero_after",
    ):
        go_to_view("after")
        st.rerun()

n1, n2, n3 = st.columns([1, 1, 1])

with n1:
    if st.button(
        "🌱 Quick crop check for your field",
        use_container_width=True,
        key="hero_start_field",
    ):
        go_to_view("plan")
        st.rerun()

with n2:
    if st.button(
        "☀️ NASA climate + water stress",
        use_container_width=True,
        key="hero_field_insights",
    ):
        go_to_view("field")
        st.rerun()

with n3:
    if st.button(
        "🔬 Explore the method",
        use_container_width=True,
        key="hero_method",
    ):
        go_to_view("method")
        st.rerun()

n4, n5, n6 = st.columns([1, 1, 1])

with n4:
    if st.button(
        "🩺 Crop check",
        use_container_width=True,
        key="hero_crop_check",
    ):
        go_to_view("check")
        st.rerun()

with n5:
    if st.button(
        "📚 Crop check history",
        use_container_width=True,
        key="hero_history",
    ):
        go_to_view("history")
        st.rerun()

with n6:
    if st.button(
        "🌾 Rotation insights",
        use_container_width=True,
        key="hero_rotation",
    ):
        go_to_view("plan")
        st.session_state["show_rotation_hint"] = True
        st.rerun()

render_top_tiles()

view_key = st.session_state.pop(
    "requested_view",
    st.query_params.get("view", "storm"),
)
st.query_params["view"] = view_key
view_to_label = {
    "storm": "🌀 Storm-ready plan",
    "after": "🛰️ After the storm",
    "plan": "🌱 Plan",
    "field": "☀️ My field",
    "check": "🩺 Crop check",
    "history": "📚 History",
    "method": "🔬 Method",
}
label_to_view = {label: key for key, label in view_to_label.items()}

active_nav = st.segmented_control(
    "Navigation",
    list(view_to_label.values()),
    default=view_to_label.get(view_key, "🌀 Storm-ready plan"),
    label_visibility="collapsed",
)

selected_view = label_to_view.get(active_nav, "storm")
if selected_view != view_key:
    st.query_params["view"] = selected_view
    st.rerun()


# =========================================================
# HURRICANE TO HARVEST (fieldshift package)
# =========================================================

if active_nav == "🌀 Storm-ready plan":
    fs_ui.render_storm_plan()

if active_nav == "🛰️ After the storm":
    fs_ui.render_after_storm()


# =========================================================
# PLAN
# =========================================================

if active_nav == "🌱 Plan":
    st.markdown('<div id="planner"></div>', unsafe_allow_html=True)

    if st.session_state.pop("show_rotation_hint", False):
        st.info(
            "Rotation insights are part of the crop recommendation results. "
            "Build a recommendation below to compare crop-family diversity, "
            "nitrogen-fixing crops and same-family rotation cautions."
        )

    render_section_intro(
        "Step 1",
        "Plan the next crop",
        "Choose your goal, pin the field, and let FarmFit compare what makes the most sense for this location.",
    )

    crop_names = crops["crop"].tolist()

    p1, p2, p3 = st.columns([1.2, 1, 1])

    with p1:
        current_crop = st.selectbox(
            "What is growing here now?",
            ["Nothing / Field is resting", "Other"] + crop_names,
        )

    with p2:
        priority = st.selectbox(
            "What matters most?",
            ["Balanced", "Save water", "Improve soil / rotation"],
        )

    with p3:
        timing = st.selectbox(
            "When might you plant?",
            ["Soon / next 2 weeks", "Later / just exploring"],
        )

    helper1, helper2 = st.columns([1, 1.25])

    with helper1:
        know_ph = st.toggle("I know my soil pH")

    soil_ph = None
    if know_ph:
        with helper2:
            soil_ph = st.number_input(
                "Soil pH",
                min_value=3.0,
                max_value=10.0,
                value=6.0,
                step=0.1,
            )

    mode = st.segmented_control(
        "How do you want to explore?",
        ["Recommend crops for me", "Compare crops I choose"],
        default="Recommend crops for me",
    )

    if mode == "Compare crops I choose":
        candidate_crops = st.multiselect(
            "Crops you are considering",
            crop_names,
            max_selections=5,
        )
    else:
        candidate_crops = [
            crop for crop in crop_names if crop != current_crop
        ]

    st.markdown(
        """
        <div class="ff-mini-banner">
          <div class="ff-icon-line">🧭 Pin the field</div>
          <div class="ff-subtle" style="margin-top:.25rem;">
            Tap the map below. FarmFit will use the selected coordinates to
            retrieve elevation, NASA climate history and weather forecast data.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    farm_map = folium.Map(
        location=[
            st.session_state.farm_latitude,
            st.session_state.farm_longitude,
        ],
        zoom_start=10,
        control_scale=True,
        tiles="OpenStreetMap",
    )

    folium.Marker(
        [
            st.session_state.farm_latitude,
            st.session_state.farm_longitude,
        ],
        tooltip="Selected field",
        icon=folium.Icon(color="green", icon="leaf"),
    ).add_to(farm_map)

    map_data = st_folium(
        farm_map,
        height=390,
        width=None,
        key="planning_map",
    )

    if map_data and map_data.get("last_clicked"):
        new_lat = round(map_data["last_clicked"]["lat"], 6)
        new_lng = round(map_data["last_clicked"]["lng"], 6)

        if (
            new_lat != st.session_state.farm_latitude
            or new_lng != st.session_state.farm_longitude
        ):
            st.session_state.farm_latitude = new_lat
            st.session_state.farm_longitude = new_lng
            st.rerun()

    latitude = st.session_state.farm_latitude
    longitude = st.session_state.farm_longitude
    elevation = get_elevation(latitude, longitude)

    m1, m2, m3 = st.columns(3)
    m1.metric("Latitude", f"{latitude:.4f}")
    m2.metric("Longitude", f"{longitude:.4f}")
    m3.metric(
        "Elevation",
        f"{elevation:.0f} m" if elevation is not None else "Unavailable",
    )

    if st.button(
        "Build my recommendation",
        type="primary",
        use_container_width=True,
    ):
        if mode == "Compare crops I choose" and not candidate_crops:
            st.warning("Choose at least one crop.")
        else:
            with st.spinner("Reading the field conditions..."):
                nasa = get_nasa_climate(latitude, longitude)
                forecast = get_weather_forecast(latitude, longitude)

            if nasa is None:
                st.error("NASA climate data could not be loaded.")
            else:
                results = make_recommendations(
                    candidate_crops,
                    current_crop,
                    nasa,
                    forecast,
                    soil_ph,
                    priority,
                    timing,
                )

                st.session_state.last_results = {
                    "results": results,
                    "nasa": nasa,
                    "forecast": forecast,
                    "current_crop": current_crop,
                    "priority": priority,
                    "timing": timing,
                    "soil_ph": soil_ph,
                    "mode": mode,
                }

    state = st.session_state.last_results

    if not state:
        st.markdown('<div id="recommendations"></div>', unsafe_allow_html=True)
        st.info(
            "Rotation insights appear here after you build a recommendation. "
            "FarmFit compares the current crop family with each next-crop option."
        )

    if state:
        st.divider()

        results = state["results"]
        nasa = state["nasa"]
        forecast = state["forecast"]

        render_section_intro(
            "Field snapshot",
            "This is what FarmFit is seeing",
            "Historical climate is used for crop fit, while the forecast supports near-term context.",
        )

        s1, s2, s3 = st.columns(3)
        s1.metric("Avg temperature", f"{nasa['temperature']} °C")
        s2.metric("Avg annual rainfall", f"{nasa['annual_rainfall']} mm")
        s3.metric("Climate baseline", nasa["years"])

        if forecast is not None:
            show_weather_cards(forecast)

        st.markdown('<div id="recommendations"></div>', unsafe_allow_html=True)
        render_section_intro(
            "Recommendations",
            "Best-fitting options",
            "FarmFit ranks crops using environmental fit, rotation/soil logic, and near-term water screening when relevant.",
        )

        shown = results[:5]

        for index, result in enumerate(shown, start=1):
            with st.container(border=True):
                heading, score_col = st.columns([5, 1])

                with heading:
                    title = (
                        f"#{index} {result['crop']}"
                        if state["mode"] == "Recommend crops for me"
                        else result["crop"]
                    )
                    st.markdown(f"### {title}")
                    st.caption(
                        f"{result['crop_type']} · {result['family']}"
                    )

                with score_col:
                    st.metric(
                        "FarmFit",
                        f"{result['comparison_score']}/100",
                    )

                if result["nitrogen_fixing"] == "Yes":
                    st.markdown(
                        '<span class="ff-chip">Nitrogen-fixing legume</span>',
                        unsafe_allow_html=True,
                    )

                e1, e2, e3 = st.columns(3)

                for col, (label, status) in zip(
                    [e1, e2, e3],
                    result["environment"].items(),
                ):
                    with col:
                        st.markdown(
                            f"**{status_symbol(status)} {label}**  \n{status}"
                        )

                positives, cautions = recommendation_reasons(
                    result,
                    state["priority"],
                    state["timing"],
                )

                with st.expander("Why FarmFit placed this crop here", expanded=index == 1):
                    st.markdown("**How the score was weighted**")
                    render_score_breakdown(result["weights"])

                    st.markdown("**What supports this option**")
                    for item in positives:
                        st.markdown(
                            f'<div class="ff-reason">{item}</div>',
                            unsafe_allow_html=True,
                        )

                    if cautions:
                        st.markdown("**What to watch**")
                        for item in cautions:
                            st.markdown(
                                f'<div class="ff-warning">{item}</div>',
                                unsafe_allow_html=True,
                            )

                    if result["water"]:
                        w = result["water"]
                        st.markdown("**Water calculation**")
                        st.write(
                            f"7-day ETo = {w['eto_7d']} mm, Kc = {w['kc']}, "
                            f"so ETc = {w['etc_7d']} mm. Forecast rainfall = "
                            f"{w['rain_7d']} mm. Screening gap = "
                            f"{w['screening_gap']} mm."
                        )
                        st.caption("Kc source/basis: " + str(w["basis"]))

        names = [result["crop"] for result in shown]
        inter = find_intercrops(names)

        if inter:
            with st.expander("Intercropping possibilities"):
                for option in inter:
                    st.markdown(
                        f"**{option['crop_1']} + {option['crop_2']}**"
                    )
                    st.write(option["reason"])

        st.caption(
            "FarmFit is comparing supported options. The score is not a "
            "probability of crop success or a yield forecast."
        )


# =========================================================
# MY FIELD
# =========================================================

if active_nav == "☀️ My field":
    st.markdown('<div id="climate-insights"></div>', unsafe_allow_html=True)
    render_section_intro(
        "Field context",
        "What your field looks like right now",
        "A cleaner field dashboard with visual weather, monthly climate, and crop-water screening.",
    )

    latitude = st.session_state.farm_latitude
    longitude = st.session_state.farm_longitude

    with st.spinner("Loading field conditions..."):
        nasa = get_nasa_climate(latitude, longitude)
        forecast = get_weather_forecast(latitude, longitude)
        elevation = get_elevation(latitude, longitude)

    f1, f2, f3 = st.columns(3)
    f1.metric("Latitude", f"{latitude:.4f}")
    f2.metric("Longitude", f"{longitude:.4f}")
    f3.metric(
        "Elevation",
        f"{elevation:.0f} m" if elevation is not None else "Unavailable",
    )

    if forecast is not None:
        st.markdown("### Next 7 days")
        show_weather_cards(forecast)

    if nasa:
        st.markdown("### Climate context")
        c1, c2, c3 = st.columns(3)
        c1.metric("Average temperature", f"{nasa['temperature']} °C")
        c2.metric("Average annual rainfall", f"{nasa['annual_rainfall']} mm")
        c3.metric(
            "5-year rainfall range",
            f"{nasa['annual_rainfall_min']}–{nasa['annual_rainfall_max']} mm",
        )

        months = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]

        climate = pd.DataFrame(
            {
                "Month": months,
                "Rainfall (mm)": [
                    nasa["monthly_rainfall"].get(i)
                    for i in range(1, 13)
                ],
                "Temperature (°C)": [
                    nasa["monthly_temperature"].get(i)
                    for i in range(1, 13)
                ],
            }
        )

        chart_data = climate.set_index("Month")

        st.markdown("**Typical monthly rainfall**")
        st.bar_chart(chart_data["Rainfall (mm)"], color="#66B96B")

        st.markdown("**Typical monthly temperature**")
        st.bar_chart(chart_data["Temperature (°C)"], color="#F4A340")

    st.markdown('<div id="water-stress-test"></div>', unsafe_allow_html=True)

    render_section_intro(
        "Water stress test",
        "Will forecast rain likely keep up with this crop's near-term water demand?",
        "FarmFit compares 7-day crop evapotranspiration (ETc) with forecast rainfall, then translates the gap into a simple planning signal.",
    )

    w1, w2, w3 = st.columns(3)

    with w1:
        water_crop = st.selectbox(
            "Crop",
            crops["crop"].tolist(),
            key="field_water_crop",
        )

    with w2:
        stage = st.selectbox(
            "Growth stage",
            ["Initial", "Mid-season", "Late season"],
        )

    with w3:
        irrigation_access = st.selectbox(
            "Irrigation access",
            [
                "No irrigation available",
                "Limited irrigation",
                "Reliable irrigation",
            ],
        )

    profile = calculate_water_profile(
        water_crop,
        forecast,
        stage,
    )

    if profile:
        stress = interpret_water_stress(profile, irrigation_access)

        st.markdown(f"### {stress['level']}")
        st.write(stress["message"])

        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Reference ETo", f"{profile['eto_7d']} mm")
        q2.metric("Estimated crop ETc", f"{profile['etc_7d']} mm")
        q3.metric("Forecast rain", f"{profile['rain_7d']} mm")
        q4.metric("Uncovered demand", f"{profile['screening_gap']} mm")

        if stress["gap"] <= 0:
            st.success(
                "Near-term signal: forecast rainfall covers the crop's ETc screening demand."
            )
        elif stress["gap"] <= 10:
            st.warning(
                "Near-term signal: some crop water demand is not covered by forecast rain."
            )
        else:
            st.error(
                "Near-term signal: a larger share of crop water demand is not covered by forecast rain."
            )

        st.markdown("#### What this means for the farmer")
        for action in stress["actions"]:
            st.markdown(
                f'<div class="ff-reason">{action}</div>',
                unsafe_allow_html=True,
            )

        with st.expander("How the stress test is calculated"):
            st.write(
                f"FarmFit uses Kc = {profile['kc']} for {water_crop} at the "
                f"{stage.lower()} stage. Over the next 7 days, ETo is "
                f"{profile['eto_7d']} mm, giving ETc of {profile['etc_7d']} mm. "
                f"Forecast rainfall is {profile['rain_7d']} mm."
            )
            st.code(
                "ETc = Kc × ETo\n"
                "screening_gap = max(ETc - forecast_rainfall, 0)"
            )
            st.caption(
                "The Low / Watch / Elevated labels are prototype communication "
                "heuristics, not published crop-stress thresholds. This screen "
                "does not model effective rainfall, runoff, root-zone storage, "
                "rooting depth or irrigation efficiency."
            )

        st.caption("Kc source/basis: " + str(profile["basis"]))


# =========================================================
# CROP CHECK
# =========================================================

if active_nav == "🩺 Crop check":
    st.markdown('<div id="crop-check"></div>', unsafe_allow_html=True)
    render_section_intro(
        "Crop check",
        "Record what you can actually observe",
        "Instead of relying on free text alone, FarmFit uses structured field observations and maps them to categories worth investigating.",
    )

    st.markdown(
        """
        <div class="ff-tiles">
          <div class="ff-tile">
            <div class="ff-tile-icon">👀</div>
            <div class="ff-tile-title">Observe</div>
            <div class="ff-tile-copy">Record what you can actually see instead of guessing the cause.</div>
          </div>
          <div class="ff-tile">
            <div class="ff-tile-icon">🪲</div>
            <div class="ff-tile-title">Add context</div>
            <div class="ff-tile-copy">Capture pest evidence, water conditions and recent pesticide use.</div>
          </div>
          <div class="ff-tile">
            <div class="ff-tile-icon">🧭</div>
            <div class="ff-tile-title">Screen</div>
            <div class="ff-tile-copy">FarmFit maps the observations to categories worth investigating.</div>
          </div>
          <div class="ff-tile">
            <div class="ff-tile-icon">📚</div>
            <div class="ff-tile-title">Remember</div>
            <div class="ff-tile-copy">Save the check so repeated field patterns become visible over time.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    with c1:
        check_crop = st.selectbox(
            "Crop",
            ["Not sure"] + crops["crop"].tolist(),
            key="check_crop",
        )

        plant_part = st.selectbox(
            "Where is the problem most visible?",
            PLANT_PARTS,
        )

        severity = st.selectbox(
            "How serious does it look?",
            [
                "Minor / only a few spots or plants",
                "Moderate / clearly affecting growth",
                "Severe / spreading quickly",
            ],
        )

    with c2:
        pest_evidence = st.selectbox(
            "Any visible pest evidence?",
            PEST_EVIDENCE,
        )

        water_observation = st.selectbox(
            "What have you noticed about water recently?",
            WATER_OBSERVATIONS,
        )

        pesticide_used = st.radio(
            "Has a pesticide been used recently?",
            ["No", "Yes"],
            horizontal=True,
        )

    symptoms = st.multiselect(
        "What are you seeing?",
        SYMPTOMS,
        placeholder="Select all that apply",
    )

    pesticide_type = ""
    pesticide_name = ""
    days_since_application = None

    if pesticide_used == "Yes":
        pc1, pc2, pc3 = st.columns(3)

        with pc1:
            pesticide_type = st.selectbox(
                "Type",
                [
                    "Insecticide",
                    "Fungicide",
                    "Herbicide",
                    "Other / not sure",
                ],
            )

        with pc2:
            pesticide_name = st.text_input(
                "Product name, if known",
            )

        with pc3:
            days_since_application = st.number_input(
                "Days since application",
                min_value=0,
                max_value=365,
                value=0,
            )

    note = st.text_area(
        "Anything else you noticed? (optional)",
        placeholder="Example: problem began two days after heavy rain...",
    )

    source = st.segmented_control(
        "Photo",
        ["Camera", "Upload", "No photo"],
        default="Camera",
    )

    photo = None

    if source == "Camera":
        photo = st.camera_input("Take a crop photo")
    elif source == "Upload":
        photo = st.file_uploader(
            "Upload crop photo",
            type=["jpg", "jpeg", "png"],
        )

    if symptoms:
        possibilities, checks = structured_crop_assessment(
            symptoms,
            pest_evidence,
            water_observation,
            pesticide_used,
            severity,
        )

        st.markdown("### Screening result")

        st.markdown("**Possible categories to investigate**")
        for item in possibilities:
            st.markdown(
                f'<div class="ff-reason">{item}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("**What to check next**")
        for item in checks:
            st.markdown(
                f'<div class="ff-warning">{item}</div>',
                unsafe_allow_html=True,
            )

        st.caption(
            "These are screening categories, not diagnoses. Similar crop "
            "symptoms can have multiple causes."
        )

    if st.button(
        "Save crop check",
        type="primary",
        use_container_width=True,
    ):
        if not symptoms and not note.strip() and photo is None:
            st.warning("Add at least one symptom, note or photo.")
        else:
            forecast_now = get_weather_forecast(
                st.session_state.farm_latitude,
                st.session_state.farm_longitude,
            )

            temp_today = None
            rain_today = None
            rain_3 = None

            if forecast_now is not None and not forecast_now.empty:
                temp_today = float(forecast_now.iloc[0]["High °C"])
                rain_today = float(forecast_now.iloc[0]["Rain mm"])
                rain_3 = float(forecast_now.head(3)["Rain mm"].sum())

            possibilities, checks = structured_crop_assessment(
                symptoms,
                pest_evidence,
                water_observation,
                pesticide_used,
                severity,
            )

            assessment = format_assessment(possibilities, checks)

            save_crop_check(
                {
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "crop": check_crop,
                    "plant_part": plant_part,
                    "symptoms": " | ".join(symptoms),
                    "severity": severity,
                    "pest_evidence": pest_evidence,
                    "water_observation": water_observation,
                    "pesticide_used": pesticide_used,
                    "pesticide_type": pesticide_type,
                    "pesticide_name": pesticide_name,
                    "days_since_application": days_since_application,
                    "note": note.strip(),
                    "latitude": st.session_state.farm_latitude,
                    "longitude": st.session_state.farm_longitude,
                    "temperature_today": temp_today,
                    "rain_today": rain_today,
                    "rain_next_3_days": rain_3,
                    "image": photo.getvalue() if photo is not None else None,
                    "rule_assessment": assessment,
                }
            )

            st.success("Crop check saved to field history.")


# =========================================================
# HISTORY
# =========================================================

if active_nav == "📚 History":
    render_section_intro(
        "Farm memory",
        "Your field history",
        "Review saved crop checks in a simple table, then open one entry to edit or delete it.",
    )

    history = load_crop_checks()

    if history.empty:
        st.info("No crop checks have been saved yet.")
    else:
        crop_filter = st.selectbox(
            "View history for",
            ["All crops"] + sorted(history["crop"].dropna().unique().tolist()),
        )

        filtered = history.copy()

        if crop_filter != "All crops":
            filtered = filtered[filtered["crop"] == crop_filter]

        insights = history_insights(history, crop_filter)

        if insights:
            with st.expander("Patterns FarmFit noticed in these records"):
                for insight in insights:
                    st.markdown(
                        f'<div class="ff-reason">{insight}</div>',
                        unsafe_allow_html=True,
                    )
                st.caption(
                    "These patterns are descriptive associations, not proof of cause."
                )

        table = filtered[
            [
                "id",
                "created_at",
                "crop",
                "severity",
                "symptoms",
                "water_observation",
                "pest_evidence",
            ]
        ].copy()

        table.columns = [
            "ID",
            "Date",
            "Crop",
            "Severity",
            "Symptoms",
            "Water observation",
            "Pest evidence",
        ]

        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Manage an entry")

        options = {
            f"#{row.id} · {row.crop} · {row.created_at}": row.id
            for row in filtered.itertuples()
        }

        chosen = st.selectbox(
            "Select entry",
            list(options.keys()),
            key="history_manage_entry",
        )

        record = filtered[
            filtered["id"] == options[chosen]
        ].iloc[0]

        r1, r2, r3 = st.columns(3)
        r1.metric("Crop", record["crop"])
        r2.metric("Severity", record["severity"] or "Not recorded")
        r3.metric(
            "Rain next 3 days",
            (
                f"{record['rain_next_3_days']:.1f} mm"
                if pd.notna(record["rain_next_3_days"])
                else "Unavailable"
            ),
        )

        if record["image"] is not None:
            with st.expander("View saved image"):
                st.image(
                    record["image"],
                    caption="Saved crop image",
                    use_container_width=True,
                )

        action_col1, action_col2 = st.columns(2)

        with action_col1:
            edit_clicked = st.button(
                "✏️ Edit selected entry",
                use_container_width=True,
                key=f"edit_selected_{record['id']}",
            )

        with action_col2:
            delete_clicked = st.button(
                "🗑️ Delete selected entry",
                use_container_width=True,
                key=f"delete_selected_{record['id']}",
            )

        if edit_clicked:
            st.session_state["editing_history_id"] = int(record["id"])

        if delete_clicked:
            st.session_state["deleting_history_id"] = int(record["id"])

        if st.session_state.get("editing_history_id") == int(record["id"]):
            with st.container(border=True):
                st.markdown("#### Edit crop check")

                edit_crop = st.selectbox(
                    "Crop",
                    ["Not sure"] + crops["crop"].tolist(),
                    index=(
                        ["Not sure"] + crops["crop"].tolist()
                    ).index(record["crop"])
                    if record["crop"] in (["Not sure"] + crops["crop"].tolist())
                    else 0,
                    key=f"edit_crop_{record['id']}",
                )

                ec1, ec2 = st.columns(2)

                with ec1:
                    edit_plant_part = st.selectbox(
                        "Affected part",
                        PLANT_PARTS,
                        index=(
                            PLANT_PARTS.index(record["plant_part"])
                            if record["plant_part"] in PLANT_PARTS
                            else 0
                        ),
                        key=f"edit_part_{record['id']}",
                    )

                    edit_severity = st.selectbox(
                        "Severity",
                        [
                            "Minor / only a few spots or plants",
                            "Moderate / clearly affecting growth",
                            "Severe / spreading quickly",
                        ],
                        index=(
                            [
                                "Minor / only a few spots or plants",
                                "Moderate / clearly affecting growth",
                                "Severe / spreading quickly",
                            ].index(record["severity"])
                            if record["severity"] in [
                                "Minor / only a few spots or plants",
                                "Moderate / clearly affecting growth",
                                "Severe / spreading quickly",
                            ]
                            else 0
                        ),
                        key=f"edit_severity_{record['id']}",
                    )

                with ec2:
                    edit_pest = st.selectbox(
                        "Pest evidence",
                        PEST_EVIDENCE,
                        index=(
                            PEST_EVIDENCE.index(record["pest_evidence"])
                            if record["pest_evidence"] in PEST_EVIDENCE
                            else 0
                        ),
                        key=f"edit_pest_{record['id']}",
                    )

                    edit_water = st.selectbox(
                        "Water observation",
                        WATER_OBSERVATIONS,
                        index=(
                            WATER_OBSERVATIONS.index(record["water_observation"])
                            if record["water_observation"] in WATER_OBSERVATIONS
                            else 0
                        ),
                        key=f"edit_water_{record['id']}",
                    )

                saved_symptoms = split_saved_list(record["symptoms"])
                edit_symptoms = st.multiselect(
                    "Symptoms",
                    SYMPTOMS,
                    default=[
                        symptom
                        for symptom in saved_symptoms
                        if symptom in SYMPTOMS
                    ],
                    key=f"edit_symptoms_{record['id']}",
                )

                edit_note = st.text_area(
                    "Farmer note",
                    value=str(record["note"] or ""),
                    key=f"edit_note_{record['id']}",
                )

                save_col, cancel_col = st.columns(2)

                with save_col:
                    if st.button(
                        "Save changes",
                        type="primary",
                        use_container_width=True,
                        key=f"save_edit_{record['id']}",
                    ):
                        update_crop_check(
                            int(record["id"]),
                            {
                                "crop": edit_crop,
                                "plant_part": edit_plant_part,
                                "symptoms": " | ".join(edit_symptoms),
                                "severity": edit_severity,
                                "pest_evidence": edit_pest,
                                "water_observation": edit_water,
                                "note": edit_note,
                            },
                        )
                        st.session_state.pop("editing_history_id", None)
                        st.success("Crop check updated.")
                        st.rerun()

                with cancel_col:
                    if st.button(
                        "Cancel",
                        use_container_width=True,
                        key=f"cancel_edit_{record['id']}",
                    ):
                        st.session_state.pop("editing_history_id", None)
                        st.rerun()

        if st.session_state.get("deleting_history_id") == int(record["id"]):
            with st.container(border=True):
                st.warning(
                    f"Delete crop check #{int(record['id'])} for {record['crop']}? "
                    "This cannot be undone."
                )

                confirm_col, cancel_col = st.columns(2)

                with confirm_col:
                    if st.button(
                        "Yes, delete it",
                        use_container_width=True,
                        key=f"confirm_delete_{record['id']}",
                    ):
                        delete_crop_check(int(record["id"]))
                        st.session_state.pop("deleting_history_id", None)
                        st.success("Crop check deleted.")
                        st.rerun()

                with cancel_col:
                    if st.button(
                        "Cancel",
                        use_container_width=True,
                        key=f"cancel_delete_{record['id']}",
                    ):
                        st.session_state.pop("deleting_history_id", None)
                        st.rerun()




# =========================================================
# METHOD
# =========================================================

if active_nav == "🔬 Method":
    st.markdown('<div id="method-top"></div>', unsafe_allow_html=True)
    render_section_intro(
        "Scientific logic",
        "How FarmFit reaches a result",
        "This section explains the technical method, where each part fits, and what the app can and cannot conclude.",
    )

    st.write(
        "FarmFit separates **sourced measurements** from **product-level scoring**. "
        "The sourced measurements remain visible so the farmer can understand why "
        "a crop ranks where it does."
    )

    st.markdown("### 1. Field location becomes the environmental key")
    st.write(
        "The farmer pins the field on the map. Latitude and longitude are then "
        "used as the common key for environmental requests. Elevation is looked "
        "up separately. This avoids asking the farmer to manually enter weather "
        "or climate measurements."
    )

    st.markdown("### 2. Historical climate describes the field context")
    st.write(
        "FarmFit requests daily temperature and precipitation from NASA POWER "
        "for the previous five complete calendar years. Daily values are "
        "aggregated into a mean temperature, average annual rainfall, annual "
        "rainfall range and monthly climate profile."
    )

    st.write(
        "This historical baseline is used for crop-climate suitability. The "
        "7-day forecast is kept separate so a short weather forecast does not "
        "masquerade as long-term climate."
    )

    st.markdown("### 3. Crop suitability is range-based before it is scored")
    st.write(
        "Each supported crop has stored optimal and wider tolerance ranges for "
        "temperature, annual rainfall and soil pH. For each variable FarmFit "
        "first classifies the field as Optimal, Tolerable, Outside Range or "
        "Unknown."
    )

    st.code(
        """if optimal_min <= field_value <= optimal_max:
    status = "Optimal"
elif absolute_min <= field_value <= absolute_max:
    status = "Tolerable"
else:
    status = "Outside Range" """,
        language="python",
    )

    st.write(
        "Only after classification does FarmFit translate the categories into "
        "a transparent comparison score: Optimal = 100, Tolerable = 60, Outside "
        "Range = 0. Unknown values are excluded. This score is not a probability "
        "of crop survival or yield."
    )

    st.markdown("### 4. Rotation logic is kept separate from climate fit")
    st.write(
        "FarmFit compares the current crop family with the candidate crop "
        "family. Repeating the same family is flagged for review; changing "
        "families increases rotation diversity. Nitrogen-fixing legumes receive "
        "an additional soil/rotation signal because they can contribute "
        "biologically fixed nitrogen under suitable conditions."
    )

    st.write(
        "The model deliberately does not claim that a legume will add a fixed "
        "quantity of nitrogen. Actual fixation depends on crop, rhizobia, soil, "
        "management and growing conditions."
    )

    st.markdown("### 5. Water demand uses the FAO crop-coefficient approach")
    st.latex(r"ET_c = K_c \times ET_o")

    st.write(
        "**ETo** is reference evapotranspiration, representing atmospheric "
        "evaporative demand from a standardized well-watered reference surface. "
        "**Kc** is the crop coefficient for a growth stage. **ETc** is estimated "
        "crop evapotranspiration under the standard crop-coefficient approach."
    )

    st.write(
        "FarmFit obtains FAO-56 reference ETo from the weather service and uses "
        "the crop's stored Kc for Initial, Mid-season or Late-season growth."
    )

    st.code(
        """ETc_7d = Kc * ETo_7d
screening_gap = max(ETc_7d - forecast_rain_7d, 0)""",
        language="python",
    )

    st.write(
        "The result is called a **screening gap**, not an irrigation requirement. "
        "A true irrigation schedule also needs effective rainfall, runoff, soil "
        "water storage, rooting depth, allowable depletion and irrigation-system "
        "efficiency."
    )

    st.markdown("### 6. Water stress test turns the calculation into a farmer-facing signal")

    st.write(
        "The raw ETc calculation is useful scientifically, but a farmer also needs "
        "to know what it means. FarmFit therefore compares 7-day ETc with forecast "
        "rainfall and reports the uncovered demand as a screening gap."
    )

    st.latex(r"\text{screening gap} = \max(ET_c - P_{forecast}, 0)")

    st.write(
        "The interface then labels the result as Low, Watch closely, or Elevated. "
        "Those labels are prototype communication heuristics, not published crop-stress "
        "thresholds. Their purpose is to make the water result actionable without "
        "pretending it is a full irrigation schedule."
    )

    st.write(
        "The farmer's irrigation access is added as decision context. For example, "
        "the same uncovered demand matters more when no irrigation is available than "
        "when reliable irrigation exists."
    )

    st.markdown("**What the stress test still does not model**")
    st.markdown(
        """
- effective rainfall rather than total forecast rainfall
- runoff and deep percolation
- current root-zone soil-water storage
- crop rooting depth
- allowable soil-water depletion
- irrigation-system efficiency
- soil texture and field capacity
        """
    )

    st.write(
        "Those variables are the main path toward a more complete field water-balance "
        "model in a later FarmFit version."
    )

    st.markdown("### 7. Forecast data affects only near-term decisions")
    st.write(
        "If the farmer says they may plant in the next two weeks, FarmFit can "
        "include the 7-day water screening in the ranking. If they are only "
        "exploring a later crop, the short-term forecast gets zero weight. This "
        "prevents a one-week weather pattern from dominating a longer-term crop "
        "choice."
    )

    st.markdown("### 8. Recommendation weighting follows farmer priorities")
    weights = pd.DataFrame(
        [
            ["Soon", "Balanced", "55%", "25%", "20%"],
            ["Soon", "Save water", "40%", "20%", "40%"],
            ["Soon", "Improve soil / rotation", "45%", "40%", "15%"],
            ["Later", "Balanced", "70%", "30%", "0%"],
            ["Later", "Save water", "65%", "35%", "0%"],
            ["Later", "Improve soil / rotation", "55%", "45%", "0%"],
        ],
        columns=[
            "Planning horizon",
            "Farmer priority",
            "Environment",
            "Rotation",
            "Near-term water",
        ],
    )

    st.dataframe(weights, use_container_width=True, hide_index=True)

    st.write(
        "These weights are product-design assumptions for the prototype, not "
        "published agronomic constants. They are shown openly so they can be "
        "tested, challenged and calibrated with agronomists and farmer feedback."
    )

    st.markdown("### 9. Crop Check uses structured observations, not diagnosis")
    st.write(
        "The crop checker records observable symptoms, plant part, severity, "
        "visible pest evidence, water observations and recent pesticide use. "
        "Rule-based logic maps combinations to broad categories worth "
        "investigating such as water/root-zone stress, possible pest pressure, "
        "possible disease-related symptoms or nutrient availability."
    )

    st.write(
        "A symptom such as yellow leaves is intentionally not mapped directly "
        "to a named deficiency because the same visible symptom can have "
        "multiple causes."
    )

    st.markdown("### 10. Field history adds farm-specific evidence")
    st.write(
        "Every crop check is stored with its timestamp, field coordinates and "
        "the weather context available at the time. FarmFit can then identify "
        "recurring observations such as repeated cracking after checks that "
        "also recorded heavy rain, or repeated pest evidence."
    )

    st.write(
        "Those are described as historical associations. FarmFit does not call "
        "them causal relationships without stronger evidence."
    )

    st.markdown("### 11. What FarmFit can and cannot conclude")
    st.markdown(
        """
**FarmFit can currently support**
- comparison of crop climate ranges
- crop-family rotation diversity
- identification of nitrogen-fixing legumes
- near-term ETc water-demand screening
- evidence-backed intercropping entries
- structured field-observation history
- descriptive recurring-pattern detection

**FarmFit does not currently claim**
- exact yield prediction
- exact fertilizer requirements
- definitive pest or disease diagnosis
- pesticide selection or dosage
- exact irrigation scheduling
- causal relationships from crop-check history
- seasonal climate prediction from a 7-day forecast
        """
    )

    st.markdown("### 12. How FarmFit handles uncertainty")

    st.write(
        "FarmFit keeps three kinds of information conceptually separate: sourced "
        "environmental measurements, curated crop characteristics, and prototype "
        "decision weights. That separation matters because they do not have the "
        "same evidentiary status."
    )

    st.markdown(
        """
- **Environmental measurements:** location-based climate and forecast inputs.
- **Crop parameters:** curated crop ranges and Kc values stored in FarmFit datasets.
- **Farmer observations:** field symptoms, pest evidence, water observations and history.
- **Decision heuristics:** scoring weights, qualitative rotation scores and stress-test labels.
        """
    )

    st.write(
        "A future validation phase should compare FarmFit recommendations against "
        "agronomist review and real field outcomes, then recalibrate the heuristic "
        "weights rather than treating the prototype values as fixed."
    )

    st.markdown("### Scientific data sources used by the prototype")
    st.markdown(
        """
- **NASA POWER Daily API**: historical daily meteorological time series for the selected point.
- **FAO Irrigation and Drainage Paper 56**: crop evapotranspiration methodology and crop coefficients.
- **Open-Meteo**: 7-day forecast data and FAO-56 reference evapotranspiration (ETo).
- **FAO Ecocrop / agronomic sources in the crop dataset**: crop environmental ranges and crop-system characteristics.
        """
    )

    st.caption(
        "FarmFit is a decision-support prototype. Local agronomic knowledge, "
        "soil testing and field inspection remain important when a decision "
        "has meaningful production or financial consequences."
    )
