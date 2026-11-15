# FarmFit · Hurricane to Harvest 🌀🌱

**NASA Space Apps Challenge 2026: _Field Shift: Adapting Farms with NASA Data_**

FarmFit helps small-scale farmers in hurricane-prone regions choose crop rotations that **protect the harvest from storms, rebuild soil and save water**. After a storm, it gives them a **safe, staged path back to production**.

Pick a farm on the map. FarmFit pulls in:

- 30 years of NASA climate data
- 55 years of NOAA hurricane tracks
- the soil map and the terrain

It then compares the farmer's **current rotation with three alternatives**, month by month, with the evidence, benefits, data gaps and local checks behind each one.

> Live app: _add your Streamlit Cloud URL here_ · Demo video: _add link_ · Slides: `docs/FarmFit_Hurricane_to_Harvest.pptx`

---

## Why

On 28 October 2025, Hurricane Melissa made landfall in south-western Jamaica as a Category 5 storm. St Elizabeth, the island's "breadbasket", was among the hardest-hit parishes. The Ministry of Agriculture's preliminary assessment put the loss at about 32,400 ha of vegetables, affecting roughly 47,500 farmers. In the same week, farmers in Trinidad's Caroni plains were watching a different hazard: **heavy rain and flooding**, not wind.

Many farm calendars were handed down from a climate that has since shifted. FarmFit asks a simple question for any farm:

**Which crops should be in the ground in which month, so that the riskiest weeks find the field protected?**

## Two demo farms

| Farm | Main hazard | Story |
|---|---|---|
| 🌀 **St Elizabeth, Jamaica** (18.05° N, 77.72° W) | Wind | Melissa 2025 tops this farm's storm list (≈ 95 kt estimated at the farm). Storm-force wind arrives about 1 year in 4. |
| 🌧️ **Caroni plains, Trinidad** (10.60° N, 61.38° W) | Rain and waterlogging | No hurricane-force wind at this farm since 1971. The threat is ≥ 50 mm rain days on slow-draining soils. |

## What the app does

| Step | Feature | Data |
|---|---|---|
| ① **Farm profile** | Rain, temperature, soil, slope and storm return periods appear automatically from a map click. Historic storm tracks are coloured by the wind they brought to the farm. NASA GIBS satellite layers (SMAP, GPM IMERG, MODIS) can be shown for any date. A month-by-month hazard chart and a **data passport** list every dataset, its resolution and its status. | NASA POWER, NOAA HURDAT2, SoilGrids, NASA SRTM, NASA GIBS |
| ② **Field shift** | "Your grandparents' calendar vs today's": the first 15 years of the record against the last 15 (annual rain, heat days, ≥ 50 mm days, dry spells, wettest day, monthly rain pattern). Each change carries a trend-significance label. Storm events at the farm are counted by decade. | NASA POWER daily, HURDAT2 |
| ③ **Compare rotations** | The farmer enters their current rotation, priority, irrigation access, whether they have a wet field, and crops they can't grow. FarmFit searches **every 12-month rotation of up to 4 crops** (≈ 200,000 calendars) and shows **Current vs Storm-smart vs Soil builder vs Water saver** as month-by-month calendars over a storm-and-flood risk row. Each plan gets five scores, plus why it was suggested, evidence, benefits, information gaps and points to check locally. The plan downloads as text and can be shared on WhatsApp. | FAO ECOCROP, FAO-56, all of the above |
| ④ **Hurricane stress test** | **Replay a real storm** (e.g. Melissa 2025) on every calendar: what was in the field that day, at which growth stage, and the estimated loss. A **Monte Carlo** of 5,000 seasons drawn from the farm's own storm and heavy-rain history gives average loss, bad-year (1-in-10) loss and the chance of losing more than half the harvest. Sliders test a stormier or wetter future. | HURDAT2, NASA POWER |
| ⑤ **Storm water bank** | Taken from our **IFRS flood-resilience project**: size a rain tank that catches wet-season runoff and feeds drip irrigation in the dry season. A slow-release rule frees tank space before forecast heavy rain. | NASA POWER, FAO-56 |
| 🛰️ **After the storm** | Upload a field photo. **Gemini vision** describes only what is visible (standing water, bare soil, erosion, debris, lodging) as structured JSON with a confidence value. The farmer confirms what a photo can't show: water source, whether floodwater touched the edible part, and how long water stood. NASA POWER rain and root-zone wetness for the storm window add context, alongside GIBS IMERG and SMAP layers for the storm date. Rules then produce four gated stages (safety → drain → cover → production) and a **recovery rotation** that restarts ahead of the next peak season. | Gemini, NASA POWER, GIBS, FDA guidance |

## Datasets

| Dataset | Provider | Used for | Resolution | Access |
|---|---|---|---|---|
| **POWER daily** (T2M, T2M_MAX/MIN, PRECTOTCORR, RH2M, WS2M, WS10M_MAX, GWETTOP, GWETROOT, ALLSKY_SFC_SW_DWN) | NASA LaRC (MERRA-2 and CERES based) | Climate normals, heavy-rain probability, soil wetness, ET₀, then-vs-now shift, storm-window rain | 0.5° × 0.625° | Live API, cached in `data/cache` |
| **HURDAT2** Atlantic best track, 1851-2025 (release 23 Sep 2026) | NOAA National Hurricane Center | Storm exposure at the farm, storm replay, Monte Carlo | 6-hourly fixes | Bundled as `data/hurdat2_caribbean.csv` (1950+, Caribbean / Gulf box), built by `scripts/build_hurdat2.py` |
| **SoilGrids 2.0** (pH, SOC, clay, sand, silt, N, bulk density) | ISRIC | Soil pH fit, texture, drainage class | 250 m | Live API, farmer can override |
| **SRTM GL1** | NASA / USGS via OpenTopoData | Elevation and slope (Horn's method), RUSLE slope factor | 30 m | Live API |
| **SMAP L4 surface soil moisture**, **GPM IMERG precipitation rate**, **MODIS NDVI and true colour** | NASA GIBS (EOSDIS) | Map layers for any date, including the storm date | 9 km / 0.1° / 250 m | WMTS tiles |
| **ECOCROP** crop ranges, **FAO-56** crop coefficients | FAO | Crop climate fit and crop water demand | Crop level | `data/crops_fieldshift.csv` |
| Crop calendars, stage vulnerability, flood tolerance | FarmFit heuristics from crop architecture (documented per crop) | Wind and flood loss by growth stage | Crop level | `data/crops_fieldshift.csv`, to be validated with CARDI and extension services |

## Methodology

**1. Storm exposure at the farm (NOAA HURDAT2).**
- Every track is interpolated to 15-minute steps.
- Sustained wind at the farm comes from a modified Rankine vortex. Inside the radius of maximum wind (Rₘ) the wind is V = Vₘₐₓ·r/Rₘ; outside it is V = Vₘₐₓ·(Rₘ/r)⁰·⁶.
- Rₘ is taken from HURDAT2 where reported, otherwise 40 km. Winds are multiplied by 0.85 for land exposure.
- Each storm keeps its peak wind at the farm. For 1971-2025 we count, per month, the share of years with storm-force (≥ 34 kt) and hurricane-force (≥ 64 kt) wind.
- Check: Melissa 2025 comes out as the strongest wind at St Elizabeth and Beryl 2024 at Carriacou, while Trinidad shows no hurricane-force wind since 1971, which matches the historical record.

**2. Climate and water (NASA POWER).**
- Monthly normals come from 30 years of daily data.
- p(heavy rain) is the share of years with a ≥ 50 mm day in that month.
- Reference evapotranspiration uses FAO-56 Hargreaves: ET₀ = 0.0023·Rₐ·(T + 17.8)·√(Tₘₐₓ − Tₘᵢₙ).
- Crop water need is ETc = Kc·ET₀, with Kc by growth stage. Irrigation need is Σ max(0, ETc − 0.8·P).
- Waterlogging probability scales p(heavy rain) by root-zone wetness (GWETROOT ≥ 0.7) and soil drainage.

**3. Field shift.** We compare the first and second halves of the record. Each annual indicator also gets an OLS trend per decade with a t-statistic. A change is labelled "clear" only when |t| ≥ 2.

**4. Rotation scoring.** All five scores are 0-100 and the weights are listed in `fieldshift/planner.py`.

| Score | How it is calculated |
|---|---|
| Climate fit | ECOCROP temperature (each month), annual rainfall and pH ranges |
| Storm & flood safety | Expected harvest loss = 1 − Π(1 − Pᵥᵤ·v + Pₜₛ·0.45·v + P_flood·0.5·f) over the crop's months, where v and f are wind and flood vulnerability at that growth stage |
| Soil health | 45% living cover weighted by each month's share of rain (RUSLE C×R logic), 25% legume months, 20% crop-family diversity, 10% deep roots |
| Water saving | exp(−irrigation / 450 mm) |
| Food and income months | Share of the year producing a harvest, and number of harvests |

Rotations are enumerated exhaustively: cyclic, no same family back-to-back, at most one fallow month. Each strategy profile picks its top plan, and the three plans must differ by at least two crops. Under "no irrigation", crops needing more than 120 mm of irrigation are excluded. Rice and dasheen are only offered if the farmer says they have a wet, managed field.

**5. Stress test.**
- *Replay*: the storm's date at the farm gives the crop and growth stage in the field that day. Loss = wind severity(kt) × stage vulnerability.
- *Monte Carlo*: 5,000 years of month-by-month draws from the farm's own storm and heavy-rain probabilities, with a fixed seed so results are reproducible.

**6. After the storm.**
- AI is only used to *describe* the photo, and it reports a confidence.
- Decisions are explicit rules. Under the FDA flood-crop guidance, crops whose edible portion touched floodwater are treated as adulterated. Leafy greens are withheld when contamination is possible. Each stage has a gate to pass before moving on.
- The recovery rotation is regenerated from two months after the storm with the Storm-smart profile.

## Limits and where local expertise is essential

- **Scale.** Satellite and reanalysis cells (POWER ≈ 55 km, SMAP 9 km, SoilGrids 250 m) are much larger than a farm. Valleys, windbreaks and drainage ditches are invisible to them. Satellite data gives the regional picture; ground data (a soil test, a rain gauge, CoCoRaHS) sharpens it. Farmers can override soil values.
- **Vulnerability values** for wind and flood by growth stage are transparent heuristics, not field trials. They are listed per crop and need validation with CARDI, the USDA Caribbean Climate Hub and national extension services.
- **The wind model** ignores storm asymmetry, terrain and gusts. It screens exposure; it does not forecast.
- **Markets, labour and prices** are not modelled.
- **Food safety** after flooding must be confirmed with the Ministry of Agriculture.

## Keeping the data fresh

The data reaches the site in three ways:

| How | Datasets | Key needed |
|---|---|---|
| **Live, on every map click** (deployed app) | NASA POWER, ISRIC SoilGrids, NASA SRTM, NASA GIBS map layers | none |
| **Scheduled refresh**: `.github/workflows/refresh-data.yml` runs `scripts/refresh_data.py` daily June-November and weekly otherwise, commits `data/cache/`, and Streamlit Cloud redeploys | NASA POWER (30-year + last 45 days), GPM IMERG Final at the farm (GES DISC data rods), SMAP soil moisture + MODIS NDVI (LP DAAC AppEEARS), NOAA IBTrACS current-season tracks | free NASA Earthdata Login for IMERG / SMAP / NDVI |
| **Annual** | NOAA HURDAT2 (new release each spring): run `scripts/build_hurdat2.py` | none |

Farms refreshed on the schedule are listed in `data/farms.json`; add pilot farms there. The app's data passport shows when each dataset was last refreshed.

**Setup**
1. Create a free account at https://urs.earthdata.nasa.gov.
2. In the GitHub repo, go to **Settings → Secrets and variables → Actions** and add `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD`.
3. Under **Settings → Actions → General → Workflow permissions**, choose **Read and write**.
4. **Actions → Refresh NASA data → Run workflow** runs the refresh once by hand.

## Run it

```bash
git clone https://github.com/keydahknow/FarmFit.git
cd FarmFit
python -m venv .venv && source .venv/bin/activate      # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/cache_demo_sites.py     # optional: pre-fetch real NASA/SoilGrids/SRTM data for the demo farms
streamlit run app.py
```

Photo analysis needs a Gemini key in `.streamlit/secrets.toml` (never commit it):

```toml
GEMINI_API_KEY = "your-key"
# GEMINI_MODEL = "gemini-2.5-flash"   # optional override
```

Tests (offline, using a **synthetic** fixture that is clearly labelled and never shown as NASA data):

```bash
pip install pytest && pytest -q
```

### Deploy (Streamlit Community Cloud)

1. Push to GitHub.
2. Go to share.streamlit.io → **New app**, pick the repo, branch `main`, file `app.py`.
3. Under **Advanced settings → Secrets**, paste `GEMINI_API_KEY = "…"`.
4. Deploy. Run `scripts/cache_demo_sites.py` locally first and commit `data/cache/*.json` so the demo farms load instantly.

## Project layout

| Path | Purpose |
|---|---|
| `app.py` | Streamlit app: original FarmFit views plus the two new views |
| `fieldshift/storms.py` | HURDAT2 loading, interpolation, wind-at-farm, monthly exposure |
| `fieldshift/power.py` | NASA POWER fetch and cache, climate normals, ET₀, field-shift statistics |
| `fieldshift/soil_terrain.py` | SoilGrids, SRTM slope, USDA texture, RUSLE slope factor |
| `fieldshift/planner.py` | Crop table, rotation enumeration, scoring, strategy generation, explanations, stress tests |
| `fieldshift/recovery.py` | Gemini photo assessment, field-state rules, staged recovery |
| `fieldshift/ui.py` | Streamlit views, calendars, maps, charts |
| `data/crops_fieldshift.csv` | 25 Caribbean crops and cover crops with ranges, Kc, stage vulnerability and sources |
| `data/hurdat2_caribbean.csv` | NOAA HURDAT2 subset (1950-2025) |
| `fieldshift/earthdata.py` | NASA Earthdata access: IMERG data rods, AppEEARS SMAP / NDVI |
| `scripts/` | Data build, cache and scheduled refresh scripts |
| `.github/workflows/refresh-data.yml` | Scheduled data refresh |
| `tests/` | Engine tests and synthetic fixture generator |
| `crops.csv`, `crop_water.csv`, `intercropping.csv`, `farmfit.db` | Original FarmFit data |

## Team workflow

We use branches and pull requests on `main`. See [GIT_SHEET.md](GIT_SHEET.md).

## References

**Data**
- NASA POWER Project, NASA Langley Research Center. https://power.larc.nasa.gov. *"These data were obtained from the NASA Langley Research Center POWER Project funded through the NASA Earth Science Directorate Applied Science Program."*
- Landsea, C. W. & Franklin, J. L. (2013). Atlantic hurricane database uncertainty and presentation of a new database format (HURDAT2). *Monthly Weather Review* 141, 3576-3592. Data: https://www.nhc.noaa.gov/data/#hurdat
- Poggio, L. et al. (2021). SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty. *SOIL* 7, 217-240. https://soilgrids.org
- NASA SRTM GL1 (Farr et al., 2007, *Rev. Geophys.* 45), served by OpenTopoData. https://www.opentopodata.org
- NASA Global Imagery Browse Services (GIBS). https://nasa-gibs.github.io/gibs-api-docs/ (SMAP L4, GPM IMERG, MODIS layers)
- FAO ECOCROP. https://gaez.fao.org/pages/ecocrop

**Methods**
- Allen, R. G. et al. (1998). *Crop evapotranspiration*, FAO Irrigation and Drainage Paper 56 (Kc values, Table 12; Hargreaves eq. 52). https://www.fao.org/3/x0490e/x0490e00.htm
- Hargreaves, G. H. & Samani, Z. A. (1985). Reference crop evapotranspiration from temperature. *Applied Engineering in Agriculture* 1(2), 96-99.
- Holland, G. J. (1980). An analytic model of the wind and pressure profiles in hurricanes. *Monthly Weather Review* 108, 1212-1218 (vortex wind-profile family).
- McCool, D. K. et al. (1987). Revised slope steepness factor for the Universal Soil Loss Equation. *Trans. ASAE* 30(5), 1387-1396.

**Agronomy and safety**
- USDA Caribbean Climate Hub: *Adaptation Guide: Climate Change on Farms and Forested Lands in the Caribbean* and crop-specific practice guides (e.g. plantains and bananas). https://caribbeanclimatehub.org
- U.S. FDA (2011). *Guidance for Industry: Evaluating the Safety of Flood-affected Food Crops for Human Consumption*. https://www.fda.gov/regulatory-information/search-fda-guidance-documents/guidance-industry-evaluating-safety-flood-affected-food-crops-human-consumption
- Philippine Rice Research Institute (PhilRice): rice varieties for submergence, stagnant flooding and deep water. https://www.philrice.gov.ph
- FAO Conservation Agriculture: soil cover, crop diversification, minimum disturbance. https://www.fao.org/conservation-agriculture/en/
- Caribbean Agricultural Research and Development Institute (CARDI). https://www.cardi.org
- Ministry of Agriculture, Fisheries and Mining, Jamaica (14 Nov 2025). *Preliminary Assessments Reveal $29.5B in Agricultural Damage from Hurricane Melissa*. https://moa.gov.jm/node/4779

## AI use

Gemini vision describes field photos (structured JSON, with a confidence value). Code and documentation were developed with AI assistance (Claude) and reviewed by the team. No AI-generated imagery or data is presented as NASA data.

## License

MIT (add a LICENSE file).
