const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const { applyTheme } = require("/root/.claude/skills/synced/efc0e3e4-ad16-4d33-954f-f538873091eb_60703634-82d0-4bd8-b6d1-591c093acfd6/pptx/scripts/apply_theme.js");
const fa = require("react-icons/fa");
const md = require("react-icons/md");
const gi = require("react-icons/gi");

const THEME = {
  name: "Hurricane to Harvest",
  headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: "0B2545", lt1: "FFFFFF", dk2: "13315C", lt2: "EEF3EC",
    accent1: "1D6F5F", accent2: "FFD166", accent3: "C1121F", accent4: "2F7D32",
    accent5: "8C6A43", accent6: "3A86FF", hlink: "1D6F5F", folHlink: "13315C" },
};
const HEX = THEME.colors;

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9"; // 10 x 5.625
  pres.title = "Hurricane to Harvest - FarmFit";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  pres.defineSlideMaster({
    title: "DARK", background: { color: HEX.dk1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 1.55, w: 5.6, h: 1.2, fontSize: 44, bold: true, color: C.background1, valign: "top", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "CONTENT", background: { color: HEX.lt1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9.0, h: 0.75, fontSize: 28, bold: true, color: C.text1, valign: "middle", margin: 0 }, text: "" } },
      { text: { text: "FarmFit · Hurricane to Harvest · NASA Space Apps 2026", options: { x: 0.5, y: 5.25, w: 6, h: 0.25, fontSize: 9, color: "617064", margin: 0 } } },
    ],
    slideNumber: { x: 9.1, y: 5.25, w: 0.4, h: 0.25, fontSize: 9, color: "617064" },
  });

  const I = {
    storm: await icon(gi.GiTornado, HEX.dk1), stormW: await icon(gi.GiTornado, HEX.accent2),
    map: await icon(fa.FaMapMarkedAlt, "FFFFFF"), shift: await icon(fa.FaHistory, "FFFFFF"),
    cal: await icon(fa.FaCalendarAlt, "FFFFFF"), test: await icon(fa.FaBolt, "FFFFFF"), camera: await icon(fa.FaCamera, "FFFFFF"),
    sat: await icon(md.MdSatelliteAlt, "FFFFFF"), leaf: await icon(fa.FaSeedling, "FFFFFF"), globe: await icon(fa.FaGlobeAmericas, "FFFFFF"),
    check: await icon(fa.FaUserCheck, "FFFFFF"), drop: await icon(fa.FaTint, "FFFFFF"),
  };
  const circleIcon = (s, data, x, y, d, fill, name) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill }, objectName: name + " circle" });
    s.addImage({ data, x: x + d * 0.22, y: y + d * 0.22, w: d * 0.56, h: d * 0.56, objectName: name + " icon" });
  };
  const card = (s, x, y, w, h, name, fill = C.background2) =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: fill }, objectName: name });

  // ---------------- 1. Title
  pres.addSection({ title: "Opening" });
  let s = pres.addSlide({ masterName: "DARK", sectionTitle: "Opening" });
  s.addText("NASA SPACE APPS 2026 · FIELD SHIFT: ADAPTING FARMS WITH NASA DATA", { x: 0.6, y: 0.75, w: 7.5, h: 0.35, fontSize: 11, bold: true, color: C.accent2, charSpacing: 2, margin: 0, isTextBox: true });
  s.addText("Hurricane to Harvest", { placeholder: "title" });
  s.addText("Crop rotations that weather the storm and rebuild the soil", { x: 0.6, y: 2.75, w: 5.4, h: 0.8, fontSize: 20, color: "DBE7F3", margin: 0, isTextBox: true });
  s.addText([
    { text: "FarmFit", options: { bold: true, color: "FFFFFF", breakLine: true } },
    { text: "NASA POWER · SMAP · GPM IMERG · MODIS · SRTM · NOAA HURDAT2 · SoilGrids · FAO", options: { color: "9FB3C8" } },
  ], { x: 0.6, y: 4.05, w: 6.0, h: 0.7, fontSize: 12, margin: 0, isTextBox: true });
  s.addShape(pres.shapes.OVAL, { x: 6.75, y: 1.15, w: 2.75, h: 2.75, fill: { color: HEX.dk2 }, line: { color: HEX.accent2, width: 2 }, objectName: "storm motif" });
  s.addImage({ data: I.stormW, x: 7.4, y: 1.8, w: 1.45, h: 1.45, objectName: "storm icon" });
  s.addText("Two demo farms: St Elizabeth, Jamaica and the Caroni plains, Trinidad", { x: 6.55, y: 4.1, w: 3.15, h: 0.6, fontSize: 11, color: "DBE7F3", align: "center", margin: 0, isTextBox: true });
  s.addNotes("Hurricane to Harvest is a decision-support tool built on FarmFit. It helps small-scale Caribbean farmers choose crop rotations that protect the harvest from storms and rebuild soil, and it gives them a safe path back after a storm. Everything is built on open NASA and partner data.");

  // ---------------- 2. Problem
  pres.addSection({ title: "Problem" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem" });
  s.addText("One storm can erase a season's harvest", { placeholder: "title" });
  const stats = [["32,400 ha", "of vegetable crops lost"], ["47,500", "vegetable farmers affected"], ["J$29.5 B", "preliminary agricultural damage"]];
  stats.forEach(([n, l], i) => {
    const y = 1.25 + i * 1.18;
    s.addText(n, { x: 0.5, y, w: 3.2, h: 0.65, fontSize: 40, bold: true, color: C.accent3, margin: 0, isTextBox: true });
    s.addText(l, { x: 0.5, y: y + 0.62, w: 3.6, h: 0.35, fontSize: 14, color: C.text1, margin: 0, isTextBox: true });
  });
  s.addText("Hurricane Melissa, Jamaica, 28 Oct 2025. Source: Ministry of Agriculture, Fisheries and Mining, 14 Nov 2025", { x: 0.5, y: 4.8, w: 4.3, h: 0.35, fontSize: 10, color: "617064", margin: 0, isTextBox: true });
  card(s, 4.85, 1.2, 4.65, 3.85, "problem card");
  s.addText("Calendars set for an older climate", { x: 5.1, y: 1.38, w: 4.2, h: 0.45, fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true });
  s.addText([
    { text: "At a St Elizabeth farm, storm-force wind now arrives about 1 year in 4. 11 of 14 events since 1971 came after 2000 (NOAA HURDAT2).", options: { bullet: true, breakLine: true } },
    { text: "Fragile crops (peppers, tomatoes, plantain) often sit at their most vulnerable stage in August to October.", options: { bullet: true, breakLine: true } },
    { text: "In Trinidad's Caroni plains, no hurricane-force wind since 1971. The threat is heavy rain on slow-draining soil.", options: { bullet: true, breakLine: true } },
    { text: "Farmers need to know which crop should be in which month, for their own farm.", options: { bullet: true } },
  ], { x: 5.1, y: 1.9, w: 4.2, h: 3.0, fontSize: 14, color: C.text1, paraSpaceAfter: 8, valign: "top", margin: 0, isTextBox: true });
  s.addNotes("Melissa made landfall in south-western Jamaica as a Category 5. St Elizabeth, the breadbasket parish, was among the hardest hit. Our own analysis of NOAA's HURDAT2 shows storm-force wind reaching a St Elizabeth farm about once every four years, with most events since 2000. Trinidad has a different risk: flooding. One tool has to handle both.");

  // ---------------- 3. Solution journey
  pres.addSection({ title: "Solution" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Solution" });
  s.addText("Pick a farm, get four calendars and a recovery plan", { placeholder: "title" });
  const steps = [
    [I.map, "Farm profile", "Climate, soil, slope and storm history from one map click"],
    [I.shift, "Field shift", "First 15 years vs last 15 years of NASA climate"],
    [I.cal, "Compare", "Current rotation vs Storm-smart, Soil builder, Water saver"],
    [I.test, "Stress test", "Replay Melissa; simulate 5,000 seasons"],
    [I.camera, "After the storm", "Photo, AI, rules: a staged recovery calendar"],
  ];
  const fills = [C.accent1, C.text2, C.accent4, C.accent3, C.accent5];
  steps.forEach(([ic, t, d], i) => {
    const x = 0.5 + i * 1.84;
    circleIcon(s, ic, x + 0.6, 1.1, 0.55, fills[i], t);
    s.addText(t, { x, y: 1.72, w: 1.75, h: 0.32, fontSize: 14, bold: true, color: C.text1, align: "center", margin: 0, isTextBox: true });
    s.addText(d, { x, y: 2.04, w: 1.75, h: 0.62, fontSize: 11, color: "4A5A4F", align: "center", valign: "top", margin: 0, isTextBox: true });
  });
  s.addImage({ path: "cal_rows.png", x: 0.9, y: 2.82, w: 8.2, h: 8.2 * 240 / 1060, objectName: "calendar screenshot" });
  s.addText("Top row: chance per year of storm-force wind or a waterlogging rain day. Striped: bare soil. Red outline: the month Melissa struck.", { x: 0.9, y: 4.75, w: 8.2, h: 0.3, fontSize: 10, color: "617064", margin: 0, isTextBox: true });
  s.addNotes("The farmer picks a farm or a demo site. Five steps follow. The heart of it is the comparison: their current rotation against three alternatives, found by searching around 200,000 possible 12-month rotations. Each one shows why it was suggested, its evidence, benefits, data gaps and what to check locally.");

  // ---------------- 4. Data
  pres.addSection({ title: "Data" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  s.addText("Eight open datasets fused onto one farm-month grid", { placeholder: "title" });
  const ds = [
    ["NASA POWER", "30 yr daily rain, temp, wind, soil wetness", "≈ 55 km"],
    ["GPM IMERG", "Storm-date rainfall map layer", "0.1°"],
    ["SMAP L4", "Surface soil moisture layer", "9 km"],
    ["MODIS", "NDVI and true-colour after storms", "250 m"],
    ["NASA SRTM", "Elevation and slope for erosion", "30 m"],
    ["NOAA HURDAT2", "Every storm track 1950-2025", "6-hourly"],
    ["SoilGrids", "pH, carbon, texture, drainage", "250 m"],
    ["FAO crop data", "ECOCROP ranges, FAO-56 water use", "25 crops"],
  ];
  ds.forEach(([n, u, r], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.5 + col * 3.05, y = 1.2 + row * 0.95;
    card(s, x, y, 2.9, 0.82, "dataset " + n, i < 5 ? "E6F0F4" : C.background2);
    s.addText(n, { x: x + 0.15, y: y + 0.08, w: 1.9, h: 0.3, fontSize: 14, bold: true, color: C.text1, margin: 0, isTextBox: true });
    s.addText(r, { x: x + 1.95, y: y + 0.08, w: 0.82, h: 0.3, fontSize: 10, color: C.accent1, bold: true, align: "right", margin: 0, isTextBox: true });
    s.addText(u, { x: x + 0.15, y: y + 0.4, w: 2.65, h: 0.35, fontSize: 11, color: "4A5A4F", margin: 0, isTextBox: true });
  });
  s.addShape(pres.shapes.RIGHT_ARROW, { x: 6.7, y: 2.75, w: 0.5, h: 0.45, fill: { color: C.accent2 }, line: { color: C.accent2 }, objectName: "fusion arrow" });
  card(s, 7.35, 1.2, 2.15, 3.75, "scores card", HEX.dk1);
  s.addText("12 months × 1 farm", { x: 7.5, y: 1.35, w: 1.9, h: 0.35, fontSize: 14, bold: true, color: C.accent2, margin: 0, isTextBox: true });
  s.addText([
    { text: "Climate fit", options: { bullet: true, breakLine: true } },
    { text: "Storm and flood safety", options: { bullet: true, breakLine: true } },
    { text: "Soil health", options: { bullet: true, breakLine: true } },
    { text: "Water saving", options: { bullet: true, breakLine: true } },
    { text: "Food months", options: { bullet: true } },
  ], { x: 7.5, y: 1.8, w: 1.9, h: 1.9, fontSize: 14, color: C.background1, paraSpaceAfter: 6, valign: "top", margin: 0, isTextBox: true });
  s.addText("A data passport shows each dataset's resolution, period and live/cached status.", { x: 7.5, y: 3.85, w: 1.9, h: 0.95, fontSize: 11, italic: true, color: "DBE7F3", valign: "top", margin: 0, isTextBox: true });
  s.addNotes("Blue cards are NASA data; green are partner data. Everything is resampled to the farm and to calendar months, so the data become five transparent scores. The data passport tells farmers and judges which data are live, cached or missing, and at what resolution. Satellite cells are bigger than a farm, so farmers can correct the soil with their own test.");

  // ---------------- 5. Science
  pres.addSection({ title: "Science" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Science" });
  s.addText("Transparent models anyone can audit", { placeholder: "title" });
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  s.addChart(pres.charts.BAR, [
    { name: "St Elizabeth, Jamaica", labels: months, values: [0,0,0,0,0,0,3.6,10.9,3.6,3.6,1.8,0] },
    { name: "Caroni, Trinidad", labels: months, values: [0,0,0,0,0,1.8,0,3.6,1.8,0,0,0] },
  ], { x: 0.4, y: 1.15, w: 5.0, h: 3.75, barDir: "col", barGapWidthPct: 60,
    chartColors: [HEX.accent3, HEX.accent6], showTitle: true, title: "Chance a month brings storm-force wind to the farm (%)",
    titleFontSize: 12, titleColor: HEX.dk1, titleFontFace: "+mn-lt",
    showLegend: true, legendPos: "b", legendFontSize: 11, legendFontFace: "+mn-lt", legendColor: HEX.dk1,
    catAxisLabelColor: "4A5A4F", valAxisLabelColor: "4A5A4F", catAxisLabelFontSize: 10, valAxisLabelFontSize: 10,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    valGridLine: { color: "E2E8E0", size: 0.5 }, catGridLine: { style: "none" }, valAxisLabelFormatCode: "0" });
  s.addText("NOAA HURDAT2 1971-2025, wind estimated at each farm", { x: 0.5, y: 4.9, w: 4.8, h: 0.25, fontSize: 10, color: "617064", margin: 0, isTextBox: true });
  const methods = [
    ["Wind at the farm", "Every track at 15-min steps; modified Rankine vortex V = Vmax(Rm/r)^0.6. Melissa ranks #1 at St Elizabeth, Beryl at Carriacou."],
    ["Water", "FAO-56 Hargreaves ET0 and stage Kc; irrigation = Σ max(0, ETc − 0.8P)"],
    ["Soil", "Living cover weighted by monthly rain (RUSLE C×R), legume months, family diversity, SRTM slope"],
    ["Search and test", "≈ 200,000 rotations enumerated; 5,000-season Monte Carlo; 10 automated tests"],
  ];
  methods.forEach(([h, b], i) => {
    const y = 1.15 + i * 0.95;
    s.addText(h, { x: 5.75, y, w: 3.75, h: 0.3, fontSize: 14, bold: true, color: C.accent1, margin: 0, isTextBox: true });
    s.addText(b, { x: 5.75, y: y + 0.3, w: 3.75, h: 0.6, fontSize: 11, color: C.text1, valign: "top", margin: 0, isTextBox: true });
  });
  s.addNotes("Science we can defend. Wind at each farm comes from NOAA tracks with a standard vortex profile, and it reproduces history: Melissa is the top storm at St Elizabeth and Beryl at Carriacou. Water uses FAO-56; soil uses RUSLE logic. Every weight is published in the code. The model screens exposure; it does not forecast storms.");

  // ---------------- 6. Result
  pres.addSection({ title: "Results" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("Replaying Melissa on each calendar", { placeholder: "title" });
  s.addImage({ path: "replay_cards.png", x: 0.5, y: 1.15, w: 6.0, h: 6.0 * 152 / 1060, objectName: "replay screenshot" });
  s.addText("Estimated loss on 28 Oct 2025 (≈ 95 kt at the farm)", { x: 0.5, y: 2.05, w: 6.0, h: 0.25, fontSize: 10, color: "617064", margin: 0, isTextBox: true });
  s.addText("On 28 Oct 2025 the typical rotation had sweet peppers mid-season (≈ 60% loss). The Storm-smart calendar had harvested earlier and held the soil under a cover crop.", { x: 0.5, y: 2.5, w: 6.0, h: 1.2, fontSize: 15, color: C.text1, valign: "top", margin: 0, isTextBox: true });
  card(s, 0.5, 3.95, 6.0, 1.05, "after storm flow", "F3EFE8");
  const flow = [["Photo", I.camera, C.accent5], ["Gemini", I.sat, C.text2], ["Rules + FDA", I.check, C.accent3], ["Recovery", I.leaf, C.accent4]];
  flow.forEach(([t, ic, f], i) => {
    const x = 0.75 + i * 1.45;
    circleIcon(s, ic, x, 4.1, 0.45, f, t);
    s.addText(t, { x: x + 0.5, y: 4.15, w: 0.9, h: 0.35, fontSize: 12, bold: true, color: C.text1, margin: 0, isTextBox: true });
  });
  s.addText("After the storm: AI describes the photo; rules decide; the farmer confirms what a photo can't show.", { x: 0.75, y: 4.6, w: 5.6, h: 0.3, fontSize: 11, color: "4A5A4F", margin: 0, isTextBox: true });
  card(s, 6.85, 1.15, 2.65, 3.85, "monte carlo card", HEX.dk1);
  s.addText("5,000", { x: 7.05, y: 1.35, w: 2.3, h: 0.75, fontSize: 44, bold: true, color: C.accent2, margin: 0, isTextBox: true });
  s.addText("simulated storm seasons per farm", { x: 7.05, y: 2.1, w: 2.3, h: 0.5, fontSize: 13, color: C.background1, margin: 0, isTextBox: true });
  s.addText("Average loss, bad-year (1 in 10) loss and the chance of losing more than half. Sliders test a stormier or wetter future.", { x: 7.05, y: 2.75, w: 2.3, h: 1.4, fontSize: 12, color: "DBE7F3", valign: "top", margin: 0, isTextBox: true });
  s.addText("Exposure screen, not a forecast", { x: 7.05, y: 4.35, w: 2.3, h: 0.4, fontSize: 11, italic: true, color: C.accent2, margin: 0, isTextBox: true });
  s.addNotes("The demo: Melissa hit on 28 October. The typical St Elizabeth rotation had sweet peppers in the field, an estimated 60 percent loss. The alternatives had harvested before the peak and kept a cover crop on the soil. The Monte Carlo turns the farm's own history into a distribution of bad years. After a storm, a photo plus a few questions produce a gated recovery plan that follows FDA flood-crop safety guidance.");

  // ---------------- 7. Impact
  pres.addSection({ title: "Impact" });
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Impact" });
  s.addText("From two Caribbean farms to every storm coast", { x: 0.6, y: 0.45, w: 8.8, h: 0.7, fontSize: 30, bold: true, color: C.background1, margin: 0, isTextBox: true });
  const cols = [
    [I.leaf, "Local", ["Pilots in Jamaica and Trinidad with extension officers", "Works offline: text plan plus WhatsApp share", "IFRS rain tanks bank storm water for the dry season"]],
    [I.globe, "Global", ["Any farm in the Atlantic basin today", "Next: IBTrACS for typhoons and cyclones (Philippines, Bangladesh, Pacific)", "Rice submergence guidance from PhilRice"]],
    [I.check, "Validate", ["Crop vulnerability values reviewed with CARDI and the USDA Caribbean Climate Hub", "Ground sensors (IFRS-style JSON feed) to check SMAP", "Supports, never replaces, farmer judgment"]],
  ];
  cols.forEach(([ic, t, items], i) => {
    const x = 0.6 + i * 3.0;
    card(s, x, 1.45, 2.8, 3.05, "impact " + t, HEX.dk2);
    circleIcon(s, ic, x + 0.2, 1.62, 0.5, [C.accent4, C.accent1, C.accent5][i], t);
    s.addText(t, { x: x + 0.8, y: 1.67, w: 1.8, h: 0.4, fontSize: 18, bold: true, color: C.accent2, margin: 0, isTextBox: true });
    s.addText(items.map((it, k) => ({ text: it, options: { bullet: true, breakLine: k < items.length - 1 } })),
      { x: x + 0.2, y: 2.3, w: 2.45, h: 2.4, fontSize: 12, color: C.background1, paraSpaceAfter: 6, valign: "top", margin: 0, isTextBox: true });
  });
  s.addText("Live app: [add Streamlit URL]   ·   Code: github.com/keydahknow/FarmFit", { x: 0.6, y: 4.8, w: 8.8, h: 0.3, fontSize: 12, color: "9FB3C8", margin: 0, isTextBox: true });
  s.addNotes("Locally, we start with extension officers in Jamaica and Trinidad. The plan works offline and shares on WhatsApp. It links to our IFRS flood-resilience work, banking storm water for the dry season. Globally, the same engine extends to typhoon and cyclone basins with IBTrACS. Before anyone plants by it, the crop vulnerability values need local validation. The tool supports farmers; it never replaces their judgment.");

  await pres.writeFile({ fileName: "FarmFit_Hurricane_to_Harvest.pptx" });
  await applyTheme("FarmFit_Hurricane_to_Harvest.pptx", THEME);
  console.log("written");
})();
