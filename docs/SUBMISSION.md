# NASA Space Apps 2026: submission text

**Project name:** FarmFit · Hurricane to Harvest
**Challenge:** Field Shift: Adapting Farms with NASA Data

## High-level summary

Hurricane to Harvest helps small-scale farmers in hurricane-prone regions choose crop rotations that protect the harvest from storms, rebuild soil and save water, and it guides them back to production after a storm.

A farmer taps their farm on a map. FarmFit fuses 30 years of NASA POWER climate data, 75 years of NOAA hurricane tracks, SoilGrids soil, NASA SRTM terrain and FAO crop science. It then compares the farmer's current rotation with three alternatives (Storm-smart, Soil builder, Water saver), month by month.

Each plan explains why it was suggested, the evidence, its benefits, the information gaps and what to check locally. A stress test replays real storms such as Hurricane Melissa (2025) on every calendar and simulates 5,000 storm seasons. After a storm, a field photo analysed by AI, plus NASA rain and soil-moisture context and FDA food-safety rules, produce a staged recovery calendar.

We demonstrate it on two contrasting farms:

- **St Elizabeth, Jamaica:** wind is the main hazard.
- **Caroni plains, Trinidad:** flooding is the main hazard.

## Project details

**What it does**

1. **Farm profile.** One map click returns:
   - rainfall and temperature normals, heavy-rain probability and root-zone soil wetness (NASA POWER, MERRA-2)
   - soil pH, texture and drainage (SoilGrids)
   - slope (NASA SRTM)
   - every storm since 1950 converted into the wind it brought to that farm (NOAA HURDAT2 with a modified Rankine vortex)
   - NASA GIBS layers (SMAP soil moisture, GPM IMERG rain, MODIS NDVI) for any date

   A "data passport" lists each dataset, its resolution, its period and whether it is live or cached.
2. **Field shift.** The first 15 years of NASA POWER data against the last 15: rainfall, days above 32 °C, ≥ 50 mm rain days, dry spells and the monthly rain pattern. Each change carries a trend-significance label.
3. **Compare rotations.** The farmer enters their current rotation, priority, irrigation access and constraints. FarmFit searches every 12-month rotation of up to four crops (about 200,000 calendars, 25 Caribbean crops and cover crops). It scores each one on climate fit (FAO ECOCROP), storm and flood safety, soil health, water saving and food months, then shows the best three alongside the current rotation.
4. **Hurricane stress test.** Replay a real storm to see which crop and growth stage were in the field that day and the estimated loss. A Monte Carlo of 5,000 seasons gives average loss, bad-year loss and the chance of losing more than half the harvest; sliders test stormier or wetter futures.
5. **Storm water bank.** Taken from our IFRS flood-resilience project, this sizes a rain tank that captures storm runoff for dry-season irrigation.
6. **After the storm.** Gemini vision describes only what is visible in a field photo, with a confidence value. The farmer confirms the water source and whether floodwater touched edible crops. Explicit rules, including FDA guidance that flood-contacted edible crops are adulterated, produce four gated stages (safety → drain → cover → production) and a recovery rotation.

**Benefits.** The tool shows farmers which months are risky for their own farm. It keeps fragile crop stages out of peak storm weeks and cuts bare-soil months during erosive rains. It adds legumes and cover crops to build soil, and it gives a safe, staged recovery path. Plans download as text and share on WhatsApp, so they work offline.

**How we built it.** Python and Streamlit, with pandas/numpy, folium (NASA GIBS WMTS layers), Altair, requests and the Google Gemini API. The scoring weights, vulnerability values and assumptions are all published in the code and README, and 10 automated tests check the engine.

**Science and validation.** Methods:
- FAO-56 Hargreaves ET₀ and crop coefficients for water need
- RUSLE cover × rainfall logic and the McCool slope factor for erosion
- a vortex wind profile for storm exposure
- OLS trends with t-statistics for the field shift

The exposure model reproduces history: Melissa 2025 is the strongest wind at the St Elizabeth farm, Beryl 2024 at Carriacou, and Trinidad shows no hurricane-force wind since 1971. It is an exposure screen, not a forecast.

**Limits and human judgment.** Satellite cells are larger than farms, so farmers can override soil values. Crop vulnerability values are transparent heuristics that need validation with CARDI and extension officers, and markets are not modelled. FarmFit supports farmer judgment; it never replaces it.

**Impact.** The first users are farmers and extension officers in Jamaica and Trinidad and Tobago. The engine works for any farm in the Atlantic basin today. With NOAA IBTrACS, the same approach extends to typhoon and cyclone coasts, from the Philippines to Mozambique.

## NASA data

- NASA POWER daily (MERRA-2 / CERES): T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, WS2M, WS10M_MAX, GWETTOP, GWETROOT, ALLSKY_SFC_SW_DWN
- NASA SRTM GL1 30 m elevation (via OpenTopoData)
- NASA GIBS: SMAP L4 surface soil moisture, GPM IMERG precipitation rate, MODIS Terra NDVI 8-day and corrected reflectance

## Partner and other data

NOAA NHC HURDAT2 (1851-2025); ISRIC SoilGrids 2.0; FAO ECOCROP; FAO Irrigation & Drainage Paper 56; U.S. FDA flood-affected crops guidance; USDA Caribbean Climate Hub adaptation guides; PhilRice; CARDI; Jamaica Ministry of Agriculture Melissa assessment.

## Use of AI

Google Gemini vision describes field photos as structured JSON with a confidence value. Every decision is made by documented rules plus farmer confirmation. Code and documentation were developed with AI assistance (Claude) and reviewed by the team. No AI-generated imagery or data is presented as NASA data.
