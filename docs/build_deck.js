const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const { applyTheme } = require("/root/.claude/skills/synced/efc0e3e4-ad16-4d33-954f-f538873091eb_60703634-82d0-4bd8-b6d1-591c093acfd6/pptx/scripts/apply_theme.js");
const fa = require("react-icons/fa");
const gi = require("react-icons/gi");

// The almanac palette from the app (fieldshift/art.py)
const THEME = {
  name: "Hurricane to Harvest almanac",
  headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "1F2B3A", lt1: "F3EEE3", dk2: "4C5563", lt2: "E9E1CF",
    accent1: "C2502F", accent2: "D99A2B", accent3: "3F7A4C", accent4: "3F7EA0",
    accent5: "9A6B43", accent6: "BCD5E1", hlink: "3F7EA0", folHlink: "4C5563" },
};
const HEX = THEME.colors;

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  return "image/png;base64," + (await sharp(Buffer.from(svg)).png().toBuffer()).toString("base64");
}

process.chdir(require("path").join(__dirname, "deck_assets"));
(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9"; // 10 x 5.625
  pres.title = "Hurricane to Harvest - FarmFit";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  pres.defineSlideMaster({
    title: "INK", background: { color: HEX.dk1 },
    objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.55, y: 1.0, w: 4.6, h: 1.6, fontSize: 46, bold: true,
      color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } }],
  });
  pres.defineSlideMaster({
    title: "PAPER", background: { color: HEX.lt1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.25, w: 9.0, h: 0.7, fontSize: 26, bold: true,
        color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
      { line: { x: 0.5, y: 0.98, w: 9.0, h: 0, line: { color: HEX.dk1, width: 1.25 } } },
      { text: { text: "FarmFit · Hurricane to Harvest · NASA Space Apps 2026 · Field Shift", options: { x: 0.5, y: 5.27, w: 6.5, h: 0.22, fontSize: 9, color: HEX.dk2, margin: 0 } } },
    ],
    slideNumber: { x: 9.1, y: 5.27, w: 0.4, h: 0.22, fontSize: 9, color: HEX.dk2 },
  });

  const I = {
    seed: await icon(fa.FaSeedling, "FFFFFF"), globe: await icon(fa.FaGlobeAmericas, "FFFFFF"), check: await icon(fa.FaUserCheck, "FFFFFF"),
    storm: await icon(gi.GiTornado, HEX.accent2),
  };
  const card = (s, x, y, w, h, name, fill = C.background2, line) =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.1, fill: { color: fill }, line: { color: line || fill, width: 1 }, objectName: name });
  const kicker = (s, text, x, y, w, color = C.accent1) =>
    s.addText(text, { x, y, w, h: 0.25, fontSize: 10, bold: true, color, charSpacing: 2, margin: 0, isTextBox: true });
  const pic = (s, path, x, y, w, pxW, pxH, name) => s.addImage({ path, x, y, w, h: w * pxH / pxW, objectName: name,
    shadow: { type: "outer", color: "1F2B3A", opacity: 0.25, blur: 8, offset: 3, angle: 90 } });

  // ---------------- 1. Title
  pres.addSection({ title: "Opening" });
  let s = pres.addSlide({ masterName: "INK", sectionTitle: "Opening" });
  kicker(s, "NASA SPACE APPS 2026 · FIELD SHIFT: ADAPTING FARMS WITH NASA DATA", 0.55, 0.55, 8.5, C.accent2);
  s.addText("Hurricane to Harvest", { placeholder: "title" });
  s.addText("A farm's year, read from the sky to the bedrock", { x: 0.55, y: 2.75, w: 4.4, h: 0.8, fontSize: 19, italic: true, color: "E9E1CF", fontFace: "Cambria", margin: 0, isTextBox: true });
  s.addText([
    { text: "FarmFit", options: { bold: true, color: "F3EEE3", breakLine: true } },
    { text: "Pick your farm. Scroll down through it: storms, planting, recovery, water, soil, evidence.", options: { color: "BCD5E1" } },
  ], { x: 0.55, y: 3.75, w: 4.3, h: 0.85, fontSize: 12, margin: 0, valign: "top", isTextBox: true });
  pic(s, "landing.jpg", 5.25, 0.95, 4.3, 1400, 974, "landing screenshot");
  s.addText("Demo farms: St Elizabeth, Jamaica · Caroni plains, Trinidad", { x: 5.25, y: 4.05, w: 4.3, h: 0.3, fontSize: 11, color: "BCD5E1", align: "center", margin: 0, isTextBox: true });
  s.addNotes("Hurricane to Harvest is FarmFit rebuilt as one journey. A farmer picks their farm and scrolls from the sky above it to the rock beneath it. Every layer answers one question with open NASA and partner data: what storms do here, what to plant when, how to recover, whether the field is heading into drought, and what the soil is like.");

  // ---------------- 2. Problem
  pres.addSection({ title: "Problem" });
  s = pres.addSlide({ masterName: "PAPER", sectionTitle: "Problem" });
  s.addText("One storm erases a season. Then prices fall.", { placeholder: "title" });
  const stats = [["32,400 ha", "of vegetables lost to Hurricane Melissa, 28 Oct 2025"], ["47,500", "vegetable farmers affected in Jamaica"],
                 ["Jan 2026", "prices fell sharply as everyone replanted the same fast crops"]];
  stats.forEach(([n, l], i) => {
    const y = 1.2 + i * 1.18;
    s.addText(n, { x: 0.5, y, w: 4.0, h: 0.62, fontSize: 38, bold: true, color: C.accent1, fontFace: "Cambria", margin: 0, isTextBox: true });
    s.addText(l, { x: 0.5, y: y + 0.6, w: 4.1, h: 0.4, fontSize: 13, color: C.text1, margin: 0, isTextBox: true });
  });
  s.addText("Jamaica Ministry of Agriculture, Fisheries and Mining (Nov 2025, Jan 2026)", { x: 0.5, y: 4.85, w: 4.3, h: 0.25, fontSize: 9, color: C.text2, margin: 0, isTextBox: true });
  card(s, 4.95, 1.2, 4.55, 3.85, "problem card", C.background2);
  s.addText("And the dry season is the quieter half", { x: 5.2, y: 1.35, w: 4.1, h: 0.45, fontSize: 17, bold: true, color: C.text1, fontFace: "Cambria", margin: 0, isTextBox: true });
  s.addText([
    { text: "A strong El Niño is under way (NOAA ONI +2.5 °C).", options: { bullet: true, breakLine: true } },
    { text: "At the Caroni farm, El Niño years brought only 64% of normal Dec-Feb rain (30 years of NASA POWER).", options: { bullet: true, breakLine: true } },
    { text: "At St Elizabeth, storm-force wind arrives about 1 year in 4, mostly Aug to Oct (NOAA HURDAT2).", options: { bullet: true, breakLine: true } },
    { text: "Calendars were set for an older climate. Farmers need to know which crop belongs in which month, on their own farm.", options: { bullet: true } },
  ], { x: 5.2, y: 1.9, w: 4.1, h: 3.0, fontSize: 13, color: C.text1, paraSpaceAfter: 8, valign: "top", margin: 0, isTextBox: true });
  s.addNotes("Melissa made landfall as a Category 5 and hit Jamaica's breadbasket. The Ministry counted about 32,400 hectares of vegetables and 47,500 farmers. Three months later prices fell sharply because so many farmers replanted the same fast crops. And storms are only half of it: a strong El Niño is under way, and at our Trinidad farm El Niño years brought only two-thirds of normal dry-season rain.");

  // ---------------- 3. The journey
  pres.addSection({ title: "Journey" });
  s = pres.addSlide({ masterName: "PAPER", sectionTitle: "Journey" });
  s.addText("One scroll, from the sky to the bedrock", { placeholder: "title" });
  s.addImage({ path: "world.png", x: 0.5, y: 1.12, w: 1.0, h: 4.05, objectName: "world strip", sizing: { type: "cover", w: 1.0, h: 4.05 } });
  const layers = [
    [1.15, "Storms", "Live NOAA storm watch, checklist, alerts, exposure, replay a real storm"],
    [1.72, "Plant", "Your rotation vs three better ones; the planting-window orchard"],
    [2.38, "Recover", "Photo check, IMERG rain, flood maps, staged path back, insurance"],
    [3.02, "Water", "SMAP, MODIS plant stress, IMERG, El Niño test, water bank"],
    [3.68, "Soil & ask", "Texture, drainage, pH, slope; soil probe; Ask FarmFit"],
    [4.45, "Evidence", "Every dataset, method and limit"],
  ];
  layers.forEach(([y, t, d]) => {
    s.addShape(pres.shapes.LINE, { x: 1.5, y: y + 0.13, w: 0.22, h: 0, line: { color: HEX.dk1, width: 1 }, objectName: t + " tick" });
    s.addText(t, { x: 1.78, y, w: 1.25, h: 0.28, fontSize: 13, bold: true, color: C.accent1, fontFace: "Cambria", margin: 0, isTextBox: true });
    s.addText(d, { x: 1.78, y: y + 0.25, w: 3.0, h: 0.35, fontSize: 10, color: C.text1, margin: 0, isTextBox: true });
  });
  pic(s, "intro.jpg", 5.0, 1.2, 4.5, 1400, 681, "intro screenshot");
  s.addText([
    { text: "The farmer picks their farm first. ", options: { bold: true } },
    { text: "A hand-drawn world slides behind the page as they scroll, so each tool sits in its layer of the farm. A tree on the side comes alive as they go: canopy above ground, roots below. Short story beats carry them from one layer to the next." },
  ], { x: 5.0, y: 3.55, w: 4.5, h: 1.5, fontSize: 12, color: C.text1, valign: "top", margin: 0, isTextBox: true });
  s.addNotes("This is the interface. There are no tabs. The farmer picks a farm, then scrolls down through it. The background moves from sky to field to topsoil, clay, the water table and bedrock, and each tool sits in its own layer. A living tree on the side fills in as they go and doubles as navigation. The opening line is specific to the farm: on 28 October 2025, Melissa reached this field with about 95 knots of wind.");

  // ---------------- 4. The field decides
  pres.addSection({ title: "Field" });
  s = pres.addSlide({ masterName: "PAPER", sectionTitle: "Field" });
  s.addText("When the sky clears, the field decides", { placeholder: "title" });
  pic(s, "calendar.jpg", 0.5, 1.2, 5.6, 1600, 355, "calendar screenshot");
  pic(s, "orchard.jpg", 0.5, 2.62, 5.6, 1600, 515, "orchard screenshot");
  s.addText([
    { text: "241,772 rotations searched", options: { bold: true, color: HEX.accent1, breakLine: true } },
    { text: "for this farm; the best Storm-smart, Soil builder and Water saver plans shown beside the farmer's own.", options: { breakLine: true } },
    { text: " ", options: { fontSize: 6, breakLine: true } },
    { text: "Each plan says why", options: { bold: true, color: HEX.accent1, breakLine: true } },
    { text: "evidence, benefits, pest-cycle breaks, livestock feed, market timing (NAMDEVCO prices), information gaps, and what to check with an extension officer.", options: { breakLine: true } },
    { text: " ", options: { fontSize: 6, breakLine: true } },
    { text: "The orchard", options: { bold: true, color: HEX.accent1, breakLine: true } },
    { text: "one tree per planting month. Blossom and fruit show the chance of a good harvest: 4,000 simulated seasons of storm and flood × climate fit × water. Capped at 95%+." },
  ], { x: 6.35, y: 1.2, w: 3.15, h: 3.95, fontSize: 11.5, color: C.text1, valign: "top", margin: 0, isTextBox: true });
  s.addNotes("This is the decision layer. FarmFit searches every 12-month rotation of up to four crops, about 240,000 for this farm, and shows the best three beside the farmer's own. The striped and outlined months are where Melissa would have hit. The orchard answers a simpler question: if I plant sweet peppers, which month? January is best, July riskiest, because a July planting is in the field through the storm peak. We cap at 95% because the model leaves out pests, prices and luck.");

  // ---------------- 5. Data
  pres.addSection({ title: "Data" });
  s = pres.addSlide({ masterName: "PAPER", sectionTitle: "Data" });
  s.addText("Eight NASA datasets, plus partner and local data", { placeholder: "title" });
  const nasa = [
    ["NASA POWER", "30 yr daily rain, heat, wind, soil wetness", "≈ 55 km"],
    ["GPM IMERG V07", "Daily rain at the farm, storm windows", "0.1°"],
    ["SMAP L3", "Surface soil moisture", "9 km"],
    ["SMAP L4", "Root-zone moisture, top 1 m", "9 km"],
    ["MODIS NDVI", "How green the crops are", "250 m"],
    ["MODIS ET / PET", "Plant water stress (ET ÷ PET)", "500 m"],
    ["NASA SRTM", "Elevation, slope, erosion", "30 m"],
    ["MODIS flood · OPERA", "Where flood water stood", "250 / 30 m"],
  ];
  nasa.forEach(([n, u, r], i) => {
    const col = i % 2, row = Math.floor(i / 2), x = 0.5 + col * 2.95, y = 1.18 + row * 0.82;
    card(s, x, y, 2.8, 0.72, "nasa " + n, "DCE8EE");
    s.addText(n, { x: x + 0.12, y: y + 0.06, w: 1.85, h: 0.28, fontSize: 12.5, bold: true, color: C.text1, margin: 0, isTextBox: true });
    s.addText(r, { x: x + 1.9, y: y + 0.06, w: 0.78, h: 0.28, fontSize: 9.5, bold: true, color: C.accent4, align: "right", margin: 0, isTextBox: true });
    s.addText(u, { x: x + 0.12, y: y + 0.36, w: 2.6, h: 0.3, fontSize: 10, color: C.text2, margin: 0, isTextBox: true });
  });
  card(s, 6.5, 1.18, 3.0, 3.2, "partner card", HEX.dk1);
  s.addText("Partner and local", { x: 6.65, y: 1.3, w: 2.7, h: 0.32, fontSize: 14, bold: true, color: C.accent2, margin: 0, isTextBox: true });
  s.addText([
    { text: "NOAA HURDAT2, IBTrACS, live NHC storms", options: { bullet: true, breakLine: true } },
    { text: "NOAA ENSO index (season ahead)", options: { bullet: true, breakLine: true } },
    { text: "ISRIC SoilGrids; FAO ECOCROP, FAO-56", options: { bullet: true, breakLine: true } },
    { text: "NAMDEVCO wholesale prices (TT open data)", options: { bullet: true, breakLine: true } },
    { text: "CIMH drought bulletin; CCRIF micro-insurance; RADA", options: { bullet: true } },
  ], { x: 6.65, y: 1.7, w: 2.75, h: 2.6, fontSize: 11, color: C.background1, paraSpaceAfter: 5, valign: "top", margin: 0, isTextBox: true });
  card(s, 0.5, 4.5, 9.0, 0.62, "pipeline", C.background2);
  s.addText([
    { text: "Kept live: ", options: { bold: true, color: HEX.accent1 } },
    { text: "GitHub Actions refreshes the data daily in hurricane season and twice a week otherwise (Earthdata login, AppEEARS tasks carried between runs); storm alerts every 3 hours. A data passport shows each dataset's resolution and freshness." },
  ], { x: 0.65, y: 4.55, w: 8.7, h: 0.52, fontSize: 11, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
  s.addNotes("Blue cards are NASA. POWER gives 30 years of daily climate. IMERG, SMAP surface and root zone, MODIS greenness and evapotranspiration come through the scheduled refresh with an Earthdata login; flood maps come live from GIBS. Partner and local data add the storms, the El Niño index, soils, crop science, Trinidad wholesale prices, the regional drought bulletin and insurance.");

  // ---------------- 6. Results
  pres.addSection({ title: "Results" });
  s = pres.addSlide({ masterName: "PAPER", sectionTitle: "Results" });
  s.addText("What the data says, farm by farm", { placeholder: "title" });
  kicker(s, "ST ELIZABETH, JAMAICA · REPLAYING MELISSA", 0.5, 1.12, 4.4);
  pic(s, "replay.jpg", 0.5, 1.42, 4.35, 1600, 480, "replay screenshot");
  s.addText("On 28 Oct 2025 the farm's usual rotation had sweet peppers mid-season: an estimated 60% loss. The Storm-smart and Soil builder calendars had harvested earlier and had a cover crop holding the soil.",
    { x: 0.5, y: 2.85, w: 4.35, h: 1.0, fontSize: 11.5, color: C.text1, valign: "top", margin: 0, isTextBox: true });
  s.addText("Wind at the farm from NOAA tracks with a modified Rankine vortex: an exposure screen, not a forecast.", { x: 0.5, y: 3.9, w: 4.35, h: 0.45, fontSize: 9.5, italic: true, color: C.text2, margin: 0, isTextBox: true });
  kicker(s, "CARONI PLAINS, TRINIDAD · THE SEASON AHEAD", 5.15, 1.12, 4.4, C.accent4);
  pic(s, "enso.jpg", 5.15, 1.42, 4.35, 1600, 977, "enso screenshot");
  s.addText("SMAP: driest of 4 Novembers on record (0.43 vs usual 0.51 m³/m³). MODIS: plants using 0.58 of the water they could.",
    { x: 5.15, y: 4.2, w: 4.35, h: 0.6, fontSize: 10.5, color: C.text1, valign: "top", margin: 0, isTextBox: true });
  s.addNotes("Two farms, two hazards. In Jamaica, replaying Melissa: the usual rotation loses about 60%; the storm-smart calendar loses almost nothing because the harvest is in and a cover crop holds the soil. In Trinidad, the risk is drought: El Niño years brought 64% of normal Dec-Feb rain, this year is a strong El Niño, SMAP has the driest November in its short record, and MODIS shows plants already short of water. So the advice is: bank water and favour drought-tolerant crops.");

  // ---------------- 7. Impact
  pres.addSection({ title: "Impact" });
  s = pres.addSlide({ masterName: "INK", sectionTitle: "Impact" });
  s.addText("Ready before the storm, back faster after it", { x: 0.55, y: 0.4, w: 8.9, h: 0.7, fontSize: 28, bold: true, color: C.background1, fontFace: "Cambria", margin: 0, isTextBox: true });
  const cols = [
    [I.seed, "Farmers", ["Plans that keep fragile stages out of the storm peak", "Phone alerts, printable almanac, WhatsApp, offline text", "English, Español, Français, Kreyòl"]],
    [I.globe, "Region", ["Glut warning: stagger replanting after storms", "Parametric micro-insurance explained with the farm's own storm odds", "Advice that reaches farms an extension officer can't visit this week"]],
    [I.check, "Next", ["Validate crop values with CARDI, RADA and extension officers", "Soil-probe network to check SMAP on the ground", "Typhoon and cyclone coasts via NOAA IBTrACS"]],
  ];
  cols.forEach(([ic, t, items], i) => {
    const x = 0.55 + i * 3.0;
    card(s, x, 1.35, 2.8, 3.15, "impact " + t, "2C3B4E");
    s.addShape(pres.shapes.OVAL, { x: x + 0.2, y: 1.52, w: 0.5, h: 0.5, fill: { color: [HEX.accent3, HEX.accent4, HEX.accent1][i] }, line: { color: [HEX.accent3, HEX.accent4, HEX.accent1][i] }, objectName: t + " circle" });
    s.addImage({ data: ic, x: x + 0.31, y: 1.63, w: 0.28, h: 0.28, objectName: t + " icon" });
    s.addText(t, { x: x + 0.8, y: 1.57, w: 1.8, h: 0.4, fontSize: 18, bold: true, color: C.accent2, fontFace: "Cambria", margin: 0, isTextBox: true });
    s.addText(items.map((it, k) => ({ text: it, options: { bullet: true, breakLine: k < items.length - 1 } })),
      { x: x + 0.2, y: 2.2, w: 2.45, h: 2.2, fontSize: 12, color: C.background1, paraSpaceAfter: 6, valign: "top", margin: 0, isTextBox: true });
  });
  s.addText("Live app: [add Streamlit URL]   ·   Code: github.com/keydahknow/FarmFit   ·   Supports farmers' judgment; never replaces it.", { x: 0.55, y: 4.75, w: 8.9, h: 0.3, fontSize: 11, color: "BCD5E1", margin: 0, isTextBox: true });
  s.addNotes("For farmers, the point is preparedness: the right crop in the ground before the storm, and a safe path back after it, in their language, on paper or on their phone. For the region, FarmFit warns about the glut that follows a storm and explains parametric insurance using the farm's own storm odds. Next we validate the crop values with CARDI and extension officers, ground-truth SMAP with cheap soil probes, and take the same engine to typhoon and cyclone coasts.");

  await pres.writeFile({ fileName: "../FarmFit_Hurricane_to_Harvest.pptx" });
  await applyTheme("../FarmFit_Hurricane_to_Harvest.pptx", THEME);
  console.log("written");
})();
