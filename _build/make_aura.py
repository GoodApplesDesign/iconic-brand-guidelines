"""Renders the animated aura: the primary stack in V3 Gold on Noir, as a subtle cinematic loop.

Lighting follows Joey's reference (a gold coin catching a warm key light): soft light that travels all the way round the
ring, catching brightest at the top right, with a large bloom off the lit metal, a few broad hazy shafts, a warm bloom
behind the ring that follows the ring's own shape (so there are no hard edges), and faint out-of-focus dust in the light. The logo never rotates: it only pushes in and
floats very slightly. Fine film grain keeps it filmic and stops the dark gradients banding.

Run: python3 _build/make_aura.py   (needs Google Chrome and ffmpeg; PREVIEW=1 writes four stills only)
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
WARM, PALE, AMBER = '#F0C773', '#FFF1CF', '#B07A22'

# the logo's geometry, in its own units (primary-stack viewBox 264.638 x 230.637)
VB_W, VB_H = 264.638, 230.637
RING_C, RING_R = (113.3, 115.3), 114.3
SCALE = 0.42 * H / (2 * RING_R)  # ring diameter = 42% of frame height


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
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
                        '--default-background-color=00000000', f'--force-device-scale-factor={scale}',
                        f'--window-size={W},{H}', f'--screenshot={shot}', 'file://' + os.path.join(tmp, 'p.html')],
                       check=True, capture_output=True)
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


def main():
    svg = open(os.path.join(ROOT, 'assets', 'logo', 'svg', 'primary-stack-gold.svg'), encoding='utf-8').read()
    ring_im, (cx, cy) = render_layer(re.sub(r'fill="#EDEDEA"', 'fill="none"', svg))
    mark_im, _ = render_layer(re.sub(r'fill="url\(#[^)]+\)"', 'fill="none"', svg))
    R = RING_R * SCALE
    # soft blooms that follow the ring's own shape (no circle seams), made once and moved with the logo
    a1 = np.asarray(ring_im.resize((W, H), Image.LANCZOS), np.float32)[..., 3] / 255
    blooms = [Image.fromarray(blur(a1, sg)) for sg in (10, 34, 110)]

    # dust: a few dim, out-of-focus motes that only show where the light falls, drifting on small closed paths
    rng = np.random.default_rng(11)
    N = 110
    ang = rng.uniform(-np.pi, np.pi, N)
    rad = R * rng.uniform(0.8, 1.9, N)
    dust_xy = np.stack([cx + rad * np.cos(ang), cy + rad * np.sin(ang)], 1)
    dust_amp = rng.uniform(8, 30, (N, 2))
    dust_ph = rng.uniform(0, 2 * np.pi, (N, 2))
    dust_size = rng.uniform(1.6, 3.4, N)
    dust_b = rng.uniform(0.12, 0.35, N)

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    hy, hx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
    os.makedirs(OUT, exist_ok=True)
    n = FPS * SECONDS
    preview = os.environ.get('PREVIEW')
    out = os.path.join(OUT, 'aura-gold.mp4')
    ff = None if preview else subprocess.Popen(
        ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
         '-i', '-', '-vf', 'scale=out_color_matrix=bt709:out_range=tv', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17',
         '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
         '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    grain_rng = np.random.default_rng(7)
    key = np.deg2rad(-60)  # where the light is strongest: the top right, as on the round-two slide
    for f in (range(0, n, n // 4) if preview else range(n)):
        t = f / n  # 0..1, loops seamlessly
        # the logo: a slow, slight push-in and float, never a rotation
        s = 1 + 0.03 * (0.5 - 0.5 * np.cos(2 * np.pi * t))
        ty = -5 * np.sin(2 * np.pi * t)
        ring = np.asarray(place(ring_im, 2, s, ty, cx, cy), np.float32) / 255
        mark = np.asarray(place(mark_im, 2, s, ty, cx, cy), np.float32) / 255
        ring_rgb, ring_a = ring[..., :3], ring[..., 3:4]
        mark_rgb, mark_a = mark[..., :3], mark[..., 3:4]
        ccy = cy + ty

        # the light travels all the way round the ring once per loop, catching brightest as it passes the top right
        # and fading out as it crosses the gap where the wordmark breaks through (so it never floats in mid-air)
        phi = key + 2 * np.pi * t
        wrap = lambda v: np.angle(np.exp(1j * v))
        catch = 0.66 + 0.34 * ((1 + np.cos(wrap(phi - key))) / 2) ** 1.3
        gap = np.clip((np.abs(wrap(phi)) - np.deg2rad(5)) / np.deg2rad(10), 0, 1)  # the ring's gap is only about +-6 degrees
        flare = catch * gap
        gx, gy = cx + R * s * 0.985 * np.cos(phi), ccy + R * s * 0.985 * np.sin(phi)
        d = wrap(np.arctan2(yy - ccy, xx - cx) - phi)
        lobe = np.exp(-(d / 1.0) ** 2)[..., None]

        b10, b34, b110 = (np.asarray(place(b, 1, s, ty, cx, cy), np.float32)[..., None] for b in blooms)
        haze = np.exp(-((xx - gx) ** 2 + (yy - gy) ** 2) / (2 * 300 ** 2))[..., None]
        glow = ((b34 * 0.26 * rgb(WARM) + b110 * 0.34 * rgb(AMBER)) * (0.28 + 0.72 * lobe) * (0.55 + 0.45 * catch)
                + haze * rgb(AMBER) * 0.16 * flare)

        # dust, visible only inside the light
        dust = np.zeros((H, W), np.float32)
        px = dust_xy[:, 0] + dust_amp[:, 0] * np.sin(2 * np.pi * t + dust_ph[:, 0])
        py = dust_xy[:, 1] + dust_amp[:, 1] * np.cos(2 * np.pi * t + dust_ph[:, 1]) + ty
        lit = np.exp(-((px - gx) ** 2 + (py - gy) ** 2) / (2 * 260 ** 2)) * flare
        for x0, y0, sz, bb in zip(px, py, dust_size, dust_b * lit):
            if bb < 0.01:
                continue
            r0 = int(sz * 3) + 1
            xi, yi = int(x0), int(y0)
            if not (r0 <= xi < W - r0 and r0 <= yi < H - r0):
                continue
            gy_, gx_ = np.mgrid[yi - r0:yi + r0 + 1, xi - r0:xi + r0 + 1]
            dust[yi - r0:yi + r0 + 1, xi - r0:xi + r0 + 1] += bb * np.exp(-((gx_ - x0) ** 2 + (gy_ - y0) ** 2) / (2 * sz ** 2))
        frame = np.minimum(NOIR + glow + dust[..., None] * rgb('#E9C77F') * 0.5, 1)
        frame = ring_rgb * ring_a + frame * (1 - ring_a)

        # the metal catching the light: a broad soft sheen around the glint
        sheen_m = np.exp(-(d / 0.6) ** 2)[..., None] * ring_a
        frame = np.minimum(frame + sheen_m * rgb(PALE) * 0.42 * flare, 1)
        frame = mark_rgb * mark_a + frame * (1 - mark_a)

        # soft light: a large bloom from the glint and the lit metal, plus a few broad hazy shafts (worked at half size)
        hl = sheen_m[::2, ::2, 0] * flare + np.exp(-((hx - gx / 2) ** 2 + (hy - gy / 2) ** 2) / (2 * 4 ** 2)) * flare
        bloom = blur(hl, 8) * 0.9 + blur(hl, 26) * 0.75 + blur(hl, 70) * 0.5
        rays = np.zeros_like(hx)
        rx, ry = hx - gx / 2, hy - gy / 2
        for k, (a_deg, length, width, amp) in enumerate([(-35, 210, 9, 0.10), (145, 160, 8, 0.08), (55, 90, 6, 0.05), (235, 80, 6, 0.04)]):
            a_ = np.deg2rad(a_deg + 5 * np.sin(2 * np.pi * t + k))
            along = rx * np.cos(a_) + ry * np.sin(a_)
            perp = -rx * np.sin(a_) + ry * np.cos(a_)
            rays += np.exp(-(perp / width) ** 2) * np.exp(-np.abs(along) / length) * amp
        light = np.asarray(Image.fromarray((bloom + rays * flare).astype(np.float32)).resize((W, H), Image.BICUBIC), np.float32)
        light = np.clip(light, 0, 4)[..., None] * rgb('#FFE7B0') * 0.55
        frame = 1 - (1 - frame) * np.exp(-light)  # soft, filmic highlight roll-off

        grain = grain_rng.normal(0, 1.1, (H, W, 1)).astype(np.float32)
        out_px = np.clip(frame * 255 + grain, 0, 255).astype(np.uint8)
        if ff:
            ff.stdin.write(out_px.tobytes())
        if f == 0:
            Image.fromarray(out_px).save(os.path.join(OUT, 'aura-gold-poster.jpg'), quality=90)
        if f % (n // 4) == 0:
            Image.fromarray(out_px).save(os.path.join(HERE, f'aura-frame-{f // (n // 4)}.png'))
    if ff:
        ff.stdin.close()
        ff.wait()
        print('wrote', out, os.path.getsize(out) // 1024, 'KB')


if __name__ == '__main__':
    main()
