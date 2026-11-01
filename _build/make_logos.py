"""Builds every logo colourway from the four SVGs exported from Logo Development-v3.ai.

Run: python3 _build/make_logos.py  (from the repo root)
Writes assets/logo/svg/<lockup>-<variant>.svg and a manifest used by the site.
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, '_build', 'logo-src')
OUT = os.path.join(ROOT, 'assets', 'logo', 'svg')

# brand palette (Logo Development-v3.ai, round 3)
NOIR, BLANC = '#111111', '#EDEDEA'
STOPS = [0, .18, .36, .46, .56, .78, 1]
RAMPS = {
    'gold':     ['#6A4910', '#B3882F', '#E6C674', '#FAEDC2', '#D7B45E', '#9A6F22', '#56390C'],
    'silver':   ['#5C5C5C', '#9E9E9E', '#D9D9D9', '#F8F8F8', '#C9C9C9', '#8C8C8C', '#4E4E4E'],
    'bronze':   ['#55321A', '#9A6636', '#D19E68', '#F2D5AC', '#BF8A55', '#80502A', '#45280F'],
    'graphite': ['#1C1C1C', '#3A3A3A', '#5E5E5E', '#7C7C7C', '#4C4C4C', '#2E2E2E', '#151515'],
}
# variant -> (ring: ramp name or flat hex, wordmark colour)
VARIANTS = {
    'gold':        ('gold', BLANC),
    'silver':      ('silver', BLANC),
    'bronze':      ('bronze', BLANC),
    'graphite':    ('graphite', NOIR),
    'gold-lite':   ('#DDC68C', BLANC),
    'bronze-lite': ('#B4885A', BLANC),
    'blanc':       (BLANC, BLANC),
    'noir':        (NOIR, NOIR),
}
LOCKUPS = ['primary-stack', 'wide-stack', 'wordmark', 'icon']


def clean(svg):
    svg = re.sub(r'<\?xml[^>]*>\s*', '', svg)
    svg = re.sub(r'\s*<!--.*?-->', '', svg, flags=re.S)
    svg = svg.replace(' id="Layer_1"', '')
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + svg.strip() + '\n'


def recolour(svg, ring, mark):
    svg = svg.replace('fill="#eee"', f'fill="{mark}"')
    if ring in RAMPS:
        cols = iter(RAMPS[ring] * 4)
        svg = re.sub(r'stop-color="#[0-9a-fA-F]{3,6}"', lambda m: f'stop-color="{next(cols)}"', svg)
    else:
        svg = re.sub(r'fill="url\(#[^)]+\)"', f'fill="{ring}"', svg)
        svg = re.sub(r'\s*<defs>.*?</defs>', '', svg, flags=re.S)
        svg = svg.replace(' xmlns:xlink="http://www.w3.org/1999/xlink"', '')
    return svg


os.makedirs(OUT, exist_ok=True)
manifest = {}
for lockup in LOCKUPS:
    src = clean(open(os.path.join(SRC, lockup + '.svg'), encoding='utf-8').read())
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', src).group(1).split()]
    manifest[lockup] = {'w': vb[2], 'h': vb[3], 'variants': []}
    for name, (ring, mark) in VARIANTS.items():
        if lockup == 'wordmark' and name not in ('blanc', 'noir', 'gold-lite', 'bronze-lite'):
            continue  # no ring, so only the flat wordmark colours apply
        if lockup == 'wordmark' and name in ('gold-lite', 'bronze-lite'):
            mark = ring  # the Lite wordmarks take the metal colour on the letters
        out = recolour(src, ring, mark)
        open(os.path.join(OUT, f'{lockup}-{name}.svg'), 'w', encoding='utf-8').write(out)
        manifest[lockup]['variants'].append(name)
# misuse example only (outlined logo), kept out of the download packs
MISUSE = os.path.join(ROOT, 'assets', 'logo', 'misuse')
os.makedirs(MISUSE, exist_ok=True)
src = clean(open(os.path.join(SRC, 'primary-stack.svg'), encoding='utf-8').read())
outline = re.sub(r'fill="(#eee|url\(#[^)]+\))"', 'fill="none" stroke="#EDEDEA" stroke-width=".8"', src)
outline = re.sub(r'\s*<defs>.*?</defs>', '', outline, flags=re.S)
open(os.path.join(MISUSE, 'primary-stack-outline.svg'), 'w', encoding='utf-8').write(outline)
json.dump(manifest, open(os.path.join(ROOT, '_build', 'logos.json'), 'w'), indent=1)
print(json.dumps({k: (round(v['w'], 1), round(v['h'], 1), len(v['variants'])) for k, v in manifest.items()}))
