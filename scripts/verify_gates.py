#!/usr/bin/env python3
"""Tier 1 구조 게이트 — 6축 통합 결정적 사후 검증 (LLM 콜 0).

`verify_change_rate.py`(문자율 단축 게이트)의 확장판. 문자 diff는 구조
편집에 눈이 없다 — 실측에서 change_rate 2.77% 뒤에 문장 터치율 29.7%,
ending_comma -86%, C-8 대구 -75%가 숨어 있었다. 이 스크립트는 문자율에
더해 (목표 달성 · 대구 전멸 · golden+수치) 3축을 결정적 코드로 판정해
문자율의 사각지대를 보완한다. 기존 verify_change_rate.py는 그대로 두고
(하위 호환), 신규 게이트는 이 파일이 담당한다.

6축 + 리포트:
    P0 문자율   — change_rate() vs WARN 30% / ABORT 50% (기존과 동일 판정)
    P1 목표달성 — before z > +2.0인 어휘 S1 지표가 after에서 z <= +1.0으로
                  내려왔는가. 미달(> +2.0)·과교정(< -1.5)은 WARN.
    P2 전멸    — C-8 대구: before >= 5 AND after == 0 이면 FAIL.
    P3 golden  — scripts/checks.run_checks() 실패 목록 (수치 주입 포함).
                 fail 레벨 코드만 출력·집계 (warn은 P6 보존에서만 보고).
    P4 터치율  — 원문 문장 중 after에 그대로 없는 비율. 게이트 아님, 보고만.
    P5 서법    — 당위("~해야 한다")·추측("~할 수 있다") 표지 총수가 줄면 WARN.
                 줄었다 = 필자가 요구·유보한 것을 단정으로 바꿨을 가능성.
                 I-4 처방은 '이동'만 허용하므로 총수가 보존돼야 정상이다.
                 늘어나는 것은 대상 아님(당위 주입은 P3 golden 소관).
    P6 보존    — 엔티티·수치 소실 관찰. 1건 이상이면 WARN(exit 1)으로 올린다.
                 (삭제는 축약 부산물일 수 있어 exit 2는 주지 않는다.)

Exit code (verify_change_rate.py와 의미 동일):
    0 — 수렴 (전 축 통과)
    1 — 경고 (문자율 30~50% / 목표 미달·과교정 / 전멸 / golden FAIL / 서법 감소)
    2 — 중단 (문자율 >= 50%). 윤문본 채택 금지 — 최우선.
    3 — 실행 오류 (입력 파일 없음 등). 게이트 판정 불가.

CLI:
    python3 scripts/verify_gates.py \
        --before _workspace/{run_id}/01_input.txt \
        --after  _workspace/{run_id}/final.md \
        --genre essay
    옵션: --json (구조화 출력 병기) / --ignore-markup (문자율 축만 적용)
"""

from __future__ import annotations

import argparse
import json
import re as _re
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_REFS = os.path.join(_ROOT, "skills", "humanize-korean", "references")
# checks 는 프로덕션 검사 구현이라 scripts/ 에 둔다(이 파일과 같은 디렉터리).
# 예전에는 tests/golden/ 에 있어 프로덕션 게이트가 테스트 트리를 런타임 import 했고,
# tests/ 를 뺀 선별 배포에서는 P3 golden 축이 통째로 죽었다. (#59)
for _p in (_REFS, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import checks as _checks  # noqa: E402  (sys.path mutation is intentional)
import metrics_v2 as _m  # noqa: E402

# final.md 본문 끝의 메타데이터 주석 블록. 여는 마커부터 파일 끝까지.
_SUMMARY_BLOCK_RE = re.compile(r"<!--\s*HUMANIZE-SUMMARY\b.*", re.DOTALL)

# P1 목표 달성 축의 어휘 S1 후보 지표. lexical_diversity는 제외 —
# 높을수록 사람 글이라 감축 대상이 아니다.
S1_CANDIDATE_METRICS = (
    "comma_inclusion_rate",
    "comma_usage_rate",
    "ending_comma_rate",
    "comma_segment_length",
    "hanja_nominalizer_density",
)

# P1 임계값
S1_SELECT_Z = 2.0      # before z가 이보다 크면 S1 대상
S1_ACHIEVED_Z = 1.0    # after z가 이하이면 달성
S1_MISSED_Z = 2.0      # after z가 이보다 크면 미달 (조용한 실패)
S1_OVERCORRECT_Z = -1.5  # after z가 미만이면 과교정

# P2 전멸 임계값 — 원래 대구가 이만큼은 있어야 "전멸"이 의미를 가진다.
ANNIHILATION_MIN_BEFORE = 5

_WS_RE = re.compile(r"\s+")


def strip_summary_block(text: str) -> str:
    """final.md에서 `<!-- HUMANIZE-SUMMARY -->` 메타 블록을 제거한다."""
    return _SUMMARY_BLOCK_RE.sub("", text).strip()


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _norm_sentence(s: str) -> str:
    return _WS_RE.sub(" ", s).strip()


def sentence_touch_rate(before: str, after: str) -> tuple[float, int, int]:
    """원문 문장 중 after에 (공백 정규화 후) 그대로 없는 비율.

    게이트가 아니라 리포트 전용 — 문자율이 낮아도 구조 편집이 넓게 퍼져
    있으면 이 수치가 드러낸다. 반환: (rate, touched, total).
    """
    before_sents = [_norm_sentence(s) for s in _m._split_sentences(before)]
    before_sents = [s for s in before_sents if s]
    if not before_sents:
        return 0.0, 0, 0
    after_set = {_norm_sentence(s) for s in _m._split_sentences(after)}
    touched = sum(1 for s in before_sents if s not in after_set)
    return touched / len(before_sents), touched, len(before_sents)


# ── P5 서법 보존 ───────────────────────────────────────────────────
# 실행자 자기 점검은 신뢰할 수 없다: A/B 실측에서 "게이트 롤백 0건"이라
# 보고했으나 의무 표지가 실제로 줄어든 사례가 2건 있었다(6→5, 9→8).
# 당위·추측 표지의 '총수'를 결정적으로 세어 서법 변경을 잡는다.
#
# 원칙: 표지가 줄면 = 필자가 요구·유보한 것을 단정으로 바꿨을 가능성.
#       I-4 처방은 '이동'만 허용하므로 총수가 보존돼야 정상이다.
#       늘어나는 것은 게이트 대상이 아니다(원문에 없던 당위 주입은
#       P3 golden의 상투구 축이 별도로 본다).
DEONTIC_RE = _re.compile(
    r"[가-힣]야\s*(?:한다|합니다|했다|하며|하고|할)"
    r"|[가-힣]\s*필요가\s*있다"
    r"|요구된다"
    r"|하지\s*않으면\s*안\s*[되돼]"
)
HEDGE_RE = _re.compile(
    r"수\s*(?:있다|있습니다|있을)"
    r"|것으로\s*(?:보인다|보입니다|전망)"
    r"|가능성이\s*(?:있다|높다)"
    r"|[을ㄹ]\s*수도"
)
# 감소 허용 폭 — 문장 병합 등 정상 처리에서 1건은 흔들릴 수 있다.
MODALITY_TOLERANCE = 0


def count_modality(text: str) -> tuple[int, int]:
    """(당위 표지 수, 완곡 표지 수)."""
    return len(DEONTIC_RE.findall(text)), len(HEDGE_RE.findall(text))


def judge_s1_targets(
    z_before: dict, z_after: dict
) -> tuple[list[dict], bool]:
    """P1 목표 달성 판정. 반환: (지표별 판정 목록, warn 여부).

    S1 대상 = S1_CANDIDATE_METRICS 중 before z > +2.0인 지표.
    각 대상: after z <= +1.0 달성 / > +2.0 미달(WARN) / < -1.5 과교정(WARN)
    / 그 사이는 부분 개선(통과). after z가 None이면 판정 불가(보고만).
    """
    results: list[dict] = []
    warn = False
    for key in S1_CANDIDATE_METRICS:
        zb = z_before.get(key)
        if zb is None or zb <= S1_SELECT_Z:
            continue
        za = z_after.get(key)
        if za is None:
            verdict = "판정불가 (after z 없음)"
        elif za <= S1_OVERCORRECT_Z:
            verdict, warn = "과교정", True
        elif za <= S1_ACHIEVED_Z:
            verdict = "달성"
        elif za > S1_MISSED_Z:
            verdict, warn = "미달", True
        else:
            verdict = "부분 개선"
        results.append({
            "metric": key,
            "z_before": round(zb, 2),
            "z_after": round(za, 2) if za is not None else None,
            "verdict": verdict,
        })
    return results, warn


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Tier 1 구조 게이트 (5축 통합)")
    p.add_argument("--before", required=True, help="원문 경로 (01_input.txt)")
    p.add_argument("--after", required=True, help="윤문본 경로 (final.md)")
    p.add_argument("--genre", default="essay", help="essay/column/report/blog/abstract")
    p.add_argument("--json", action="store_true", help="구조화 JSON 출력 병기")
    p.add_argument(
        "--ignore-markup",
        action="store_true",
        help="문자율 축에서 마크업 줄·줄머리 장식을 제외하고 본문만 비교",
    )
    args = p.parse_args(argv)

    for path in (args.before, args.after):
        if not os.path.exists(path):
            print(f"error: 파일 없음: {path}", file=sys.stderr)
            return 3

    try:
        before = strip_summary_block(_read(args.before))
        after = strip_summary_block(_read(args.after))
    except OSError as e:
        print(f"error: 파일 읽기 실패: {e}", file=sys.stderr)
        return 3

    report: dict = {"genre": args.genre}
    warn = False

    # --- P0 문자율 (기존 verify_change_rate.py와 동일 판정) ---------------
    rate = _m.change_rate(before, after, ignore_markup=args.ignore_markup)
    abort = rate >= _m.CHANGE_RATE_ABORT
    if _m.CHANGE_RATE_WARN <= rate < _m.CHANGE_RATE_ABORT:
        warn = True
    scope = "본문만 (마크업 제외)" if args.ignore_markup else "전문"
    if abort:
        p0_verdict = "ABORT — 강제 중단. 윤문본 채택 금지"
    elif rate >= _m.CHANGE_RATE_WARN:
        p0_verdict = "WARN — 과윤문 경고"
    else:
        p0_verdict = "OK"
    report["change_rate"] = {
        "rate": round(rate, 4), "scope": scope, "verdict": p0_verdict,
    }
    print(f"[P0 문자율] {rate * 100:.1f}% [{scope}] — {p0_verdict} "
          f"(경고 {_m.CHANGE_RATE_WARN * 100:.0f}% / 중단 {_m.CHANGE_RATE_ABORT * 100:.0f}%)")

    # --- P1 목표 달성 (before z > +2.0인 어휘 S1 지표) --------------------
    try:
        z_before = _m.compute_all_v2(before, genre=args.genre)["z_scores"]
        z_after = _m.compute_all_v2(after, genre=args.genre)["z_scores"]
    except Exception as e:  # graceful degrade — 이 축만 판정 불가
        z_before, z_after = {}, {}
        print(f"[P1 목표달성] 판정 불가 (metrics 오류: {e})", file=sys.stderr)
    s1_results, s1_warn = judge_s1_targets(z_before, z_after)
    warn = warn or s1_warn
    report["s1_targets"] = s1_results
    if not s1_results:
        print("[P1 목표달성] N/A — 구조 진단 (어휘 S1 앵커 없음)")
    else:
        for r in s1_results:
            za = f"{r['z_after']:+.2f}" if r["z_after"] is not None else "?"
            print(f"[P1 목표달성] {r['metric']}: z {r['z_before']:+.2f} → {za}"
                  f"  {r['verdict']}")

    # --- P2 전멸 (C-8 대구) ----------------------------------------------
    anti_before = _m.antithesis_count(before)
    anti_after = _m.antithesis_count(after)
    annihilated = anti_before >= ANNIHILATION_MIN_BEFORE and anti_after == 0
    warn = warn or annihilated
    report["antithesis"] = {
        "before": anti_before, "after": anti_after,
        "verdict": "FAIL — 전멸" if annihilated else (
            "OK" if anti_before >= ANNIHILATION_MIN_BEFORE
            else "스킵 (원문 대구 < 5)"),
    }
    print(f"[P2 전멸] C-8 대구 {anti_before} → {anti_after} — "
          f"{report['antithesis']['verdict']}")

    # --- P3 golden --------------------------------------------------------
    # warn 레벨(entity_lost/number_dropped)은 P6 보존 축에서만 보고한다.
    # P3는 fail 레벨 코드만 출력·집계 — 중복 경고 방지.
    failures = _checks.run_checks(before, after)
    fail_failures = [f for f in failures if f.level != "warn"]
    warn = warn or bool(failures)  # exit 판정은 warn 포함 전체 기준 유지
    report["golden"] = [
        {"code": f.code, "message": f.message, "level": f.level}
        for f in failures
    ]
    if fail_failures:
        print(f"[P3 golden] FAIL — {len(fail_failures)}건:")
        for f in fail_failures:
            print(f"    [FAIL] {f}")
    else:
        print("[P3 golden] PASS (수치 주입·각주·인용·register 이상 없음)")

    # --- P4 터치율 (리포트 전용 — 게이트 아님) ----------------------------
    touch_rate, touched, total = sentence_touch_rate(before, after)
    report["sentence_touch"] = {
        "rate": round(touch_rate, 4), "touched": touched, "total": total,
    }
    print(f"[P4 터치율] {touch_rate * 100:.1f}% ({touched}/{total} 문장) — 보고 전용")

    # --- P5 서법 보존 (당위·추측 표지 총수) -------------------------------
    deo_b, hed_b = count_modality(before)
    deo_a, hed_a = count_modality(after)
    deo_lost = deo_b - deo_a
    hed_lost = hed_b - hed_a
    modality_fail = deo_lost > MODALITY_TOLERANCE or hed_lost > MODALITY_TOLERANCE
    warn = warn or modality_fail
    report["modality"] = {
        "deontic": {"before": deo_b, "after": deo_a},
        "hedge": {"before": hed_b, "after": hed_a},
        "verdict": ("FAIL — 서법 표지 감소(당위·추측을 단정으로 바꿨을 수 있음)"
                    if modality_fail else "OK"),
    }
    print(f"[P5 서법] 당위 {deo_b} → {deo_a} / 완곡 {hed_b} → {hed_a} — "
          f"{report['modality']['verdict']}")

    # --- P6 보존 (엔티티·수치 소실 — 1건 이상이면 WARN) ------------------
    e_lost = _checks.dropped_entities(before, after)
    n_lost = _checks.dropped_numbers(before, after)
    report["preservation"] = {"entities_lost": e_lost, "numbers_lost": n_lost}
    if e_lost or n_lost:
        warn = True
    if e_lost:
        print(f"[P6 보존] 엔티티 소실: {e_lost} "
              f"(삭제는 축약 부산물일 수 있음 — WARN)")
    if n_lost:
        print(f"[P6 보존] 수치 소실: {n_lost} "
              f"(문장 병합·표기 통합이면 정상 — WARN)")
    if not e_lost and not n_lost:
        print("[P6 보존] OK (엔티티·수치 소실 없음)")

    # --- 통합 판정 --------------------------------------------------------
    if abort:
        verdict, code = "ABORT — 강제 중단. 윤문본 채택 금지", 2
    elif warn:
        verdict, code = "WARN — 경고. 사용자 고지 + finalize 승급", 1
    else:
        verdict, code = "OK — 수렴", 0
    report["gate"] = {"verdict": verdict, "exit_code": code}
    print(f"gate: {verdict}")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


# ── 콘솔 하드닝 (#84) ───────────────────────────────────────────────
# Windows(cp949)에서 한글·em-dash 출력이 UnicodeEncodeError 로 죽는 것을 막는다.
import os as _os  # noqa: E402
import sys as _sys  # noqa: E402

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import console as _console  # noqa: E402

if __name__ == "__main__":
    _sys.exit(_console.run_gate(main))
