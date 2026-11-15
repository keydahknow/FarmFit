"""The scroll journey: from the sky above the farm down to the bedrock.

One continuous page. A fixed, very tall illustration (sky, field, topsoil,
clay and water table, bedrock) slides behind the content as the reader
scrolls, so every section sits in its own layer of the world. A living tree
on the left comes alive part by part: canopy for the sections above ground,
roots for the ones below. Small fruit trees show, month by month, the chance
that a planting turns into a good harvest.

All artwork is inline SVG drawn in code. One tiny script (in a zero-height
component) watches the scroll position and sets CSS variables on the page.
"""

import html
from urllib.parse import quote

import streamlit.components.v1 as components

from . import art

# Layers in reading order: key, title, where the background sits (viewBox
# units, 0 = top of the sky, 5000 = bedrock) when the layer starts and ends.
LAYERS = [
    ("sky", "Storms", 0, 700),
    ("field", "Plant", 1250, 1550),
    ("recover", "Recover", 1550, 1750),
    ("water", "Water", 2050, 2800),
    ("soil", "Soil & ask", 2950, 3700),
    ("bedrock", "Evidence", 4350, 5000),
]

P, I, T, O, Lf, S, C = art.PAPER, art.INK, art.TERRA, art.OCHRE, art.LEAF, art.SEA, art.CLAY

CSS = f"""
<style>
html{{background:#9cc4dc}}
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stMainBlockContainer"]{{background:transparent !important}}
.block-container{{position:relative;z-index:1;max-width:1080px !important;padding-left:2.2rem !important;padding-right:2.2rem !important}}
@media (min-width:1180px){{.block-container{{margin-left:auto;margin-right:auto;padding-left:150px !important}}}}

/* the world behind the page */
#fs-world{{position:fixed;inset:0;z-index:-1;pointer-events:none;background-repeat:no-repeat;background-size:100% 600vh;
  background-position:0 calc(var(--fs-bg,0) * -500vh);transition:background-position .35s cubic-bezier(.2,.7,.2,1)}}

/* layers: readable paper panels floating in the world */
.st-key-landing,.st-key-topbar{{background:rgba(243,238,227,.94);border-radius:16px;padding:1.2rem 1.5rem !important;
  box-shadow:0 18px 50px rgba(20,28,40,.18);border:1px solid rgba(255,255,255,.5)}}
.st-key-topbar{{padding:.6rem 1.1rem !important;border-radius:12px}}
[class*="st-key-layer_"]{{background:rgba(243,238,227,.94);border-radius:16px;padding:1.5rem 1.7rem 1.2rem 1.7rem !important;
  box-shadow:0 18px 50px rgba(20,28,40,.18);backdrop-filter:blur(3px);border:1px solid rgba(255,255,255,.5)}}
.fs-beat{{min-height:34vh;display:flex;flex-direction:column;justify-content:center;align-items:flex-start;padding:2rem 0}}
.fs-beat .k{{font:600 .72rem/1 'InterVar',sans-serif;letter-spacing:.2em;text-transform:uppercase;color:#fff;opacity:.9;
  text-shadow:0 1px 8px rgba(0,0,0,.35)}}
.fs-beat .h{{font:600 clamp(2rem,4.2vw,3.4rem)/1.02 'Fraunces',serif;color:#fff;max-width:44rem;margin:.4rem 0;
  text-shadow:0 2px 18px rgba(0,0,0,.35);font-variation-settings:'SOFT' 100,'WONK' 1}}
.fs-beat .d{{font:italic 400 1.15rem/1.45 'Fraunces',serif;color:#fff;max-width:38rem;text-shadow:0 1px 12px rgba(0,0,0,.45)}}
.fs-beat.dark .k,.fs-beat.dark .h,.fs-beat.dark .d{{color:{I};text-shadow:0 1px 14px rgba(243,238,227,.7)}}

/* landing */
.fs-hero{{min-height:58vh;display:flex;flex-direction:column;justify-content:flex-end;padding:3rem 0 1.5rem 0}}
.fs-hero .t{{font:600 clamp(3rem,8vw,6.2rem)/.9 'Fraunces',serif;color:#fff;text-shadow:0 3px 24px rgba(20,30,45,.35);
  font-variation-settings:'SOFT' 100,'WONK' 1;margin:.4rem 0 .8rem 0}}
.fs-hero .d{{font:italic 400 1.3rem/1.45 'Fraunces',serif;color:#fff;max-width:40rem;text-shadow:0 1px 14px rgba(0,0,0,.4)}}
.fs-hero .k{{font:600 .75rem/1 'InterVar',sans-serif;letter-spacing:.2em;text-transform:uppercase;color:#fff}}
.fs-demo{{border-radius:12px;padding:1rem 1.1rem;background:rgba(255,255,255,.55);border:1px solid rgba(31,43,58,.15);height:100%}}
.fs-demo b{{font:600 1.15rem 'Fraunces',serif;color:{I}}}
.fs-demo .s{{font-size:.84rem;color:{art.INK2};margin-top:.3rem}}

/* the living tree */
#fs-tree{{position:fixed;left:44px;top:50%;transform:translateY(-50%);width:118px;height:min(80vh,680px);z-index:6}}
#fs-tree svg{{width:100%;height:100%;overflow:visible}}
#fs-tree .part path,#fs-tree .part circle,#fs-tree .part ellipse{{transition:all .6s ease}}
#fs-tree .ghost{{stroke:rgba(255,255,255,.55);fill:none}}
#fs-tree .part .live{{opacity:0;transition:opacity .7s ease}}
#fs-tree .part.on .live{{opacity:1}}
#fs-tree .part.now .live{{filter:drop-shadow(0 0 6px rgba(255,236,170,.95))}}
#fs-tree text{{font:600 10px 'InterVar',sans-serif;fill:#fff;letter-spacing:.06em;text-transform:uppercase;cursor:pointer;
  paint-order:stroke;stroke:rgba(20,28,40,.55);stroke-width:2.5px}}
#fs-tree .part.now text{{fill:#FFE7A3}}
#fs-tree .hit{{cursor:pointer;pointer-events:all;fill:transparent}}
#fs-vine{{display:none;position:fixed;top:0;left:0;height:5px;z-index:7;background:linear-gradient(90deg,{Lf},{O});
  width:calc(var(--fs-prog,0) * 100%);transition:width .3s}}
@media (max-width:1179px){{#fs-tree{{display:none}} #fs-vine{{display:block}}}}

/* planting-window orchard */
.fs-orchard{{display:grid;grid-template-columns:repeat(12,1fr);gap:.2rem;align-items:end;margin:.4rem 0 .2rem 0}}
.fs-orchard .tr{{text-align:center;border-radius:10px;padding:.25rem 0 .35rem 0}}
.fs-orchard .tr.best{{background:rgba(217,154,43,.16);outline:1.5px solid {O}}}
.fs-orchard svg{{width:100%;height:auto;display:block}}
.fs-orchard .m{{font:600 .78rem 'InterVar',sans-serif;color:{I}}}
.fs-orchard .p{{font:600 .95rem 'Fraunces',serif;color:{I}}}
.fs-orchard .tr.low .p{{color:{T}}}
@media (max-width:720px){{.fs-orchard{{grid-template-columns:repeat(6,1fr)}}}}
</style>
"""


def _clouds(cx, cy, s=1.0, o=0.9):
    return (f'<g opacity="{o}" fill="#fff"><ellipse cx="{cx}" cy="{cy}" rx="{120*s}" ry="{34*s}"/>'
            f'<ellipse cx="{cx-55*s}" cy="{cy-18*s}" rx="{60*s}" ry="{36*s}"/><ellipse cx="{cx+40*s}" cy="{cy-26*s}" rx="{70*s}" ry="{44*s}"/></g>')


def world_svg():
    """Sky -> field -> topsoil -> clay and water table -> bedrock (viewBox 1440 x 6000)."""
    roots = "".join(
        f'<path d="M{x} 2010 C {x+dx} 2250, {x-dx} 2500, {x+dx//2} {2600+d}" stroke="#E2C29B" stroke-width="{w}" fill="none" opacity=".75"/>'
        for x, dx, d, w in [(260, 40, 120, 5), (330, -30, 40, 4), (520, 50, 300, 6), (760, -40, 80, 4), (980, 35, 260, 5),
                            (1180, -45, 140, 4), (1320, 30, 60, 3)])
    deep = "".join(
        f'<path d="M{x} 2600 C {x+30} 3000, {x-40} 3400, {x+10} {3800+d}" stroke="#E7CFAE" stroke-width="3" fill="none" opacity=".55"/>'
        for x, d in [(540, 0), (1000, 180), (300, -120)])
    pebbles = "".join(f'<ellipse cx="{(i*173)%1440}" cy="{2100+(i*311)%850}" rx="{9+(i%4)*4}" ry="{6+(i%3)*3}" fill="#7a573c" opacity=".55"/>'
                      for i in range(60))
    drops = "".join(f'<path d="M{x} {y} q 9 14 0 22 q -9 -8 0 -22z" fill="{S}" opacity=".75"/>'
                    for x, y in [(200, 2300), (430, 2460), (690, 2380), (880, 2560), (1100, 2420), (1270, 2640), (610, 2700), (980, 2760)])
    strata = "".join(f'<path d="M0 {y} C 360 {y-30}, 720 {y+30}, 1080 {y-10} S 1440 {y+20}, 1440 {y}" stroke="rgba(255,255,255,.18)" stroke-width="3" fill="none"/>'
                     for y in range(3150, 4250, 110))
    rock = "".join(f'<path d="M0 {y} L 220 {y-25} L 520 {y+15} L 900 {y-20} L 1200 {y+10} L 1440 {y-15}" stroke="rgba(255,255,255,.16)" stroke-width="4" fill="none"/>'
                   for y in range(4450, 6000, 160))
    rows = "".join(f'<path d="M{x} 2000 L {720 + (x-720)*0.25} 1760" stroke="{"#6E9A55" if i % 2 else "#A9B85E"}" stroke-width="22" opacity=".9"/>'
                   for i, x in enumerate(range(-400, 1900, 70)))
    return f"""<svg viewBox="0 0 1440 6000" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
<defs>
 <linearGradient id="g-sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#6f9fbf"/><stop offset=".45" stop-color="#9cc4dc"/><stop offset=".85" stop-color="#f1d9b3"/><stop offset="1" stop-color="#f6c98f"/></linearGradient>
 <linearGradient id="g-top" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5a3b26"/><stop offset="1" stop-color="#6d4a2f"/></linearGradient>
 <linearGradient id="g-sub" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8f5f3a"/><stop offset="1" stop-color="#b07a4c"/></linearGradient>
 <linearGradient id="g-rock" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5d6672"/><stop offset="1" stop-color="#2f3640"/></linearGradient>
</defs>
<rect x="0" y="0" width="1440" height="2000" fill="url(#g-sky)"/>
<g opacity=".22" stroke="#fff" stroke-width="10" fill="none" stroke-linecap="round">
 <path d="M1180 640 m -110 0 a 110 110 0 1 1 110 110 a 75 75 0 1 1 -75 -75 a 40 40 0 1 1 40 40"/>
</g>
{_clouds(1100, 260, 1.2)}{_clouds(420, 900, .9, .8)}{_clouds(1250, 1120, .8, .75)}{_clouds(200, 1350, .7, .7)}
<circle cx="1120" cy="1560" r="110" fill="{O}" opacity=".85"/>
<g stroke="{I}" stroke-width="3" fill="none" opacity=".5"><path d="M820 760 q 12 -10 24 0 q 12 -10 24 0"/><path d="M880 720 q 9 -8 18 0 q 9 -8 18 0"/></g>
<path d="M0 1720 C 240 1640, 420 1700, 640 1660 S 1100 1600, 1440 1690 L 1440 2000 L 0 2000 Z" fill="#7FA3A5" opacity=".75"/>
<path d="M0 1790 C 300 1730, 520 1800, 800 1760 S 1200 1740, 1440 1790 L 1440 2000 L 0 2000 Z" fill="#5E8C5A"/>
<g>{rows}</g>
<g transform="translate(1080 1745)"><rect x="0" y="0" width="90" height="62" fill="{P}"/><path d="M-10 2 L45 -38 L100 2Z" fill="{T}"/>
 <rect x="35" y="28" width="20" height="34" fill="{I}" opacity=".8"/></g>
<g transform="translate(250 1730)"><rect x="-6" y="0" width="12" height="80" fill="#6b4a32"/>
 <circle cx="0" cy="-20" r="54" fill="{Lf}"/><circle cx="-30" cy="0" r="34" fill="{Lf}"/><circle cx="32" cy="-2" r="36" fill="{Lf}"/>
 <circle cx="-20" cy="-30" r="7" fill="{O}"/><circle cx="18" cy="-12" r="7" fill="{O}"/><circle cx="2" cy="-44" r="7" fill="{O}"/></g>
<rect x="0" y="1990" width="1440" height="20" fill="#4c7a45"/>
<rect x="0" y="2008" width="1440" height="1000" fill="url(#g-top)"/>
{pebbles}{roots}{drops}
<path d="M620 2860 c 30 -20 60 20 90 0 s 60 20 90 0" stroke="#d98c8c" stroke-width="10" fill="none" stroke-linecap="round"/>
<rect x="0" y="3000" width="1440" height="1300" fill="url(#g-sub)"/>
{strata}{deep}
<path d="M0 3900 C 360 3860, 720 3940, 1080 3890 S 1440 3920, 1440 3900 L 1440 4120 C 1080 4150, 720 4080, 360 4130 S 0 4100, 0 4120 Z" fill="{S}" opacity=".55"/>
<g fill="#fff" opacity=".35">{''.join(f'<circle cx="{x}" cy="{4000 + (x * 7) % 60}" r="5"/>' for x in range(40, 1440, 90))}</g>
<rect x="0" y="4300" width="1440" height="1700" fill="url(#g-rock)"/>
{rock}
<g transform="translate(1040 4900)" stroke="rgba(255,255,255,.35)" stroke-width="6" fill="none">
 <path d="M0 0 m -70 0 a 70 70 0 1 1 70 70 a 48 48 0 1 1 -48 -48 a 26 26 0 1 1 26 26"/></g>
</svg>"""


def tree_svg():
    """A tree whose parts come alive as the reader reaches each layer."""
    gl = 330  # ground line
    parts = {
        "sky": (f'<path class="live" d="M60 140 C 60 110, 40 90, 26 70" stroke="{Lf}" stroke-width="5" fill="none"/>'
                f'<g class="live"><circle cx="26" cy="64" r="22" fill="{Lf}"/><circle cx="58" cy="52" r="26" fill="#5c9a5f"/>'
                f'<circle cx="88" cy="70" r="20" fill="{Lf}"/>'
                + "".join(f'<circle cx="{x}" cy="{y}" r="4.5" fill="#F4B6C2"/>' for x, y in [(20, 58), (44, 44), (66, 40), (86, 62), (56, 66)])
                + "</g>", 28, 46),
        "field": (f'<path class="live" d="M60 190 C 75 172, 92 160, 104 150" stroke="{Lf}" stroke-width="5" fill="none"/>'
                  f'<g class="live"><circle cx="104" cy="146" r="18" fill="#5c9a5f"/><circle cx="96" cy="150" r="4.5" fill="#F4B6C2"/>'
                  f'<circle cx="110" cy="140" r="4.5" fill="#F4B6C2"/></g>', 112, 150),
        "recover": (f'<path class="live" d="M60 250 C 45 236, 30 228, 16 222" stroke="{Lf}" stroke-width="5" fill="none"/>'
                    f'<g class="live"><circle cx="16" cy="218" r="17" fill="{Lf}"/><circle cx="12" cy="226" r="6" fill="{O}"/>'
                    f'<circle cx="24" cy="214" r="6" fill="{T}"/></g>', -2, 214),
        "water": (f'<path class="live" d="M60 {gl} C 52 360, 34 380, 22 410 M60 {gl} C 70 362, 90 380, 100 404" stroke="#7CC3E6" stroke-width="4" fill="none"/>'
                  f'<g class="live"><path d="M22 414 q 5 8 0 13 q -5 -5 0 -13z" fill="#7CC3E6"/><path d="M100 408 q 5 8 0 13 q -5 -5 0 -13z" fill="#7CC3E6"/></g>',
                  104, 392),
        "soil": (f'<path class="live" d="M60 {gl} C 60 400, 48 450, 40 500 M60 {gl} C 66 410, 80 460, 86 512" stroke="#E2C29B" stroke-width="4" fill="none"/>',
                 90, 486),
        "bedrock": (f'<path class="live" d="M60 {gl} C 62 430, 56 520, 60 600" stroke="#E7CFAE" stroke-width="5" fill="none"/>'
                    f'<g class="live"><rect x="30" y="604" width="60" height="10" rx="3" fill="#7d8792"/></g>', 66, 596),
    }
    names = {k: title for k, title, *_ in LAYERS}
    body = []
    for key, (live, tx, ty) in parts.items():
        anchor = "end" if tx < 30 else "start"
        body.append(f'<g class="part" data-layer="{key}">{live}'
                    f'<text x="{tx}" y="{ty}" text-anchor="{anchor}" data-layer="{key}">{html.escape(names[key])}</text>'
                    f'<rect class="hit" data-layer="{key}" x="{min(tx, 60) - 40}" y="{ty - 14}" width="80" height="22"/></g>')
    ghost = (f'<path class="ghost" d="M60 {gl} L60 140 M60 140 C 60 110, 40 90, 26 70 M60 190 C 75 172, 92 160, 104 150 '
             f'M60 250 C 45 236, 30 228, 16 222 M60 {gl} C 62 430, 56 520, 60 600" stroke-width="2" stroke-dasharray="3 5"/>'
             f'<circle class="ghost" cx="56" cy="62" r="40" stroke-width="1.5" stroke-dasharray="3 5"/>')
    trunk = (f'<path d="M60 {gl} L60 140" stroke="#6b4a32" stroke-width="9" stroke-linecap="round" '
             f'style="stroke-dasharray:200;stroke-dashoffset:calc(200 - 200 * var(--fs-trunk,0.08));transition:stroke-dashoffset .6s"/>')
    ground = f'<path d="M4 {gl} Q 60 {gl-8} 116 {gl}" stroke="#fff" stroke-width="2" fill="none" opacity=".7"/>'
    return (f'<div id="fs-tree"><svg viewBox="-20 20 160 620" xmlns="http://www.w3.org/2000/svg">{ghost}{trunk}{ground}'
            + "".join(body) + '</svg></div><div id="fs-vine"></div>')


SCRIPT = """
<script>
(function(){
  const P = window.parent; const D = P.document;
  const LAYERS = %s;
  if (P.__fsJourney) { P.__fsJourney.update(); return; }
  function scroller(){
    const c = [D.querySelector('[data-testid="stMain"]'), D.querySelector('[data-testid="stAppViewContainer"]'), D.scrollingElement];
    for (const el of c){ if (el && el.scrollHeight > el.clientHeight + 20) return el; }
    return D.scrollingElement;
  }
  function boxes(){
    return LAYERS.map(([key,,a,b]) => { const el = D.querySelector('.st-key-layer_' + key); if (!el) return null;
      const r = el.getBoundingClientRect(); return {key, el, top:r.top, bottom:r.bottom, a, b}; }).filter(Boolean);
  }
  let busy = false;
  function update(){
    busy = false;
    const vh = P.innerHeight, mid = vh * 0.45, bx = boxes(), root = D.documentElement;
    let bg = 0, cur = null;
    if (bx.length){
      if (mid < bx[0].top){ const t = Math.max(0, Math.min(1, 1 - (bx[0].top - mid) / vh)); bg = bx[0].a * t; }
      for (let i = 0; i < bx.length; i++){
        const L = bx[i];
        if (mid >= L.top && mid <= L.bottom){ const f = (mid - L.top) / Math.max(1, L.bottom - L.top); bg = L.a + f * (L.b - L.a); cur = L.key; }
        else if (i + 1 < bx.length && mid > L.bottom && mid < bx[i+1].top){
          const N = bx[i+1], f = (mid - L.bottom) / Math.max(1, N.top - L.bottom); bg = L.b + f * (N.a - L.b); cur = f < .5 ? L.key : N.key; }
        else if (i === bx.length - 1 && mid > L.bottom){ bg = L.b; cur = L.key; }
      }
    }
    root.style.setProperty('--fs-bg', (bg / 5000).toFixed(4));
    const s = scroller(), prog = s ? s.scrollTop / Math.max(1, s.scrollHeight - s.clientHeight) : 0;
    root.style.setProperty('--fs-prog', prog.toFixed(3));
    const idx = cur ? LAYERS.findIndex(l => l[0] === cur) : -1;
    root.style.setProperty('--fs-trunk', Math.min(1, 0.08 + Math.max(0, Math.min(idx, 2) + 1) / 3 * 0.92).toFixed(3));
    D.querySelectorAll('#fs-tree .part').forEach(g => {
      const k = g.getAttribute('data-layer'), j = LAYERS.findIndex(l => l[0] === k);
      g.classList.toggle('on', idx >= 0 && j <= idx); g.classList.toggle('now', k === cur);
    });
  }
  function onScroll(){ if (!busy){ busy = true; P.requestAnimationFrame(update); } }
  D.addEventListener('scroll', onScroll, true); P.addEventListener('resize', onScroll);
  D.addEventListener('click', e => {
    const t = e.target.closest && e.target.closest('#fs-tree [data-layer]'); if (!t) return;
    const el = D.querySelector('.st-key-layer_' + t.getAttribute('data-layer'));
    if (el) el.scrollIntoView({behavior:'smooth', block:'start'});
  }, true);
  new P.MutationObserver(onScroll).observe(D.body, {childList:true, subtree:true});
  P.__fsJourney = {update};
  update();
})();
</script>
"""


def install(st):
    """Page CSS, the world behind the page, the tree, and the scroll script."""
    st.markdown(CSS, unsafe_allow_html=True)
    # The world is painted as a background image, not a 600vh element: a layer that tall
    # exceeds GPU texture limits on 2x/3x screens and Chrome then shows stale tiles.
    uri = "data:image/svg+xml;charset=utf-8," + quote(world_svg(), safe="")
    st.markdown(f'<style>#fs-world{{background-image:url("{uri}")}}</style><div id="fs-world"></div>{tree_svg()}',
                unsafe_allow_html=True)
    import json
    components.html(SCRIPT % json.dumps(LAYERS), height=0)


def beat(kicker, headline, dek="", dark=False):
    return (f'<div class="fs-beat{" dark" if dark else ""}"><div class="k">{kicker}</div><div class="h">{headline}</div>'
            + (f'<div class="d">{dek}</div>' if dek else "") + "</div>")


# ---------------------------------------------------------------------------
# Planting-window orchard
# ---------------------------------------------------------------------------

BLOSSOM_SPOTS = [(38, 28), (52, 22), (64, 32), (30, 42), (46, 40), (60, 46), (72, 40), (40, 54), (56, 58)]


def fruit_tree(p, storm=False):
    """A small tree: fuller canopy, more blossoms and ripe fruit as p (0-1) rises."""
    p = max(0.0, min(1.0, p))
    leaf_o = 0.25 + 0.75 * p
    n = int(round(p * len(BLOSSOM_SPOTS)))
    fruit = p >= 0.7
    flowers = "".join(
        (f'<circle cx="{x}" cy="{y}" r="5" fill="{O if i % 2 else T}"/>' if fruit and i % 3 != 2 else
         f'<g transform="translate({x} {y})"><circle r="4.2" fill="#F4B6C2"/><circle r="1.6" fill="{O}"/></g>')
        for i, (x, y) in enumerate(BLOSSOM_SPOTS[:n]))
    fallen = "" if p >= 0.4 else "".join(f'<ellipse cx="{x}" cy="104" rx="4" ry="2" fill="{C}" opacity=".7"/>' for x in (28, 70, 80))
    swirl = (f'<path d="M84 12 m -8 0 a 8 8 0 1 1 8 8 a 5 5 0 1 1 -5 -5" stroke="{S}" stroke-width="2.2" fill="none"/>' if storm else "")
    return (f'<svg viewBox="0 0 100 112" xmlns="http://www.w3.org/2000/svg">'
            f'<ellipse cx="50" cy="104" rx="34" ry="5" fill="rgba(31,43,58,.12)"/>'
            f'<path d="M50 104 L50 66 M50 76 L38 64 M50 72 L63 60" stroke="#6b4a32" stroke-width="5" stroke-linecap="round" fill="none"/>'
            f'<g opacity="{leaf_o:.2f}"><circle cx="50" cy="40" r="27" fill="{Lf}"/><circle cx="32" cy="50" r="17" fill="#5c9a5f"/>'
            f'<circle cx="68" cy="50" r="18" fill="#5c9a5f"/></g>{flowers}{fallen}{swirl}</svg>')


def pct(p):
    """The model leaves out pests, markets and luck, so it never claims certainty."""
    return "95%+" if p > 0.95 else f"{p:.0%}"


def orchard_html(window, month_names, crop):
    best = max(window, key=lambda w: w["p_good"])["start"]
    cells = []
    for w in window:
        water = "fully covered" if w["water"] >= 1 else f"{w['water']:.0%} covered"
        tip = (f"{crop} planted in {month_names[w['start'] - 1]}, harvest {month_names[w['harvest'] - 1]}: "
               f"{w['p_safe']:.0%} chance storms and floods take less than a fifth of the harvest; "
               f"climate fit {w['fit']:.2f}; water {water} (irrigation need about {w['water_need']:.0f} mm)")
        cls = "tr" + (" best" if w["start"] == best else "") + (" low" if w["p_good"] < 0.35 else "")
        cells.append(f'<div class="{cls}" title="{html.escape(tip)}">{fruit_tree(w["p_good"], storm=w["p_safe"] < 0.6)}'
                     f'<div class="m">{month_names[w["start"] - 1]}</div><div class="p">{pct(w["p_good"])}</div></div>')
    return f'<div class="fs-orchard">{"".join(cells)}</div>'
