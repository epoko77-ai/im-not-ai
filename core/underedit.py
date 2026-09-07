#!/usr/bin/env python3
"""과소윤문 게이트 — 라우터가 지목한 티가 실제로 줄었는지 본다.

**기존 게이트는 한쪽만 봤다.** `verify_change_rate.py`(철칙 #4)와
`reinjection.py`(철칙 #6)는 둘 다 "너무 많이 했다"를 잡는다.
"너무 적게 했다"는 아무도 안 봤다.

실측 근거 (2026-09-02, n=4 · 근거 등급 E3): 스킬 윤문 4회 중 1회가 변경률
0.4% 로 사실상 아무것도 하지 않았다 — 분산 7.04 → 7.00, 장문율 0.00% 그대로.
라우터는 standard(고칠 게 있다)로 판정했는데 티가 남았고 게이트는 통과시켰다.
같은 실측의 성공 회차는 분산 +22%~+48%. 임계 +5% 가 그 사이를 가른다.

같은 라운드의 대조군(맨 프롬프트 윤문)은 6회 중 4회가 이 실패 모드였다
(변경률 1.9~4.9%, 분산 7.04 → 6.80~6.98 로 **하락**). 이 게이트가 잡는 것이
그 차이다.

**light 경로는 검사하지 않는다** — 라우터가 "고칠 게 없다"고 판정한 글이므로
변화가 없는 것이 정답이다.

표준 라이브러리만. 언어 무관 — 어휘 카운터만 언어별로 주입한다.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Callable

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from metrics_universal import compute_universal  # noqa: E402

# 개선 판정 임계 — 전부 E3(자체 실측 n=4)의 잠정값이다.
DISPERSION_MIN_REL_GAIN = 0.05   # 분산 5% 이상 상승
DISPERSION_MIN_ABS_GAIN = 0.5    # 그리고 절대 0.5 이상 — 잡음 바닥
LONG_RATE_MIN_ABS_GAIN = 1.0     # 장문율 1%p 이상 상승
COMMA_MIN_ABS_DROP = 5.0         # 쉼표 포함률 5%p 이상 하락

# 라우터가 "손댈 게 있다"고 본 경로. light 는 검사 대상이 아니다.
CHECKED_HINTS = ("standard", "heavy")


def check_underedit(
    before: str,
    after: str,
    *,
    route_hint: str,
    unit: str = "tokens",
    long_threshold: int = 35,
    lexicon_counter: Callable[[str], int] | None = None,
    validated: dict[str, tuple[Callable[[str], float], str, float]] | None = None,
) -> dict:
    """지목된 티가 실제로 줄었는지 판정한다.

    반환:
        ``failed``   — 개선이 하나도 없으면 True
        ``skipped``  — light 경로라 검사하지 않았으면 True
        ``improved`` — {지표: (before, after)} 개선된 것만
        ``signals``  — {지표: (before, after)} 전수(보고용)

    ``validated`` 는 **그 장르에서 판별력이 확인된 지표**를 넣는 통로다
    ({이름: (계측함수, "down"|"up", 최소 변화폭)}). 건수형 지표는 한 건만 줄어도
    의미가 있어 하한이 0 에 가깝고(인간 중앙값이 0 이다), 연속형은 잡음 하한을 둔다. 실측 2026-09-05: 영어 블로그 셀에서 이
    게이트가 변경률 0.5% 짜리 윤문을 통과시켰다 — 렉시콘 단어 하나가 빠진 것을
    개선으로 쳤기 때문이다. 정작 그 장르에서 검증된 신호(tricolon·쉼표 절)는
    보고 있지 않았다. 판별력 없는 지표로 내리는 판정은 판정이 아니다.
    """
    bu = compute_universal(before, long_threshold=long_threshold, unit=unit)
    au = compute_universal(after, long_threshold=long_threshold, unit=unit)

    signals = {
        "dispersion": (
            bu["sentence_length_dispersion"],
            au["sentence_length_dispersion"],
        ),
        "long_sentence_rate": (bu["long_sentence_rate"], au["long_sentence_rate"]),
        "comma_inclusion_rate": (
            bu["comma_inclusion_rate"],
            au["comma_inclusion_rate"],
        ),
    }
    if lexicon_counter is not None:
        signals["lexicon_hits"] = (lexicon_counter(before), lexicon_counter(after))
    for name, (fn, _want, _min) in (validated or {}).items():
        signals[name] = (fn(before), fn(after))

    if route_hint not in CHECKED_HINTS:
        return {
            "failed": False,
            "skipped": True,
            "improved": {},
            "signals": signals,
            "note": f"route_hint={route_hint} — 라우터가 손댈 게 없다고 판정, 검사 생략",
        }

    improved: dict[str, tuple[float, float]] = {}
    db, da = signals["dispersion"]
    # 두 조건을 모두 넘어야 개선이다.
    #  (a) 절대 하한 — 잡음과 실제 변화를 가른다. 이게 없으면 분산 0.0 → 0.28
    #      같은 한 단어짜리 손질이 개선으로 잡힌다.
    #  (b) 상대 하한 — 다만 분산이 정확히 0(완전한 메트로놈, 최악)이면
    #      상대 증가율을 쓸 수 없으므로 절대 하한만 본다.
    abs_ok = (da - db) >= DISPERSION_MIN_ABS_GAIN
    rel_ok = db == 0 or (da - db) / db >= DISPERSION_MIN_REL_GAIN
    if abs_ok and rel_ok:
        improved["dispersion"] = (db, da)
    lb, la = signals["long_sentence_rate"]
    if la - lb >= LONG_RATE_MIN_ABS_GAIN:
        improved["long_sentence_rate"] = (lb, la)
    cb, ca = signals["comma_inclusion_rate"]
    if cb - ca >= COMMA_MIN_ABS_DROP:
        improved["comma_inclusion_rate"] = (cb, ca)
    if "lexicon_hits" in signals:
        xb, xa = signals["lexicon_hits"]
        if xa < xb:
            improved["lexicon_hits"] = (xb, xa)
    # 검증된 신호는 방향만 맞으면 개선으로 친다 — 이 장르에서 판별력이 확인된
    # 지표이므로 잡음 하한을 따로 두지 않는다.
    for name, (_fn, want, min_delta) in (validated or {}).items():
        vb, va = signals[name]
        delta = (vb - va) if want == "down" else (va - vb)
        if delta >= min_delta:
            improved[name] = (vb, va)

    return {
        "failed": not improved,
        "skipped": False,
        "improved": improved,
        "signals": signals,
        "note": (
            "개선 없음 — 라우터가 지목한 티가 그대로다"
            if not improved
            else "개선: "
            + ", ".join(f"{k} {b}→{a}" for k, (b, a) in sorted(improved.items()))
        ),
    }


def _en_validated(genre: str) -> dict | None:
    """영어 장르별 **검증된** 신호. 없으면 None(기존 산술 지표만 쓴다)."""
    if genre != "blog":
        return None  # abstract 셀은 쉼표 계열이 이미 산술 지표에 들어 있다
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "lang", "en"))
        from metrics_en import _TRICOLON_RE  # noqa: PLC0415
        from metrics_universal import comma_segment_length  # noqa: PLC0415

        def tricolon(text: str) -> float:
            tokens = len(text.split()) or 1
            return round(len(_TRICOLON_RE.findall(text)) / tokens * 1000, 2)

        # tricolon: 인간 중앙값 0.00 이라 한 건 감소도 의미가 있다(하한 0.01).
        # comma_segment: 인간 9.68 vs AI 8.34 — 격차 1.34 의 약 1/4 을 잡음 하한으로.
        return {
            "tricolon(EN-3)": (tricolon, "down", 0.01),
            "comma_segment_length": (comma_segment_length, "up", 0.3),
        }
    except Exception:  # noqa: BLE001 — 신호가 없어도 게이트는 돌아야 한다.
        return None


def _en_lexicon_counter() -> Callable[[str], int] | None:
    """영어 라우터 렉시콘 히트 수 — 없으면 None(그 신호만 빠진다)."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "lang", "en"))
        from metrics_en import lexicon_hits, load_lexicon  # noqa: PLC0415

        lex = load_lexicon()
        return lambda t: lexicon_hits(t, lex, router_only=True)[0]
    except Exception:  # noqa: BLE001 — 사전이 없어도 게이트는 돌아야 한다.
        return None


UNIT_BY_LANG = {"en": ("tokens", 35), "ko": ("chars", 100)}


def main(argv: list[str] | None = None) -> int:
    """Exit code: 0 통과·생략 / 1 과소윤문 / 3 실행 오류."""
    ap = argparse.ArgumentParser(description="과소윤문 게이트")
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--lang", choices=("en", "ko"), default="ko")
    ap.add_argument("--genre", default="blog",
                    help="영어 임계 셀 (abstract|blog) — 검증된 신호를 고른다")
    ap.add_argument(
        "--route-hint",
        required=True,
        choices=("light", "standard", "heavy"),
        help="shim 의 00_metrics.json 에 있는 값 그대로",
    )
    args = ap.parse_args(argv)

    try:
        with open(args.before, encoding="utf-8") as f:
            before = f.read()
        with open(args.after, encoding="utf-8") as f:
            after = f.read()
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    unit, threshold = UNIT_BY_LANG[args.lang]
    out = check_underedit(
        before,
        after,
        route_hint=args.route_hint,
        unit=unit,
        long_threshold=threshold,
        lexicon_counter=_en_lexicon_counter() if args.lang == "en" else None,
        validated=_en_validated(args.genre) if args.lang == "en" else None,
    )
    for name, (b, a) in sorted(out["signals"].items()):
        print(f"  {name:22} {b} → {a}")
    print(f"underedit: {out['note']}")
    if out["skipped"]:
        print("gate: SKIP — light 경로")
        return 0
    if out["failed"]:
        print(
            "gate: FAIL — 과소윤문. 라우터가 지목한 티를 실제로 손볼 것 "
            "(분산·장문율·쉼표·어휘 중 최소 하나)"
        )
        return 1
    print("gate: OK — 지목된 티가 줄었다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
