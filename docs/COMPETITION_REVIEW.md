# FarmFit vs the competition requirements

## 1. Mandatory deliverables

| Requirement | Status |
|---|---|
| Responds to an official challenge (*Field Shift: Adapting Farms with NASA Data*) | ✅ |
| Working, deployed web app (URL) | ✅ Built. The Streamlit Cloud URL still has to go into the README and slide 7 |
| 30-second demo video (MP4) | ✅ `FarmFit_Hurricane_to_Harvest_30s.mp4` (29.9 s) |
| Presentation, up to 7 slides (PPTX) | ✅ `docs/FarmFit_Hurricane_to_Harvest.pptx` |
| Project description | ✅ `docs/SUBMISSION.md` |
| Public source code | ✅ github.com/keydahknow/FarmFit |
| README with datasets, methods and references | ✅ `README.md` |
| Uses NASA data | ✅ POWER, GPM IMERG, SMAP L3 and L4, MODIS NDVI and ET, SRTM, GIBS (MODIS flood, OPERA DSWx) |
| Use of AI disclosed | ✅ README and SUBMISSION (Gemini for photos and Q&A, labelled as suggestions; code built with Claude) |

## 2. The challenge brief, point by point

| The brief asks for… | Where FarmFit does it |
|---|---|
| Local soil information | My farm: SoilGrids texture, drainage, pH and organic matter, plus SRTM slope; the farmer can override with their own soil type or pH |
| Crop characteristics | 25 Caribbean crops with FAO ECOCROP ranges, FAO-56 water coefficients, days to harvest, nitrogen fixing, cover value, wind and flood vulnerability by growth stage |
| Farmer priorities: water use | Water saver strategy; irrigation need per crop and month; storm water bank; watering this week |
| … forage value | Strategy explanations list livestock feed for each crop (FAO Feedipedia) |
| … nitrogen fixing | Crop comparison ("makes its own nitrogen"); soil score; restoration guide |
| … erosion reduction | Bare-soil months on erosive-rain months (RUSLE logic with SRTM slope); restoration for eroded land |
| … organic matter | Soil builder strategy; 5-year roadmap; restoration for tired soil |
| … market suitability | NAMDEVCO price seasons; price at harvest per strategy; profit calculator using the farmer's own numbers |
| Highlight when fields are bare | Calendar shows bare months against the risk row |
| Seasons when crops are vulnerable | Storm and flood risk row; growth-stage vulnerability; the planting-window trees and heatmap |
| Rotations that break pest cycles | Pest-cycle check (same family back to back) in every strategy; 5-year plan alternates families |
| Reduce water demand / improve infiltration | Water saver; cover crops; restoration for compacted soil |
| Supplemental income | Market timing, profit calculator, feed value |
| Compare at least three strategies including the existing one | Current rotation vs Storm-smart, Soil builder, Water saver (out of about 240,000 calendars) |
| For each: why, evidence, benefits, gaps, risks needing local review | Every strategy card has why, evidence, benefits, gaps and "check locally" |

## 3. Judging criteria

**Impact.** Caribbean agriculture loses crops to storms, then to the glut that follows recovery, and the dry season is the quieter half of the risk. FarmFit covers the whole cycle: plan, prepare, respond, restore, resilience. It does this for commercial farms and for home gardens, which matter for household food security.

**Creativity.**
- The interface tells the story: each page sits at its own depth of a hand-drawn world, from sky to bedrock.
- Planting windows are shown as blossoming fruit trees.
- Onboarding progress grows from a seed to a fruiting tree.
- The community pest map works like a traffic app.
- El Niño is tested on the farm's own rainfall record rather than quoted as a rule of thumb.

**Validity.**
- Methods are published: FAO-56 evapotranspiration, the ECOCROP suitability ranges, RUSLE slope factors, a Rankine wind model for storms, Monte Carlo simulation, empirical percentiles, and OLS trends with standard errors.
- Every number on screen is labelled as measured data, a model estimate, your numbers, or a simulated example.
- Limits are stated plainly: chances are capped at "95%+", short records are ranked rather than turned into percentiles, rice is recommended only where it can grow, and warming is shown as a what-if scenario, not a forecast.
- 30 automated tests cover the engine, the parsers and the safeguards.

**Relevance.** It answers *Field Shift* directly: adapting what and when farms plant to a changing climate, using NASA data at farm scale.

**Presentation.** A 30-second video and a 7-slide deck in the same visual identity. The app itself opens with a one-minute onboarding and a "Plant now, or wait?" answer.

## 4. Strongest advantages

1. **Hurricane-to-harvest cycle.** No other entry we have seen links storm exposure at the field, crop growth stages, recovery and soil restoration.
2. **Data depth with honesty.** Eight NASA datasets refreshed on a schedule, each number labelled by where it comes from.
3. **Community pest and disease watch** with location blurring, an "unverified until reviewed" status, officer verification and outbreak detection.
4. **Built for real Caribbean farmers:** four languages, home-garden mode, works on a phone, a printable summary, WhatsApp sharing and free phone alerts.
5. **Local data:** NAMDEVCO prices, CIMH drought bulletins, CCRIF micro-insurance, RADA, ODPM, the T&T Met Service and CARDI.

Compared with the AgriWise demo (Luxor, Egypt), which offers a polished "plant now or wait?" advisor built on NASA POWER: FarmFit gives the same direct answer and adds storms, satellite soil moisture and plant stress, the market, soil restoration, community reporting and a home-garden mode.

## 5. Local impact: Trinidad and Tobago first

**Use cases**
- **Caroni rice and vegetable farmer:** sees that El Niño years brought about 64% of normal dry-season rain at this farm, and that a strong El Niño is under way. Plans water storage and drought-tolerant crops. After flooding, gets rice suggested for waterlogged clay that can hold water, and not for land it doesn't suit.
- **Penal or Moruga vegetable grower:** gets a pest alert when armyworm is reported 5 km away, scouts the field, and reports back.
- **Port of Spain home gardener:** gets container crops for this month, how much to water this week, and storm-prep steps.
- **Ministry extension officer:** reviews reports, verifies them, adds guidance, and sees possible outbreaks.

**How a pilot would measure impact** (targets to test, not claims):
- number of farms onboarded;
- share of pest reports verified by officers, and time to verification;
- time from first report to an area alert;
- plans downloaded or printed;
- in a follow-up season: crop loss reported after storms, and whether planting dates changed.

**Sustainability and scale**
- Open data and free services: NASA, NOAA, ISRIC, Open-Meteo and ntfy. Hosting is free at pilot scale.
- Data refreshes run on scheduled GitHub Actions.
- Works for any farm in the Atlantic basin today. NOAA IBTrACS extends the storm engine worldwide.
- Next steps: move pest reports to a persistent database, add ministry accounts, and translate with native speakers.

## 6. Gaps and limitations (stated honestly)

- **Market data:** NAMDEVCO prices arrive only after the scheduled refresh runs. Jamaica's farmgate prices are published as PDFs and are not yet parsed.
- **Missing farm economics:** labour, fertiliser cost and yield are not in any open dataset we could verify, so the profit calculator uses the farmer's own numbers.
- **Pest report storage:** reports are stored on the app's disk. Streamlit Community Cloud resets that disk on restart, so a production deployment needs a database.
- **Flood risk:** the flood rating comes from drainage, slope and elevation. It is not an official flood map, and T&T flood-zone layers are not public as open data.
- **Validation:** crop vulnerability values are transparent estimates that need checking with CARDI and extension officers.
- **Languages:** French and Kreyòl text needs review by native speakers.
- **Live services not yet tested end to end:** the Gemini, news feed, NHC storm feed and map tiles need checking on the deployed site, because this build environment cannot reach them.
