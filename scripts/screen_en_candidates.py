#!/usr/bin/env python3
"""영어 후보 패턴 승격 심사 — 기존 arXiv 대조군으로 E1 근거를 만든다.

`lang/en/candidate-pool.md` 의 후보는 커뮤니티 축(E3)만 있다. 이 스크립트는
`scripts/build_en_baseline.py` 가 모아둔 인간 42편(2015~2020, ChatGPT 이전) vs
같은 제목 AI 21편으로 **판별력을 실측**해 학술/실측 축을 붙인다.

신규 수집 0 — 이미 있는 코퍼스를 다시 재기만 한다.

판정: AUC 의 0.5 이탈폭
    >= 0.20  판별 가능 → 승격 후보
    >= 0.10  약함 → 보류
    <  0.10  무작위 → 기각

⚠️ G2 과업 통제는 지켜진다(같은 논문 제목). G1(전 모델)은 AI 3모델 혼합이라
부분 충족 — 모델별 분해는 표본이 작아(모델당 7편) 하지 않는다.

사용: python3 scripts/screen_en_candidates.py
"""
from __future__ import annotations

import itertools
import json
import os
import re
import statistics
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_WORK = os.path.join(_ROOT, "_workspace", "en_baseline")

# (blader 번호, 이름, 계수 함수) — 문서당 1000토큰당 밀도로 잰다.
# 정규식으로 잴 수 없는 후보(#2 name-dropping, #22 tone 등)는 여기 없다.
CANDIDATES: list[tuple[str, str, str]] = [
    ("#5",  "vague sources",
     r"\b(?:studies (?:show|suggest)|research (?:shows|suggests)|experts? (?:say|agree)"
     r"|it is (?:widely )?(?:believed|thought|understood)|many (?:argue|believe))\b"),
    ("#8",  "avoiding is/are (be동사 회피의 역지표)",
     r"\b(?:is|are|was|were)\b"),
    ("#12", "false from X to Y ranges",
     r"\bfrom \w+(?: \w+){0,2} to \w+(?: \w+){0,2}\b"),
    ("#23", "filler phrases",
     r"\b(?:it(?:'s| is) (?:important|worth) (?:to note|noting)|needless to say"
     r"|at the end of the day|when it comes to|in order to)\b"),
    ("#25", "generic positive endings",
     r"\b(?:promising (?:direction|avenue|results)|opens? (?:up )?new (?:avenues|possibilities)"
     r"|paves? the way|holds? (?:great )?promise|exciting (?:direction|opportunit))\w*\b"),
    ("#26", "hyphenated word pairs",
     r"\b[a-z]+-[a-z]+\b"),
    ("#27", "pretending to reveal a deeper truth",
     r"\b(?:the (?:real|deeper|underlying) (?:question|issue|problem|truth)"
     r"|what(?:'s| is) (?:really|actually) (?:going on|at (?:stake|play)))\b"),
    ("#31", "dramatic fragments (문장 없는 절)",
     r"(?:^|[.!?]\s+)(?:And|But|Or|Because|Which|Not)\b[^.!?]{0,40}[.!?]"),
    ("#32", "formulaic sayings",
     r"\b(?:double-edged sword|tip of the iceberg|game.?chang\w+|silver bullet"
     r"|low-hanging fruit|move the needle)\b"),
    # ⚠️ 초판은 동사 목록(highlight·underscor·reflect…)을 박았고 인간·AI 모두 0.00 이
    # 나왔다. 그 목록은 **블로그 장르의 분사**다 — 학술 초록은 spanning·suggesting·
    # showing·tracking 을 쓴다. C-8 첫 정규식(재현율 0/6)과 같은 실패다.
    # **통사 프레임으로 잡는다.** 프레임으로 바꾸자 AUC 0.605 → 0.726.
    ("EN-1", "present participial clause (쉼표 + -ing 프레임)",
     r",\s+\w+ing\b"),
]

_WS = re.compile(r"\s+")


def _density(text: str, rx: re.Pattern) -> float:
    tokens = len([t for t in _WS.split(text) if t]) or 1
    return len(rx.findall(text)) / tokens * 1000


def _repeated_openings(text: str) -> float:
    """#11 — 문장 첫 단어 반복률(%). 정규식이 아니라 계수형."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(sents) < 2:
        return 0.0
    firsts = [s.split()[0].lower() for s in sents if s.split()]
    if not firsts:
        return 0.0
    dupes = len(firsts) - len(set(firsts))
    return dupes / len(firsts) * 100


def _load(name: str) -> list[str]:
    path = os.path.join(_WORK, name)
    if not os.path.exists(path):
        raise SystemExit(f"{path} 없음 — build_en_baseline.py 를 먼저 실행할 것")
    with open(path, encoding="utf-8") as f:
        return [r["text"] for r in json.load(f)]


def _auc(ai: list[float], human: list[float]) -> float:
    gt = sum(1 for x, y in itertools.product(ai, human) if x > y)
    tie = sum(1 for x, y in itertools.product(ai, human) if x == y)
    return (gt + 0.5 * tie) / (len(ai) * len(human))


def _verdict(auc: float) -> str:
    d = abs(auc - 0.5)
    if d >= 0.20:
        return "승격 후보"
    if d >= 0.10:
        return "보류(약함)"
    return "기각(무작위)"


def main() -> int:
    human, ai = _load("human.json"), _load("ai.json")
    print(f"인간 {len(human)}편(arXiv 2015~2020) vs AI {len(ai)}편(같은 제목, 3모델)\n")
    print(f"{'후보':10}{'이름':40}{'인간':>8}{'AI':>8}{'배수':>7}{'AUC':>7}  판정")
    rows = []
    for tag, name, pattern in CANDIDATES:
        rx = re.compile(pattern, re.I)
        h = [_density(t, rx) for t in human]
        a = [_density(t, rx) for t in ai]
        hm, am = statistics.median(h), statistics.median(a)
        auc = _auc(a, h)
        rows.append((tag, name, hm, am, auc))
        ratio = round(am / hm, 2) if hm else float("inf")
        print(f"{tag:10}{name[:38]:40}{hm:>8.2f}{am:>8.2f}{ratio:>7}{auc:>7.3f}  {_verdict(auc)}")

    h = [_repeated_openings(t) for t in human]
    a = [_repeated_openings(t) for t in ai]
    hm, am = statistics.median(h), statistics.median(a)
    auc = _auc(a, h)
    ratio = round(am / hm, 2) if hm else float("inf")
    print(f"{'#11':10}{'repeated sentence openings (%)':40}{hm:>8.2f}{am:>8.2f}{ratio:>7}{auc:>7.3f}  {_verdict(auc)}")
    rows.append(("#11", "repeated sentence openings", hm, am, auc))

    promoted = [r for r in rows if abs(r[4] - 0.5) >= 0.20]
    zero = [r for r in rows if r[2] == 0 and r[3] == 0]
    print(f"\n승격 후보 {len(promoted)}건 / 심사 {len(rows)}건")
    if zero:
        print(f"⚠️ 인간·AI 모두 0.00 인 후보 {len(zero)}건: "
              + ", ".join(r[0] for r in zero))
        print("   장르 문제다 — 학술 초록에는 그 패턴이 아예 없다(블로그·마케팅 산문 패턴).")
        print("   기각이 아니라 **판정 불가**로 읽고, 칼럼 코퍼스가 생기면 재심사한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
