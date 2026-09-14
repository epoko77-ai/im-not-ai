#!/usr/bin/env python3
"""Tier 1 구조 게이트 — 5축 통합 결정적 사후 검증 (LLM 콜 0).

`verify_change_rate.py`(문자율 단축 게이트)의 확장판. 문자 diff는 구조
편집에 눈이 없다 — 실측에서 change_rate 2.77% 뒤에 문장 터치율 29.7%,
ending_comma -86%, C-8 대구 -75%가 숨어 있었다. 이 스크립트는 문자율에
더해 (목표 달성 · 대구 전멸 · golden+수치) 3축을 결정적 코드로 판정해
문자율의 사각지대를 보완한다. 기존 verify_change_rate.py는 그대로 두고
(하위 호환), 신규 게이트는 이 파일이 담당한다.

5축 + 리포트:
    P0 문자율   — change_rate() vs WARN 30% / ABORT 50% (기존과 동일 판정)
    P1 목표달성 — before z > +2.0인 어휘 S1 지표가 after에서 z <= +1.0으로
                  내려왔는가. 미달(> +2.0)·과교정(< -1.5)은 WARN.
    P2 전멸    — C-8 대구: before >= 5 AND after == 0 이면 FAIL.
    P3 golden  — scripts/checks.run_checks() 실패 목록 (수치 주입 포함).
    P4 터치율  — 원문 문장 중 after에 그대로 없는 비율 + 수치 소실 관찰.
                 게이트 아님, 보고만 (수치 소실은 문장 병합·표기 통합의
                 정상 부산물일 수 있어 exit code에 기여하지 않는다).
    P5 서법    — 원문·윤문본을 문장 정렬해, 짝 문장에서 당위("~해야 한다")·추측
                 ("~할 수 있다")이 사라졌으면 WARN. 총수가 아니라 **문장쌍**으로 본다
                 — 총수는 오검출과 실손실이 상쇄돼 진짜 위반을 가린다.
                 짝 유사도가 낮은 건은 보고만 하고 exit code에 넣지 않는다.
                 늘어나는 것은 대상 아님(당위 주입은 P3 golden 소관).

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
# ⚠️ 완곡 사전과 같은 이유로 넓게 잡는다. 구 사전은 "~야 한다" 계열과 "필요가 있다"뿐이라
# 결말 당위를 통째로 놓쳤다 — "지금이야말로 제도의 틀을 다시 짤 때다", "규제 정비가 시급하다",
# "대책이 필요하다", "손봐야만 한다", "우리의 과제다", "속도가 관건이다"가 전부 미검출이었다.
# I-4의 표적이 바로 **문단을 끝맺는 당위**인데, 그 대표형을 세지 못하면 P5가 I-4 처방의
# 위반(당위 삭제·서법 치환)을 검출할 수 없다.
#
# `(?!이)`: "불이야 하고 외쳤다"·"내 스타일이야 하지만" 같은 계사(-이야)를 배제한다.
# 앞 음절을 한글 전체로 열어 두면 이 오검출이 실제로 났다.
DEONTIC_RE = _re.compile(
    r"(?:(?!이)[가-힣])야\s*(?:한다|합니다|했다|하며|하고|하는|할|함)"
    r"|(?:(?!이)[가-힣])야만"
    r"|필요가\s*있"
    r"|필요하다|필요합니다"
    r"|요구된다|요구됩니다"
    # 부사형은 완료된 행위의 방식이라 당위가 아니다("환자를 시급히 이송했다",
    # "공사가 불가피하게 연기됐다"). 종결형만 잡는다. "불가피하다"는 당위보다
    # 예측 단정에 가까워 아예 뺀다.
    r"|시급하다|시급합니다"
    r"|바람직하다|바람직합니다"
    # ⚠️ "~할 때다 / 시점이다 / 때가 왔다" 갈래는 **넣지 않는다.**
    #  (1) 오검출: "그 사진은 내가 어릴 때다", "터진 건 방심했을 때다"처럼 순수 시점 서술이
    #      같은 형태다. -ㄹ 때다는 당위와 회상 양쪽에 쓰여 어휘로 분리되지 않는다.
    #  (2) D-6 충돌: D-6은 "지금이야말로 ~할 때다"에서 상투적 껍데기만 벗기라고 처방한다.
    #      이 갈래를 세면 **카탈로그가 승인한 편집이 서법 소실로 잡히고**, 복원기가
    #      "지금이야말로"를 도로 심는다(실측 3/3 재현). 변종을 채워 넣어도 모델이 다음
    #      환언("짜기에 지금만 한 때가 없다")으로 빠져나가 두더지잡기가 된다.
    #      결말 당위 자체는 "~해야 한다" 계열이 대표형으로 잡는다.
    # 맨몸 명사는 오검출이다("촉구 집회가 열렸다", "당부의 말로 대신했다"). 또 "촉구했다"는
    # 제3자 발화 보도라 필자의 서법이 아니다 — 현재형 동사만 남긴다.
    r"|촉구한다|당부한다"
    # 두 군데가 좁았다: 어간을 "하-"로 못 박아 "풀지 않으면"을 놓쳤고,
    # 꼬리 `[되돼]`가 **"안 된다"의 '된'을 못 잡았다**(된 != 되).
    r"|[가-힣]지\s*않으면\s*안\s*(?:된다|됩니다|되며|돼|되)"
)
# ⚠️ 완곡 사전은 넓어야 한다. 구 사전은 네 갈래뿐이라 **실측에서 완곡 7개 중 1개만 셌다** —
# "판단된다·여겨진다·듯하다·추정·배제할 수 없다"가 전부 빠져 있었다. 서법 보존을 표방하면서
# 그 위반을 검출하지 못하는 상태였다(A/B에서 게이트가 통과시킨 출력이 유보를 단정으로
# 바꾼 문장을 그대로 담고 있었다: "낮은 것으로 판단된다" → "낮은 수치다").
#
# 넓히되 두 가지는 넣지 않는다:
#  (1) **카탈로그가 제거를 지시하는 상투구** — D-2 "시사하는 바가 크다", I-1 "~것이다" 결말.
#      규칙이 시킨 편집을 게이트가 되돌리라고 하는 상충이 생긴다.
#  (2) **일반 명사·동사로도 흔한 말** — 견해·관측·이르다("견해차", "관측 장비", "합의에 이르다").
#      실측에서 과탐이었다.
HEDGE_RE = _re.compile(
    r"수\s*(?:있다|있습니다|있을)"
    r"|것으로\s*(?:보인다|보입니다|전망|판단|추정|알려)"
    # 맨몸 "가능성"은 복합명사에 걸린다("성장 가능성 평가 지표"). 조사가 붙은 형태만.
    r"|가능성[이도은을에]"
    r"|[을ㄹ]\s*수도|수도\s*있"
    # 맨몸 "보인다"는 시각 지각이다("창밖으로 남산이 보인다"). 인식 양태 조사와 함께만.
    r"|[로으]\s*보인다|[로으]\s*보입니다"
    r"|판단된다|판단됩니다"
    r"|여겨진다|여겨집니다"
    r"|해석된다|추정된다|기대된다|우려된다"
    r"|듯하|듯\s*싶"
    r"|것\s*같다"
    # ⚠️ "전망"·"예상"을 맨몸으로 넣으면 **"이전 전망치보다"** 같은 명사에 걸린다.
    # 그러면 원문·윤문본 양쪽에서 같이 잡혀 **진짜 서법 소실을 가린다**
    # ("낮은 것으로 판단된다" → "낮은 수치다"가 전망치 때문에 손실 0으로 계산됐다).
    r"|전망(?:이다|된다|한다|했다|입니다|이며|하고)"
    r"|예상(?:된다|이다|한다|했다|됩니다)"
    r"|단정하기"
    r"|여지(?:도|가)?\s*있"
    r"|배제할\s*수\s*없"
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

    # --- P3 golden + 수치 -------------------------------------------------
    failures = _checks.run_checks(before, after)
    warn = warn or bool(failures)
    report["golden"] = [{"code": f.code, "message": f.message} for f in failures]
    if failures:
        print(f"[P3 golden] FAIL — {len(failures)}건:")
        for f in failures:
            print(f"    FAIL {f}")
    else:
        print("[P3 golden] PASS (수치 주입·각주·인용·register 이상 없음)")

    # --- P4 터치율 + 수치 소실 관찰 (리포트 전용 — 게이트 아님) -----------
    touch_rate, touched, total = sentence_touch_rate(before, after)
    report["sentence_touch"] = {
        "rate": round(touch_rate, 4), "touched": touched, "total": total,
    }
    print(f"[P4 터치율] {touch_rate * 100:.1f}% ({touched}/{total} 문장) — 보고 전용")
    dropped = _checks.dropped_numbers(before, after)
    report["numbers_dropped"] = dropped
    if dropped:
        print(f"[P4 수치소실] 관찰: {dropped} "
              f"(문장 병합·표기 통합이면 정상 — exit 미반영, 확인 요망)")

    # --- P5 서법 보존 (문장쌍 판정) ---------------------------------------
    #
    # 총수 비교에서 문장쌍 판정으로 바꿨다. 총수는 **위치를 안 보기 때문에 오검출과
    # 실손실이 서로 상쇄된다** — 윤문이 다른 문장에서 사전 어휘를 우연히 만들어내면
    # ("재빨리"→"시급히") 진짜 서법 소실이 net 0으로 가려진다. 한 표현이 표지 2개로
    # 세지는 이중 계수도 있어, 동력을 보존한 정상 윤문이 false WARN을 냈다.
    #
    # 문장쌍은 "어느 문장의 어떤 서법이 사라졌는가"를 보므로 상쇄가 구조적으로 불가능하다.
    # 덤으로 카탈로그 충돌 상당수가 자동 해소된다 — D-2·D-3의 상투구 삭제는 문장이 통째로
    # 사라지거나 짝이 없어 판정 대상 밖이다(총수 기준에서는 곧바로 위반이었다).
    #
    # 정렬 코드는 restore_modality가 이미 갖고 있다(같은 사전을 쓰는 단일 출처).
    # 순환 import를 피하려고 함수 안에서 늦게 불러온다.
    from restore_modality import find_losses  # noqa: PLC0415

    losses = find_losses(before, after)
    confident = [l for l in losses if not l.get("low_sim")]
    uncertain = [l for l in losses if l.get("low_sim")]
    modality_fail = len(confident) > MODALITY_TOLERANCE
    warn = warn or modality_fail
    deo_b, hed_b = count_modality(before)
    deo_a, hed_a = count_modality(after)
    report["modality"] = {
        "lost_pairs": [
            {"kind": l["kind"], "before": l["before"], "after": l["after"]}
            for l in confident
        ],
        # 짝 유사도가 낮아 같은 문장인지 확신할 수 없는 건은 exit code에 넣지 않는다.
        # 다만 조용히 버리지도 않는다 — 진짜 소실이 여기 섞여 있을 수 있다(P4와 같은 정책).
        "uncertain_pairs": [
            {"kind": l["kind"], "before": l["before"], "after": l["after"]}
            for l in uncertain
        ],
        # 총수는 참고용으로만 남긴다. 판정 근거가 아니다.
        "counts": {
            "deontic": {"before": deo_b, "after": deo_a},
            "hedge": {"before": hed_b, "after": hed_a},
        },
        "verdict": (f"FAIL — 서법 소실 {len(confident)}문장"
                    if modality_fail else "OK"),
    }
    print(f"[P5 서법] 소실 {len(confident)}문장 "
          f"(참고 총수: 당위 {deo_b}→{deo_a} / 완곡 {hed_b}→{hed_a}) — "
          f"{report['modality']['verdict']}")
    for l in confident[:3]:
        print(f"          [{l['kind']}] {l['before'][:34]} → {l['after'][:34]}")
    if uncertain:
        print(f"          관찰: 짝 유사도가 낮아 판정 보류한 건 {len(uncertain)}건 "
              f"(exit 미반영 — 확인 요망)")

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
