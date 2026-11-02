"""Renders the animated aura: the primary stack in V3 Gold on Noir, as a subtle cinematic loop.

The ring keeps the logo's own V3 Gold gradients (one on each arc), but each one is driven by a light: the gradient's
brightest line passes through that light's spot on the ring and turns with it. At the start of the loop both lights sit
exactly where the static logo's highlights are, so the first frame is the static logo. The lights are locked opposite
each other and swing round the ring together, at different, changing strengths, and the gold follows them. A hairline sharp bevel along the ring's
edges catches whichever light faces it.
Round the ring (v12): only the lit metal glows, as a tight bright halo that falls off fast into a long faint tail (no even
fog round the ring), a thin sharp glisten hugging the ring's outer edge at each light (on the
metal only), a small, faint four-point twinkle that flashes once per light per loop, and a bloom off the brightest metal and the glistens, all scaled by each light's strength. The logo never rotates: it only
pushes in and floats very slightly. Fine film grain keeps it filmic and stops the dark gradients banding.

Run: python3 _build/make_aura.py   (needs Google Chrome and ffmpeg; PREVIEW=8 writes eight evenly spaced stills only)
Writes assets/video/aura-gold.mp4 (1920x1080, 30 fps) and assets/video/aura-gold-poster.jpg.
"""
import os, re, subprocess, tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'assets', 'video')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
W, H, FPS, SECONDS = 1920, 1080, 30, 10
NOIR = np.array([17, 17, 17], np.float32) / 255
WARM, AMBER = '#F0C773', '#B07A22'

# the logo's geometry, in its own units (primary-stack viewBox 264.638 x 230.637)
VB_W, VB_H = 264.638, 230.637
RING_C, RING_R = (113.3, 115.3), 114.3
SCALE = 0.42 * H / (2 * RING_R)  # ring diameter = 42% of frame height
# the V3 Gold stops, as in the SVG; the brightest is at 0.46
STOPS = [(0, '#6A4910'), (.18, '#B3882F'), (.36, '#E6C674'), (.46, '#FAEDC2'), (.56, '#D7B45E'), (.78, '#9A6F22'),
         (1, '#56390C')]
FACET = 1.0                 # px: width of the hairline bevel along each edge of the ring
GLOW_CORE, GLOW_TAIL = 0.75, 2.6  # strength of the tight halo at the lit metal, and of its long faint tail


def rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255


def render_layer(svg_text, scale=2):
    """Renders the logo SVG at its frame position onto a transparent canvas at `scale` x the frame size."""
    lw, lh = VB_W * SCALE, VB_H * SCALE
    x, y = (W - lw) / 2, (H - lh) / 2
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, 'l.svg'), 'w').write(svg_text)
        open(os.path.join(tmp, 'p.html'), 'w').write(
            f'<html><body style="margin:0;background:transparent"><img src="l.svg" '
            f'style="position:absolute;left:{x:.3f}px;top:{y:.3f}px;width:{lw:.3f}px;height:{lh:.3f}px"></body></html>')
        shot = os.path.join(tmp, 's.png')
        for attempt in range(3):  # headless Chrome now and then exits early; a retry always works
            r = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
                                '--default-background-color=00000000', f'--force-device-scale-factor={scale}',
                                f'--window-size={W},{H}', f'--screenshot={shot}', 'file://' + os.path.join(tmp, 'p.html')],
                               capture_output=True)
            if r.returncode == 0 and os.path.exists(shot):
                break
        else:
            raise RuntimeError('Chrome could not render the logo')
        im = Image.open(shot).convert('RGBA')
    return im, (x + RING_C[0] * SCALE, y + RING_C[1] * SCALE)


def blur(img, sigma):
    """Gaussian blur via FFT (float precision, no banding)."""
    pad = int(sigma * 3)
    p = np.pad(img, ((pad, pad), (pad, pad)))
    fy = np.fft.fftfreq(p.shape[0])[:, None]
    fx = np.fft.fftfreq(p.shape[1])[None, :]
    g = np.exp(-2 * (np.pi ** 2) * sigma ** 2 * (fx ** 2 + fy ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(p) * g))[pad:-pad, pad:-pad].astype(np.float32)


def place(im, k, s, ty, cx, cy):
    """Scales an image (k x frame size) by s about the ring centre and lifts it by ty, resampled to the frame."""
    data = (k / s, 0, k * (cx - cx / s), 0, k / s, k * (cy - (cy + ty) / s))
    return im.transform((W, H), Image.AFFINE, data, resample=Image.BICUBIC)


def fit_circle(pts):
    x, y = pts[:, 0], pts[:, 1]
    D, E, F = np.linalg.lstsq(np.stack([x, y, np.ones_like(x)], 1), -(x ** 2 + y ** 2), rcond=None)[0]
    ox, oy = -D / 2, -E / 2
    return ox, oy, np.sqrt(ox ** 2 + oy ** 2 - F)


def ring_circles(alpha, k, cx, cy, R):
    """The crescent band as two circles (its outer and inner edges), fitted to the rendered ring, relative to the ring
    centre, at rest size. Scans stay clear of the gap and the thin tips."""
    outer, inner = [], []
    rs = np.arange(R * 0.8, R * 1.15, 0.25)
    for deg in np.r_[np.arange(-150, -25, 2), np.arange(26, 151, 2)]:
        th = np.deg2rad(deg)
        v = alpha[((cy + rs * np.sin(th)) * k).astype(int), ((cx + rs * np.cos(th)) * k).astype(int)]
        on = rs[v > 0.5]
        if len(on) > 2:
            inner.append((on.min() * np.cos(th), on.min() * np.sin(th)))
            outer.append((on.max() * np.cos(th), on.max() * np.sin(th)))
    return fit_circle(np.array(outer)), fit_circle(np.array(inner))


def gradients(svg, cx, cy):
    """The ring's two V3 Gold gradients from the SVG, as (start, end) points relative to the ring centre in frame px."""
    x0, y0 = (W - VB_W * SCALE) / 2, (H - VB_H * SCALE) / 2
    out = []
    for m in re.finditer(r'<linearGradient id="[^"]+"[^>]*?x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)" '
                         r'gradientTransform="translate\(([-\d.]+) ([-\d.]+)\) rotate\(([-\d.]+)\)"', svg):
        x1, y1, x2, y2, tx, ty, rot = map(float, m.groups())
        c, s = np.cos(np.deg2rad(rot)), np.sin(np.deg2rad(rot))
        f = lambda x, y: np.array([x0 + (tx + c * x - s * y) * SCALE - cx, y0 + (ty + s * x + c * y) * SCALE - cy])
        out.append((f(x1, y1), f(x2, y2)))
    return out


def gold(g):
    xs = [p for p, _ in STOPS]
    cs = np.array([rgb(c) for _, c in STOPS])
    g = np.clip(g, 0, 1)
    return np.stack([np.interp(g, xs, cs[:, i]) for i in range(3)], -1).astype(np.float32)


def wrap(v):
    return np.angle(np.exp(1j * v))


def main():
    svg = open(os.path.join(ROOT, 'assets', 'logo', 'svg', 'primary-stack-gold.svg'), encoding='utf-8').read()
    ring_im, (cx, cy) = render_layer(re.sub(r'fill="#EDEDEA"', 'fill="none"', svg))
    mark_im, _ = render_layer(re.sub(r'fill="url\(#[^)]+\)"', 'fill="none"', svg))
    R = RING_R * SCALE
    (ox, oy, ro), (ix, iy, ri) = ring_circles(np.asarray(ring_im, np.float32)[..., 3] / 255, 2, cx, cy, R)
    rm = (ro + ri) / 2

    # each arc's gradient as a light: where its brightest line (0.46) crosses the ring is the light's spot.
    # The top arc's light starts at the upper left, the bottom arc's at the lower right, as in the static logo.
    lights = []
    for p1, p2 in gradients(svg, cx, cy):
        axis = p2 - p1
        n0, ln = axis / np.linalg.norm(axis), np.linalg.norm(axis)
        h0 = p1 + 0.46 * axis
        phis = np.deg2rad(np.arange(-180, 180, 0.05))
        side = (rm * np.cos(phis) - h0[0]) * n0[0] + (rm * np.sin(phis) - h0[1]) * n0[1]
        roots = phis[np.nonzero(np.diff(np.sign(side)))[0]]
        roots = roots[(np.abs(roots) > np.deg2rad(25)) & (np.abs(roots) < np.deg2rad(155))]
        lights.append(dict(phi0=float(roots[0]), n0=n0, ln=ln))
    top, bottom = sorted(lights, key=lambda l: l['phi0'])  # the top arc's light has the negative angle (y points down)

    # soft blooms that follow the ring's own shape (no circle seams), made once and moved with the logo
    a1 = np.asarray(ring_im.resize((W, H), Image.LANCZOS), np.float32)[..., 3] / 255
    blooms = [Image.fromarray(blur(a1, sg)) for sg in (34, 110)]

    # the box round the ring where the gold is worked out, sampled at 2x so the hairline bevel stays crisp but smooth
    B = int(R * 1.22)
    bx0, by0 = int(cx) - B, int(cy) - B
    sx, sy = np.meshgrid(bx0 + (np.arange(4 * B) + 0.5) / 2, by0 + (np.arange(4 * B) + 0.5) / 2)
    down = lambda v: v.reshape(2 * B, 2, 2 * B, 2, -1).mean((1, 3))

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    hy, hx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
    os.makedirs(OUT, exist_ok=True)
    n = FPS * SECONDS
    preview = int(os.environ.get('PREVIEW', 0))
    out = os.path.join(OUT, 'aura-gold.mp4')
    ff = None if preview else subprocess.Popen(
        ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
         '-i', '-', '-vf', 'scale=out_color_matrix=bt709:out_range=tv', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17',
         '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
         '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    grain_rng = np.random.default_rng(7)
    frames = [round(i * n / preview) for i in range(preview)] if preview else range(n)
    for f in frames:
        t = f / n  # 0..1, loops seamlessly
        tau = 2 * np.pi * t
        # the logo: a slow, slight push-in and float, never a rotation
        s = 1 + 0.03 * (0.5 - 0.5 * np.cos(tau))
        ty = -5 * np.sin(tau)
        ccy = cy + ty

        # the two lights start as the static logo: at their resting spots, square on, at full strength
        # the lights are locked opposite each other, like one rig: both turn round the ring by the same angle (and their
        # gradients turn with them), swinging from the rest position and back, clear of the gap. Their strengths still
        # differ and change on their own rhythms.
        swing = np.deg2rad(44 * (1 - np.cos(tau)) + 49 * np.sin(tau))  # 0 at rest; from about -22 to +110 degrees:
        # each light sweeps nearly the whole length of its arc and back, never crossing the gap
        for l_ in (top, bottom):
            l_['phi'] = l_['phi0'] + swing
            l_['turn'] = swing
        top['power'] = 1 + 0.22 * np.sin(tau) + 0.08 * np.sin(3 * tau)
        bottom['power'] = 1 - 0.3 * np.sin(2 * tau) - 0.1 * np.sin(tau)

        # the gold: each arc's gradient runs square to its light's (turned) direction, with its brightest line
        # through the light's spot, and is as bright as the light is strong
        qx, qy = (sx - cx) / s, (sy - ccy) / s
        col = np.zeros(qx.shape + (3,), np.float32)
        for l_, arc in ((top, qy < 0), (bottom, qy >= 0)):
            c, sn = np.cos(l_['turn']), np.sin(l_['turn'])
            nx, ny = c * l_['n0'][0] - sn * l_['n0'][1], sn * l_['n0'][0] + c * l_['n0'][1]
            g = 0.46 + ((qx - rm * np.cos(l_['phi'])) * nx + (qy - rm * np.sin(l_['phi'])) * ny) / l_['ln']
            col = np.where(arc[..., None], gold(g) * l_['power'] ** 0.8, col)
        # the hairline bevel: a sharp edge along each side of the band, bright where it faces a light and a touch darker
        # elsewhere (the outer edge faces the light on its side, the inner edge the light across the ring)
        d_out = ro - np.hypot(qx - ox, qy - oy)
        d_in = np.hypot(qx - ix, qy - iy) - ri
        wide = (d_out + d_in) > 5
        ang = np.arctan2(qy, qx)
        face_out = sum(l_['power'] * np.clip(np.cos(ang - l_['phi']), 0, 1) ** 6 for l_ in (top, bottom))
        face_in = sum(l_['power'] * np.clip(-np.cos(ang - l_['phi']), 0, 1) ** 6 for l_ in (top, bottom))
        bevel = np.where(wide & (d_out < FACET), 0.72 + 0.6 * face_out,
                         np.where(wide & (d_in < FACET), 0.72 + 0.6 * face_in, 1))
        col = np.minimum(col * bevel[..., None], 1.2)
        ring_rgb = np.zeros((H, W, 3), np.float32)
        ring_rgb[by0:by0 + 2 * B, bx0:bx0 + 2 * B] = down(col)

        ring_a = np.asarray(place(ring_im, 2, s, ty, cx, cy), np.float32)[..., 3:4] / 255
        mark = np.asarray(place(mark_im, 2, s, ty, cx, cy), np.float32) / 255
        mark_rgb, mark_a = mark[..., :3], mark[..., 3:4]

        # where each light's spot is on screen, and how close each pixel is (round the ring) to each light
        spots = [(cx + rm * s * np.cos(l_['phi']), ccy + rm * s * np.sin(l_['phi']), l_['power']) for l_ in (top, bottom)]
        pix_ang = np.arctan2(yy - ccy, xx - cx)
        lobe = sum(l_['power'] * np.exp(-(wrap(pix_ang - l_['phi']) / 1.0) ** 2) for l_ in (top, bottom))

        # the glow: only the lit parts of the metal glow. A tight, bright halo hugs the ring where each light is and
        # falls away fast into a long, faint tail (several blur sizes summed, like real light falloff), so there is no
        # even fog round the dim parts of the ring. Worked at half size.
        ra_h = ring_a[::2, ::2, 0]
        hang = np.arctan2(hy - ccy / 2, hx - cx / 2)
        lit = sum(l_['power'] ** 1.5 * np.exp(-(wrap(hang - l_['phi']) / 0.6) ** 2) for l_ in (top, bottom))
        src = ra_h * lit
        core = blur(src, 2) * 0.55 + blur(src, 6) * 0.42
        tail = blur(src, 16) * 0.38 + blur(src, 42) * 0.3 + blur(src, 100) * 0.22
        up = lambda v: np.asarray(Image.fromarray(v.astype(np.float32)).resize((W, H), Image.BICUBIC), np.float32)[..., None]
        glow_l = up(core) * rgb('#F6D58E') * GLOW_CORE + up(tail) * rgb('#C88E35') * GLOW_TAIL
        frame = 1 - (1 - NOIR) * np.exp(-glow_l)
        frame = np.minimum(ring_rgb, 1) * ring_a + frame * (1 - ring_a)

        # the glisten: a thin, sharp specular streak hugging the ring's outer edge at each light, sliding with it,
        # with a tiny hot core where it peaks
        ro_s = ro * s
        rr = np.hypot(xx - (cx + ox * s), yy - (ccy + oy * s))
        rang = np.arctan2(yy - (ccy + oy * s), xx - (cx + ox * s))
        glis = np.zeros_like(xx)
        for (gx, gy, p), l_ in zip(spots, (top, bottom)):
            arc = wrap(rang - l_['phi']) * ro_s
            edge = rr - (ro_s - 1.2)
            streak = np.exp(-0.5 * (arc / 46) ** 2) * np.exp(-0.5 * (edge / 1.3) ** 2)
            core = np.exp(-0.5 * (arc / 9) ** 2) * np.exp(-0.5 * (edge / 2.4) ** 2)
            glis += (streak * 1.0 + core * 0.65) * p ** 2.2
        glis *= ring_a[..., 0]  # only on the metal, so it never trails off the end of the ring into the gap
        # the twinkle: now and then, at a light's spot, a small sharp four-point sparkle flashes and fades (alternating lights)
        tw = np.zeros_like(xx)
        for te, l_ in ((0.12, top), (0.62, bottom)):  # used sparingly: once per light per loop
            dt = (t - te + 0.5) % 1 - 0.5
            env = np.exp(-0.5 * (dt / 0.018) ** 2) * 0.7
            if env < 0.01:
                continue
            px_ = cx + ox * s + (ro_s - 1.2) * np.cos(l_['phi'])
            py_ = ccy + oy * s + (ro_s - 1.2) * np.sin(l_['phi'])
            x0, y0 = int(px_) - 120, int(py_) - 120
            wx, wy = xx[y0:y0 + 241, x0:x0 + 241] - px_, yy[y0:y0 + 241, x0:x0 + 241] - py_
            a0 = np.deg2rad(12 + 60 * dt)  # the cross turns very slightly as it flashes
            sparkle = np.exp(-0.5 * (wx ** 2 + wy ** 2) / 2.0 ** 2) * 0.8
            for k_, (da, ln_) in enumerate(((0, 30), (90, 30), (45, 10), (135, 10))):
                a = a0 + np.deg2rad(da)
                along = wx * np.cos(a) + wy * np.sin(a)
                perp = -wx * np.sin(a) + wy * np.cos(a)
                sparkle += np.exp(-0.5 * (perp / 0.7) ** 2) * np.exp(-np.abs(along) / (ln_ * (0.4 + 0.6 * env))) * (0.65 if k_ < 2 else 0.25)
            tw[y0:y0 + 241, x0:x0 + 241] += sparkle * env * l_['power']
        frame = 1 - (1 - frame) * (1 - np.clip(glis, 0, 1)[..., None] * rgb('#FFF4DA'))
        frame = 1 - (1 - frame) * (1 - np.clip(tw, 0, 1)[..., None] * rgb('#FFF8E8'))
        frame = mark_rgb * mark_a + frame * (1 - mark_a)

        # soft light: a bloom off the brightest gold and off each glisten (worked at half size)
        lum = (ring_rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)) * ring_a[..., 0]
        hl = np.clip(lum - 0.8, 0, None).reshape(H // 2, 2, W // 2, 2).mean((1, 3)) * 1.6
        hl += (glis + tw * 0.5).reshape(H // 2, 2, W // 2, 2).mean((1, 3)) * 0.9
        bloom = blur(hl, 8) * 0.8 + blur(hl, 26) * 0.6 + blur(hl, 70) * 0.4
        light = np.asarray(Image.fromarray(bloom.astype(np.float32)).resize((W, H), Image.BICUBIC), np.float32)
        light = np.clip(light, 0, 4)[..., None] * rgb('#FFE7B0') * 0.55
        frame = 1 - (1 - frame) * np.exp(-light)  # soft, filmic highlight roll-off

        grain = grain_rng.normal(0, 1.1, (H, W, 1)).astype(np.float32)
        out_px = np.clip(frame * 255 + grain, 0, 255).astype(np.uint8)
        if ff:
            ff.stdin.write(out_px.tobytes())
        if f == 0 and ff:
            Image.fromarray(out_px).save(os.path.join(OUT, 'aura-gold-poster.jpg'), quality=90)
        if preview:
            i = frames.index(f)
            Image.fromarray(out_px).save(os.path.join(HERE, f'aura-frame-{i}.png'))
            msg = (f't={t:.3f} top {np.rad2deg(top["phi"]):.0f}deg x{top["power"]:.2f}  '
                   f'bottom {np.rad2deg(bottom["phi"]):.0f}deg x{bottom["power"]:.2f}')
            if f == 0:  # the first frame's gold should be the static logo's (the hairline bevel aside)
                static = np.asarray(ring_im.resize((W, H), Image.LANCZOS), np.float32)[..., :3] / 255
                m = a1 > 0.99
                msg += f'  | vs static logo: mean diff {np.abs(ring_rgb - static)[m].mean() * 255:.1f}/255'
            print(msg, flush=True)
    if ff:
        ff.stdin.close()
        ff.wait()
        print('wrote', out, os.path.getsize(out) // 1024, 'KB')


if __name__ == '__main__':
    main()
