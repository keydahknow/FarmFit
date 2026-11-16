"""Caribbean agriculture news and official sources.

Headlines come live from Google News RSS searches (no key needed) and are
shown as links to the original publishers. The official-source list is fixed
and checked by hand.
"""

import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

QUERIES = {
    "Trinidad and Tobago": "agriculture OR farmers Trinidad Tobago",
    "Jamaica": "agriculture OR farmers Jamaica",
    "Caribbean region": "Caribbean agriculture OR farmers OR CARDI OR CARICOM food",
}

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


def headlines(region, limit=8, timeout=12):
    q = QUERIES[region]
    url = "https://news.google.com/rss/search"
    params = {"q": q + " when:60d", "hl": "en-TT", "gl": "TT", "ceid": "TT:en"}
    r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "FarmFit/1.0"})
    r.raise_for_status()
    return parse_rss(r.text, limit)


def parse_rss(xml_text, limit=8):
    root = ET.fromstring(xml_text)
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        source = (item.findtext("source") or "").strip()
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
