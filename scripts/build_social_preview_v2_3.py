"""Build assets/social-preview.png for v2.3 — BEFORE/AFTER 예시 모음.

일반인이 "내 문장이 어떻게 좋아지는지" 바로 보게 한다. v2.3 신규 신호(대구·짧은 문장)와
누적된 대표 AI 티(번역투·피동·대명사 직역·관계절 좌향수식·번역투 완곡·결산 피벗)를 함께.
예시는 imnotai.kr 실제 엔진 출력 + v2.0 프리뷰의 검증된 사례. v2.0 디자인 톤 유지.
1280×640. Pretendard.
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
OUT = ASSETS / "social-preview.png"

FONT_DIR = Path.home() / "Library" / "Fonts"
F_BLACK = str(FONT_DIR / "Pretendard-Black.otf")
F_BOLD = str(FONT_DIR / "Pretendard-Bold.otf")
F_SEMI = str(FONT_DIR / "Pretendard-SemiBold.otf")
F_MED = str(FONT_DIR / "Pretendard-Medium.otf")
F_REG = str(FONT_DIR / "Pretendard-Regular.otf")

BG = "#F4EFE5"
TITLE = "#1F2A1F"
SUB = "#5C5042"
RULE = "#C9BEA9"
BEFORE = "#C0573F"
BTEXT = "#9A5E52"
AFTER = "#2D5C3F"
META = "#7A6E5C"
LINK = "#2D5C3F"
BADGE_BG = "#2D5C3F"

W, H = 1280, 640
MID = 648


def font(path, size):
    return ImageFont.truetype(path, size)


def dt(d, xy, text, f, fill, anchor="la"):
    d.text(xy, text, font=f, fill=fill, anchor=anchor)


def tw(f, text):
    b = f.getbbox(text)
    return b[2] - b[0]


def build():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Header — 워드마크 + 버전 배지
    dt(d, (72, 52), "im-not-ai", font(F_BLACK, 62), TITLE)
    # v2.3 배지 (워드마크 오른쪽)
    fb = font(F_BOLD, 20)
    bx = 72 + tw(font(F_BLACK, 62), "im-not-ai") + 22
    badge = "v2.3"
    pad = 12
    bw = tw(fb, badge) + pad * 2
    d.rounded_rectangle([bx, 74, bx + bw, 74 + 34], radius=8, fill=BADGE_BG)
    dt(d, (bx + pad, 79), badge, fb, "#FFFFFF")

    dt(d, (W - 72, 56), "한글 AI 티 제거기 · 오픈소스", font(F_MED, 20), SUB, anchor="ra")
    dt(d, (W - 72, 84), "AI가 쓴 글을 사람이 쓴 글처럼", font(F_SEMI, 22), AFTER, anchor="ra")

    d.line([(72, 140), (W - 72, 140)], fill=RULE, width=2)

    # Column labels
    dt(d, (72, 152), "AI 티 나는 문장", font(F_BOLD, 16), BEFORE)
    dt(d, (MID + 28, 152), "다듬은 결과", font(F_BOLD, 16), AFTER)
    d.line([(MID, 146), (MID, 556)], fill=RULE, width=2)

    # 6행 — 카테고리 라벨 + BEFORE / AFTER
    rows = [
        ("번역투 · 피동",
         "요인들에 의해 발생되어진다고 볼 수 있다.",
         "여러 요인으로 발생한다."),
        ("영어식 대명사 직역",
         "그는 그의 시계를 보았다.",
         "시계를 보았다."),
        ("반복되는 대구",
         "기술이 아니라 방식이다. 속도가 아니라 방향이다.",
         "단순한 기술이 아니라 삶의 방식이다. 속도보다 방향이 중요하다."),
        ("관계절 좌향 수식",
         "AI가 학습한 데이터가 보여주는 언어 패턴",
         "AI 학습 데이터의 언어 패턴"),
        ("번역투 완곡 표현",
         "생산성을 높일 수 있다. 이를 통해 경쟁력을 강화할 수 있다.",
         "생산성을 높여 경쟁력을 강화한다."),
        ("상투적 결론 공식",
         "결론적으로, 본질적으로 시사하는 바가 크다고 할 수 있다.",
         "시사하는 바가 크다."),
    ]

    f_lab = font(F_SEMI, 12)
    f_b = font(F_REG, 17)
    f_a = font(F_MED, 17)
    y = 190
    row_gap = 61
    for lab, b_text, a_text in rows:
        dt(d, (72, y), lab, f_lab, BEFORE)
        dt(d, (72, y + 18), b_text, f_b, BTEXT)
        dt(d, (MID + 28, y + 18), a_text, f_a, TITLE)
        y += row_gap

    # Bottom rule
    d.line([(72, 566), (W - 72, 566)], fill=RULE, width=2)

    dt(d, (72, 588), "데이터로 검증한 AI 티 제거  ·  무료 체험 imnotai.kr",
       font(F_SEMI, 16), TITLE)
    dt(d, (W - 72, 588), "github.com/epoko77-ai/im-not-ai", font(F_MED, 16), LINK, anchor="ra")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, format="PNG", optimize=True)
    print(f"saved: {OUT} ({W}x{H})")


if __name__ == "__main__":
    build()
