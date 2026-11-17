"""Farming news for wherever the farm is, plus official sources.

Where the farm is: OpenStreetMap Nominatim reverse geocoding (country), else the
place name the farmer searched for, else a broad region from the coordinates.

Headlines: Google News RSS, then Bing News RSS (no keys). Every successful fetch
is saved under data/cache/news/, and the scheduled data refresh saves headlines
for the pilot countries, the Caribbean and the world, so when both live feeds are
unreachable the page still shows the most recent saved headlines, dated.
"""

import json
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; FarmFit/1.0; +https://github.com/keydahknow/FarmFit)"}
CACHE = Path(__file__).resolve().parents[1] / "data" / "cache" / "news"

# Broad regions by coordinates, checked in order (first match wins).
REGIONS = [
    ("Caribbean", 9.5, 27.5, -90.0, -58.0),
    ("Central America", 7.0, 22.0, -118.0, -77.0),
    ("South America", -56.0, 13.0, -82.0, -34.0),
    ("North America", 13.0, 84.0, -170.0, -50.0),
    ("Europe", 35.0, 72.0, -25.0, 45.0),
    ("Middle East", 12.0, 42.0, 34.0, 63.0),
    ("Africa", -36.0, 38.0, -26.0, 55.0),
    ("South Asia", 5.0, 38.0, 60.0, 92.0),
    ("Southeast Asia", -11.0, 28.0, 92.0, 141.0),
    ("East Asia", 18.0, 55.0, 100.0, 150.0),
    ("Central Asia", 35.0, 56.0, 46.0, 88.0),
    ("Oceania", -50.0, 0.0, 110.0, 180.0),
    ("Pacific Islands", -30.0, 25.0, 140.0, 180.0),
]
ALIASES = {"trinidad": "Trinidad and Tobago", "tobago": "Trinidad and Tobago", "t&t": "Trinidad and Tobago",
           "usa": "United States", "uk": "United Kingdom"}
PRESETS = {  # saved by the scheduled refresh so there is always something to show
    "Trinidad and Tobago": "agriculture OR farmers Trinidad Tobago",
    "Jamaica": "agriculture OR farmers Jamaica",
    "Caribbean": "Caribbean agriculture OR farmers OR CARDI OR CARICOM food",
    "World": "agriculture farmers climate harvest",
}


def region_of(lat, lon):
    for name, lo_lat, hi_lat, lo_lon, hi_lon in REGIONS:
        if lo_lat <= lat <= hi_lat and lo_lon <= lon <= hi_lon:
            return name
    return "World"


def country_from_place(place):
    if not place:
        return None
    last = place.split(",")[-1].strip()
    return ALIASES.get(last.lower(), last) or None


def reverse_country(lat, lon, timeout=8):
    """Country name in English from OpenStreetMap Nominatim, or None."""
    try:
        r = requests.get("https://nominatim.openstreetmap.org/reverse",
                         params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 3, "accept-language": "en"},
                         headers=UA, timeout=timeout)
        r.raise_for_status()
        return (r.json().get("address") or {}).get("country")
    except Exception:  # noqa: BLE001
        return None


def locate(lat, lon, place=None):
    """{'country': str|None, 'region': str} for the farm."""
    country = reverse_country(lat, lon) or country_from_place(place)
    return {"country": ALIASES.get((country or "").lower(), country), "region": region_of(lat, lon)}


def query_for(scope, name):
    if scope == "world":
        return PRESETS["World"]
    if name in PRESETS:
        return PRESETS[name]
    return f'agriculture OR farmers OR crops "{name}"'


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "world"


def save_cache(key, items, folder=CACHE):
    try:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{slug(key)}.json").write_text(json.dumps({"fetched": time.strftime("%Y-%m-%d"), "items": items}, indent=1))
    except Exception:  # noqa: BLE001
        pass


def load_cache(key, folder=CACHE):
    f = folder / f"{slug(key)}.json"
    if not f.exists():
        return None
    try:
        data = json.loads(f.read_text())
        return data if data.get("items") else None
    except Exception:  # noqa: BLE001
        return None


def google(q, limit=8, timeout=7):
    r = requests.get("https://news.google.com/rss/search", params={"q": q + " when:90d", "hl": "en-US", "gl": "US", "ceid": "US:en"},
                     timeout=timeout, headers=UA)
    r.raise_for_status()
    return parse_rss(r.text, limit)


def bing(q, limit=8, timeout=7):
    r = requests.get("https://www.bing.com/news/search", params={"q": q, "format": "rss", "qft": "sortbydate=\"1\""},
                     timeout=timeout, headers=UA)
    r.raise_for_status()
    return parse_rss(r.text, limit)


def fetch(key, q, limit=8, folder=CACHE):
    """Live headlines (Google, then Bing), saved on success. Returns (items, how) with how = 'live' or None."""
    for source in (google, bing):
        try:
            items = source(q, limit)
            if items:
                save_cache(key, items, folder)
                return items, "live"
        except Exception:  # noqa: BLE001
            continue
    return None, None


def news_for(scopes, limit=8, folder=CACHE):
    """scopes: list of (key, query), most specific first. Order of attempts keeps the page quick:
    live for the first scope, then any saved copy, then live for the wider scopes.
    Returns {'items', 'key', 'how': 'live'|'saved', 'fetched'} or None."""
    def live(key, q):
        items, _ = fetch(key, q, limit, folder)
        return {"items": items, "key": key, "how": "live", "fetched": time.strftime("%Y-%m-%d")} if items else None

    if scopes and (res := live(*scopes[0])):
        return res
    for key, _ in scopes:
        saved = load_cache(key, folder)
        if saved:
            return {"items": saved["items"][:limit], "key": key, "how": "saved", "fetched": saved.get("fetched")}
    for key, q in scopes[1:]:
        if res := live(key, q):
            return res
    return None


# Real, stable pages farmers read; shown only if no headlines (live or saved) exist at all.
FURTHER_READING = [
    ("FAO Newsroom", "https://www.fao.org/newsroom/en", "Food and agriculture news from the UN Food and Agriculture Organization."),
    ("CGIAR news", "https://www.cgiar.org/news-events/news/", "Research news on crops, climate and farming from CGIAR centres."),
]

OFFICIAL = [
    ("Trinidad and Tobago Meteorological Service", "https://www.metoffice.gov.tt", "Official forecasts, warnings and agromet bulletins for T&T."),
    ("Ministry of Agriculture, Land and Fisheries (T&T)", "https://agriculture.gov.tt", "Extension services, farmer registration, programmes."),
    ("Office of Disaster Preparedness and Management (ODPM)", "https://www.odpm.gov.tt", "T&T disaster alerts and preparedness."),
    ("NAMDEVCO", "https://www.namdevco.com.tt", "Market prices, farmers' markets, post-harvest support (T&T)."),
    ("Meteorological Service of Jamaica", "https://metservice.gov.jm", "Official forecasts and warnings for Jamaica."),
    ("RADA (Jamaica)", "https://rada.gov.jm", "Rural Agricultural Development Authority: extension and damage reporting."),
    ("ODPEM (Jamaica)", "https://www.odpem.org.jm", "Jamaica disaster preparedness and emergency management."),
    ("CIMH: Caribbean Climate Outlooks and Drought Bulletin", "https://rcc.cimh.edu.bb", "Regional seasonal outlooks, SPI drought monitor."),
    ("CARDI", "https://www.cardi.org", "Caribbean Agricultural Research and Development Institute."),
    ("FAO Sub-regional Office for the Caribbean", "https://www.fao.org/americas/oficinas/caribbean/en", "Programmes, guidance, food security."),
    ("CCRIF Livelihood Protection Policy", "https://www.ccrif.org/livelihood-protection-policy-lpp", "Parametric micro-insurance for small farmers."),
    ("NOAA National Hurricane Center", "https://www.nhc.noaa.gov", "Live tropical storm advisories."),
]


def parse_rss(xml_text, limit=8):
    root = ET.fromstring(xml_text)
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        source = (item.findtext("source") or "").strip()
        if not source:
            source = next(((c.text or "").strip() for c in item if c.tag.lower().endswith("source")), "")
        when = item.findtext("pubDate")
        try:
            when = parsedate_to_datetime(when).date().isoformat() if when else ""
        except Exception:  # noqa: BLE001
            when = ""
        if source and title.endswith(" - " + source):
            title = title[: -len(source) - 3]
        title = re.sub(r"\s+", " ", title)
        if title and link:
            out.append({"title": title, "link": link, "source": source, "date": when})
        if len(out) >= limit:
            break
    return out


TT = {"Trinidad and Tobago Meteorological Service", "Ministry of Agriculture, Land and Fisheries (T&T)",
      "Office of Disaster Preparedness and Management (ODPM)", "NAMDEVCO"}
JM = {"Meteorological Service of Jamaica", "RADA (Jamaica)", "ODPEM (Jamaica)"}
GENERAL = [
    ("Your national weather service (WMO directory)", "https://community.wmo.int/en/members",
     "Find the official forecasts and warnings for your country."),
    ("FAO country profiles", "https://www.fao.org/countryprofiles/en/", "Food and agriculture programmes and data for your country."),
]
STORM_CENTRES = [  # (name, url, what, test(lat, lon))
    ("NOAA National Hurricane Center", "https://www.nhc.noaa.gov", "Live tropical storm advisories (Atlantic and eastern Pacific).",
     lambda lat, lon: lat >= 0 and -180 <= lon <= -20),
    ("Joint Typhoon Warning Center", "https://www.metoc.navy.mil/jtwc/jtwc.html", "Tropical cyclone warnings for the Pacific and Indian Oceans.",
     lambda lat, lon: lon >= 40 or lon <= -150),
    ("IMD Regional Specialised Meteorological Centre, New Delhi", "https://rsmcnewdelhi.imd.gov.in",
     "Cyclone bulletins for the Bay of Bengal and Arabian Sea.", lambda lat, lon: lat >= 0 and 40 <= lon <= 100),
    ("Australian Bureau of Meteorology: tropical cyclones", "http://www.bom.gov.au/cyclone/",
     "Cyclone warnings for Australia and nearby seas.", lambda lat, lon: lat < 0 and 90 <= lon <= 170),
]


def official_for(country, region, lat, lon):
    """Official sources that fit this farm: national ones where we have them checked by hand, regional, then general."""
    out = []
    if region == "Caribbean" or country in ("Trinidad and Tobago", "Jamaica"):
        for name, url, what in OFFICIAL:
            if name in TT and country != "Trinidad and Tobago":
                continue
            if name in JM and country != "Jamaica":
                continue
            out.append((name, url, what))
    else:
        out += GENERAL
        out += [(n, u, w) for n, u, w, test in STORM_CENTRES if test(lat, lon)]
    return out
