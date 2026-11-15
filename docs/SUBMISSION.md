# NASA Space Apps 2026: submission text

**Project name:** FarmFit · Hurricane to Harvest
**Challenge:** Field Shift: Adapting Farms with NASA Data

## High-level summary

Hurricane to Harvest helps small-scale Caribbean farmers plan a farm year that survives the storm season, rebuilds soil and saves water, and it guides them safely back to production after a storm.

A farmer picks their farm, then scrolls one continuous journey from the sky above the field to the bedrock beneath it. In the sky: every storm since 1971 turned into the wind it brought to that farm, live NOAA storm watch and a storm checklist. In the field: the farmer's current rotation compared with three alternatives (Storm-smart, Soil builder, Water saver), each explained with evidence, benefits, market timing, information gaps and local checks, plus an orchard of twelve fruit trees whose blossom shows the chance of a good harvest for each planting month. Under the surface: NASA SMAP soil moisture, MODIS plant water stress, GPM IMERG rain and a season-ahead El Niño test that uses the farm's own 30-year rain record. Deeper: the soil and a chat assistant grounded in all of it. At the bedrock: every dataset and method.

We demonstrate it on two contrasting farms: St Elizabeth, Jamaica, where Category 5 Hurricane Melissa struck on 28 October 2025, and the Caroni plains, Trinidad, where flooding and dry-season drought matter more than wind.

## Project details

**What it does**

1. **Pick your farm.** Demo farms, a place search, or a pin on a satellite map. Everything that follows is computed for that point.
2. **Storm ready (the sky).** Live NOAA NHC storms with a threat level and an arrival estimate; a storm checklist for the crop in the field this month; free phone alerts (ntfy) for storms, drought and very wet spells; storm exposure from NOAA HURDAT2 and IBTrACS with a modified Rankine vortex (Melissa 2025 comes out at about 95 kt at the St Elizabeth farm); replay a real storm on every calendar; 5,000 simulated seasons with sliders for a stormier or wetter future.
3. **Plan my season (the field).** FarmFit searches about 200,000 twelve-month rotations of up to four crops (25 Caribbean crops and cover crops) and scores each on climate fit (FAO ECOCROP + NASA POWER), storm and flood safety, soil health, water saving and food months. It shows the best three beside the farmer's own rotation. Each strategy explains why it was suggested, the evidence, benefits (including pest-cycle breaks and livestock feed), wholesale market timing (NAMDEVCO), information gaps and what to check with an extension officer. The planting-window orchard shows, for any crop, the chance of a good harvest by planting month: the share of 4,000 simulated seasons in which storms and floods take less than 20% of the crop, × climate fit × the share of the irrigation need the farmer's water covers. Plans print as an A4 almanac and share on WhatsApp.
4. **After a storm.** Gemini vision describes only what is visible in a field photo; the farmer confirms what a photo can't show. GPM IMERG rain around the storm and MODIS flood and OPERA Sentinel-1 radar water maps for the storm date add context. FDA food-safety rules drive four gated recovery stages and a recovery rotation that warns about post-storm gluts. Farmers see where to report damage (RADA) and how CCRIF's parametric Livelihood Protection Policy works, in terms of their own farm's storm odds.
5. **Water watch (under the surface).** Rain and root-zone wetness ranked against 30 years; SMAP L3 surface and SMAP L4 root-zone moisture; plant water stress from MODIS ET ÷ PET; a season-ahead card that splits 30 years of the farm's rain by El Niño, neutral and La Niña with the correlation r (at the Trinidad farm, El Niño years brought 64% of normal Dec-Feb rain, and a strong El Niño is under way); this week's watering advice; a storm water bank from our IFRS project; and the field shift between 1996-2010 and 2011-2025.
6. **Soil and roots.** SoilGrids texture, drainage, pH and organic matter with SRTM slope, turned into plain advice; a US$15 ESP32 soil probe compared with SMAP; and Ask FarmFit, a Gemini assistant that answers in English, Spanish, French or Kreyòl from a briefing of the farm's own data.
7. **Data and method (the bedrock).** A data passport lists every dataset, its resolution and when it was last refreshed.

**Keeping it live.** A GitHub Actions workflow refreshes the data every day in hurricane season and twice a week otherwise: NASA POWER, IMERG (GES DISC OPeNDAP), SMAP and MODIS (LP DAAC AppEEARS, with requests carried between runs), NOAA IBTrACS, the ENSO index and NAMDEVCO prices. A second workflow checks storms every 3 hours and sends alerts.

**Why it is different.** The interface is the story: a hand-drawn world slides behind the page as the farmer scrolls, so each tool sits in its layer of the farm, and a tree on the side comes alive (canopy above ground, roots below) as they go. Every number traces back to an open dataset, and the app is honest about limits: it shows "95%+" rather than certainty, and ranks SMAP against "4 Novembers on record" instead of claiming a percentile from three years.

**How we built it.** Python and Streamlit, pandas and numpy, folium with NASA GIBS WMTS tiles, Altair and hand-written SVG, requests, the Google Gemini API, GitHub Actions and ntfy. 26 automated tests check the engine and the data parsers.

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
