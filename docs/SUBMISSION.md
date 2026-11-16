# NASA Space Apps 2026: submission text

**Project name:** FarmFit · Hurricane to Harvest
**Challenge:** Field Shift: Adapting Farms with NASA Data

## High-level summary

Hurricane to Harvest is a Caribbean farm-resilience platform. It helps farmers and home gardeners decide what to plant and when, prepare for storms and drought, recover faster after a hurricane, and warn each other about pests and diseases, using NASA Earth data worked out for their exact field.

A farmer first sets up their farm in about a minute: location, size, crops and water. Soil details and equipment are optional, because many farmers have no soil test or sensors. The home page then answers the question every farmer asks, **plant now, or wait?**, for each of their crops. It shows four plain risk gauges (storm, drought, flooding, heat) and the next 16 days of weather. Separate pages cover weather, crops and markets, a planner with four time horizons, the full storm cycle (prepare, respond, restore the soil, build resilience), a community pest and disease map with officer verification, and news with an AI assistant that knows the farm. Home gardeners get a simpler set of pages for containers and small plots.

We demonstrate it on two contrasting farms: St Elizabeth, Jamaica, where Category 5 Hurricane Melissa struck on 28 October 2025, and the Caroni plains, Trinidad, where flooding and dry-season drought matter more than wind. A strong El Niño is under way, and at the Caroni farm El Niño years have brought only 64% of normal December-February rain.

## Project details

**What it does**

1. **Set up first.** Farm or home garden; location by search, map pin or coordinates; size; crops; water; optional soil type, pH and equipment. A tree grows from seed to fruit as each step is finished. The profile is saved as a bookmarkable link or a file and can be edited at any time.
2. **Home: plant now, or wait?** For each crop, the chance of a good harvest if planted this month compared with its best month, with a verdict and a 12-month bar strip. Chance = simulated seasons from the farm's own NOAA storm and NASA heavy-rain records × FAO climate fit × whether the farmer's water covers the crop's needs, capped at "95%+". Also: four risk gauges with plain reasons, the 16-day forecast, El Niño season ahead, nearby pest reports and a printable summary.
3. **Weather.** Forecast rain, rain chance, highs and lows and humidity; this year's rain against the farm's 30-year range; heat, humidity and heavy-rain days by month; NASA SMAP surface and root-zone moisture, MODIS plant water stress and GPM IMERG rain; watering advice and a storm water bank.
4. **Crops & market.** A crop × planting-month heatmap; a side-by-side comparison of chance, storm safety, climate fit, irrigation need, days to harvest, nitrogen and price at harvest, with every value labelled *measured data*, *model estimate* or *your numbers*; a profit calculator that uses only the farmer's own yields and costs; NAMDEVCO wholesale price seasons.
5. **Planner.** Next 3 months, 1 year (the farmer's rotation compared with Storm-smart, Soil builder and Water saver, chosen from about 240,000 calendars, each explained with why, evidence, benefits, pest-cycle breaks, livestock feed, market timing, gaps and local checks), a 5-year roadmap with land, water and protection milestones, and a warming what-if beyond 5 years (+1 and +2 °C against FAO crop ranges, clearly labelled as a scenario).
6. **Storms & recovery.** Prepare: live NOAA storm watch, a checklist for the crop in the field, free phone alerts, the farm's storm exposure since 1971, and a replay of Hurricane Melissa on every calendar. Respond and recover: Gemini photo check, FDA-based staged recovery, where to report damage, CCRIF micro-insurance. Restore the soil: by condition (waterlogged, eroded, salt-damaged, compacted, tired), checked against the farm. Rice is suggested only for waterlogged clay that can hold water, never as a universal fix. Build resilience: crops that withstand wind, windbreaks and insurance.
7. **Pest watch.** Farmers report pests and diseases with a photo, a category and a severity. Locations are blurred to about 2 km, and every report stays *Unverified* until an agricultural officer reviews it. Reports can be filtered by type, severity, distance and time. Farmers can follow their area for free phone alerts. Gemini gives a photo suggestion labelled "not a diagnosis". An officer dashboard verifies reports, adds guidance and flags possible outbreaks.
8. **News & ask.** Caribbean agriculture headlines; official sources (T&T Met Service, MALF, ODPM, NAMDEVCO, RADA, ODPEM, CIMH, CARDI, FAO, CCRIF); and Ask FarmFit, a Gemini assistant grounded in the farm's data, in English, Spanish, French and Kreyòl.
9. **For everyone.** Text size, dark mode, phone layouts, printable summaries and WhatsApp sharing.

**Keeping it live.** A GitHub Actions workflow refreshes the data every day in hurricane season and twice a week otherwise: NASA POWER, IMERG (GES DISC OPeNDAP), SMAP and MODIS (LP DAAC AppEEARS, with requests carried between runs), NOAA IBTrACS, the ENSO index and NAMDEVCO prices. A second workflow checks storms every 3 hours and sends alerts.

**Why it is different.** It covers the whole cycle from hurricane to harvest, not just the weather. Each page sits at its own depth of a hand-drawn world, from the sky (storms) through the field (planting) to the soil and the bedrock (evidence). Planting windows show as blossoming fruit trees. Every number traces back to an open dataset, and the app is honest about limits: it shows "95%+" rather than certainty, and ranks SMAP against "4 Novembers on record" instead of claiming a percentile from three years.

**How we built it.** Python and Streamlit, pandas and numpy, folium with NASA GIBS WMTS tiles, Altair and hand-written SVG, requests, the Google Gemini API, GitHub Actions and ntfy. 30 automated tests check the engine, the data parsers and the safeguards (location blurring, unverified status, the rice rule).

**Limits and human judgment.** Satellite cells are larger than farms, so farmers can override soil values. Crop vulnerability values are transparent heuristics that need validation with CARDI and extension officers. Labour and input costs are not modelled. FarmFit supports farmer judgment; it never replaces it.

**Impact.** First users: farmers and extension officers in Jamaica and Trinidad and Tobago. The engine works for any farm in the Atlantic basin today, and with NOAA IBTrACS it extends to typhoon and cyclone coasts.

## NASA data

- NASA POWER daily (MERRA-2 / CERES): T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, WS2M, WS10M_MAX, GWETTOP, GWETROOT, ALLSKY_SFC_SW_DWN
- GPM IMERG V07 daily, Final and Late runs (GES DISC OPeNDAP)
- SMAP L3 enhanced surface soil moisture (SPL3SMP_E) and SMAP L4 root-zone soil moisture (SPL4SMGP), via LP DAAC AppEEARS
- MODIS MOD13Q1 NDVI and MOD16A2 evapotranspiration (ET, PET), via AppEEARS
- NASA SRTM GL1 30 m elevation (via OpenTopoData)
- NASA GIBS: SMAP, GPM IMERG, MODIS NDVI and corrected reflectance, MODIS combined flood (2-day), OPERA DSWx Sentinel-1 surface water

## Partner, local and other data

NOAA NHC HURDAT2 and CurrentStorms; NOAA IBTrACS; NOAA CPC Oceanic Niño Index; ISRIC SoilGrids 2.0; FAO ECOCROP and FAO-56; NAMDEVCO wholesale prices (Trinidad and Tobago open data); CIMH Caribbean Drought Bulletin; CCRIF Livelihood Protection Policy; Jamaica Ministry of Agriculture Melissa assessment; U.S. FDA flood-affected crops guidance; USDA Caribbean Climate Hub; CARDI.

## Use of AI

Google Gemini describes field photos as structured JSON with a confidence value, and answers farmer questions from a briefing of the farm's own data. Every recommendation comes from documented rules and models plus farmer confirmation. Code and documentation were developed with AI assistance (Claude) and reviewed by the team. No AI-generated imagery or data is presented as NASA data; all artwork is drawn in code.
