"""After the storm: restoring damaged land, chosen by the soil's condition.

No single crop fixes every field. Rice, for example, tolerates standing water
and suits heavy clay that can be bunded and kept flooded (the Caroni plains
were rice country), but it is the wrong choice on free-draining or sloping
land, without a water supply, or where salt water came in. Each condition
below has first steps, crops that suit it and the conditions under which they
suit it, and what to avoid. Sources are named on every entry.
"""

CONDITIONS = {
    "waterlogged": {
        "label": "Waterlogged or still flooded",
        "sign": "Water stands for more than a day after rain; soil smells sour; roots are brown.",
        "first": ["Open drains and furrows at the low end; do not walk or drive on wet soil (it compacts).",
                  "Wait until the soil crumbles in your hand before tilling.",
                  "Do not eat produce that flood water touched (U.S. FDA)."],
        "crops": [
            ("Rice", "rice", "Tolerates standing water. Suits heavy clay you can bund and keep flooded; flood-tolerant "
             "'Sub1' varieties survive about two weeks under water (IRRI).",
             lambda f: f["clay"] >= 35 and f["water_ok"] and f["flat"],
             "Needs clay soil, a reliable water supply and flat land you can bund. Not on sandy, sloping or dry farms."),
            ("Dasheen", "dasheen", "Grows in wet, heavy soils where most vegetables rot.",
             lambda f: f["clay"] >= 25, "Needs soil that stays moist; poor on sandy land."),
            ("Sesbania (green manure)", None, "A fast legume that tolerates waterlogging and adds nitrogen when cut back "
             "into the soil (FAO green-manure guidance).", lambda f: True, ""),
        ],
        "avoid": "Tomato, sweet pepper, watermelon, cucumber and beans until the soil drains: their roots die in waterlogged soil.",
        "source": "IRRI (Sub1 rice), FAO green manure and soil drainage guidance, U.S. FDA flood-affected crops guidance",
    },
    "eroded": {
        "label": "Topsoil washed away",
        "sign": "Gullies, exposed roots or stones, pale subsoil showing, soil piled at the bottom of the field.",
        "first": ["Fill small gullies; lay brush or stone across them to slow water.",
                  "Plant across the slope (on the contour), never up and down it.",
                  "Cover bare soil within weeks: bare soil loses most in the next heavy rain."],
        "crops": [
            ("Vetiver grass hedges", None, "Deep, dense roots hold soil on slopes; widely used for erosion control in "
             "the Caribbean (World Bank / FAO vetiver system).", lambda f: True, ""),
            ("Pigeon peas", "pigeon peas", "Contour hedgerows with deep roots; fix nitrogen; give food and goat feed.",
             lambda f: True, ""),
            ("Mucuna", "mucuna", "Fast ground-covering legume; smothers weeds and adds organic matter.",
             lambda f: not f["very_dry"], "Needs some rain or water to establish."),
            ("Sweet potato", "sweet potato", "Vines cover the ground quickly and produce food.",
             lambda f: f["drainage_ok"], "Rots in waterlogged soil."),
        ],
        "avoid": "Clean-tilled row crops (corn, cassava) on slopes until the soil is held by hedges or cover.",
        "source": "USDA NRCS conservation practices, FAO conservation agriculture, World Bank vetiver system",
    },
    "salt": {
        "label": "Salt damage from sea water or storm surge",
        "sign": "White crust when dry, leaves burnt at the edges, near the coast after a surge.",
        "first": ["Let heavy fresh rain (or clean irrigation) wash salt down, but only where water can drain away.",
                  "Ask your extension office to test salinity (EC) before planting sensitive crops.",
                  "Add organic matter; it helps the soil recover structure."],
        "crops": [
            ("Sorghum", "sorghum", "Among the more salt-tolerant field crops (FAO Irrigation & Drainage Paper 29).",
             lambda f: True, ""),
            ("Cowpea", "cowpea", "Moderately salt-tolerant legume; adds nitrogen while the soil recovers.",
             lambda f: f["drainage_ok"], "Dislikes waterlogging."),
        ],
        "avoid": "Beans, peppers, sweet potato, corn and onions: they are salt-sensitive (FAO 29). Rice is also "
                 "moderately sensitive, so salt-damaged land is not rice land until it is washed out.",
        "source": "FAO Irrigation & Drainage Paper 29 (water quality for agriculture)",
    },
    "compacted": {
        "label": "Hard, compacted or crusted",
        "sign": "A spade is hard to push in; water runs off instead of soaking in; roots grow sideways.",
        "first": ["Loosen only when the soil is moist, not wet.",
                  "Keep heavy machines off wet fields.",
                  "Use deep-rooted crops as 'biological ploughs'."],
        "crops": [
            ("Pigeon peas", "pigeon peas", "Deep taproots open channels in hard soil.", lambda f: True, ""),
            ("Sorghum", "sorghum", "Fibrous deep roots; tolerates heat and dry spells.", lambda f: True, ""),
            ("Sunn hemp", "sunn hemp", "Fast, deep-rooted legume cover; adds nitrogen and organic matter.",
             lambda f: f["drainage_ok"], "Poor in waterlogged soil."),
        ],
        "avoid": "Root crops that need loose soil (cassava, sweet potato) until the soil is opened up.",
        "source": "USDA NRCS soil health, FAO conservation agriculture",
    },
    "depleted": {
        "label": "Tired, low-fertility soil",
        "sign": "Yellow, weak plants even with water; yields falling year after year.",
        "first": ["Get a soil test (pH and nutrients) from your extension office.",
                  "Return crop residue and compost to the field instead of burning it.",
                  "Grow a legume cover crop before the next cash crop."],
        "crops": [
            ("Mucuna", "mucuna", "Large amounts of organic matter and nitrogen; a classic soil-builder.", lambda f: not f["very_dry"], ""),
            ("Sunn hemp", "sunn hemp", "Quick nitrogen and biomass in about two months.", lambda f: f["drainage_ok"], ""),
            ("Cowpea", "cowpea", "Fixes nitrogen and gives a food or feed harvest.", lambda f: f["drainage_ok"], ""),
            ("Pigeon peas", "pigeon peas", "Perennial nitrogen source and food.", lambda f: True, ""),
        ],
        "avoid": "Back-to-back heavy feeders (corn, cabbage, tomato) without a legume in between.",
        "source": "FAO cover crops and green manure guidance, CARDI",
    },
}


def field_facts(soil, terrain, irrigation, wet_field, rain_dry_season_mm=None):
    clay = float((soil or {}).get("clay_pct") or 0)
    drainage = (soil or {}).get("drainage") or "Moderate"
    slope = float((terrain or {}).get("slope_pct") or 0)
    return {
        "clay": clay,
        "drainage_ok": drainage not in ("Very slow",),
        "flat": slope < 3,
        "water_ok": irrigation != "No irrigation" or wet_field,
        "very_dry": rain_dry_season_mm is not None and rain_dry_season_mm < 40 and irrigation == "No irrigation",
    }


def recommend(condition, facts):
    """(crop, crop_table_key, why, suits_here, why_not) for a condition at this farm."""
    c = CONDITIONS[condition]
    out = []
    for name, key, why, test, caveat in c["crops"]:
        ok = bool(test(facts))
        out.append({"name": name, "key": key, "why": why, "suits": ok, "caveat": caveat})
    return sorted(out, key=lambda r: not r["suits"])
