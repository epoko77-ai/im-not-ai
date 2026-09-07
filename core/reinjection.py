#!/usr/bin/env python3
"""G3 역주입 게이트 — 윤문 전후를 같은 지표로 재측정한다.

철칙 #6(No New Tells)의 코드화. 지우기로 한 티가 줄었어도 다른 지표가
새로 올랐으면 실패다. **윤문 콜은 티를 지우면서 자기 모델의 개인어를 심는다.**

실측 근거 (`core/principles.md` G3):
- 영어 — 스파이크 윤문에서 목표 지표는 전부 0 으로 내려갔는데 em dash 가
  2→5(9.33/1k)로 늘었다. 장문 부재를 고치려 문장을 이어 붙이면서 접합부에
  대시를 심은 것이다. 발표된 Claude Opus 4.6 = 9.09/1k 와 거의 일치한다.
- 한국어 — D-9 결산 정리가 '결국' 을 역주입해 재실측에서 2→4 로 늘었다.

**원시 건수로 판정한다.** 밀도로 보면 본문이 짧아진 것만으로 상승이 잡혀
오탐이 난다(스파이크 I-4 3.42→3.73, 건수는 2→2 불변).

언어 무관 — 무엇을 셀지는 호출자가 counters 로 주입한다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Callable

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from metrics_universal import compute_universal  # noqa: E402


def check_reinjection(
    before: str,
    after: str,
    counters: dict[str, Callable[[str], int]],
    *,
    unit: str = "tokens",
    long_threshold: int = 35,
) -> dict:
    """전후를 같은 카운터로 재측정해 신규 상승분을 찾는다.

    반환:
        ``failed``      — 하나라도 올랐으면 True
        ``risen``       — {이름: (before_n, after_n)} 오른 항목만
        ``dispersion``  — (before, after) 문장길이 분산. **판정에 쓰지 않는다**
                          — 분산 상승은 E-1 처방의 의도된 결과이므로 보고만 한다.
        ``note``        — 사람이 읽을 한 줄
    """
    risen: dict[str, tuple[int, int]] = {}
    for name, fn in counters.items():
        b, a = fn(before), fn(after)
        if a > b:
            risen[name] = (b, a)

    bu = compute_universal(before, long_threshold=long_threshold, unit=unit)
    au = compute_universal(after, long_threshold=long_threshold, unit=unit)

    return {
        "failed": bool(risen),
        "risen": risen,
        "dispersion": (
            bu["sentence_length_dispersion"],
            au["sentence_length_dispersion"],
        ),
        "note": (
            "역주입 없음 — 티는 줄기만 했다"
            if not risen
            else "역주입 감지: "
            + ", ".join(f"{k} {b}→{a}" for k, (b, a) in sorted(risen.items()))
        ),
    }


# ---------------------------------------------------------------------------
# 언어별 기본 카운터 — CLI 가 쓴다
# ---------------------------------------------------------------------------
#
# 무엇을 셀지의 기준: **윤문이 심을 수 있는 것**만 센다. 원문에 있던 티가
# 줄어드는 건 정상이고, 없던 게 늘어나는 것이 G3 의 대상이다.


def _count(pattern: str, flags: int = 0) -> Callable[[str], int]:
    rx = re.compile(pattern, flags)
    return lambda t: len(rx.findall(t))


# 영어: em dash(윤문 모델의 개인어 — 스파이크에서 2→5 실측) + 담화 공식.
# 어휘 항목은 lang/en/lexicon.json 의 router_eligible 에서 가져온다.
#
# ⚠️ hedge·수동태·contraction 은 여기서 세지 않는다. G3 는 "늘어난 것"을 잡는데,
# 그것들의 위험은 **줄어드는 것**이다(LLM 이 이미 과소 사용 — lang/en/scholarship.md).
# 소실 감시는 별도 게이트가 필요하다 — 한국어 verify_gates 의 P5 서법 축에 대응하며
# 영어판은 아직 없다. 룰북의 「건드리면 안 되는 것」이 현재 유일한 방어다.
def _en_counters() -> dict[str, Callable[[str], int]]:
    counters: dict[str, Callable[[str], int]] = {
        "em_dash": _count(r"—"),
        "conclusion_marker": _count(
            r"\b(?:In conclusion|To summarize|In summary|Ultimately)\b"
        ),
        "cleft": _count(r"\b(?:What matters is|What we need is|The real question is)\b"),
        "closing_formula": _count(
            r"\b(?:now is the time|the time has come|as we move forward)\b", re.I
        ),
    }
    lex = os.path.join(os.path.dirname(_HERE), "lang", "en", "lexicon.json")
    try:
        with open(lex, encoding="utf-8") as f:
            words = [
                e["word"] for e in json.load(f)["entries"] if e.get("router_eligible")
            ]
        if words:
            alt = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
            counters["excess_vocab"] = _count(rf"\b(?:{alt})\b", re.I)
    except Exception:  # noqa: BLE001 — 사전이 없어도 게이트는 돌아야 한다.
        pass
    return counters


# 한국어: 실측으로 역주입이 확인된 것들(D-9 '결국' 2→4 등).
def _ko_counters() -> dict[str, Callable[[str], int]]:
    return {
        "결국": _count(r"결국"),
        "결산공식": _count(r"(?:으로|로)\s*이어진다|하는\s*이유다|에\s*직결된다"),
        "결말공식": _count(r"할\s*때(?:입니다|이다)|시점(?:입니다|이다)"),
        "시간지평": _count(r"(?:^|[.!?]\s+)(?:향후|앞으로|중장기적으로)", re.M),
        "hype": _count(r"혁신적|획기적|압도적|전례\s*없는"),
    }


COUNTERS_BY_LANG = {"en": _en_counters, "ko": _ko_counters}
UNIT_BY_LANG = {"en": ("tokens", 35), "ko": ("chars", 100)}


def main(argv: list[str] | None = None) -> int:
    """Exit code: 0 역주입 없음 / 1 역주입 감지 / 3 실행 오류."""
    ap = argparse.ArgumentParser(description="G3 역주입 게이트 (철칙 #6)")
    ap.add_argument("--before", required=True, help="윤문 전 텍스트 파일")
    ap.add_argument("--after", required=True, help="윤문 후 텍스트 파일")
    ap.add_argument("--lang", choices=("en", "ko"), default="ko")
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
    out = check_reinjection(
        before,
        after,
        COUNTERS_BY_LANG[args.lang](),
        unit=unit,
        long_threshold=threshold,
    )
    b, a = out["dispersion"]
    print(f"reinjection: {out['note']}")
    print(f"dispersion: {b} → {a}  (E-1 처방 결과 — 판정에 쓰지 않음)")
    if out["failed"]:
        print("gate: FAIL — 철칙 #6 위반. 해당 표현을 원문 수준으로 되돌릴 것")
        return 1
    print("gate: OK — 새 티 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
