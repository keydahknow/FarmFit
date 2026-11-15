"""Visual identity: a farmer's almanac redrawn with satellite data.

Risograph-style flat inks on paper, hand-drawn (wobbly) line art, an
expressive serif for headings (Fraunces) and Inter for text. All artwork
is inline SVG drawn in code, so it is crisp at any size and needs no
image files.
"""

import altair as alt

PAPER = "#F3EEE3"
PAPER2 = "#E9E1CF"
INK = "#1F2B3A"
INK2 = "#4C5563"
TERRA = "#C2502F"
OCHRE = "#D99A2B"
LEAF = "#3F7A4C"
SEA = "#3F7EA0"
SKY = "#BCD5E1"
CLAY = "#9A6B43"

FONT_CSS = """
@font-face{font-family:'Fraunces';src:url('app/static/fonts/Fraunces.ttf') format('truetype');font-weight:100 900;font-display:swap}
@font-face{font-family:'Fraunces';src:url('app/static/fonts/Fraunces-Italic.ttf') format('truetype');font-style:italic;font-weight:100 900;font-display:swap}
@font-face{font-family:'InterVar';src:url('app/static/fonts/Inter.ttf') format('truetype');font-weight:100 900;font-display:swap}
"""

CSS = f"""
<style>
{FONT_CSS}
:root{{--paper:{PAPER};--paper2:{PAPER2};--ink:{INK};--ink2:{INK2};--terra:{TERRA};--ochre:{OCHRE};--leaf:{LEAF};--sea:{SEA};--clay:{CLAY}}}
html, body, [data-testid="stAppViewContainer"], .stApp{{background:var(--paper)}}
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button, .stMarkdown{{font-family:'InterVar',Inter,system-ui,sans-serif}}
.stApp h1,.stApp h2,.stApp h3,.stApp h4{{font-family:'Fraunces',Georgia,serif !important;color:var(--ink);letter-spacing:-.01em;font-weight:600}}
[data-testid="stHeader"], [data-testid="stToolbar"], footer, #MainMenu{{display:none !important}}
.block-container{{padding-top:1.2rem !important;max-width:1180px}}
.stApp [data-testid="stVerticalBlockBorderWrapper"]{{border-color:rgba(31,43,58,.14) !important;border-radius:6px !important;background:rgba(255,255,255,.35)}}

/* masthead */
.al-mast{{display:grid;grid-template-columns:1.05fr 1fr;gap:1.5rem;align-items:end;border-bottom:2px solid var(--ink);padding-bottom:.6rem;margin-bottom:.9rem}}
.al-kicker{{font:600 .72rem/1.2 'InterVar',sans-serif;letter-spacing:.16em;text-transform:uppercase;color:var(--terra)}}
.al-title{{font:600 3.1rem/0.95 'Fraunces',serif;color:var(--ink);margin:.35rem 0 .45rem 0;font-variation-settings:'SOFT' 100,'WONK' 1}}
.al-dek{{font:italic 400 1.12rem/1.4 'Fraunces',serif;color:var(--ink2);max-width:34rem}}
.al-art svg{{width:100%;height:auto;display:block}}
.al-farm{{font:500 .85rem 'InterVar',sans-serif;color:var(--ink2)}}

/* section headers */
.al-sec{{display:flex;gap:.8rem;align-items:flex-start;margin:.4rem 0 .9rem 0}}
.al-sec svg{{flex:0 0 46px;height:46px}}
.al-sec h2{{margin:0 !important;padding:0 !important;font-size:1.75rem !important}}
.al-sec p{{margin:.15rem 0 0 0;color:var(--ink2);font-size:.95rem;max-width:46rem}}
.al-h{{font:600 1.15rem 'Fraunces',serif;color:var(--ink);margin:1.3rem 0 .4rem 0;border-top:1px solid rgba(31,43,58,.25);padding-top:.7rem}}
.al-note{{font-size:.8rem;color:var(--ink2);margin-top:.35rem}}
.al-rule{{border:none;border-top:1px dashed rgba(31,43,58,.3);margin:1rem 0}}

/* figures */
.al-figs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:0;border-top:1px solid var(--ink);border-bottom:1px solid var(--ink);margin:.4rem 0 1rem 0}}
.al-fig{{padding:.7rem .9rem;border-right:1px solid rgba(31,43,58,.18)}}
.al-fig:last-child{{border-right:none}}
.al-fig .n{{font:600 1.9rem/1.05 'Fraunces',serif;color:var(--ink);font-variant-numeric:lining-nums}}
.al-fig .l{{font:600 .68rem 'InterVar',sans-serif;letter-spacing:.12em;text-transform:uppercase;color:var(--ink2);margin-bottom:.25rem}}
.al-fig .s{{font-size:.8rem;color:var(--ink2);margin-top:.2rem}}
.al-fig.terra .n{{color:var(--terra)}} .al-fig.sea .n{{color:var(--sea)}} .al-fig.leaf .n{{color:var(--leaf)}}

/* status stamp */
.al-stamp{{display:inline-block;font:700 .72rem 'InterVar',sans-serif;letter-spacing:.12em;text-transform:uppercase;padding:.25rem .55rem;border:2px solid currentColor;border-radius:3px;transform:rotate(-1.5deg)}}
.al-stamp.dry2{{color:#9b2f17}} .al-stamp.dry1{{color:var(--terra)}} .al-stamp.normal{{color:var(--leaf)}} .al-stamp.wet1{{color:var(--sea)}} .al-stamp.wet2{{color:#1f4f6e}}
.al-stamp.act{{color:#9b2f17}} .al-stamp.ready{{color:var(--ochre)}} .al-stamp.calm{{color:var(--leaf)}}

/* almanac calendar */
.al-cal{{display:grid;grid-template-columns:160px repeat(12,1fr);column-gap:3px;row-gap:5px;align-items:end;margin:.3rem 0 .2rem 0}}
.al-cal .mh{{font:600 .66rem 'InterVar',sans-serif;letter-spacing:.1em;text-transform:uppercase;color:var(--ink2);text-align:center;position:relative}}
.al-cal .mh.hit{{color:var(--terra)}}
.al-cal .rl{{font:500 .9rem 'Fraunces',serif;color:var(--ink);align-self:center;line-height:1.1}}
.al-cal .rl small{{display:block;font:500 .66rem 'InterVar',sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--ink2)}}
.al-cal .risk{{height:34px;display:flex;flex-direction:column;justify-content:flex-end;border-bottom:1px solid var(--ink)}}
.al-cal .risk i{{display:block;width:62%;margin:0 auto}}
.al-cal .seg{{height:38px;border:1.4px solid var(--ink);border-radius:2px;display:flex;align-items:center;padding:0 .45rem;font:600 .74rem 'InterVar',sans-serif;color:var(--ink);overflow:hidden;white-space:nowrap;text-overflow:ellipsis;min-width:0}}
.al-cal .seg.hit{{box-shadow:inset 0 0 0 2px var(--terra);outline:2px dashed var(--terra);outline-offset:2px}}
.al-cal .bare{{height:38px;border:1px dashed rgba(31,43,58,.35);border-radius:2px;background:transparent}}
.al-cal .bare.hit{{outline:2px dashed var(--terra);outline-offset:2px}}
.al-key{{display:flex;gap:1.1rem;flex-wrap:wrap;font-size:.75rem;color:var(--ink2);margin:.35rem 0 0 160px}}
.al-key span{{display:inline-flex;align-items:center;gap:.35rem}}
.al-key b{{display:inline-block;width:14px;height:10px;border:1px solid var(--ink)}}

/* strategy cards */
.al-card{{border:1.4px solid var(--ink);border-radius:3px;padding:.85rem .95rem;background:rgba(255,255,255,.45);height:100%}}
.al-card.best{{background:#fff8e6;box-shadow:4px 4px 0 var(--ochre)}}
.al-card h4{{margin:0 0 .15rem 0 !important;font-size:1.15rem !important}}
.al-card .tag{{font:600 .64rem 'InterVar',sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--terra)}}
.al-card .dek{{font:italic .86rem/1.35 'Fraunces',serif;color:var(--ink2);margin:.25rem 0 .6rem 0}}
.al-meter{{display:grid;grid-template-columns:118px 1fr 26px;align-items:center;gap:.4rem;font-size:.74rem;color:var(--ink2);margin:.18rem 0}}
.al-meter .t{{height:6px;background:rgba(31,43,58,.1);position:relative}}
.al-meter .t i{{position:absolute;left:0;top:0;bottom:0}}
.al-meter b{{color:var(--ink);text-align:right;font-weight:600}}
.al-facts{{font-size:.78rem;color:var(--ink2);border-top:1px dashed rgba(31,43,58,.3);margin-top:.55rem;padding-top:.45rem;line-height:1.5}}
.al-facts b{{color:var(--ink)}}

/* checklists and stages */
.al-list{{list-style:none;padding:0;margin:.3rem 0}}
.al-list li{{display:grid;grid-template-columns:22px 1fr;gap:.5rem;padding:.42rem 0;border-bottom:1px dashed rgba(31,43,58,.22);font-size:.92rem}}
.al-list li:before{{content:'';width:14px;height:14px;border:1.6px solid var(--ink);border-radius:2px;margin-top:.15rem}}
.al-stage{{border-top:3px solid var(--ink);padding-top:.5rem}}
.al-stage .w{{font:600 .66rem 'InterVar',sans-serif;letter-spacing:.12em;text-transform:uppercase;color:var(--terra)}}
.al-stage h4{{margin:.1rem 0 .3rem 0 !important;font-size:1.1rem !important}}
.al-stage ul{{padding-left:1rem;font-size:.84rem;color:var(--ink)}}
.al-stage .gate{{font:italic .82rem 'Fraunces',serif;color:var(--leaf)}}
.al-storm{{border:1.4px solid var(--ink);border-radius:3px;padding:.8rem 1rem;background:rgba(255,255,255,.45);margin-bottom:.6rem}}

/* widgets */
.stButton>button, .stDownloadButton>button, .stLinkButton>a{{border-radius:3px !important;border:1.4px solid var(--ink) !important;font-weight:600 !important}}
.stButton>button[kind="primary"]{{background:var(--ink) !important;color:var(--paper) !important}}
[data-testid="stSegmentedControl"] button, [data-testid="stBaseButton-segmented_control"], [data-testid="stBaseButton-segmented_controlActive"]{{font-family:'Fraunces',serif !important;font-size:1rem !important;border-radius:2px !important}}
button[data-variant="segmented_control"]{{font-family:'Fraunces',serif !important;border-radius:2px !important;border-color:rgba(31,43,58,.35) !important}}
button[data-variant="segmented_control"] p{{font-family:'Fraunces',serif !important;font-size:1rem !important}}
button[data-variant="segmented_control"][aria-checked="true"]{{background:var(--ink) !important;border-color:var(--ink) !important}}
button[data-variant="segmented_control"][aria-checked="true"] p{{color:var(--paper) !important}}
[data-testid="stExpander"] details{{border-radius:3px !important;border-color:rgba(31,43,58,.25) !important;background:transparent}}
[data-testid="stExpander"] summary p{{font-family:'Fraunces',serif !important;font-size:1rem !important}}
[data-testid="stDataFrame"]{{border:1px solid rgba(31,43,58,.2);border-radius:3px}}
@media (max-width: 800px){{.al-mast{{grid-template-columns:1fr}} .al-title{{font-size:2.3rem}} .al-cal{{grid-template-columns:96px repeat(12,1fr)}} .al-key{{margin-left:0}}}}
</style>
"""

# --- SVG building blocks ----------------------------------------------------

_FILTERS = """
<defs>
  <filter id="wob" x="-5%" y="-5%" width="110%" height="110%">
    <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="3.2"/>
  </filter>
  <filter id="grain" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="3" result="t"/>
    <feColorMatrix in="t" type="matrix" values="0 0 0 0 0.12  0 0 0 0 0.16  0 0 0 0 0.22  0 0 0 0.55 -0.18"/>
    <feComposite in2="SourceGraphic" operator="in"/>
  </filter>
  <pattern id="rows" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(-12)">
    <line x1="0" y1="0" x2="0" y2="9" stroke="#1F2B3A" stroke-width="1.3" opacity=".45"/>
  </pattern>
  <pattern id="dots" width="7" height="7" patternUnits="userSpaceOnUse">
    <circle cx="2" cy="2" r="1" fill="#1F2B3A" opacity=".4"/>
  </pattern>
  <pattern id="rain" width="14" height="22" patternUnits="userSpaceOnUse" patternTransform="rotate(14)">
    <line x1="4" y1="0" x2="4" y2="9" stroke="#3F7EA0" stroke-width="2" stroke-linecap="round"/>
  </pattern>
</defs>
"""


def masthead_art():
    """Landscape: plantain, ridged field, rain cloud, hurricane glyph, satellite on its orbit."""
    return f"""
<svg viewBox="0 0 640 250" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Hand-drawn farm under a passing storm, watched by a satellite">
{_FILTERS}
<g filter="url(#wob)">
  <rect x="0" y="0" width="640" height="250" fill="{SKY}" opacity=".55"/>
  <path d="M40 40 Q320 -30 610 70" fill="none" stroke="{INK}" stroke-width="1.4" stroke-dasharray="3 6"/>
  <g transform="translate(470,34) rotate(18)">
    <rect x="-7" y="-5" width="14" height="10" fill="{OCHRE}" stroke="{INK}" stroke-width="1.5"/>
    <rect x="-27" y="-3" width="17" height="6" fill="{SEA}" stroke="{INK}" stroke-width="1.2"/>
    <rect x="10" y="-3" width="17" height="6" fill="{SEA}" stroke="{INK}" stroke-width="1.2"/>
    <path d="M0 5 L-6 22 L6 22 Z" fill="{OCHRE}" opacity=".35"/>
  </g>
  <g transform="translate(560,92)">
    <circle r="11" fill="none" stroke="{TERRA}" stroke-width="4"/>
    <path d="M0 -11 C 16 -30, 40 -22, 46 -8" fill="none" stroke="{TERRA}" stroke-width="5" stroke-linecap="round"/>
    <path d="M0 11 C -16 30, -40 22, -46 8" fill="none" stroke="{TERRA}" stroke-width="5" stroke-linecap="round"/>
  </g>
  <g transform="translate(120,58)">
    <path d="M-60 22 Q-62 -2 -36 0 Q-30 -22 -6 -16 Q8 -34 30 -18 Q56 -20 56 6 Q72 10 64 24 Z" fill="#fff" stroke="{INK}" stroke-width="1.6"/>
    <rect x="-52" y="26" width="112" height="56" fill="url(#rain)"/>
  </g>
  <path d="M0 168 Q140 120 300 150 T640 132 L640 250 L0 250 Z" fill="{LEAF}" opacity=".9"/>
  <path d="M0 196 Q170 150 360 180 T640 172 L640 250 L0 250 Z" fill="{OCHRE}"/>
  <path d="M0 196 Q170 150 360 180 T640 172 L640 250 L0 250 Z" fill="url(#rows)"/>
  <path d="M0 226 Q200 204 420 222 T640 214 L640 250 L0 250 Z" fill="{CLAY}"/>
  <path d="M0 226 Q200 204 420 222 T640 214 L640 250 L0 250 Z" fill="url(#dots)"/>
  <g transform="translate(96,214)" stroke="{INK}" stroke-width="1.5">
    <path d="M0 0 L3 -78" stroke-width="7" stroke="{CLAY}"/>
    <path d="M3 -74 C -30 -96 -64 -90 -78 -70 C -48 -70 -24 -68 3 -70 Z" fill="{LEAF}"/>
    <path d="M3 -76 C 26 -110 62 -112 78 -94 C 50 -88 26 -82 3 -74 Z" fill="#5E9A62"/>
    <path d="M2 -78 C -6 -116 6 -138 22 -146 C 22 -120 14 -98 4 -78 Z" fill="{LEAF}"/>
    <path d="M3 -60 C 26 -60 46 -46 54 -30 C 32 -34 16 -42 3 -54 Z" fill="#5E9A62"/>
  </g>
  <g fill="{INK}">
    <path d="M250 184 l0 -16 m0 4 l-6 -4 m6 4 l6 -6" stroke="{INK}" stroke-width="1.4" fill="none"/>
    <path d="M300 186 l0 -18 m0 5 l-7 -5 m7 5 l7 -7" stroke="{INK}" stroke-width="1.4" fill="none"/>
    <path d="M350 188 l0 -16 m0 4 l-6 -4 m6 4 l6 -6" stroke="{INK}" stroke-width="1.4" fill="none"/>
    <path d="M400 186 l0 -18 m0 5 l-7 -5 m7 5 l7 -7" stroke="{INK}" stroke-width="1.4" fill="none"/>
  </g>
</g>
<rect x="0" y="0" width="640" height="250" filter="url(#grain)" opacity=".5"/>
</svg>"""


def _icon(body, color=INK):
    return (f'<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
            f'<defs><filter id="iw"><feTurbulence type="fractalNoise" baseFrequency="0.06" numOctaves="1" seed="2"/>'
            f'<feDisplacementMap in="SourceGraphic" scale="1.6"/></filter></defs>'
            f'<g filter="url(#iw)" fill="none" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
            f'<circle cx="24" cy="24" r="21" fill="{PAPER2}" stroke="{INK}" stroke-width="1.6"/>{body}</g></svg>')


ICONS = {
    "plan": _icon(f'<path d="M12 34 h24"/><path d="M24 34 V20"/><path d="M24 24 C 16 24 13 18 14 13 C 20 13 24 17 24 24 Z" fill="{LEAF}"/>'
                  f'<path d="M24 21 C 31 21 35 16 34 11 C 28 11 24 15 24 21 Z" fill="#5E9A62"/>'),
    "water": _icon(f'<path d="M24 11 C 18 20 14 25 14 30 A10 10 0 0 0 34 30 C 34 25 30 20 24 11 Z" fill="{SEA}"/>'
                   f'<path d="M19 30 A5 5 0 0 0 23 35" stroke="#fff"/>'),
    "storm": _icon(f'<circle cx="24" cy="24" r="4" stroke="{TERRA}" stroke-width="3"/>'
                   f'<path d="M24 20 C 30 12 38 14 38 20" stroke="{TERRA}" stroke-width="3.2"/>'
                   f'<path d="M24 28 C 18 36 10 34 10 28" stroke="{TERRA}" stroke-width="3.2"/>'),
    "after": _icon(f'<path d="M14 34 h20"/><path d="M20 34 L17 20 L23 26"/><path d="M28 34 V24"/>'
                   f'<path d="M28 26 C 34 26 36 21 35 17 C 30 17 28 21 28 26 Z" fill="{LEAF}"/>'),
    "data": _icon(f'<path d="M14 15 h20 v20 h-20 z" fill="#fff"/><path d="M18 21 h12 M18 26 h12 M18 31 h7"/>'
                  f'<circle cx="34" cy="14" r="4" fill="{OCHRE}"/>'),
}


def section(icon, title, dek):
    return f'<div class="al-sec">{ICONS[icon]}<div><h2>{title}</h2><p>{dek}</p></div></div>'


def figures(items):
    """items: list of (label, number, sub, tone) -> almanac 'figures' strip."""
    cells = "".join(
        f'<div class="al-fig {tone or ""}"><div class="l">{label}</div><div class="n">{num}</div><div class="s">{sub}</div></div>'
        for label, num, sub, tone in items
    )
    return f'<div class="al-figs">{cells}</div>'


def stamp(text, key):
    return f'<span class="al-stamp {key}">{text}</span>'


def heading(text):
    return f'<div class="al-h">{text}</div>'


# --- chart theme ------------------------------------------------------------

def _theme():
    return {
        "config": {
            "background": "transparent",
            "font": "InterVar, Inter, sans-serif",
            "view": {"stroke": None},
            "title": {"font": "Fraunces, Georgia, serif", "fontSize": 15, "fontWeight": 600, "color": INK, "anchor": "start"},
            "axis": {"labelColor": INK2, "titleColor": INK2, "domainColor": INK, "tickColor": INK,
                     "gridColor": "rgba(31,43,58,0.08)", "labelFontSize": 11, "titleFontSize": 11, "titleFontWeight": 500},
            "axisX": {"grid": False, "labelAngle": 0},
            "legend": {"labelColor": INK2, "titleColor": INK2, "orient": "bottom", "labelFontSize": 11, "symbolType": "square"},
            "range": {"category": [TERRA, SEA, LEAF, OCHRE, CLAY, INK]},
            "bar": {"stroke": INK, "strokeWidth": 0.8},
            "line": {"strokeWidth": 2},
        }
    }


def register_chart_theme():
    try:
        alt.themes.register("almanac", _theme)
        alt.themes.enable("almanac")
    except Exception:  # noqa: BLE001 - newer Altair uses alt.theme
        try:
            @alt.theme.register("almanac", enable=True)
            def _t():
                return alt.theme.ThemeConfig(_theme())
        except Exception:  # noqa: BLE001
            pass


CROP_TEXTURE = {
    "Legume": "radial-gradient(rgba(31,43,58,.35) 1px, transparent 1.3px) 0 0/6px 6px",
    "Cereal": "repeating-linear-gradient(-55deg, rgba(31,43,58,.28) 0 1px, transparent 1px 6px)",
    "Root/tuber": "repeating-linear-gradient(0deg, rgba(31,43,58,.25) 0 1px, transparent 1px 6px)",
    "Cover crop": "repeating-linear-gradient(45deg, rgba(31,43,58,.22) 0 1px, transparent 1px 7px), repeating-linear-gradient(-45deg, rgba(31,43,58,.22) 0 1px, transparent 1px 7px)",
}
