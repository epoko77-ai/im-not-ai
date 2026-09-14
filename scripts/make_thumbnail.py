"""Generate social preview thumbnail for im-not-ai.

Size 1280x640 (GitHub social preview recommended).
Warm cream background, typographic minimalism with before/after exemplar.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HOME = Path.home()
FONT_DIR = HOME / "Library/Fonts"
OUT = Path(__file__).resolve().parent.parent / "assets" / "social-preview.png"
OUT.parent.mkdir(parents=True, exist_ok=True)


def F(weight, size):
    names = {
        "black": "Pretendard-Black.otf",
        "xbold": "Pretendard-ExtraBold.otf",
        "bold": "Pretendard-Bold.otf",
        "semi": "Pretendard-SemiBold.otf",
        "med": "Pretendard-Medium.otf",
        "reg": "Pretendard-Regular.otf",
        "light": "Pretendard-Light.otf",
    }
    return ImageFont.truetype(str(FONT_DIR / names[weight]), size)


W, H = 1280, 640
BG = (245, 241, 232)
INK = (26, 26, 26)
MUTED = (110, 104, 98)
DIVIDER = (218, 208, 192)
STRIKE = (196, 78, 60)
AFTER = (45, 96, 74)
BADGE_BG = (228, 218, 202)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

PAD = 72

# ---------- Header ----------
d.text((PAD, 56), "im-not-ai", font=F("black", 82), fill=INK)

subtitle = "한글 AI 티 제거기"
sub_f = F("med", 26)
sw = d.textlength(subtitle, font=sub_f)
d.text((W - PAD - sw, 94), subtitle, font=sub_f, fill=MUTED)

# divider
d.line([(PAD, 170), (W - PAD, 170)], fill=DIVIDER, width=2)


# ---------- Before / After exemplar ----------

def strike_text(x, y, text, font_, ink=INK, strike_color=STRIKE):
    """Draw text and overlay a strike line through the middle."""
    d.text((x, y), text, font=font_, fill=ink)
    bb = d.textbbox((x, y), text, font=font_)
    mid = (bb[1] + bb[3]) // 2 + 2
    d.line([(bb[0] - 2, mid), (bb[2] + 2, mid)], fill=strike_color, width=3)
    return bb[2]


def plain(x, y, text, font_, color=INK):
    d.text((x, y), text, font=font_, fill=color)
    return d.textbbox((x, y), text, font=font_)[2]


body_f = F("semi", 36)
label_f = F("bold", 16)

# Labels
label_y = 218
d.text((PAD, label_y), "BEFORE  (AI)", font=label_f, fill=STRIKE)
d.text((W // 2 + 40, label_y), "AFTER  (사람)", font=label_f, fill=AFTER)

# Row 1 — 수동태
y1 = 260
x = PAD
x = plain(x, y1, "지속될 것으로 ", body_f)
x = strike_text(x, y1, "보여진다", body_f)
x = plain(x, y1, ".", body_f)

arrow_x = W // 2 - 30
d.text((arrow_x, y1 - 2), "→", font=F("bold", 40), fill=MUTED)

plain(W // 2 + 40, y1, "계속될 것이다.", body_f, color=AFTER)

# Row 2 — 대구 (단순한 X가 아닌 Y)
y2 = 332
x = PAD
x = strike_text(x, y2, "단순한", body_f)
x = plain(x, y2, " 트렌드가 ", body_f)
x = strike_text(x, y2, "아닌", body_f)
x = plain(x, y2, " 흐름이다.", body_f)

d.text((arrow_x, y2 - 2), "→", font=F("bold", 40), fill=MUTED)
plain(W // 2 + 40, y2, "시대가 바뀌고 있다.", body_f, color=AFTER)

# Row 3 — 지시대명사 (이것은/그것은)
y3 = 404
x = PAD
x = strike_text(x, y3, "이것은", body_f)
x = plain(x, y3, " 변화의 신호이다.", body_f)

d.text((arrow_x, y3 - 2), "→", font=F("bold", 40), fill=MUTED)
plain(W // 2 + 40, y3, "변화가 시작됐다.", body_f, color=AFTER)


# ---------- Stats row ----------
d.line([(PAD, 480), (W - PAD, 480)], fill=DIVIDER, width=1)

stat_y = 510
# Score badge
score_f = F("xbold", 44)
score_label_f = F("semi", 14)

d.text((PAD, stat_y - 4), "74.5", font=score_f, fill=STRIKE)
arrow_gap = d.textlength("74.5", font=score_f)
d.text((PAD + arrow_gap + 14, stat_y + 10), "→", font=F("med", 32), fill=MUTED)
d.text((PAD + arrow_gap + 62, stat_y - 4), "9.5", font=score_f, fill=AFTER)

after_x = PAD + arrow_gap + 62 + d.textlength("9.5", font=score_f)
d.text((PAD, stat_y + 52), "AI-tell score", font=score_label_f, fill=MUTED)

# A+ badge
badge_x = after_x + 40
badge_w, badge_h = 88, 44
d.rounded_rectangle(
    [(badge_x, stat_y + 2), (badge_x + badge_w, stat_y + 2 + badge_h)],
    radius=22, fill=AFTER
)
grade = "A+"
gf = F("xbold", 26)
gw = d.textlength(grade, font=gf)
d.text(
    (badge_x + (badge_w - gw) // 2, stat_y + 8),
    grade, font=gf, fill=(255, 255, 255)
)

# Categories · patterns
meta = "10 categories  ·  40+ patterns  ·  v1.1"
meta_f = F("med", 22)
mw = d.textlength(meta, font=meta_f)
d.text((badge_x + badge_w + 32, stat_y + 12), meta, font=meta_f, fill=MUTED)


# ---------- Footer: URL ----------
url = "github.com/epoko77-ai/im-not-ai"
url_f = F("semi", 22)
uw = d.textlength(url, font=url_f)
d.text((W - PAD - uw, H - 50), url, font=url_f, fill=INK)


img.save(OUT, "PNG", optimize=True)
print(f"saved: {OUT}  ({OUT.stat().st_size // 1024} KB)")
