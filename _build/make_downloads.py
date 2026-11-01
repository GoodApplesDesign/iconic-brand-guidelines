"""Builds everything in assets/downloads: logo PNGs and zip packs, Adobe swatches (ASE), CSS colour tokens, Aileron zip.

Run after make_logos.py:  python3 _build/make_downloads.py
Renders PNGs with headless Google Chrome (transparent background, 2000 px wide).
"""
import glob, json, os, re, struct, subprocess, tempfile, zipfile
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SVG = os.path.join(ROOT, 'assets', 'logo', 'svg')
PNG = os.path.join(HERE, 'png')  # build cache, only shipped inside the zips
OUT = os.path.join(ROOT, 'assets', 'downloads')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
FONTS = os.path.expanduser('~/Library/Fonts')

COLOURS = [('Noir', '#111111'), ('Graphite', '#2E2E2E'), ('Blanc', '#EDEDEA'), ('Brown', '#54350F'),
           ('Olive', '#4E5410'), ('Bronze Lite', '#B4885A'), ('Gold Lite', '#DDC68C')]
STOPS = [0, 18, 36, 46, 56, 78, 100]
METALS = {
    'Gold': ['#6A4910', '#B3882F', '#E6C674', '#FAEDC2', '#D7B45E', '#9A6F22', '#56390C'],
    'Silver': ['#5C5C5C', '#9E9E9E', '#D9D9D9', '#F8F8F8', '#C9C9C9', '#8C8C8C', '#4E4E4E'],
    'Bronze': ['#55321A', '#9A6636', '#D19E68', '#F2D5AC', '#BF8A55', '#80502A', '#45280F'],
    'Graphite': ['#1C1C1C', '#3A3A3A', '#5E5E5E', '#7C7C7C', '#4C4C4C', '#2E2E2E', '#151515'],
}


def render_png(svg_path, out_path, width=2000):
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', open(svg_path).read()).group(1).split()]
    height = round(width * vb[3] / vb[2])
    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, 'p.html')
        open(page, 'w').write(f'<html><body style="margin:0;background:transparent">'
                              f'<img src="file://{svg_path}" style="display:block;width:{width}px;height:{height}px"></body></html>')
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
                        '--default-background-color=00000000', f'--window-size={width},{height}',
                        f'--screenshot={out_path}', f'file://{page}'], check=True, capture_output=True)
    im = Image.open(out_path)
    assert im.mode == 'RGBA' and im.getpixel((0, 0))[3] == 0, f'{out_path} is not transparent'


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def ase(groups):
    """Adobe Swatch Exchange v1.0: groups of global RGB swatches."""
    def name_bytes(n):
        s = (n + '\0').encode('utf-16-be')
        return struct.pack('>H', len(n) + 1) + s
    blocks = []
    for gname, swatches in groups:
        body = name_bytes(gname)
        blocks.append(struct.pack('>HI', 0xC001, len(body)) + body)
        for n, h in swatches:
            r, g, b = (c / 255 for c in hex_rgb(h))
            body = name_bytes(n) + b'RGB ' + struct.pack('>fffH', r, g, b, 0)
            blocks.append(struct.pack('>HI', 0x0001, len(body)) + body)
        blocks.append(struct.pack('>HI', 0xC002, 0))
    return b'ASEF' + struct.pack('>HHI', 1, 0, len(blocks)) + b''.join(blocks)


def css_tokens():
    lines = ['/* ICONIC Beverages colour tokens */', ':root {']
    lines += [f'  --iconic-{n.lower().replace(" ", "-")}: {h};' for n, h in COLOURS]
    for m, ramp in METALS.items():
        stops = ', '.join(f'{c} {p}%' for c, p in zip(ramp, STOPS))
        lines.append(f'  --iconic-{m.lower()}-gradient: linear-gradient(125deg, {stops});')
    return '\n'.join(lines + ['}', ''])


def main():
    os.makedirs(PNG, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    manifest = json.load(open(os.path.join(HERE, 'logos.json')))
    svgs = sorted(glob.glob(os.path.join(SVG, '*.svg')))
    for s in svgs:
        render_png(s, os.path.join(PNG, os.path.basename(s)[:-4] + '.png'))
    print('rendered', len(svgs), 'PNGs')

    # icon extras: favicons and a social avatar (gold icon on Noir)
    icon = Image.open(os.path.join(PNG, 'icon-gold.png'))
    extras = {}
    for size in (16, 32, 180, 512):
        im = icon.copy(); im.thumbnail((size, size), Image.LANCZOS)
        canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0)); canvas.paste(im, ((size - im.width) // 2, (size - im.height) // 2), im)
        extras[f'favicon-{size}.png'] = canvas
    avatar = Image.new('RGBA', (1080, 1080), hex_rgb('#111111') + (255,))
    im = icon.copy(); im.thumbnail((560, 560), Image.LANCZOS)
    avatar.paste(im, ((1080 - im.width) // 2, (1080 - im.height) // 2), im)
    extras['social-avatar-1080.png'] = avatar
    for n, im in extras.items():
        im.save(os.path.join(PNG, n))
    extras['favicon-16.png'].save(os.path.join(PNG, 'favicon.ico'), sizes=[(16, 16), (32, 32)], append_images=[extras['favicon-32.png']])

    def pack(zip_name, lockups, extra=()):
        with zipfile.ZipFile(os.path.join(OUT, zip_name), 'w', zipfile.ZIP_DEFLATED) as z:
            for l in lockups:
                for v in manifest[l]['variants']:
                    z.write(os.path.join(SVG, f'{l}-{v}.svg'), f'{l}/SVG/ICONIC-{l}-{v}.svg')
                    z.write(os.path.join(PNG, f'{l}-{v}.png'), f'{l}/PNG/ICONIC-{l}-{v}.png')
            for e in extra:
                z.write(os.path.join(PNG, e), f'icon/extras/{e}')
        print('zipped', zip_name, os.path.getsize(os.path.join(OUT, zip_name)) // 1024, 'KB')

    icon_extras = ['favicon-16.png', 'favicon-32.png', 'favicon-180.png', 'favicon-512.png', 'favicon.ico', 'social-avatar-1080.png']
    pack('ICONIC-logo-suite.zip', list(manifest), icon_extras)
    for l in manifest:
        pack(f'ICONIC-{l}.zip', [l], icon_extras if l == 'icon' else ())

    groups = [('ICONIC palette', COLOURS)] + [(f'ICONIC {m} gradient stops', [(f'{m} {p}%', c) for c, p in zip(ramp, STOPS)]) for m, ramp in METALS.items()]
    open(os.path.join(OUT, 'ICONIC-colours.ase'), 'wb').write(ase(groups))
    open(os.path.join(OUT, 'ICONIC-colours.css'), 'w').write(css_tokens())

    with zipfile.ZipFile(os.path.join(OUT, 'Aileron.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(glob.glob(os.path.join(FONTS, 'Aileron-*.otf'))):
            z.write(f, 'Aileron/' + os.path.basename(f))
        z.writestr('Aileron/README.txt', 'Aileron by Sora Sagano (dot colon). Released with no rights reserved (CC0): free for personal and commercial use.\n')
    print('done')


if __name__ == '__main__':
    main()
