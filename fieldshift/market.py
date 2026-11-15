"""Local market timing from NAMDEVCO wholesale prices (Trinidad and Tobago).

NAMDEVCO publishes average monthly wholesale prices for the Norris Deonarine
Northern Wholesale Market as open data (CC-BY) on data.gov.tt. The scheduled
refresh downloads them; this module turns them into a seasonal price index per
crop: a harvest month with an index above 1 usually sells above the year's
average. The file layouts vary by year, so parsing is deliberately forgiving.
"""

import io
import re
from pathlib import Path

import numpy as np
import pandas as pd
import requests

CKAN = "https://data.gov.tt/api/3/action/package_search"
MONTH_NAMES = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

# FarmFit crop -> words that identify it in NAMDEVCO commodity names
ALIASES = {
    "Tomato": ["tomato"], "Sweet Pepper": ["sweet pepper", "pepper sweet", "bell pepper"],
    "Hot Pepper": ["hot pepper", "pepper hot", "scotch"], "Eggplant": ["melongene", "eggplant", "baigan"],
    "Okra": ["ochro", "okra"], "Cucumber": ["cucumber"], "Pumpkin": ["pumpkin"], "Watermelon": ["watermelon", "melon"],
    "Sweet Potato": ["sweet potato"], "Cassava": ["cassava"], "Dasheen": ["dasheen"], "Plantain": ["plantain"],
    "Bodi": ["bodi"], "Pigeon Peas": ["pigeon pea"], "Cabbage": ["cabbage"], "Pak Choi": ["pak choi", "patchoi", "pak-choi"],
    "Callaloo": ["callaloo", "dasheen bush", "spinach"], "Corn": ["corn"], "Common Bean": ["bean"], "Cowpea": ["cowpea", "black eye"],
    "Peanut": ["peanut"], "Rice": ["rice"],
}


def _month_of(text):
    t = str(text).strip().lower()[:3]
    return MONTH_NAMES.index(t) + 1 if t in MONTH_NAMES else None


def tidy(df):
    """Any NAMDEVCO price table -> columns commodity, month, price."""
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    month_cols = [c for c in df.columns if _month_of(c)]
    text_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c]) and c not in month_cols]
    if not text_cols:
        return pd.DataFrame(columns=["commodity", "month", "price"])
    name_col = max(text_cols, key=lambda c: df[c].astype(str).str.contains("[A-Za-z]{3}").mean() * df[c].nunique())
    if len(month_cols) >= 3:  # wide: one column per month
        long = df.melt(id_vars=[name_col], value_vars=month_cols, var_name="m", value_name="price")
        long["month"] = long["m"].map(_month_of)
    else:  # long: a month/date column and a price column
        date_col = next((c for c in df.columns if re.search("month|date|period", c, re.I)), None)
        price_col = next((c for c in df.columns if re.search("price|avg|average|\\$", c, re.I) and c != name_col), None)
        if not (date_col and price_col):
            return pd.DataFrame(columns=["commodity", "month", "price"])
        long = df[[name_col, date_col, price_col]].rename(columns={price_col: "price"})
        months = long[date_col].map(_month_of)
        dates = pd.to_datetime(long[date_col], errors="coerce")
        long["month"] = months.fillna(dates.dt.month)
    long["price"] = pd.to_numeric(long["price"].astype(str).str.replace(r"[^0-9.]", "", regex=True), errors="coerce")
    long = long.rename(columns={name_col: "commodity"}).dropna(subset=["month", "price"])
    long = long[long["price"] > 0]
    long["month"] = long["month"].astype(int)
    long["commodity"] = long["commodity"].astype(str).str.strip()
    return long[["commodity", "month", "price"]]


def fetch_namdevco(timeout=60, max_files=8):
    """Download NAMDEVCO wholesale price CSVs through the CKAN API (run on the scheduled refresh)."""
    r = requests.get(CKAN, params={"q": "namdevco wholesale prices", "rows": 30}, timeout=timeout)
    r.raise_for_status()
    frames, used = [], []
    for pkg in r.json()["result"]["results"]:
        if "wholesale" not in pkg.get("title", "").lower():
            continue
        for res in pkg.get("resources", []):
            if len(used) >= max_files:
                break
            if str(res.get("format", "")).lower() not in ("csv", "xlsx", "xls"):
                continue
            try:
                raw = requests.get(res["url"], timeout=timeout).content
                df = pd.read_csv(io.BytesIO(raw)) if res["format"].lower() == "csv" else pd.read_excel(io.BytesIO(raw))
                t = tidy(df)
                if len(t):
                    t["source"] = pkg["title"]
                    frames.append(t)
                    used.append(pkg["title"])
            except Exception:  # noqa: BLE001
                continue
    if not frames:
        raise RuntimeError("no parseable NAMDEVCO wholesale files")
    return pd.concat(frames, ignore_index=True), used


def load(path):
    path = Path(path)
    return pd.read_csv(path) if path.exists() else None


def price_index(prices, crop):
    """Month (1-12) -> price relative to the crop's yearly average, or None."""
    if prices is None or crop not in ALIASES:
        return None
    names = prices["commodity"].str.lower()
    mask = np.zeros(len(prices), dtype=bool)
    for word in ALIASES[crop]:
        mask |= names.str.contains(word, regex=False).to_numpy()
    sub = prices[mask]
    if sub.empty or sub["month"].nunique() < 6:
        return None
    by_month = sub.groupby("month")["price"].median()
    return (by_month / by_month.mean()).to_dict()


def plan_market(plan, prices):
    """Harvest-month price index for each crop in a plan (crops without data are skipped)."""
    out = []
    for p in plan.plantings:
        idx = price_index(prices, p.crop)
        if idx:
            h = p.month_list()[-1]
            best = max(idx, key=idx.get)
            out.append({"crop": p.crop, "harvest": h, "index": idx.get(h), "best": best, "best_index": idx[best]})
    return out
