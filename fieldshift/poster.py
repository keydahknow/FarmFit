"""One-page printable almanac for a farm (A4, portrait).

A self-contained HTML file: open it in any browser and print, or save as
PDF. It works offline once downloaded and carries the alert QR code, so
it can be pinned up in a shed or handed out by extension officers.
"""

from datetime import date
from html import escape

from . import art
from .i18n import month, t


def _month_notes(plan, site, crops, lang):
    occ = plan.occupancy()
    notes = []
    starts = {p.start: p.crop for p in plan.plantings}
    ends = {p.month_list()[-1]: p.crop for p in plan.plantings}
    risk = site.p_hu + site.p_ts
    for m in range(1, 13):
        bits = []
        if m in starts:
            bits.append(f"Plant <b>{escape(starts[m])}</b>")
        if m in ends and crops.loc[ends[m]].harvest_value > 0:
            bits.append(f"Harvest <b>{escape(ends[m])}</b>")
        elif m in ends:
            bits.append(f"Cut or turn in <b>{escape(ends[m])}</b>")
        if occ[m - 1] is None:
            bits.append("Bare: sow a cover crop")
        if risk[m - 1] >= 0.05:
            bits.append(f"Storm watch ({risk[m - 1]:.0%} of years)")
        if site.p_flood[m - 1] >= 0.15:
            bits.append("Keep drains open")
        notes.append((month(m, lang), "; ".join(bits) or "Tend crops"))
    return notes


def build(farm_label, plan, current, site, crops, calendar_html, summary, steps, topic_url, qr, lang="en"):
    m = plan.metrics
    rows = "".join(f"<tr><th>{mo}</th><td>{txt}</td></tr>" for mo, txt in _month_notes(plan, site, crops, lang))
    checklist = "".join(f"<li>{escape(s)}</li>" for s in steps[:7])
    rp = summary.get("return_period_storm_force")
    year = date.today().year + (1 if date.today().month >= 10 else 0)
    return f"""<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8"><title>{escape(farm_label)} almanac {year}</title>
<style>
@page{{size:A4 portrait;margin:11mm}}
*{{box-sizing:border-box}}
:root{{--ink:{art.INK};--ink2:{art.INK2};--terra:{art.TERRA};--sea:{art.SEA};--leaf:{art.LEAF};--paper:{art.PAPER};--clay:{art.CLAY};--ochre:{art.OCHRE}}}
body{{margin:0;background:{art.PAPER};color:{art.INK};font:10.5pt/1.4 Georgia,'Times New Roman',serif}}
.sheet{{max-width:190mm;margin:0 auto;padding:6mm 0}}
.top{{display:grid;grid-template-columns:1fr 78mm;gap:6mm;align-items:end;border-bottom:2px solid {art.INK};padding-bottom:3mm}}
.k{{font:700 7.5pt Arial,sans-serif;letter-spacing:.16em;text-transform:uppercase;color:{art.TERRA}}}
h1{{font:700 26pt/1 Georgia,serif;margin:2mm 0}}
.sub{{font-style:italic;color:{art.INK2}}}
.figs{{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:1px solid {art.INK};margin:3mm 0}}
.figs div{{padding:2mm 3mm;border-right:1px solid #cfc6b4}} .figs div:last-child{{border:none}}
.figs b{{display:block;font-size:15pt}} .figs span{{font:7pt Arial,sans-serif;letter-spacing:.1em;text-transform:uppercase;color:{art.INK2}}}
h2{{font:700 12pt Georgia,serif;margin:4mm 0 1.5mm 0}}
.cal{{transform:scale(.92);transform-origin:left top;margin-bottom:-4mm}}
{art.CSS.replace('<style>', '').replace('</style>', '').split('/* strategy cards */')[0].split('/* almanac calendar */')[1]}
.cols{{display:grid;grid-template-columns:1.15fr 1fr;gap:6mm}}
table{{border-collapse:collapse;width:100%;font-size:8.6pt}}
th{{text-align:left;width:11mm;font:700 7.5pt Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;vertical-align:top;padding:1.1mm 0}}
td{{border-bottom:1px dotted #bdb3a0;padding:1.1mm 0}}
ul{{padding-left:4mm;margin:0;font-size:8.8pt}} li{{margin-bottom:1mm}}
.qr{{display:grid;grid-template-columns:30mm 1fr;gap:3mm;align-items:center;border:1.4px solid {art.INK};padding:2.5mm;margin-top:3mm}}
.qr svg{{width:30mm;height:30mm}}
.foot{{font:7.5pt Arial,sans-serif;color:{art.INK2};border-top:1px solid {art.INK};margin-top:4mm;padding-top:2mm}}
.print{{position:fixed;right:8mm;top:8mm;font:600 10pt Arial;padding:2mm 4mm;border:1.4px solid {art.INK};background:#fff;cursor:pointer}}
@media print{{.print{{display:none}} body{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style></head><body>
<button class="print" onclick="window.print()">Print / save as PDF</button>
<div class="sheet">
 <div class="top"><div><div class="k">FarmFit · Hurricane to Harvest · {year}</div>
   <h1>{escape(farm_label)}</h1><div class="sub">{t(plan.title, lang)} rotation: a farmer's almanac redrawn with NASA and NOAA data</div></div>
   <div>{art.masthead_art()}</div></div>
 <div class="figs">
   <div><span>Storm-force wind</span><b>{'1 in ' + format(rp, '.0f') + ' yrs' if rp else 'rare'}</b></div>
   <div><span>Riskiest months</span><b>{', '.join(summary.get('peak_months') or []) or '—'}</b></div>
   <div><span>Harvest at risk</span><b>{m['expected_loss']:.0%}</b><span>vs {current.metrics['expected_loss']:.0%} today</span></div>
   <div><span>Bare months</span><b>{m['bare_months']}</b><span>vs {current.metrics['bare_months']} today</span></div>
 </div>
 <h2>Your year</h2><div class="cal">{calendar_html}</div>
 <div class="cols">
  <div><h2>Month by month</h2><table>{rows}</table></div>
  <div><h2>When a storm is forecast</h2><ul>{checklist}</ul>
   <div class="qr">{qr}<div><b>Storm and drought alerts</b><br/>Install the free <b>ntfy</b> app and subscribe to:<br/>
   <span style="font:8pt monospace">{escape(topic_url)}</span></div></div></div>
 </div>
 <div class="foot">Data: NASA POWER (MERRA-2), NASA SMAP, GPM IMERG, MODIS, SRTM; NOAA HURDAT2 and NHC; ISRIC SoilGrids; FAO ECOCROP and FAO-56.
 Storm odds are history, not a forecast. Check plans with your extension officer. Printed {date.today():%d %b %Y}.</div>
</div></body></html>"""
