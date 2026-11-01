"""Clearspace diagrams that measure the logo with its own O.

X is the height of the O in ICONIC. Stacks of that O (solid, low opacity, touching edge to edge) measure the clear space at
the top-left and bottom-right corners, inside a faint hairline boundary: 2X for the lockups, X for the icon. The icon has no
O, so it borrows the wordmark's O scaled to the icon's I. Drawn dark: Blanc on Noir. Writes inline SVG partials to
_build/src/partials/, pulled into pages with <!--include:name-->.

Run: python3 _build/make_diagrams.py   (then build.py)
"""
import os, re
from fontTools.svgLib.path import parse_path
from fontTools.pens.boundsPen import BoundsPen

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'src', 'partials')
GOLD = '#DDC68C'  # Gold Lite: reads on Noir
MARK, LINE, BOUNDS, TEXT = .12, .3, .3, .5  # opacities: kept low so the logo leads

# how many O's of clear space: 2X for the lockups, X for the icon
LOCKUPS = {'primary-stack': 2, 'wide-stack': 2, 'wordmark': 2, 'icon': 1}


def bounds(d):
    p = BoundsPen(None)
    parse_path(d, p)
    return p.bounds


def read(lockup):
    svg = open(os.path.join(ROOT, 'assets', 'logo', 'svg', f'{lockup}-blanc.svg'), encoding='utf-8').read()
    paths = re.findall(r'<path [^>]*?d="([^"]+)"', svg)
    return svg, paths, [bounds(d) for d in paths]


def find_o(boxes):  # the O: widest of the tall ICONIC letters
    tall = [i for i, b in enumerate(boxes) if (b[3] - b[1]) > 30 and (b[2] - b[0]) < 40]
    return max(tall, key=lambda i: boxes[i][2] - boxes[i][0])


def diagram(lockup, n):
    svg, paths, boxes = read(lockup)
    W, H = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()[2:]]
    if lockup == 'icon':
        # borrow the wordmark's O, scaled so its height matches the icon's I
        _, wpaths, wboxes = read('wordmark')
        o = find_o(wboxes)
        d, (x0, y0, x1, y1) = wpaths[o], wboxes[o]
        i_box = min(boxes, key=lambda b: b[2] - b[0])
        k = (i_box[3] - i_box[1]) / (y1 - y0)
    else:
        o = find_o(boxes)
        d, (x0, y0, x1, y1) = paths[o], boxes[o]
        k = 1.0
    X, ow = (y1 - y0) * k, (x1 - x0) * k  # the O's height (X) and width, in this lockup's units
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    C = n * X  # clear space
    pad = X * 0.5
    vx, vy, vw, vh = -C - pad, -C - pad, W + 2 * (C + pad), H + 2 * (C + pad)
    label = f'{n}X' if n > 1 else 'X'

    def o_at(tx, ty, rot):  # the O centred on (tx, ty); turned on its side left and right so its height spans X there too
        t = f'translate({tx:.2f} {ty:.2f})' + (' rotate(90)' if rot else '') + f' scale({k:.4f}) translate({-cx:.2f} {-cy:.2f})'
        return f'<path d="{d}" transform="{t}" fill="{GOLD}" fill-opacity="{MARK}"/>'

    # stacks of n O's, touching each other, the logo and the boundary, at the top-left and bottom-right corners
    marks = []
    for j in range(n):
        off = X / 2 + j * X
        marks += [o_at(ow / 2, -off, False), o_at(-off, ow / 2, True),
                  o_at(W - ow / 2, H + off, False), o_at(W + off, H - ow / 2, True)]
    logo = re.sub(r'<\?xml[^>]*>|<svg[^>]*>|</svg>', '', svg).strip()
    parts = [
        f'<svg class="diagram" viewBox="{vx:.2f} {vy:.2f} {vw:.2f} {vh:.2f}" role="img" aria-label="{lockup.replace("-", " ").capitalize()} clearspace: {label} on every side, where X is the height of the O">',
        f'<rect x="{-C:.2f}" y="{-C:.2f}" width="{W + 2 * C:.2f}" height="{H + 2 * C:.2f}" fill="none" stroke="{GOLD}" stroke-opacity="{LINE}" stroke-width="1" vector-effect="non-scaling-stroke"/>',
        f'<rect x="0" y="0" width="{W:.2f}" height="{H:.2f}" fill="none" stroke="#EDEDEA" stroke-opacity="{BOUNDS}" stroke-width="1" stroke-dasharray="3 3" vector-effect="non-scaling-stroke"/>',
        *marks,
        f'<text x="{ow * 1.35:.2f}" y="{-C / 2:.2f}" dominant-baseline="central" style="fill:{GOLD};fill-opacity:{TEXT};font-size:{vh / 17:.2f}px">{label}</text>',
        f'<g>{logo}</g>',
        '</svg>',
    ]
    return '\n'.join(parts)


os.makedirs(OUT, exist_ok=True)
for lockup, n in LOCKUPS.items():
    open(os.path.join(OUT, f'clearspace-{lockup}.svg'), 'w', encoding='utf-8').write(diagram(lockup, n))
    print('wrote clearspace', lockup)
