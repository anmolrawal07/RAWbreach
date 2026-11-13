"""Build RAWbreach brand assets (coral #ED7163 theme).

Generates into the output folder:
  logo.png, favicon.png, apple-touch-icon.png  - transparent coral logo + icons
  logo-watermark.png                           - single-colour logo for the PDF watermark
  worldmap.svg                                 - animated dotted world map

Only needed to change the brand images; the generated files are already in static/.

Usage (from the project root):
  pip install pillow
  curl -L -o land-110m.json https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/land-110m.json
  python tools/build_assets.py tools/source/logo-original.png land-110m.json static
"""
import colorsys, json, math, sys
from PIL import Image

SRC_LOGO, LAND_JSON, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

# ---------------------------------------------------------------- logo
im = Image.open(SRC_LOGO).convert("RGB")
w, h = im.size
px = im.load()
out = Image.new("RGBA", (w, h))
op = out.load()
for y in range(h):
    for x in range(w):
        r, g, b = px[x, y]
        m = max(r, g, b)
        a = max(0.0, (m - 30) / 225)            # black background -> transparent
        if a <= 0:
            op[x, y] = (0, 0, 0, 0)
            continue
        a = min(1.0, a)
        rr, gg, bb = (min(1.0, c / 255 / max(a, 1e-3)) for c in (r, g, b))  # un-premultiply
        hh, ss, vv = colorsys.rgb_to_hsv(rr, gg, bb)
        if ss > 0.08:                             # blue/cyan parts -> red (silver swoosh stays white)
            hh = (0.017 - (hh - 0.60) * 0.25) % 1.0   # coral #ED7163
            ss = min(1.0, ss * 0.62)
        rr, gg, bb = colorsys.hsv_to_rgb(hh, ss, vv)
        op[x, y] = (round(rr * 255), round(gg * 255), round(bb * 255), round(a * 255))

bbox = out.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
out = out.crop(bbox)
side = max(out.size)
sq = Image.new("RGBA", (side, side))
sq.paste(out, ((side - out.width) // 2, (side - out.height) // 2))
sq.resize((256, 256), Image.LANCZOS).save(f"{OUT}/logo.png", optimize=True)
alpha = sq.getchannel("A").point(lambda v: max(0, min(255, int((v - 60) * 1.6))))
mono = Image.new("RGBA", sq.size, (222, 98, 84, 255)); mono.putalpha(alpha)
mono.resize((400, 400), Image.LANCZOS).save(f"{OUT}/logo-watermark.png", optimize=True)
sq.resize((64, 64), Image.LANCZOS).save(f"{OUT}/favicon.png", optimize=True)
sq.resize((180, 180), Image.LANCZOS).save(f"{OUT}/apple-touch-icon.png", optimize=True)
print("logo", out.size, "->", side)

# ---------------------------------------------------------------- world map
topo = json.load(open(LAND_JSON))
sx, sy = topo["transform"]["scale"]
tx, ty = topo["transform"]["translate"]
arcs = []
for arc in topo["arcs"]:
    x = y = 0
    pts = []
    for dx, dy in arc:
        x += dx; y += dy
        pts.append((x * sx + tx, y * sy + ty))
    arcs.append(pts)

def ring(idx):
    pts = []
    for i in idx:
        a = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.extend(a if not pts else a[1:])
    un = [pts[0]]
    for x, y in pts[1:]:
        px_ = un[-1][0]
        while x - px_ > 180: x -= 360
        while x - px_ < -180: x += 360
        un.append((x, y))
    return un

rings = []
def collect(geom):
    t = geom["type"]
    if t == "GeometryCollection":
        for g in geom["geometries"]: collect(g)
    elif t == "Polygon":
        rings.extend(ring(r) for r in geom["arcs"])
    elif t == "MultiPolygon":
        for poly in geom["arcs"]: rings.extend(ring(r) for r in poly)
for obj in topo["objects"].values():
    collect(obj)
boxes = [(min(p[0] for p in r), max(p[0] for p in r), min(p[1] for p in r), max(p[1] for p in r)) for r in rings]

def land(lon, lat):
    inside = False
    for r, (x0, x1, y0, y1) in zip(rings, boxes):
        if not (y0 <= lat <= y1): continue
        lon_ = next((l for l in (lon, lon + 360, lon - 360) if x0 <= l <= x1), None)
        if lon_ is None: continue
        lon2 = lon_
        j = len(r) - 1
        for i in range(len(r)):
            xi, yi = r[i]; xj, yj = r[j]
            if (yi > lat) != (yj > lat) and lon2 < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
    return inside

miller = lambda lat: 1.25 * math.log(math.tan(math.pi / 4 + 0.4 * math.radians(lat)))
inv_miller = lambda y: math.degrees(2.5 * math.atan(math.exp(0.8 * y)) - 0.625 * math.pi)

STEP = 2.2                       # degrees of longitude between dots
U = 10                           # svg units between dots
ytop, ybot = miller(80), miller(-56)
ystep = math.radians(STEP)
cols = int(360 / STEP)
rows = int((ytop - ybot) / ystep)
base, bright = [], []
for j in range(rows):
    lat = inv_miller(ytop - (j + .5) * ystep)
    for i in range(cols):
        lon = -180 + (i + .5) * STEP
        if land(lon, lat):
            seg = f"M{i*U+5} {j*U+5}h0"
            ((i * 7 + j * 13) % 11 == 0 and bright or base).append(seg)

def proj(lon, lat):
    return ((lon + 180) / STEP * U, (ytop - miller(lat)) / ystep * U)

cities = [(-74, 40.7), (-0.1, 51.5), (-46.6, -23.5), (3.4, 6.5), (72.9, 19.1), (103.8, 1.35), (139.7, 35.7), (151.2, -33.9), (-122.4, 37.8), (37.6, 55.8)]
pings = []
for k, (lo, la) in enumerate(cities):
    x, y = proj(lo, la)
    pings.append(f'<circle class="p" cx="{x:.0f}" cy="{y:.0f}" r="9" style="animation-delay:{k*0.7:.1f}s"/><circle class="c" cx="{x:.0f}" cy="{y:.0f}" r="3.6"/>')

W, H = cols * U, rows * U
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" fill="none">
<style>
.p{{fill:#ed7163;transform-box:fill-box;transform-origin:center;animation:ping 7s ease-out infinite;opacity:0}}
.c{{fill:#f7a99f}}
@keyframes ping{{0%{{transform:scale(.4);opacity:.9}}12%{{transform:scale(2.6);opacity:0}}100%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.p{{animation:none}}}}
</style>
<path d="{''.join(base)}" stroke="#ed7163" stroke-opacity=".5" stroke-width="4.2" stroke-linecap="round"/>
<path d="{''.join(bright)}" stroke="#f4988c" stroke-opacity=".95" stroke-width="4.4" stroke-linecap="round"/>
{''.join(pings)}
</svg>'''
open(f"{OUT}/worldmap.svg", "w").write(svg)
print("map", W, "x", H, "dots", len(base) + len(bright), "bytes", len(svg))
