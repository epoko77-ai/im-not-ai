#!/usr/bin/env python3
"""서법 소실 게이트 — 유보·당위가 단정으로 바뀌었는지 본다.

**이 게이트가 없으면 영어 룰북은 자기가 시킨 일을 감시하지 못한다.**
`reinjection.py`(G3)는 "늘어난 것"을 잡는데, 영어의 위험은 반대쪽에 있다:
LLM 은 hedge 를 **인간보다 적게** 쓰고(Jiang & Hyland 2025 · Mizumoto 2024 ·
Reinhart 2025 세 연구 수렴 — `lang/en/scholarship.md`), 윤문 콜은 문장을
짧고 세게 만들라는 지시를 받으면 `may`·`suggests`·`should` 를 지운다.
그건 AI 티 제거가 아니라 **필자의 주장 강도를 바꾸는 것**이다(철칙 #1 위반).

한국어 P5(`scripts/verify_gates.py`)의 영어판이며, 그 설계 결정을 그대로
가져온다: **총수가 아니라 문장쌍으로 본다.** 총수는 위치를 보지 않아
오검출과 실손실이 상쇄되고, 그 상쇄가 진짜 위반을 가린다(한국어 실측:
"낮은 것으로 판단된다" → "낮은 수치다" 가 net 0 으로 계산됐다).

늘어나는 것은 대상이 아니다 — 없던 당위 주입은 `content_preservation` 과
G3 소관이다.

표준 라이브러리만.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from metrics_universal import split_sentences  # noqa: E402

# 짝 유사도 하한. 이보다 낮으면 "같은 문장인지 확신할 수 없다"로 보고
# exit code 에 넣지 않는다(보고는 한다 — 진짜 소실이 섞여 있을 수 있다).
# 영어 실측 보정치는 아래 __main__ 검증 주석 참조.
MIN_PAIR_SIM = 0.35
TOLERANCE = 0  # 감소 허용 폭. 문장쌍 판정이라 상쇄가 없어 0 이 맞다.

# ⚠️ 사전은 넓어야 한다. 한국어에서 좁은 완곡 사전이 실측 손실 7건 중 1건만
# 잡았다. 다만 **빈도 부사**(often·usually·generally)와 `will` 은 넣지 않는다 —
# 서법이 아니라 빈도·시제라서 잡음만 는다.
MODAL_EN = {
    "deontic": re.compile(
        r"\b(?:must|should|shall|ought\s+to|needs?\s+to|have\s+to|has\s+to|had\s+to"
        r"|required\s+to|it\s+is\s+(?:necessary|essential|imperative))\b",
        re.I,
    ),
    "hedge": re.compile(
        r"\b(?:may|might|could|can|would"
        r"|appears?|appeared|seems?|seemed"
        r"|suggests?|suggested|indicates?|indicated|implies|implied"
        r"|likely|unlikely|probably|possibly|perhaps|arguably|presumably"
        r"|potentially|apparently|roughly|approximately|somewhat|relatively"
        r"|tends?\s+to|tended\s+to|we\s+believe|it\s+is\s+possible"
        r"|to\s+some\s+extent|not\s+necessarily)\b",
        re.I,
    ),
}


def _bigrams(s: str) -> "Counter[str]":
    c = "".join(ch for ch in s.lower() if ch.isalnum())
    return Counter(c[i : i + 2] for i in range(len(c) - 1))


def _sim(a: str, b: str) -> float:
    """문자 바이그램 Dice 유사도(0~1). 어미·어순 변화에 둔감하다."""
    A, B = _bigrams(a), _bigrams(b)
    if not A or not B:
        return 0.0
    return 2 * sum((A & B).values()) / (sum(A.values()) + sum(B.values()))


def align(before: list[str], after: list[str]) -> list[tuple[str, str]]:
    """Needleman-Wunsch 문장 정렬. 1:1 짝과 gap(삽입·삭제)만 낸다."""
    n, m = len(before), len(after)
    gap = -0.4
    score = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        score[i][0] = score[i - 1][0] + gap
    for j in range(1, m + 1):
        score[0][j] = score[0][j - 1] + gap
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            score[i][j] = max(
                score[i - 1][j - 1] + _sim(before[i - 1], after[j - 1]),
                score[i - 1][j] + gap,
                score[i][j - 1] + gap,
            )
    pairs: list[tuple[str, str]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and abs(
            score[i][j] - (score[i - 1][j - 1] + _sim(before[i - 1], after[j - 1]))
        ) < 1e-9:
            pairs.append((before[i - 1], after[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and abs(score[i][j] - (score[i - 1][j] + gap)) < 1e-9:
            pairs.append((before[i - 1], ""))
            i -= 1
        else:
            pairs.append(("", after[j - 1]))
            j -= 1
    pairs.reverse()
    return pairs


def _inserted(pairs: list[tuple[str, str]], i: int, step: int) -> str:
    """i 에서 step 방향으로 이어지는 '짝 없는 after 문장'(삽입)을 모은다."""
    out: list[str] = []
    j = i + step
    while 0 <= j < len(pairs) and not pairs[j][0].strip() and pairs[j][1].strip():
        out.append(pairs[j][1])
        j += step
    return " ".join(out)


def find_losses(before: str, after: str, modals: dict | None = None) -> list[dict]:
    """원문 문장의 서법 표지가 짝 문장에서 사라진 건을 찾는다."""
    modals = modals or MODAL_EN
    pairs = align(split_sentences(before), split_sentences(after))
    out: list[dict] = []
    for i, (b, a) in enumerate(pairs):
        b, a = b.strip(), a.strip()
        # 삭제(짝 없음)는 서법이 아니라 내용 소실 — content_preservation 소관.
        if not b or not a:
            continue
        # **분할 흡수**: 한 문장이 둘로 쪼개지면 나머지 조각이 짝 없는 삽입으로
        # 남고, 표지가 그쪽에 실려 있으면 정렬은 소실로 오판한다. 실측에서
        # "Results indicate that X, though Y." → "Results indicate that X. Y."
        # 가 그대로 false FAIL 이었다(총수는 1→1 불변). 인접 삽입 문장까지
        # 창(window)에 넣어 센다.
        # 창(window)은 **계수용**이다. 복원 대상은 정렬된 짝 문장 자체이므로
        # `a` 를 덮어쓰지 않는다 — 덮어쓰면 앞뒤 공백이 붙어 원문에서 특정되지 않는다.
        window = " ".join(x for x in (_inserted(pairs, i, -1), a, _inserted(pairs, i, +1)) if x)
        for kind, rx in modals.items():
            # **건수**로 본다. 존재 여부로 보면 "may indicate" → "indicate" 처럼
            # 같은 부류의 표지가 하나 남은 부분 소실을 통째로 놓친다.
            # 건수라서 `may` → `might` 같은 등가 치환은 1→1 로 통과한다.
            hb, ha = rx.findall(b), rx.findall(window)
            if len(ha) < len(hb):
                kept = list(ha)
                dropped = []
                for h in hb:
                    if h.lower() in [k.lower() for k in kept]:
                        kept.remove(next(k for k in kept if k.lower() == h.lower()))
                    else:
                        dropped.append(h)
                out.append({
                    "kind": kind,
                    "marker": ", ".join(dropped) or hb[0],
                    "before": b,
                    "after": a,
                    "low_sim": _sim(b, a) < MIN_PAIR_SIM,
                })
                break
    return out


def check_modality_loss(before: str, after: str, modals: dict | None = None) -> dict:
    """반환: ``failed`` · ``lost``(확신) · ``uncertain``(짝 유사도 낮음) · ``counts``."""
    modals = modals or MODAL_EN
    losses = find_losses(before, after, modals)
    lost = [l for l in losses if not l["low_sim"]]
    uncertain = [l for l in losses if l["low_sim"]]
    counts = {
        k: (len(rx.findall(before)), len(rx.findall(after)))
        for k, rx in modals.items()
    }
    return {
        "failed": len(lost) > TOLERANCE,
        "lost": lost,
        "uncertain": uncertain,
        # 총수는 참고용이다. 판정 근거가 아니다(상쇄 때문).
        "counts": counts,
        "note": (
            "서법 보존 — 유보·당위가 그대로다"
            if not lost
            else "서법 소실 "
            + ", ".join(f"{l['kind']}:{l['marker']}" for l in lost[:5])
        ),
    }


# ── 복원 ────────────────────────────────────────────────────────────────
#
# 탐지만 하면 실행자가 고쳐야 하고, 실행자는 지시를 어긴다 — 실측(2026-09-05)에서
# 룰북이 "hedge 를 제거하지 마라"고 명시했는데도 28편 중 6편에서 지웠다.
# 한국어는 게이트 직전에 결정적으로 되돌린다(`scripts/restore_modality.py` · P2.4).
# 영어도 같게 만든다.
#
# **되돌리지 않는 경우**를 셋 둔다. 되돌림이 다른 것을 망가뜨리는 자리들이다.
MERGE_LEN_RATIO = 1.6     # 짝이 이만큼 길어졌으면 병합으로 본다
MERGE_FOREIGN_TOKENS = 3  # 원문에 없던 내용어가 이만큼이면 병합으로 본다

# **복원은 판정보다 엄격하다.** 잘못 판정하면 경고 한 줄이지만, 잘못 복원하면
# 멀쩡한 편집을 되돌려 글을 망친다.
#
# 영어 실측 보정(2026-09-05, 소실 짝 55건 vs 무작위 무관 짝 400건):
#   임계 0.35 — 실제 47/55 통과 · 무관 11.2% 오통과   (판정용, MIN_PAIR_SIM)
#   임계 0.45 — 실제 41/55 통과 · 무관  0.8% 오통과   (복원용, 아래)
# 한국어 값(0.35)을 그대로 쓰면 무관 짝 아홉에 하나꼴로 되돌리게 된다.
RESTORE_MIN_SIM = 0.45


def _words(s: str) -> set[str]:
    return {w.strip(".,;:!?\"'()").lower() for w in s.split() if len(w) > 2}


def restore(before: str, after: str, modals: dict | None = None) -> tuple[str, list, list]:
    """서법이 사라진 문장을 원문 문장으로 되돌린다.

    반환: (복원된 텍스트, 복원 목록, 건너뛴 목록).
    건너뛴 것도 **보고한다** — 조용히 버리면 손실이 어디로 갔는지 흔적이 없다.
    """
    losses = find_losses(before, after, modals)
    result = after
    restored: list[dict] = []
    skipped: list[dict] = []
    for loss in losses:
        if _sim(loss["before"], loss["after"]) < RESTORE_MIN_SIM:
            skipped.append({**loss, "reason": "짝 유사도가 복원 임계 미만 — 같은 문장인지 확신 불가"})
            continue
        if result.count(loss["after"]) != 1:
            skipped.append({**loss, "reason": "결과에서 유일하게 특정되지 않음"})
            continue
        foreign = _words(loss["after"]) - _words(loss["before"])
        longer = len(loss["after"]) >= len(loss["before"]) * MERGE_LEN_RATIO
        if longer and len(foreign) >= MERGE_FOREIGN_TOKENS:
            skipped.append({**loss, "reason": "문장 병합 의심 — 되돌리면 다른 명제가 사라진다"})
            continue
        result = result.replace(loss["after"], loss["before"], 1)
        restored.append({**loss, "restored_as": loss["before"]})
    return result, restored, skipped


def main(argv: list[str] | None = None) -> int:
    """Exit code: 0 보존 / 1 소실 / 3 실행 오류."""
    ap = argparse.ArgumentParser(description="서법 소실 게이트 (영어 P5)")
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--write", action="store_true",
                    help="서법이 사라진 문장을 원문으로 되돌려 --after 파일에 쓴다")
    args = ap.parse_args(argv)

    try:
        with open(args.before, encoding="utf-8") as f:
            before = f.read()
        with open(args.after, encoding="utf-8") as f:
            after = f.read()
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    if args.write:
        fixed, restored, skipped = restore(before, after)
        if restored:
            with open(args.after, "w", encoding="utf-8") as f:
                f.write(fixed)
            for r in restored:
                print(f"restored [{r['kind']}·{r['marker']}] {r['after'][:44]} → {r['before'][:44]}")
        for sk in skipped:
            print(f"skipped   [{sk['kind']}·{sk['marker']}] {sk['reason']}")
        print(f"restore: 복원 {len(restored)}건 · 보류 {len(skipped)}건")
        after = fixed

    out = check_modality_loss(before, after)
    for kind, (b, a) in sorted(out["counts"].items()):
        print(f"  {kind:9} {b} → {a}  (참고 총수 — 판정에 쓰지 않음)")
    print(f"modality: {out['note']}")
    for l in out["lost"][:3]:
        print(f"          [{l['kind']}·{l['marker']}] {l['before'][:44]} → {l['after'][:44]}")
    if out["uncertain"]:
        print(f"          관찰: 짝 유사도가 낮아 판정 보류 {len(out['uncertain'])}건 (exit 미반영)")
    if out["failed"]:
        print("gate: FAIL — 유보·당위가 단정이 됐다. 해당 문장의 서법을 되돌릴 것")
        return 1
    print("gate: OK — 서법 보존")
    return 0


if __name__ == "__main__":
    sys.exit(main())
