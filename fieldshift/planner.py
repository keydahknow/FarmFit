"""Rotation calendars, strategy generation and hurricane stress testing.

A plan is a 12-month cyclic calendar made of plantings (crop, start month,
length in months). Every plan is scored on five transparent components:

  suitability  ECOCROP temperature / rainfall / pH ranges vs NASA POWER climate
  storm        expected share of harvest lost to storm-force wind (HURDAT2
               exposure) and waterlogging (POWER heavy-rain + soil wetness)
  soil         cover during erosive months, legume months, family diversity,
               deep roots (RUSLE-style cover x rainfall logic)
  water        irrigation need from FAO-56 Kc x ET0 minus effective rain
  food         share of the year producing a harvest

Strategies are found by exhaustively enumerating every calendar of up to
four plantings (cyclic, no same family back-to-back) and ranking them with
a different weight profile each. All weights are listed in PROFILES.
"""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

CROP_FILE = Path(__file__).resolve().parents[1] / "data" / "crops_fieldshift.csv"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

STAGES = ["seedling", "vegetative", "reproductive", "mature"]
STAGE_COVER = {"seedling": 0.25, "vegetative": 0.70, "reproductive": 1.0, "mature": 0.90}
STAGE_KC = {"seedling": "kc_ini", "vegetative": "mid_ramp", "reproductive": "kc_mid", "mature": "kc_end"}

TS_SEVERITY = 0.45        # share of hurricane-force damage caused by tropical-storm-force wind
FLOOD_SEVERITY = 0.50     # share of crop lost when a waterlogging event hits a fully sensitive crop
EFFECTIVE_RAIN = 0.80     # fraction of rainfall that becomes plant-available (screening value)

PROFILES = {
    "storm": {
        "title": "Storm-smart",
        "icon": "🌀",
        "tagline": "Harvest before the riskiest months, keep the ground covered through them.",
        "weights": {"storm": 0.40, "suitability": 0.20, "soil": 0.15, "water": 0.10, "food": 0.15},
    },
    "soil": {
        "title": "Soil builder",
        "icon": "🪱",
        "tagline": "Maximise living cover, legumes and crop-family diversity.",
        "weights": {"storm": 0.15, "suitability": 0.20, "soil": 0.40, "water": 0.10, "food": 0.15},
    },
    "water": {
        "title": "Water saver",
        "icon": "💧",
        "tagline": "Line crops up with the rains so less irrigation is needed.",
        "weights": {"storm": 0.15, "suitability": 0.20, "soil": 0.15, "water": 0.35, "food": 0.15},
    },
}
CURRENT_PROFILE = {
    "title": "Your current rotation",
    "icon": "🧑🏾‍🌾",
    "tagline": "What you plant today, scored with the same rules.",
}


def load_crops():
    df = pd.read_csv(CROP_FILE)
    df["months"] = np.maximum(1, np.round(df["days_to_harvest"] / 30.4)).astype(int)
    return df.set_index("crop", drop=False)


@dataclass
class Planting:
    crop: str
    start: int  # 1..12
    months: int

    def month_list(self):
        return [((self.start - 1 + k) % 12) + 1 for k in range(self.months)]


@dataclass
class Plan:
    key: str
    plantings: list
    title: str = ""
    icon: str = ""
    tagline: str = ""
    scores: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)

    def occupancy(self):
        """12-element list: (crop, stage) or None for each month Jan..Dec."""
        out = [None] * 12
        for p in self.plantings:
            for k, m in enumerate(p.month_list()):
                out[m - 1] = (p.crop, stage_for(k, p.months))
        return out


def stage_for(k, n):
    f = (k + 0.5) / n
    if f < 0.2:
        return "seedling"
    if f < 0.55:
        return "vegetative"
    if f < 0.85:
        return "reproductive"
    return "mature"


def classify(value, opt_min, opt_max, abs_min, abs_max):
    if value is None or pd.isna(value):
        return 0.6
    if opt_min <= value <= opt_max:
        return 1.0
    if abs_min <= value <= abs_max:
        return 0.5
    return 0.0


class Site:
    """Everything the planner needs about one farm, already monthly."""

    def __init__(self, climate, exposure, soil=None, terrain=None):
        self.climate = climate.set_index("month")
        self.exposure = exposure.set_index("month")
        self.soil = soil or {}
        self.terrain = terrain or {}
        self.annual_rain = float(self.climate["rain_mm"].sum())
        rain = self.climate["rain_mm"].to_numpy()
        self.rain_share = rain / rain.sum() if rain.sum() > 0 else np.full(12, 1 / 12)

        drainage = (self.soil or {}).get("drainage")
        drain_factor = {"Fast": 0.6, "Good": 0.8, "Moderate": 1.0, "Slow": 1.2, "Very slow": 1.35}.get(drainage, 1.0)
        wet = self.climate["soil_wet_root"].to_numpy() if "soil_wet_root" in self.climate else np.full(12, 0.7)
        wet_factor = np.where(wet >= 0.7, 1.0, 0.65)
        self.p_flood = np.clip(self.climate["p_heavy_rain"].to_numpy() * wet_factor * drain_factor, 0, 1)
        self.p_hu = self.exposure["p_hurricane_force"].to_numpy()
        self.p_ts = np.clip(self.exposure["p_storm_force"].to_numpy() - self.p_hu, 0, 1)
        self.et0 = self.climate["et0_mm"].to_numpy() if "et0_mm" in self.climate else np.full(12, 120.0)
        self.t_mean = self.climate["t_mean"].to_numpy()
        self.rain = rain


# ---------------------------------------------------------------------------
# Planting-level metrics (precomputed once per site)
# ---------------------------------------------------------------------------

def planting_metrics(site, crop_row, start, months):
    idx = [((start - 1 + k) % 12) for k in range(months)]
    stages = [stage_for(k, months) for k in range(months)]

    temp = np.mean([
        classify(site.t_mean[i], crop_row.temp_opt_min, crop_row.temp_opt_max, crop_row.temp_abs_min, crop_row.temp_abs_max)
        for i in idx
    ])
    rain = classify(site.annual_rain, crop_row.rain_opt_min, crop_row.rain_opt_max, crop_row.rain_abs_min, crop_row.rain_abs_max)
    ph = site.soil.get("ph")
    ph_score = classify(ph, crop_row.ph_opt_min, crop_row.ph_opt_max, crop_row.ph_opt_min - 1.0, crop_row.ph_opt_max + 1.0)
    suitability = 0.5 * temp + 0.3 * rain + 0.2 * ph_score

    survive = 1.0
    wind_part = flood_part = 0.0
    cover = np.zeros(12)
    water_need = 0.0
    kc_mid_ramp = (crop_row.kc_ini + crop_row.kc_mid) / 2
    for i, stage in zip(idx, stages):
        v_wind = getattr(crop_row, f"wind_{stage}")
        stage_flood = 1.3 if stage == "seedling" else 1.0
        v_flood = min(1.0, crop_row.flood_vuln * stage_flood)
        loss_m = site.p_hu[i] * v_wind + site.p_ts[i] * TS_SEVERITY * v_wind + site.p_flood[i] * FLOOD_SEVERITY * v_flood
        loss_m = min(loss_m, 0.95)
        wind_part += site.p_hu[i] * v_wind + site.p_ts[i] * TS_SEVERITY * v_wind
        flood_part += site.p_flood[i] * FLOOD_SEVERITY * v_flood
        survive *= 1 - loss_m
        cover[i] = crop_row.cover_value * STAGE_COVER[stage]
        kc = {"seedling": crop_row.kc_ini, "vegetative": kc_mid_ramp, "reproductive": crop_row.kc_mid, "mature": crop_row.kc_end}[stage]
        water_need += max(0.0, kc * site.et0[i] - EFFECTIVE_RAIN * site.rain[i])

    return {
        "crop": crop_row.crop,
        "start": start,
        "months": months,
        "family": crop_row.family,
        "value": float(crop_row.harvest_value),
        "suitability": suitability,
        "temp_fit": temp,
        "rain_fit": rain,
        "ph_fit": ph_score,
        "loss": 1 - survive,
        "wind_part": wind_part,
        "flood_part": flood_part,
        "cover": cover,
        "water_need": water_need,
        "legume_months": months if crop_row.n_fixing == "Yes" else 0,
        "deep": crop_row.root_depth == "Deep",
        "harvest_month": idx[-1] + 1,
    }


def build_option_table(site, crops, allowed=None):
    options = []
    for crop_row in crops.itertuples(index=False):
        if allowed is not None and crop_row.crop not in allowed:
            continue
        lengths = [int(max(1, round(crop_row.days_to_harvest / 30.4)))]
        if crop_row.group == "Cover crop":  # cover crops can be cut early or left longer
            lengths = sorted({max(2, lengths[0] - 1), lengths[0], lengths[0] + 1})
        for months in lengths:
            if months > 12:
                continue
            for start in range(1, 13):
                options.append(planting_metrics(site, crop_row, start, months))
    return options


# ---------------------------------------------------------------------------
# Plan-level scoring
# ---------------------------------------------------------------------------

def score_plan(site, metrics_list):
    if not metrics_list:
        return {k: 0 for k in ("suitability", "storm", "soil", "water", "food")}, {}

    months_total = sum(m["months"] for m in metrics_list)
    suitability = sum(m["suitability"] * m["months"] for m in metrics_list) / months_total

    value_months = sum(m["value"] * m["months"] for m in metrics_list)
    if value_months > 0:
        loss = sum(m["loss"] * m["value"] * m["months"] for m in metrics_list) / value_months
        wind = sum(m["wind_part"] * m["value"] * m["months"] for m in metrics_list) / value_months
        flood = sum(m["flood_part"] * m["value"] * m["months"] for m in metrics_list) / value_months
    else:
        loss = wind = flood = 0.0

    cover = np.zeros(12)
    for m in metrics_list:
        cover = np.maximum(cover, m["cover"])
    s_factor = site.terrain.get("s_factor", 1.0)
    erosion_rel = float(((1 - cover) * site.rain_share).sum())
    erosion_index = erosion_rel * s_factor
    bare_months = int((cover < 0.05).sum())
    heavy = site.p_flood >= np.quantile(site.p_flood, 0.67)
    bare_in_wet = int(((cover < 0.05) & heavy).sum())

    legume_share = sum(m["legume_months"] for m in metrics_list) / 12
    families = {m["family"] for m in metrics_list}
    deep = any(m["deep"] for m in metrics_list)

    cover_score = 1 - erosion_rel
    soil = (
        0.45 * cover_score
        + 0.25 * min(1.0, legume_share / 0.33)
        + 0.20 * min(1.0, (len(families) - 1) / 3)
        + 0.10 * (1.0 if deep else 0.5)
    )

    water_need = sum(m["water_need"] for m in metrics_list)
    water = float(np.exp(-water_need / 450))

    food_months = sum(m["months"] for m in metrics_list if m["value"] > 0)
    harvests = sum(1 for m in metrics_list if m["value"] > 0)
    food = min(1.0, food_months / 9) * (0.85 + 0.05 * min(harvests, 3))

    storm = max(0.0, 1 - loss / 0.35)

    scores = {
        "suitability": round(100 * suitability),
        "storm": round(100 * storm),
        "soil": round(100 * soil),
        "water": round(100 * water),
        "food": round(100 * food),
    }
    metrics = {
        "expected_loss": loss,
        "wind_loss": wind,
        "flood_loss": flood,
        "erosion_index": erosion_index,
        "bare_months": bare_months,
        "bare_in_wet_months": bare_in_wet,
        "legume_months": int(round(legume_share * 12)),
        "families": sorted(families),
        "irrigation_mm": water_need,
        "food_months": food_months,
        "harvests": harvests,
        "cover": cover,
    }
    return scores, metrics


def overall(scores, weights):
    return sum(scores[k] * w for k, w in weights.items())


# ---------------------------------------------------------------------------
# Enumeration
# ---------------------------------------------------------------------------

def enumerate_index_combos(options, max_plantings=4, fixed_start=None, max_gap=1):
    """Every 12-month cycle of up to `max_plantings` plantings, as option-index tuples.

    Each cyclic calendar is produced once: the first planting is the one with
    the earliest start month (unless `fixed_start` pins the first planting).
    """
    by_start = {}
    for i, opt in enumerate(options):
        by_start.setdefault(opt["start"], []).append(i)
    fam = [o["family"] for o in options]
    crop = [o["crop"] for o in options]
    length = [o["months"] for o in options]

    combos = []
    starts = [fixed_start] if fixed_start else range(1, 13)
    for s0 in starts:
        stack = [((), s0, 0, 0)]
        while stack:
            chosen, month, used, gaps = stack.pop()
            if used == 12:
                if len(chosen) > 1 and fam[chosen[0]] == fam[chosen[-1]] and gaps == 0:
                    continue
                combos.append(chosen)
                continue
            if len(chosen) >= max_plantings:
                continue
            canonical_ok = fixed_start is not None or (s0 + used) <= 12
            if chosen and not canonical_ok:
                continue
            for i in by_start.get(month, ()):
                if used + length[i] > 12:
                    continue
                if chosen and (fam[i] == fam[chosen[-1]] or any(crop[c] == crop[i] for c in chosen)):
                    continue
                stack.append((chosen + (i,), (month - 1 + length[i]) % 12 + 1, used + length[i], gaps))
            if chosen and gaps < max_gap:
                stack.append((chosen, month % 12 + 1, used + 1, gaps + 1))
    return combos


def _option_arrays(options):
    n = len(options)
    fam_codes = {f: k for k, f in enumerate(sorted({o["family"] for o in options}))}
    pad = n  # dummy index for "no planting"
    arr = {
        "suit": np.array([o["suitability"] for o in options] + [0.0]),
        "months": np.array([o["months"] for o in options] + [0]),
        "value": np.array([o["value"] for o in options] + [0.0]),
        "loss": np.array([o["loss"] for o in options] + [0.0]),
        "wind": np.array([o["wind_part"] for o in options] + [0.0]),
        "flood": np.array([o["flood_part"] for o in options] + [0.0]),
        "cover": np.vstack([o["cover"] for o in options] + [np.zeros(12)]),
        "water": np.array([o["water_need"] for o in options] + [0.0]),
        "legume": np.array([o["legume_months"] for o in options] + [0]),
        "deep": np.array([o["deep"] for o in options] + [False]),
        "fam": np.array([fam_codes[o["family"]] for o in options] + [-1]),
    }
    return arr, pad


def score_matrix(site, options, combos, chunk=150_000):
    """Vectorised version of score_plan for many combos. Returns dict of arrays."""
    arr, pad = _option_arrays(options)
    width = max(len(c) for c in combos)
    C = np.full((len(combos), width), pad, dtype=np.int32)
    for r, c in enumerate(combos):
        C[r, : len(c)] = c

    out = {k: np.empty(len(combos)) for k in
           ("suitability", "storm", "soil", "water", "food", "loss", "bare", "legume", "irrigation", "harvests")}
    heavy_mask = site.p_flood >= np.quantile(site.p_flood, 0.67)
    for a in range(0, len(C), chunk):
        c = C[a: a + chunk]
        mo = arr["months"][c]
        val = arr["value"][c]
        mt = mo.sum(1)
        suit = (arr["suit"][c] * mo).sum(1) / mt
        vm = (val * mo).sum(1)
        loss = np.divide((arr["loss"][c] * val * mo).sum(1), vm, out=np.zeros(len(c)), where=vm > 0)
        cover = arr["cover"][c].max(axis=1)
        erosion = ((1 - cover) * site.rain_share).sum(1)
        bare = (cover < 0.05).sum(1)
        legume_share = arr["legume"][c].sum(1) / 12
        fam = np.sort(arr["fam"][c], axis=1)
        distinct = ((np.diff(fam, axis=1) != 0) & (fam[:, 1:] >= 0)).sum(1) + (fam[:, 0] >= 0)
        deep = arr["deep"][c].any(1)
        soil = (0.45 * (1 - erosion) + 0.25 * np.minimum(1, legume_share / 0.33)
                + 0.20 * np.minimum(1, (distinct - 1) / 3) + 0.10 * np.where(deep, 1.0, 0.5))
        irrigation = arr["water"][c].sum(1)
        food_months = (mo * (val > 0)).sum(1)
        harvests = ((val > 0) & (c != pad)).sum(1)
        food = np.minimum(1, food_months / 9) * (0.85 + 0.05 * np.minimum(harvests, 3))
        sl = slice(a, a + len(c))
        out["suitability"][sl] = 100 * suit
        out["storm"][sl] = 100 * np.maximum(0, 1 - loss / 0.35)
        out["soil"][sl] = 100 * soil
        out["water"][sl] = 100 * np.exp(-irrigation / 450)
        out["food"][sl] = 100 * food
        out["loss"][sl] = loss
        out["bare"][sl] = bare
        out["legume"][sl] = legume_share * 12
        out["irrigation"][sl] = irrigation
        out["harvests"][sl] = harvests
    return out


IRRIGATION_LIMITS = {"No irrigation": 120.0, "Limited irrigation": 260.0, "Reliable irrigation": None}
WET_CROPS = {"Rice", "Dasheen"}


def allowed_crops(crops, wet_field=False, include=None, exclude=None):
    names = list(crops.index)
    if not wet_field:
        names = [c for c in names if c not in WET_CROPS]
    if include:
        keep = set(include) | set(crops[crops["group"] == "Cover crop"].index)
        names = [c for c in names if c in keep]
    if exclude:
        names = [c for c in names if c not in set(exclude)]
    return names


def generate_strategies(site, crops, allowed=None, fixed_start=None, irrigation="Limited irrigation",
                        require_food=True, min_difference=4):
    options = build_option_table(site, crops, allowed)
    limit = IRRIGATION_LIMITS.get(irrigation)
    options = [o for o in options if o["suitability"] >= 0.55 and (limit is None or o["water_need"] <= limit)]
    if not options:
        return {}
    combos = enumerate_index_combos(options, fixed_start=fixed_start)
    if not combos:
        return {}
    S = score_matrix(site, options, combos)
    valid = S["harvests"] > 0 if require_food else np.ones(len(combos), bool)
    if limit is not None:
        valid &= S["irrigation"] <= limit * 1.25

    plans, chosen_sets = {}, []
    for key, profile in PROFILES.items():
        total = sum(S[k] * w for k, w in profile["weights"].items())
        total = np.where(valid, total, -1)
        order = np.argsort(-total)[:5000]
        for need in (min_difference, 2, 1):  # relax only if no distinct plan exists
            pick = None
            for idx in order:
                if total[idx] < 0:
                    break
                crop_set = {options[i]["crop"] for i in combos[idx]}
                if all(len(crop_set ^ prev) >= need for prev in chosen_sets):
                    pick = idx
                    break
            if pick is not None:
                break
        if pick is None:
            continue
        combo = [options[i] for i in combos[pick]]
        scores, metrics = score_plan(site, combo)
        plans[key] = make_plan(key, combo, scores, metrics, float(total[pick]))
        chosen_sets.append({m["crop"] for m in combo})
    plans["_meta"] = {"candidates": len(combos), "options": len(options)}
    return plans


def make_plan(key, combo, scores, metrics, total=None):
    profile = PROFILES.get(key, CURRENT_PROFILE)
    plan = Plan(
        key=key,
        plantings=[Planting(m["crop"], m["start"], m["months"]) for m in combo],
        title=profile["title"],
        icon=profile["icon"],
        tagline=profile["tagline"],
        scores=scores,
        metrics={**metrics, "option_rows": combo},
    )
    if total is not None:
        plan.metrics["overall"] = total
    return plan


def evaluate_current(site, crops, plantings):
    combo = []
    for p in plantings:
        if p.crop not in crops.index:
            continue
        combo.append(planting_metrics(site, crops.loc[p.crop], p.start, p.months))
    scores, metrics = score_plan(site, combo)
    plan = make_plan("current", combo, scores, metrics)
    plan.plantings = plantings
    return plan


# ---------------------------------------------------------------------------
# Stress tests
# ---------------------------------------------------------------------------

def wind_severity(site_wind_kt):
    """Share of hurricane-level damage for a given sustained wind at the farm."""
    return float(np.interp(site_wind_kt, [25, 34, 50, 64, 96], [0.0, 0.25, 0.6, 1.0, 1.0]))


def replay_storm(plan, crops, storm_time, site_wind_kt):
    """What was in the field on the storm's day, and how much would be lost."""
    month = storm_time.month
    occupancy = plan.occupancy()
    slot = occupancy[month - 1]
    severity = wind_severity(site_wind_kt)
    if slot is None:
        return {"crop": None, "stage": None, "loss": 0.0, "severity": severity, "bare": True}
    crop, stage = slot
    row = crops.loc[crop]
    v = getattr(row, f"wind_{stage}")
    loss = severity * v
    return {
        "crop": crop,
        "stage": stage,
        "loss": loss if row.harvest_value > 0 else 0.0,
        "severity": severity,
        "bare": False,
        "cover_crop": row.harvest_value == 0,
    }


def monte_carlo(site, plans, crops, n_years=5000, storm_multiplier=1.0, rain_multiplier=1.0, seed=42):
    """Simulate seasons from the farm's own monthly storm and heavy-rain history."""
    rng = np.random.default_rng(seed)
    p_hu = np.clip(site.p_hu * storm_multiplier, 0, 0.95)
    p_ts = np.clip(site.p_ts * storm_multiplier, 0, 0.95)
    p_fl = np.clip(site.p_flood * rain_multiplier, 0, 0.95)

    u = rng.random((n_years, 12))
    wind_sev = np.where(u < p_hu, 1.0, np.where(u < p_hu + p_ts, TS_SEVERITY, 0.0))
    flood = (rng.random((n_years, 12)) < p_fl).astype(float) * FLOOD_SEVERITY

    results = {}
    for key, plan in plans.items():
        survive_weighted = np.zeros(n_years)
        total_value = 0.0
        for p in plan.plantings:
            if p.crop not in crops.index:
                continue
            row = crops.loc[p.crop]
            if row.harvest_value <= 0:
                continue
            survive = np.ones(n_years)
            for k, m in enumerate(p.month_list()):
                stage = stage_for(k, p.months)
                v_w = getattr(row, f"wind_{stage}")
                v_f = min(1.0, row.flood_vuln * (1.3 if stage == "seedling" else 1.0))
                loss_m = np.clip(wind_sev[:, m - 1] * v_w + flood[:, m - 1] * v_f, 0, 0.95)
                survive *= 1 - loss_m
            weight = row.harvest_value * p.months
            survive_weighted += survive * weight
            total_value += weight
        loss = 1 - survive_weighted / total_value if total_value else np.zeros(n_years)
        results[key] = {
            "expected_loss": float(loss.mean()),
            "p_loss_over_25": float((loss > 0.25).mean()),
            "p_loss_over_50": float((loss > 0.50).mean()),
            "bad_year_loss": float(np.quantile(loss, 0.9)),
            "worst_loss": float(np.quantile(loss, 0.99)),
            "distribution": loss,
        }
    return results


# ---------------------------------------------------------------------------
# Plain-language explanations
# ---------------------------------------------------------------------------

def month_names(nums):
    return ", ".join(MONTHS[m - 1] for m in nums)


def explain(plan, site, crops, current=None):
    """Why suggested / evidence / benefits / gaps / local review for one plan."""
    m = plan.metrics
    peak = [int(i) + 1 for i in np.argsort(site.p_hu + site.p_ts)[::-1][:3] if (site.p_hu + site.p_ts)[i] > 0]
    wet = [int(i) + 1 for i in np.argsort(site.p_flood)[::-1][:3] if site.p_flood[i] > 0]
    occ = plan.occupancy()

    in_peak = []
    for mo in peak:
        slot = occ[mo - 1]
        in_peak.append(f"{MONTHS[mo - 1]}: {slot[0]} ({slot[1]})" if slot else f"{MONTHS[mo - 1]}: bare")

    why = {
        "storm": "Your farm's storm history concentrates in "
        + (month_names(peak) if peak else "no particular month")
        + ". This calendar times harvests before those months and fills them with low, wind-tolerant or underground crops.",
        "soil": f"It keeps living cover on the field {12 - m['bare_months']} of 12 months, adds {m['legume_months']} legume months for nitrogen, "
        f"and rotates {len(m['families'])} crop families.",
        "water": f"It lines crops up with the rainy months, needing about {m['irrigation_mm']:.0f} mm of irrigation a year (screening estimate).",
        "current": "This is the calendar you entered, scored with exactly the same rules as the alternatives.",
    }.get(plan.key, "")

    evidence = [
        f"NOAA HURDAT2 (1971-2025): storm-force wind reached this farm in {int(round(site.p_ts.sum() * 55 + site.p_hu.sum() * 55))} month-events; peak months {month_names(peak) or 'none'}.",
        f"NASA POWER: {site.annual_rain:.0f} mm rain a year; ≥ 50 mm rain days most likely in {month_names(wet) or 'no month'}.",
        f"What sits in the field in peak storm months → {'; '.join(in_peak) if in_peak else 'n/a'}.",
        f"FAO-56 crop coefficients × Hargreaves ET0 → irrigation need ≈ {m['irrigation_mm']:.0f} mm/yr.",
    ]

    benefits = []
    if current is not None and plan.key != "current":
        dl = current.metrics["expected_loss"] - m["expected_loss"]
        if dl > 0.005:
            benefits.append(f"Cuts expected storm/flood harvest loss from {current.metrics['expected_loss']:.0%} to {m['expected_loss']:.0%}.")
        db = current.metrics["bare_months"] - m["bare_months"]
        if db > 0:
            benefits.append(f"{db} fewer bare months, so less soil washes away in heavy rain.")
        dleg = m["legume_months"] - current.metrics["legume_months"]
        if dleg > 0:
            benefits.append(f"{dleg} more legume months to fix nitrogen and cut fertiliser needs.")
        dw = current.metrics["irrigation_mm"] - m["irrigation_mm"]
        if dw > 20:
            benefits.append(f"About {dw:.0f} mm less irrigation per year.")
    if not benefits:
        benefits.append("Balanced on the five scores; see the score bars for trade-offs.")

    repeats = pest_cycle(plan)
    if repeats:
        a, b, fam, pests = repeats[0]
        benefits.append(f"Watch out: {a} is followed by {b} (both {fam}), which lets {pests} build up.")
    elif len(plan.plantings) > 1:
        benefits.append(f"No crop family follows itself, which breaks pest and disease cycles ({len(m['families'])} families).")
    feed = [f"{p.crop}: {FORAGE[p.crop]}" for p in plan.plantings if p.crop in FORAGE]
    if feed:
        benefits.append("Feed for livestock: " + "; ".join(feed[:3]) + ".")

    gaps = [
        "Satellite and reanalysis cells (POWER ≈ 50 km, SoilGrids 250 m) are coarser than a farm: local valleys, wind shelter and drainage are not captured.",
        "Crop wind and flood vulnerability values are FarmFit heuristics from crop architecture, not field trials.",
        "Labour and input costs are not modelled. Market timing uses wholesale prices where they exist (NAMDEVCO, Trinidad) and needs a farmer's own check elsewhere.",
    ]
    if site.soil.get("origin") is None:
        gaps.insert(0, "Soil data unavailable here, so pH and drainage are assumed. Enter a soil test to improve this.")

    review = []
    names = {p.crop for p in plan.plantings}
    if names & {"Rice", "Dasheen"}:
        review.append("Wet-condition crops (rice, dasheen) need managed water, a safe water source and locally adapted varieties. Check with extension officers or CARDI.")
    if names & {"Mucuna", "Sunn Hemp"}:
        review.append("Cover crops need termination timing and seed sources confirmed locally; mucuna can climb over neighbouring crops.")
    if "Cassava" in names or "Plantain" in names:
        review.append("Long-season crops tie up land through the storm season; confirm wind-break options and variety choice.")
    review.append("Planting dates should be checked against this season's rainfall onset and the latest hurricane-season outlook.")

    return {"why": why, "evidence": evidence, "benefits": benefits, "gaps": gaps, "review": review}


# ---------------------------------------------------------------------------
# Farmer priorities beyond yield: forage, pest cycles, planting windows
# ---------------------------------------------------------------------------

# Residue or crop that livestock can eat (goats, cattle are common on Caribbean
# mixed farms). Qualitative, from FAO Feedipedia crop pages; for local review.
FORAGE = {
    "Corn": "stover and green fodder", "Sorghum": "fodder and silage", "Rice": "straw",
    "Cowpea": "hay; leaves are high-protein feed", "Bodi": "vines as feed", "Common Bean": "haulm",
    "Pigeon Peas": "browse for goats; protein bank", "Peanut": "haulm hay", "Sweet Potato": "vines as feed",
    "Cassava": "leaves (must be wilted or dried first)", "Mucuna": "forage only after processing; beans are toxic raw",
    "Sunn Hemp": "young growth only; mature plants are not feed", "Pumpkin": "culls and vines",
}

# Pests and diseases that build up when the same family follows itself.
FAMILY_PESTS = {
    "Solanaceae": "bacterial wilt, nematodes and early blight",
    "Cucurbitaceae": "pickleworm, downy mildew and nematodes",
    "Brassicaceae": "diamondback moth and black rot",
    "Poaceae": "fall armyworm",
    "Fabaceae": "bean fly and root rots",
    "Convolvulaceae": "sweet potato weevil",
    "Amaranthaceae": "leaf caterpillars and damping-off",
}


def pest_cycle(plan):
    """Back-to-back plantings of the same family (in calendar order, wrapping)."""
    ps = sorted(plan.plantings, key=lambda p: p.start)
    if len(ps) < 2:
        return []
    crops = load_crops()
    fam = [crops.loc[p.crop, "family"] if p.crop in crops.index else None for p in ps]
    repeats = []
    for i in range(len(ps)):
        j = (i + 1) % len(ps)
        if i == j or fam[i] is None or fam[i] != fam[j]:
            continue
        repeats.append((ps[i].crop, ps[j].crop, fam[i], FAMILY_PESTS.get(fam[i], "soil-borne pests")))
    return repeats


def planting_window(site, crops, crop, irrigation="Limited irrigation", n_years=4000, seed=7, loss_ok=0.2):
    """Chance of a good harvest for `crop` planted in each month (1-12).

    good = P(simulated storm + flood loss < loss_ok, from this farm's own monthly odds)
           x climate fit (ECOCROP temperature / rain / pH, 0-1)
           x water factor (1 if the irrigation need fits the farmer's water, else the share it covers)
    """
    row = crops.loc[crop]
    months = int(max(1, round(row.days_to_harvest / 30.4)))
    rng = np.random.default_rng(seed)
    u = rng.random((n_years, 12))
    wind = np.where(u < site.p_hu, 1.0, np.where(u < site.p_hu + site.p_ts, TS_SEVERITY, 0.0))
    flood = (rng.random((n_years, 12)) < site.p_flood).astype(float) * FLOOD_SEVERITY
    limit = IRRIGATION_LIMITS.get(irrigation)
    out = []
    for start in range(1, 13):
        m = planting_metrics(site, row, start, months)
        survive = np.ones(n_years)
        for k, mo in enumerate(Planting(crop, start, months).month_list()):
            stage = stage_for(k, months)
            v_w = getattr(row, f"wind_{stage}")
            v_f = min(1.0, row.flood_vuln * (1.3 if stage == "seedling" else 1.0))
            survive *= 1 - np.clip(wind[:, mo - 1] * v_w + flood[:, mo - 1] * v_f, 0, 0.95)
        p_safe = float((1 - survive < loss_ok).mean())
        water = 1.0 if limit is None or m["water_need"] <= limit else max(0.0, limit / m["water_need"])
        p_good = p_safe * m["suitability"] * water
        out.append({"start": start, "harvest": m["harvest_month"], "p_good": p_good, "p_safe": p_safe,
                    "fit": m["suitability"], "water": water, "water_need": m["water_need"], "months": months})
    return out
