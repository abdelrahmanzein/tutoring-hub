"""Reference implementation: examiner-style annotated scripts (Zein's marking standard).

Renders each student's scanned pages with handwriting-style red marking ON the page (no margin):
M1/A1 stamps, ticks, crosses, wavy underlines, ringed part totals, and comments placed in free
space with an arrow to the error. Annotations never overlap (enforced + verified). Each script gets a
typed cover page: raw mark, % of cap, level, boundary strip, per-question marks, notes, and feedback.

This is the behavioural spec for the Tutoring Hub feature. It is Python (reportlab, Pillow, numpy,
scipy, fontTools); the app will likely port it to JS (see docs/assessment-feature.md).

Config via environment variables:
  HW_FONT_DIR   folder containing NoteworthyLight.ttf and NoteworthyBold.ttf (extracted from
                /System/Library/Fonts/Noteworthy.ttc on macOS; not committed, licence: Apple)
  DEJAVU_DIR    folder with DejaVuSans*.ttf (default /usr/share/fonts/truetype/dejavu/)
"""
import sys, os, io, re, math, random, json
import numpy as np
from scipy import ndimage
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.utils import ImageReader, simpleSplit
from fontTools.ttLib import TTFont as FT
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from boundaries import boundaries, grade as _grade

FD = os.environ.get("HW_FONT_DIR", os.path.expanduser("~/Library/Fonts/handwriting"))
D = os.environ.get("DEJAVU_DIR", "/usr/share/fonts/truetype/dejavu/")
pdfmetrics.registerFont(TTFont("HW", os.path.join(FD, "NoteworthyLight.ttf")))
pdfmetrics.registerFont(TTFont("HWB", os.path.join(FD, "NoteworthyBold.ttf")))
for n, f in [("DV", "DejaVuSans.ttf"), ("DVB", "DejaVuSans-Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(n, os.path.join(D, f)))
CMAP = FT(os.path.join(FD, "NoteworthyLight.ttf")).getBestCmap()
RED = Color(0.82, 0.07, 0.11); INK = HexColor("#222222"); GREY = HexColor("#666666")
H = 842.0
CS = 12.5          # comment font size (pt)
LH = CS * 1.18

# ---------- handwriting text with glyph fallback ----------
def runs(text):
    """Split text into (string, font, size_factor, rise_factor) runs."""
    out = []; i = 0
    while i < len(text):
        ch = text[i]
        if ch == "⁻" and i + 1 < len(text) and text[i + 1] == "¹":
            out.append(("-1", "HW", .72, .45)); i += 2; continue
        if ord(ch) in CMAP or ch in " \n":
            f = "HW"
        else:
            f = "DV"
        if out and out[-1][1] == f and out[-1][2] == 1:
            out[-1] = (out[-1][0] + ch, f, 1, 0)
        else:
            out.append((ch, f, 1, 0))
        i += 1
    return out

def width(text, size):
    return sum(pdfmetrics.stringWidth(s, f, size * k * (0.9 if f == "DV" else 1)) for s, f, k, _ in runs(text))

def draw_line(c, x, y, text, size, rng, font="HW"):
    c.saveState(); c.translate(x, y); c.rotate(rng.uniform(-1.2, 1.2))
    cx = 0.0
    for s, f, k, rise in runs(text):
        fn = font if f == "HW" else "DV"
        sz = size * k * (0.9 if f == "DV" else 1)
        c.setFont(fn, sz)
        for word in re.split(r"( )", s):
            if not word: continue
            c.drawString(cx, rise * size + rng.uniform(-.5, .5), word)
            cx += pdfmetrics.stringWidth(word, fn, sz)
    c.restoreState()

def wrap(text, maxw, size):
    lines, cur = [], ""
    for w in text.split(" "):
        t = (cur + " " + w).strip()
        if width(t, size) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

# ---------- hand-drawn marks ----------
def jitter_path(c, pts, rng, lw=1.6):
    c.setStrokeColor(RED); c.setLineWidth(lw); c.setLineCap(1); c.setLineJoin(1)
    p = c.beginPath(); p.moveTo(*pts[0])
    for a, b in zip(pts[:-1], pts[1:]):
        mx, my = (a[0] + b[0]) / 2 + rng.uniform(-.8, .8), (a[1] + b[1]) / 2 + rng.uniform(-.8, .8)
        p.curveTo(mx, my, mx, my, *b)
    c.drawPath(p, stroke=1, fill=0)

def tick(c, x, y, rng, s=8):
    jitter_path(c, [(x - s * .55, y + s * .05), (x - s * .1, y - s * .55), (x + s * .75, y + s * .85)], rng, 1.7)

def cross(c, x, y, rng, s=6):
    jitter_path(c, [(x - s, y - s), (x + s, y + s)], rng, 1.7)
    jitter_path(c, [(x - s, y + s), (x + s, y - s)], rng, 1.7)

def wavy(c, x1, x2, y, rng):
    pts = []; x = x1; up = True
    while x < x2:
        pts.append((x, y + (1.8 if up else -1.8) + rng.uniform(-.4, .4))); x += 3.5; up = not up
    if len(pts) > 1: jitter_path(c, pts, rng, 1.1)

def ring(c, cx, cy, r, rng):
    c.setStrokeColor(RED); c.setLineWidth(1.4)
    p = c.beginPath(); a0 = rng.uniform(0, 6.28); n = 26
    for i in range(n + 3):
        a = a0 + 2 * math.pi * i / n; rr = r * (1 + rng.uniform(-.06, .06)) + i * .05
        pt = (cx + rr * 1.08 * math.cos(a), cy + rr * .92 * math.sin(a))
        p.moveTo(*pt) if i == 0 else p.lineTo(*pt)
    c.drawPath(p, stroke=1, fill=0)

def arrow(c, x0, y0, x1, y1, rng):
    """Curved hand arrow from (x0,y0) to (x1,y1)."""
    d = math.hypot(x1 - x0, y1 - y0)
    if d < 14: return
    ux, uy = (x1 - x0) / d, (y1 - y0) / d
    x1, y1 = x1 - ux * 7, y1 - uy * 7  # stop short of the target
    bend = min(18, d * .15)
    mx, my = (x0 + x1) / 2 - uy * bend, (y0 + y1) / 2 + ux * bend
    c.setStrokeColor(RED); c.setLineWidth(1.1); c.setLineCap(1)
    p = c.beginPath(); p.moveTo(x0, y0); p.curveTo(mx, my, mx, my, x1, y1); c.drawPath(p, stroke=1, fill=0)
    ang = math.atan2(y1 - my, x1 - mx)
    for da in (2.6, -2.6):
        c.line(x1, y1, x1 + 7 * math.cos(ang + da), y1 + 7 * math.sin(ang + da))

# ---------- free-space finder ----------
class Space:
    def __init__(self, im, w):
        g = np.asarray(im.convert("L").resize((int(im.width * 400 / im.height), 400)), dtype=np.float32)
        bg = ndimage.median_filter(g, size=25)
        rgb = np.asarray(im.convert("RGB").resize((g.shape[1], 400)), dtype=np.float32)
        sat = rgb.max(2) - rgb.min(2)
        ink = ((bg - g) > 38) | ((sat > 70) & ((bg - g) > 15))
        ink = ndimage.binary_dilation(ink, iterations=2)
        self.ink = ink.astype(np.float32)
        self.used = np.zeros_like(self.ink)
        self.sx = g.shape[1] / w; self.sy = 400 / H; self.w = w
        self.rects = []
    def overlaps(self, x, y, bw, bh):
        return any(x < X + W and X < x + bw and y < Y + Hh and Y < y + bh for X, Y, W, Hh in self.rects)
    def free_spot(self, x, y, bw, bh, step=6):
        """Nudge a fixed mark (stamp/tick/cross) until it clears every earlier annotation."""
        for r in range(0, 12):
            for dx, dy in ((0, 0), (1, 0), (0, -1), (0, 1), (-1, 0), (1, -1), (1, 1), (-1, -1), (-1, 1)):
                nx, ny = x + dx * r * step, y + dy * r * step
                if not self.overlaps(nx, ny, bw, bh): return nx, ny
        return x, y
    def block(self, x, y, bw, bh, val=1.0):
        self.rects.append((x, y, bw, bh))
        a, b = int(x * self.sx), int((H - y - bh) * self.sy)
        self.used[max(b, 0):max(b + int(bh * self.sy) + 1, 0), max(a, 0):max(a + int(bw * self.sx) + 1, 0)] = val
    def find(self, ax, ay, bw, bh, dw=12):
        gw, gh = max(int(bw * self.sx), 1), max(int(bh * self.sy), 1)
        ny, nx = self.ink.shape
        if gw >= nx - 4 or gh >= ny - 4: return None
        S = np.pad(self.ink, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        box = (S[gh:, gw:] - S[:-gh, gw:] - S[gh:, :-gw] + S[:-gh, :-gw]) / (gw * gh)
        U = np.pad(ndimage.binary_dilation(self.used > 0, iterations=3).astype(np.float32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        ubox = (U[gh:, gw:] - U[:-gh, gw:] - U[gh:, :-gw] + U[:-gh, :-gw])
        box = box + (ubox > 0) * 1000.0   # never on top of another annotation
        # keep 2 px from edges
        box[:2, :] = 9; box[:, :2] = 9; box[-2:, :] = 9; box[:, -2:] = 9
        Y, X = np.mgrid[0:box.shape[0], 0:box.shape[1]]
        axg, ayg = ax * self.sx, (H - ay) * self.sy
        cxg, cyg = X + gw / 2, Y + gh / 2
        dist = np.hypot(cxg - axg, (cyg - ayg) * 1.0) / max(nx, ny)
        score = box * 60 + dist * dw
        i = np.unravel_index(np.argmin(score), score.shape)
        y0, x0 = i
        return (x0 / self.sx - 1, H - (y0 + gh) / self.sy - 1, box[i], score[i])

def place_text(c, sp, txt, ax, ay, rng, size=CS, anchor=True):
    best = None
    for frac in (.26, .34, .44, .58):
        maxw = sp.w * frac
        lines = wrap(txt, maxw, size)
        bw = max(width(l, size) for l in lines) + 6; bh = LH * len(lines) + 4
        r = sp.find(ax, ay, bw, bh)
        if r and (best is None or r[3] < best[0][3]): best = (r, lines, bw, bh)
    (x, y, inkfrac, _), lines, bw, bh = best
    if inkfrac > .06:   # no clean space: put a soft white patch behind the note
        c.setFillColor(Color(1, 1, 1, alpha=.86)); c.setStrokeColor(Color(1, 1, 1, alpha=0))
        c.roundRect(x - 2, y - 2, bw + 4, bh + 4, 5, stroke=0, fill=1)
    c.setFillColor(RED)
    for i, l in enumerate(lines):
        draw_line(c, x + 3, y + bh - LH * (i + 1) + 3, l, size, rng)
    sp.block(x - 3, y - 3, bw + 6, bh + 6)
    if anchor:
        # arrow from nearest box edge to anchor when the note isn't right next to it
        bx = min(max(ax, x), x + bw); by = min(max(ay, y), y + bh)
        if math.hypot(bx - ax, by - ay) > 22: arrow(c, bx, by, ax, ay, rng)

LOG = []
def page(c, png, items, seed):
    rng = random.Random(seed)
    im = Image.open(png).convert("RGB"); w = H * im.width / im.height
    c.setPageSize((w, H)); b = io.BytesIO(); im.save(b, "JPEG", quality=80); b.seek(0)
    c.drawImage(ImageReader(b), 0, 0, w, H)
    sp = Space(im, w)
    P = lambda x, y: (w * x / 100, H - H * y / 100)
    c.setFillColor(RED)
    # 1) marks on the work
    for it in items:
        k = it[0]
        if k == "s":
            x, y = P(it[1], it[2]); txt = it[3]
            fs = 14; tw = width(txt, fs)
            bx, by = sp.free_spot(x - tw / 2 - 2, y - 6, tw + 4, 18)
            draw_line(c, bx + 2, by + 3, txt, fs, rng, font="HWB"); sp.block(bx, by, tw + 4, 18)
        elif k == "t":
            x, y = P(it[1], it[2]); bx, by = sp.free_spot(x - 6, y - 6, 14, 14)
            tick(c, bx + 6, by + 6, rng); sp.block(bx, by, 14, 14)
        elif k == "x":
            x, y = P(it[1], it[2]); bx, by = sp.free_spot(x - 7, y - 7, 14, 14)
            cross(c, bx + 7, by + 7, rng); sp.block(bx, by, 14, 14)
        elif k == "u":
            x1, yy = P(it[1], it[3]); x2, _ = P(it[2], it[3]); wavy(c, x1, x2, yy - 2, rng); sp.block(x1, yy - 5, x2 - x1, 6)
    # 2) question totals: ringed mark written near the right of that line
    for it in items:
        if it[0] != "r": continue
        _, yy, lab, g, m = it
        txt = f"{lab}"; fs = 12
        lw = width(txt, fs); bw, bh = lw + 46, 26
        r = sp.find(w * .93, H - H * yy / 100, bw, bh, dw=45)
        x, y = r[0], r[1]
        if r[2] > .03:
            c.setFillColor(Color(1, 1, 1, alpha=.86)); c.roundRect(x, y, bw, bh, 5, stroke=0, fill=1)
        c.setFillColor(RED)
        draw_line(c, x + 2, y + 8, txt, fs, rng)
        cx = x + lw + 17; ring(c, cx, y + 12, 10.5, rng)
        draw_line(c, cx - width(str(g), 15) / 2, y + 7, str(g), 15, rng, font="HWB")
        draw_line(c, cx + 13, y + 5, f"/{m}", 11, rng)
        sp.block(x - 2, y - 2, bw + 4, bh + 4)
    # 3) comments in free space on the page, with an arrow to what they refer to
    for it in items:
        if it[0] != "c": continue
        _, ax, yy, txt = it
        if ax is None: place_text(c, sp, txt, w * .5, H - H * yy / 100, rng, anchor=False)
        else: place_text(c, sp, txt, *P(ax, yy), rng)
    LOG.append((png, list(sp.rects)))
    c.showPage()

def cover(c, quiz, st, rings, BOUNDS):
    name, total, notes = st["name"], st["total"], st.get("notes", [])
    CAP, AVAIL, MAXQ = quiz["cap"], quiz["available"], quiz["questions"]
    W = 595.0; c.setPageSize((W, H)); y = H - 60
    c.setFont("DVB", 18); c.setFillColor(INK); c.drawString(50, y, quiz["title"])
    y -= 26; c.setFont("DV", 13); c.drawString(50, y, name)
    lows = BOUNDS; grade = _grade(total, lows); pct = 100 * total / CAP
    c.setFillColor(RED); c.setFont("DVB", 26); c.drawRightString(W - 50, y + 8, f"{total} / {CAP}")
    c.setFont("DVB", 13); c.drawRightString(W - 50, y - 12, f"{pct:g}%  ·  Level {grade}")
    c.setFont("DV", 8.5); c.setFillColor(GREY)
    c.drawRightString(W - 50, y - 25, f"Raw mark {total} of {AVAIL} available · graded out of {CAP}")
    # boundaries strip
    yb = y - 50; bw = (W - 100) / 7
    edges = [0] + lows
    for g in range(7):
        x0 = 50 + bw * g; hi = (f"{edges[g+1]-1}" if g < 6 else "+")
        lab = f"{edges[g]}–{hi}" if g < 6 else f"{edges[g]}+"
        cur = (g + 1 == grade)
        c.setFillColor(RED if cur else HexColor("#F3F3F3")); c.setStrokeColor(HexColor("#BBBBBB"))
        c.rect(x0, yb - 16, bw, 30, stroke=1, fill=1)
        c.setFillColor(HexColor("#FFFFFF") if cur else INK); c.setFont("DVB", 10); c.drawCentredString(x0 + bw / 2, yb + 3, f"Level {g+1}")
        c.setFont("DV", 9); c.drawCentredString(x0 + bw / 2, yb - 10, lab)
    c.setFont("DV", 8.5); c.setFillColor(GREY)
    c.drawString(50, yb - 30, f"Class boundaries for this quiz (out of {CAP}; level 7 has no upper limit). Your level is highlighted.")
    y = yb - 40
    got = {k: 0 for k in MAXQ}
    for lab, g, m in rings: got[re.match(r"\d+", lab).group(0)] += g
    assert sum(got.values()) == total, (name, got, total)
    y -= 28; cw = (W - 100) / 9; c.setFillColor(INK); c.setFont("DVB", 10)
    for j, h in enumerate(["Question"] + [f"Q{k}" for k in MAXQ]): c.drawCentredString(50 + cw * (j + .5), y, h)
    y -= 18; c.setFont("DV", 10); c.drawCentredString(50 + cw * .5, y, "Marks"); c.setFillColor(RED)
    for j, k in enumerate(MAXQ): c.drawCentredString(50 + cw * (j + 1.5), y, f"{got[k]}/{MAXQ[k]}")
    c.setStrokeColor(HexColor("#BBBBBB")); c.line(50, y + 13, W - 50, y + 13); c.line(50, y - 6, W - 50, y - 6)
    y -= 30; c.setFillColor(INK)
    for n in notes:
        for ln in simpleSplit("Note: " + n, "DV", 10, W - 100): c.drawString(50, y, ln); y -= 14
        y -= 4
    fb = st["feedback"]; s, p, qs = fb["went_well"], fb["to_fix"], fb["resolve"]
    NEXT_STEP = quiz["next_step"]
    def need(n):
        nonlocal y
        if y - n < 50:
            c.showPage(); c.setPageSize((W, H)); y = H - 60
    def block(title, lines, bullet=True):
        nonlocal y
        need(40); y -= 8; c.setFont("DVB", 12); c.setFillColor(INK); c.drawString(50, y, title); y -= 18; c.setFont("DV", 10.5)
        for t in lines:
            wr = simpleSplit(t, "DV", 10.5, W - 120); need(14 * len(wr) + 3)
            for k, ln in enumerate(wr):
                if bullet and k == 0: c.drawString(58, y, "•")
                c.drawString(72, y, ln); y -= 14
            y -= 3
    block("What went well", s); block("What to fix", p)
    block("Next step", [NEXT_STEP.format(qs=", ".join(qs))], bullet=False)
    need(60); y -= 14; c.setFont("DV", 9); c.setFillColor(GREY)
    for ln in simpleSplit("How to read the marking: ✓ / ✗ show where a mark was gained or lost. M = method, A = accuracy (needs the M before it), "
                          "R = reasoning, AG = answer given; a mark in brackets, e.g. (M1), is implied by a correct answer. The ringed number on the page is your "
                          "mark for that part. Red comments explain what was missing.", "DV", 9, W - 100):
        c.drawString(50, y, ln); y -= 12
    c.showPage()


def build_script(quiz, st, page_dir, out_pdf, bounds):
    """quiz: fixtures quiz JSON; st: one student JSON; page_dir: folder with the scan PNGs."""
    rings = [(r[0], r[1], r[2]) for r in [(i[2], i[3], i[4]) for p in st["pages"] for i in p["items"] if i[0] == "r"]]
    rings += [tuple(x) for x in st.get("extra", [])]
    c = canvas.Canvas(out_pdf); c.setTitle(f'{st["name"]} – {quiz["title"]} – Marked')
    cover(c, quiz, st, rings, bounds)
    for k, p in enumerate(st["pages"]):
        page(c, os.path.join(page_dir, p["image"]), [tuple(i) for i in p["items"]], k * 7919 + len(st["name"]))
    c.save()

def overlaps():
    """Pairs of annotation rectangles that overlap (must be empty)."""
    bad = []
    for png, rects in LOG:
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, b = rects[i], rects[j]
                ox = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]); oy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
                if ox > 1 and oy > 1: bad.append((png, a, b))
    return bad

if __name__ == "__main__":
    # usage: python annotate.py fixtures/quiz.json fixtures/students.json PAGE_DIR OUT_DIR
    quiz = json.load(open(sys.argv[1])); studs = json.load(open(sys.argv[2]))
    bounds = boundaries([s["total"] for s in studs], quiz["cap"])[5]
    os.makedirs(sys.argv[4], exist_ok=True)
    for s in studs:
        build_script(quiz, s, sys.argv[3], os.path.join(sys.argv[4], f'{s["name"]} - Marked.pdf'), bounds)
    print("overlaps:", len(overlaps()))
