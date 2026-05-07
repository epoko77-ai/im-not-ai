"""Build assets/social-preview.png for v2.0 — 한국 번역학계 8유형 흡수.

기존 v1.1 디자인 톤(베이지 #F4EFE5 · 짙은 녹색 #2D5C3F · 빨강 #C0573F · BEFORE/AFTER
2단 분할)을 유지하되, 메시지를 v2.0 신규 패턴(영-한 번역학계 흔적) 3건으로 교체.
1280×640 PNG 출력. Pretendard ExtraBold/Bold/SemiBold/Medium/Regular 사용.
"""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Paths & tokens
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
OUT = ASSETS / "social-preview.png"

FONT_DIR = Path.home() / "Library" / "Fonts"
F_BLACK = str(FONT_DIR / "Pretendard-Black.otf")
F_EBOLD = str(FONT_DIR / "Pretendard-ExtraBold.otf")
F_BOLD = str(FONT_DIR / "Pretendard-Bold.otf")
F_SEMI = str(FONT_DIR / "Pretendard-SemiBold.otf")
F_MED = str(FONT_DIR / "Pretendard-Medium.otf")
F_REG = str(FONT_DIR / "Pretendard-Regular.otf")

# Design tokens
BG = "#F4EFE5"
TITLE = "#1F2A1F"
SUB = "#5C5042"
RULE = "#C9BEA9"
BEFORE = "#C0573F"
AFTER = "#2D5C3F"
META = "#7A6E5C"
LINK = "#2D5C3F"
STRIKE = "#C0573F"

W, H = 1280, 640

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def draw_text(d: ImageDraw.ImageDraw, xy, text: str, f, fill, anchor="la"):
    d.text(xy, text, font=f, fill=fill, anchor=anchor)


def text_w(f, text: str) -> int:
    bbox = f.getbbox(text)
    return bbox[2] - bbox[0]


def draw_strike(d: ImageDraw.ImageDraw, x: int, y: int, length: int, color=STRIKE, width: int = 3):
    d.line([(x, y), (x + length, y)], fill=color, width=width)


def draw_arrow(d: ImageDraw.ImageDraw, x: int, y: int, color=TITLE, size: int = 18):
    """단순 화살표 →"""
    d.line([(x, y), (x + size, y)], fill=color, width=2)
    d.line([(x + size - 6, y - 5), (x + size, y), (x + size - 6, y + 5)], fill=color, width=2)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def build():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Header — 좌상단 제목 + 우상단 부제 2줄
    f_title = font(F_BLACK, 80)
    f_sub = font(F_MED, 22)
    f_sub_em = font(F_SEMI, 22)

    draw_text(d, (72, 70), "im-not-ai", f_title, TITLE)
    # 우상단 — 한글 AI 티 제거기
    sub_line1 = "한글 AI 티 제거기"
    sub_line2 = "v2.0 · 한국 번역학계 8유형 흡수"
    draw_text(d, (W - 72, 80), sub_line1, f_sub, SUB, anchor="ra")
    draw_text(d, (W - 72, 112), sub_line2, f_sub_em, AFTER, anchor="ra")

    # Top rule
    d.line([(72, 178), (W - 72, 178)], fill=RULE, width=2)

    # Section labels
    f_label = font(F_BOLD, 18)
    draw_text(d, (72, 198), "BEFORE  (AI · 영-한 번역체)", f_label, BEFORE)
    draw_text(d, (680, 198), "AFTER  (자연 한국어)", f_label, AFTER)

    # Three pattern rows: A-16 대명사 / A-19 이중조사 / A-18 관계절
    f_ex = font(F_SEMI, 26)
    f_pat = font(F_REG, 14)

    rows = [
        # (before_text, before_strikes_index_pairs, after_text, label_left, label_right)
        # strikes: list of (start_idx, end_idx) char ranges to strike
        (
            "그는 그의 시계를 보았다.",
            [(3, 5)],  # "그의"
            "시계를 보았다.",
            "A-16 영어 대명사 직역",
            "→ 영형(생략)",
        ),
        (
            "긴장으로부터의 해방",
            [(2, 8)],  # "으로부터의"
            "긴장에서 벗어남",
            "A-19 이중 조사 결합",
            "→ 절·구로 풀어쓰기",
        ),
        (
            "사고를 일으킨 회사에서 일했던 남자를 만났다.",
            [],  # 관계절 좌향 수식은 통째로 어색 — 강조 없이
            "남자를 만났는데, 사고를 일으킨 회사에서 일했다.",
            "A-18 관계절 좌향 수식",
            "→ 후치 동격절",
        ),
    ]

    y = 240
    row_gap = 95
    for i, (b_text, strikes, a_text, lab_l, lab_r) in enumerate(rows):
        # BEFORE column
        bx = 72
        draw_text(d, (bx, y), b_text, f_ex, TITLE)
        # strike spans (approx — char index → x position via cumulative width)
        for s, e in strikes:
            prefix = b_text[:s]
            target = b_text[s:e]
            x_start = bx + text_w(f_ex, prefix)
            x_end = x_start + text_w(f_ex, target)
            mid_y = y + 18  # roughly mid of glyph
            draw_strike(d, x_start, mid_y, x_end - x_start, color=STRIKE, width=3)
        # pattern label below
        draw_text(d, (bx, y + 36), lab_l, f_pat, BEFORE)

        # arrow
        draw_arrow(d, 595, y + 18, color=SUB, size=22)

        # AFTER column
        ax = 640
        draw_text(d, (ax, y), a_text, f_ex, AFTER)
        draw_text(d, (ax, y + 36), lab_r, f_pat, AFTER)

        y += row_gap

    # Bottom rule
    d.line([(72, 540), (W - 72, 540)], fill=RULE, width=2)

    # Bottom meta — 좌측 + 우측
    f_meta = font(F_SEMI, 16)
    f_meta_sub = font(F_REG, 13)
    f_link = font(F_MED, 16)

    # 좌측: 메타
    draw_text(d, (72, 562), "10 categories · 60+ patterns · v2.0", f_meta, TITLE)
    draw_text(d, (72, 590), "이근희 · 김정우 · 김도훈 · 김혜영 · Toral 2019", f_meta_sub, META)

    # 우측: github URL
    draw_text(d, (W - 72, 590), "github.com/epoko77-ai/im-not-ai", f_link, LINK, anchor="ra")

    # Save
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, format="PNG", optimize=True)
    print(f"saved: {OUT} ({W}×{H})")


if __name__ == "__main__":
    build()
