"""Masar logo morph: GET ED + Eshra7ly logos dissolve into particles that form
the bilingual Masar lockup. Renders frames with numpy/PIL, synthesises an
ambient soundtrack, and muxes both into an MP4 with ffmpeg.

    python3 video/make_morph.py            # full render -> video/masar-logo-morph.mp4
    python3 video/make_morph.py --preview  # a few still frames -> video/preview/
"""
import math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT.parent / "site" / "assets"
FONTS = ROOT / "fonts"
W, H, FPS, DUR = 1920, 1080, 30, 13.0
SR = 44100

PAPER = np.array([240, 240, 240], np.float32)
INK = (17, 17, 17); INK2 = (85, 85, 85)
CYAN = (0, 174, 239); NAVY = (0, 48, 127); ORANGE = (247, 145, 60); BLUE = (26, 160, 230)
rng = np.random.default_rng(7)


# ---------------------------------------------------------------- helpers
def ease_io(x):  # cubic in-out
    x = np.clip(x, 0, 1)
    return np.where(x < .5, 4 * x ** 3, 1 - (-2 * x + 2) ** 3 / 2)

def ease_out(x, p=3):
    x = np.clip(x, 0, 1); return 1 - (1 - x) ** p

def ramp(t, a, b):
    return float(np.clip((t - a) / (b - a), 0, 1))

def load(name, height=None, width=None):
    im = Image.open(ASSETS / name).convert("RGBA")
    if height: im = im.resize((round(im.width * height / im.height), height), Image.LANCZOS)
    if width: im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    return im

def text_layer(txt, font, fill, tracking=0.0):
    """Render text with custom tracking (em) onto a tight RGBA image."""
    asc, desc = font.getmetrics()
    widths = [font.getlength(c) for c in txt]
    tr = tracking * font.size
    w = int(sum(widths) + tr * (len(txt) - 1) + font.size * .2)
    im = Image.new("RGBA", (w, asc + desc + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = font.size * .05
    for c, cw in zip(txt, widths):
        d.text((x, 5), c, font=font, fill=fill); x += cw + tr
    return im.crop(im.getbbox()), asc

def over(dst, layer, x, y, alpha=1.0, scale=1.0):
    """Composite a straight-alpha RGBA PIL layer onto float frame dst at (x,y) top-left, sub-pixel."""
    if alpha <= 0.002: return
    lw, lh = layer.size
    if scale != 1.0 or (x % 1) or (y % 1):
        sw, sh = lw * scale, lh * scale
        ox, oy = math.floor(x), math.floor(y)
        fx, fy = x - ox, y - oy
        bw, bh = int(math.ceil(sw + fx)) + 2, int(math.ceil(sh + fy)) + 2
        inv = 1 / scale
        layer = layer.transform((bw, bh), Image.AFFINE, (inv, 0, -fx * inv, 0, inv, -fy * inv), Image.BICUBIC)
        x, y = ox, oy
    x, y = int(x), int(y)
    arr = np.asarray(layer, np.float32)
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + arr.shape[1]), min(H, y + arr.shape[0])
    if x1 <= x0 or y1 <= y0: return
    a = arr[y0 - y:y1 - y, x0 - x:x1 - x]
    al = a[..., 3:4] / 255 * alpha
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - al) + a[..., :3] * al

def blank_rgba():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


# ---------------------------------------------------------------- layout
geted = load("logo-geted.png", width=560)
eshra = load("logo-eshra7ly.png", height=196)
masar_ar = load("logo-masar-ar.png", height=300)
f_en = ImageFont.truetype(str(FONTS / "Montserrat-450.ttf"), 250)
masar_en, _ = text_layer("Masar", f_en, INK, tracking=-0.06)
f_x = ImageFont.truetype(str(FONTS / "Montserrat-450.ttf"), 70)
times, _ = text_layer("×", f_x, INK2)
f_tag = ImageFont.truetype(str(FONTS / "Montserrat-450.ttf"), 42)
tag_en, _ = text_layer("Your gate to university life", f_tag, INK2, tracking=-0.02)
f_ar = ImageFont.truetype(str(FONTS / "Alexandria-VF.ttf"), 40)
try: f_ar.set_variation_by_axes([350])
except Exception: pass
_im = Image.new("RGBA", (900, 120), (0, 0, 0, 0))
ImageDraw.Draw(_im).text((20, 10), "بوابتك إلى الحياة الجامعية", font=f_ar, fill=INK2, direction="rtl", language="ar")
tag_ar = _im.crop(_im.getbbox())
f_by = ImageFont.truetype(str(FONTS / "Montserrat-450.ttf"), 30)
by_txt, _ = text_layer("by", f_by, INK2)
small_geted = load("logo-geted.png", height=34)
small_eshra = load("logo-eshra7ly.png", height=60)
small_x, _ = text_layer("×", ImageFont.truetype(str(FONTS / "Montserrat-450.ttf"), 34), INK2)

# intro: logos rest positions at dissolve time (after drifting inward)
CY = 520
GX_END = 960 - 90 - geted.width;  GY = CY - geted.height / 2
EX_END = 960 + 90;                EY = CY - eshra.height / 2
DRIFT = 26
# final lockup
GAP = 86
LW = masar_en.width + GAP + masar_ar.width
LX = (W - LW) / 2
LCY = 450
EN_X, EN_Y = LX, LCY - masar_en.height / 2 + 18
AR_X, AR_Y = LX + masar_en.width + GAP, LCY - masar_ar.height / 2 - 6
LOCK_BOX = (LX, min(EN_Y, AR_Y), LX + LW, max(EN_Y + masar_en.height, AR_Y + masar_ar.height))

def lockup_layer():
    im = blank_rgba()
    im.alpha_composite(masar_en, (round(EN_X), round(EN_Y)))
    im.alpha_composite(masar_ar, (round(AR_X), round(AR_Y)))
    return im

def sources_layer():
    im = blank_rgba()
    im.alpha_composite(geted, (round(GX_END), round(GY)))
    im.alpha_composite(eshra, (round(EX_END), round(EY)))
    return im

LOCK = lockup_layer()
_bb = LOCK.getbbox(); LOCK_IM = LOCK.crop(_bb); LOCK_OX, LOCK_OY = _bb[0], _bb[1]


# ---------------------------------------------------------------- particles
PAL = {"cyan": CYAN, "navy": NAVY, "orange": ORANGE, "ink": INK}

def sample(layer, step=2, thresh=150):
    a = np.asarray(layer).astype(np.float32)
    ys, xs = np.mgrid[0:H:step, 0:W:step]
    ys = ys + rng.integers(0, step, ys.shape); xs = xs + rng.integers(0, step, xs.shape)
    ys = np.clip(ys, 0, H - 1); xs = np.clip(xs, 0, W - 1)
    m = a[ys, xs, 3] > thresh
    xs, ys = xs[m].astype(np.float32), ys[m].astype(np.float32)
    col = a[ys.astype(int), xs.astype(int), :3]
    names = list(PAL); pal = np.array([PAL[n] for n in names], np.float32)
    grp = np.array(names)[np.argmin(((col[:, None, :] - pal[None]) ** 2).sum(-1), 1)]
    return xs + .5, ys + .5, col, grp

sx, sy, scol, sgrp = sample(sources_layer())
tx, ty, tcol, tgrp = sample(LOCK)
# English letters are ink; the Arabic is cyan / navy / orange
is_en = tx < (EN_X + masar_en.width + GAP / 2)
tgrp = np.where(is_en, "en", tgrp)

N = len(tx)
src_idx = np.empty(N, int)
key = lambda x, y: x + .35 * y
used = np.zeros(len(sx), int)
for tg, sg in (("cyan", ["cyan"]), ("navy", ["navy"]), ("orange", ["orange"]), ("en", ["cyan", "navy", "orange"])):
    ti = np.where(tgrp == tg)[0]
    si = np.where(np.isin(sgrp, sg))[0]
    if len(ti) == 0 or len(si) == 0: continue
    ti = ti[np.argsort(key(tx[ti], ty[ti]))]
    si = si[np.argsort(key(sx[si], sy[si]))]
    pick = si[np.round(np.linspace(0, len(si) - 1, len(ti))).astype(int)]
    src_idx[ti] = pick; used[pick] += 1
# any stray target group (e.g. anti-aliased 'ink' pixels in the Arabic) -> nearest-colour source
left = np.where(~np.isin(tgrp, ["cyan", "navy", "orange", "en"]))[0]
if len(left): src_idx[left] = rng.integers(0, len(sx), len(left)); used[src_idx[left]] += 1

P0x, P0y = sx[src_idx], sy[src_idx]
C0 = scol[src_idx]; C1 = np.where(is_en[:, None], np.array(INK, np.float32), tcol)
mult = used[src_idx].astype(np.float32)
# lift: push outward from each logo's centre
gcx, gcy = GX_END + geted.width / 2, CY
ecx, ecy = EX_END + eshra.width / 2, CY
cxs = np.where(P0x < 960, gcx, ecx); cys = np.full(N, CY)
dx, dy = P0x - cxs, P0y - cys; dn = np.hypot(dx, dy) + 1e-3
lift = rng.uniform(18, 70, N)
P1x = P0x + dx / dn * lift + rng.normal(0, 10, N)
P1y = P0y + dy / dn * lift + rng.normal(0, 10, N) - 12
# bezier controls: swirl out, then arc in from above/below
ang = rng.uniform(0, 2 * np.pi, N)
sw = rng.uniform(120, 340, N)
C1x, C1y = P1x + np.cos(ang) * sw, P1y + np.sin(ang) * sw * .7 - 60
side = np.where(ty < LCY, -1, 1)
C2x = tx + rng.normal(0, 60, N); C2y = ty + side * rng.uniform(60, 180, N)
# delays: English builds left->right, Arabic right->left, meeting in the middle
en_n = (tx - EN_X) / masar_en.width
ar_n = (AR_X + masar_ar.width - tx) / masar_ar.width
delay = np.where(is_en, en_n, ar_n) * .75 + rng.uniform(0, .18, N)
dur = rng.uniform(2.0, 2.45, N)
T_DIS, T_LIFT, T_GO = 2.9, 3.5, 3.25
# ghosts: source pixels nobody picked scatter and fade
gi = np.where(used == 0)[0]
Gx, Gy, Gc = sx[gi], sy[gi], scol[gi]
gdx, gdy = Gx - np.where(Gx < 960, gcx, ecx), Gy - CY; gdn = np.hypot(gdx, gdy) + 1e-3
Gv = rng.uniform(40, 160, len(gi))

def particle_state(t):
    """positions, colours, alphas for all particles at time t (plus ghosts)."""
    ul = ease_out(np.full(N, (t - T_DIS) / (T_LIFT - T_DIS)))
    u = ease_io((t - T_GO - delay) / dur)
    ax = P0x + (P1x - P0x) * ul; ay = P0y + (P1y - P0y) * ul
    b0, b1, b2, b3 = (1 - u) ** 3, 3 * (1 - u) ** 2 * u, 3 * (1 - u) * u ** 2, u ** 3
    x = b0 * ax + b1 * C1x + b2 * C2x + b3 * tx
    y = b0 * ay + b1 * C1y + b2 * C2y + b3 * ty
    cu = ease_io((t - T_GO - delay - dur * .35) / (dur * .6))[:, None]
    col = C0 * (1 - cu) + C1 * cu
    a0 = 1 / mult
    alpha = a0 + (1 - a0) * np.clip(u * 1.4, 0, 1)
    gt = np.clip((t - T_DIS) / 1.1, 0, 1)
    gx = Gx + gdx / gdn * Gv * ease_out(np.full(len(gi), gt)); gy = Gy + gdy / gdn * Gv * ease_out(np.full(len(gi), gt)) - 20 * gt
    ga = (1 - gt) ** 1.5
    return x, y, col, alpha, gx, gy, Gc, np.full(len(gi), ga)

# splat kernel: 4x4 taps, cone falloff
OFF = np.array([(i, j) for j in range(-1, 3) for i in range(-1, 3)], np.float32)
R = 1.6

def splat(x, y, col, alpha):
    fx, fy = np.floor(x), np.floor(y)
    px = fx[:, None] + OFF[None, :, 0]; py = fy[:, None] + OFF[None, :, 1]
    d = np.hypot(px + .5 - x[:, None], py + .5 - y[:, None])
    w = np.clip(1 - d / R, 0, 1) * alpha[:, None]
    ok = (px >= 0) & (px < W) & (py >= 0) & (py < H) & (w > 0)
    idx = (py[ok] * W + px[ok]).astype(np.int64); ww = w[ok]
    cc = np.repeat(col[:, None, :], 16, 1)[ok]
    A = np.bincount(idx, ww, W * H)
    C = np.stack([np.bincount(idx, ww * cc[:, k], W * H) for k in range(3)], -1)
    return A.reshape(H, W), C.reshape(H, W, 3)

def draw_particles(frame, t, strength=1.0):
    x, y, col, al, gx, gy, gc, ga = particle_state(t)
    xs, ys, cs, as_ = [x, gx], [y, gy], [col, gc], [al, ga]
    # motion trails from earlier samples, weighted by speed
    for k, (lag, wgt) in enumerate(((1 / 60, .55), (2 / 60, .3))):
        px, py, *_ = particle_state(t - lag)
        sp = np.hypot(x - px, y - py) / lag
        f = np.clip(sp / 500, 0, 1) * wgt
        m = f > .02
        xs.append(px[m]); ys.append(py[m]); cs.append(col[m]); as_.append(al[m] * f[m])
    A, C = splat(np.concatenate(xs), np.concatenate(ys), np.concatenate(cs), np.concatenate(as_) * strength)
    cov = 1 - np.exp(-1.9 * A)
    colr = C / np.maximum(A, 1e-6)[..., None]
    frame[:] = frame * (1 - cov[..., None]) + colr * cov[..., None]


# ---------------------------------------------------------------- path + tail elements
PATH_Y = LOCK_BOX[3] + 58
PX0, PX1 = LOCK_BOX[2] - 10, LOCK_BOX[0] + 10          # draws right -> left
PATH_PTS = [(PX0 + (PX1 - PX0) * s, PATH_Y + 11 * math.sin(s * math.pi * 2.3 + .4) * (1 - .3 * s)) for s in np.linspace(0, 1, 240)]

def path_layer(p):
    """partial blue path (0..1) rendered at 2x then downsampled."""
    S = 2
    n = max(2, int(len(PATH_PTS) * p))
    xs = [q[0] for q in PATH_PTS]; ys = [q[1] for q in PATH_PTS]
    bx0, by0 = int(min(xs)) - 30, int(min(ys)) - 30
    bw, bh = int(max(xs) - min(xs)) + 60, int(max(ys) - min(ys)) + 60
    im = Image.new("RGBA", (bw * S, bh * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [((q[0] - bx0) * S, (q[1] - by0) * S) for q in PATH_PTS[:n]]
    d.line(pts, fill=BLUE + (255,), width=7 * S, joint="curve")
    r = 3.5 * S
    for q in (pts[0], pts[-1]): d.ellipse((q[0] - r, q[1] - r, q[0] + r, q[1] + r), fill=BLUE + (255,))
    hx, hy = pts[-1]
    if p < 1:
        d.ellipse((hx - 22 * S / 2, hy - 22 * S / 2, hx + 22 * S / 2, hy + 22 * S / 2), fill=BLUE + (60,))
    d.ellipse((hx - 9 * S, hy - 9 * S, hx + 9 * S, hy + 9 * S), fill=BLUE + (255,))
    return im.resize((bw, bh), Image.LANCZOS), bx0, by0


# ---------------------------------------------------------------- frame
def render(t):
    fr = np.empty((H, W, 3), np.float32); fr[:] = PAPER
    # --- intro logos
    a_in_g = ease_out(ramp(t, .3, 1.3)); a_in_e = ease_out(ramp(t, .45, 1.45))
    drift = DRIFT * (1 - ease_io(ramp(t, 1.0, T_DIS)))
    flo = math.sin(t * 2.1) * 3 * (1 - ramp(t, 2.2, T_DIS))
    crisp_src = 1 - ramp(t, T_DIS, T_DIS + .35)
    if crisp_src > 0:
        over(fr, geted, GX_END - drift - 70 * (1 - a_in_g), GY + flo, a_in_g * crisp_src)
        over(fr, eshra, EX_END + drift + 70 * (1 - a_in_e), EY - flo, a_in_e * crisp_src)
        ax = ease_out(ramp(t, .9, 1.4)) * (1 - ramp(t, 2.2, 2.7))
        over(fr, times, 960 - times.width / 2, CY - times.height / 2 - 4, ax, scale=1)
    # --- particles
    if T_DIS <= t <= 7.2:
        strength = ramp(t, T_DIS, T_DIS + .3) * (1 - ramp(t, 6.7, 7.15))
        draw_particles(fr, t, strength)
    # --- crisp lockup with a soft pop
    a_lock = ramp(t, 6.6, 7.15)
    if a_lock > 0:
        pop = 1 + .016 * math.sin(math.pi * ramp(t, 7.25, 7.8))
        fl = math.sin((t - 7) * 1.4) * 2.5 * ramp(t, 9, 10)
        fade = 1 - ramp(t, 12.3, 13.0)
        cx, cy = (LOCK_BOX[0] + LOCK_BOX[2]) / 2, (LOCK_BOX[1] + LOCK_BOX[3]) / 2
        over(fr, LOCK_IM, cx + (LOCK_OX - cx) * pop, cy + (LOCK_OY - cy) * pop + fl, a_lock * fade, scale=pop)
        # path
        pp = ease_io(ramp(t, 7.5, 8.8))
        if pp > 0:
            im, bx, by = path_layer(float(pp))
            over(fr, im, bx, by + fl, fade)
        # taglines
        a_t = ease_out(ramp(t, 8.3, 9.2))
        ty0 = PATH_Y + 44 + 14 * (1 - a_t) + fl
        over(fr, tag_en, 960 - 24 - tag_en.width, ty0, a_t * fade)
        over(fr, tag_ar, 960 + 24, ty0 - 2, a_t * fade)
        dotx = 960 - 3
        if a_t > 0:
            d = Image.new("RGBA", (6, 6), (0, 0, 0, 0)); ImageDraw.Draw(d).ellipse((0, 0, 5, 5), fill=INK2 + (255,))
            over(fr, d, dotx, ty0 + tag_en.height / 2 - 3, a_t * fade)
        # by GET ED x Eshra7ly
        a_b = ease_out(ramp(t, 9.2, 10.0))
        row = [by_txt, small_geted, small_x, small_eshra]; gaps = 22
        tw = sum(i.width for i in row) + gaps * (len(row) - 1)
        x = 960 - tw / 2; by_c = 960 + 10 * (1 - a_b)
        for i in row:
            over(fr, i, x, by_c - i.height / 2, a_b * fade); x += i.width + gaps
    return np.clip(fr + .5, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- audio
def synth():
    n = int(DUR * SR); t = np.arange(n) / SR
    L = np.zeros(n); Rt = np.zeros(n)
    def note(freq, t0, t1, amp, pan, att=1.4, rel=1.6):
        env = np.clip((t - t0) / att, 0, 1) * np.clip((t1 - t) / rel, 0, 1)
        env = env ** 1.6
        s = np.zeros(n)
        for det in (-4, 4):
            f = freq * 2 ** (det / 1200)
            ph = 2 * np.pi * f * t
            s += np.sin(ph) + .28 * np.sin(2 * ph) + .08 * np.sin(3 * ph)
        s *= env * amp * (1 + .12 * np.sin(2 * np.pi * .23 * t + freq))
        return s * (1 - pan) , s * pan
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    chords = [  # (start, end, midi notes)
        (0.0, 3.9, [41, 60, 64, 67, 69]),      # Fmaj9
        (3.0, 7.6, [38, 57, 60, 64, 65, 69]),  # Dm9 (tension while it forms)
        (6.8, 13.0, [41, 60, 62, 67, 69, 74]), # F6/9 arrival
    ]
    for a, b, notes in chords:
        for i, m in enumerate(notes):
            amp = .05 if m < 50 else .028
            l, r = note(hz(m), a, b, amp, .3 + .4 * (i / max(1, len(notes) - 1)))
            L += l; Rt += r
    # whoosh on dissolve, rising swell into landing
    def noise_sweep(t0, t1, f0, f1, amp, pan):
        m = (t >= t0) & (t < t1); k = np.where(m)[0]
        if not len(k): return
        x = rng.normal(0, 1, len(k)); y = np.zeros(len(k)); lp = bp = 0.0
        prog = (t[k] - t0) / (t1 - t0)
        fc = f0 * (f1 / f0) ** prog
        env = np.sin(np.pi * prog) ** 2
        for i in range(len(k)):  # state-variable bandpass
            f = 2 * math.sin(math.pi * fc[i] / SR)
            hp = x[i] - lp - .6 * bp; bp += f * hp; lp += f * bp; y[i] = bp
        y *= env * amp / (np.abs(y).max() + 1e-9)
        L[k] += y * (1 - pan); Rt[k] += y * pan
    noise_sweep(2.75, 3.9, 400, 3200, .09, .35)
    noise_sweep(5.3, 7.3, 300, 5000, .06, .65)
    # sparkles as particles land
    land = T_GO + delay + dur
    for tt in rng.choice(np.sort(land), 46, replace=False):
        f = hz(rng.choice([81, 84, 86, 88, 91, 93]))
        k0 = int(tt * SR); k1 = min(n, k0 + int(.18 * SR))
        tt_ = np.arange(k1 - k0) / SR
        s = np.sin(2 * np.pi * f * tt_) * np.exp(-tt_ / .045) * .012
        p = rng.uniform(.2, .8); L[k0:k1] += s * (1 - p); Rt[k0:k1] += s * p
    # chime + soft low bloom on arrival
    for f0, t0, a in ((hz(77), 7.27, .06), (hz(84), 7.35, .045), (hz(89), 7.43, .03)):
        k0 = int(t0 * SR); tt_ = np.arange(n - k0) / SR
        s = sum(np.sin(2 * np.pi * f0 * r * tt_) * g * np.exp(-tt_ / d) for r, g, d in ((1, 1, 2.2), (2, .4, 1.2), (3.01, .18, .7), (4.2, .08, .4)))
        s *= a; L[k0:] += s * .55; Rt[k0:] += s * .45
    k0 = int(7.25 * SR); tt_ = np.arange(n - k0) / SR
    boom = np.sin(2 * np.pi * (43.65 * tt_ + 6 * (1 - np.exp(-tt_ / .08)))) * np.exp(-tt_ / .9) * .09
    L[k0:] += boom; Rt[k0:] += boom
    # reverb: FFT convolution with decaying noise
    irn = int(2.4 * SR); it = np.arange(irn) / SR
    def ir(seed):
        r = np.random.default_rng(seed).normal(0, 1, irn) * np.exp(-it / .55)
        r = np.convolve(r, np.ones(6) / 6, "same"); r[0] = 0; return r / np.sqrt((r ** 2).sum())
    def conv(x, h):
        m = len(x) + len(h); N2 = 1 << (m - 1).bit_length()
        return np.fft.irfft(np.fft.rfft(x, N2) * np.fft.rfft(h, N2), N2)[:len(x)]
    Lw, Rw = conv(L, ir(1)), conv(Rt, ir(2))
    L, Rt = L * .75 + Lw * .5, Rt * .75 + Rw * .5
    fade = np.clip(t / 1.0, 0, 1) * np.clip((DUR - t) / 1.2, 0, 1)
    L *= fade; Rt *= fade
    peak = max(np.abs(L).max(), np.abs(Rt).max())
    g = 10 ** (-7 / 20) / peak   # keep it subtle: peak at -7 dBFS
    out = (np.stack([L, Rt], -1) * g * 32767).astype(np.int16)
    p = ROOT / "masar-logo-morph.wav"
    with wave.open(str(p), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())
    return p


# ---------------------------------------------------------------- main
if __name__ == "__main__":
    if "--preview" in sys.argv:
        out = ROOT / "preview"; out.mkdir(exist_ok=True)
        for t in (1.8, 3.2, 4.2, 5.2, 6.2, 7.6, 10.0):
            Image.fromarray(render(t)).save(out / f"t{t:05.2f}.png")
        print("preview written", N, "particles,", len(gi), "ghosts"); sys.exit()
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    wav = synth()
    mp4 = ROOT / "masar-logo-morph.mp4"
    cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(wav), "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(mp4)]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int(DUR * FPS)
    for i in range(total):
        pr.stdin.write(render(i / FPS).tobytes())
        if i % 30 == 0: print(f"frame {i}/{total}", flush=True)
    pr.stdin.close(); pr.wait()
    Image.fromarray(render(10.0)).save(ROOT / "masar-logo-morph-poster.png")
    print("wrote", mp4)
