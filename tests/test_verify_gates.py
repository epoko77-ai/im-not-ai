"""Tests for scripts/verify_gates.py — Tier 1 구조 게이트 (6축 통합).

Runs under pytest OR `python -m unittest` (same convention as
test_golden.py). No LLM calls — the gate is pure Python; this suite
validates axis logic (목표달성/미달/과교정/전멸) and the merged exit codes
with synthetic z dicts and hand-made tiny texts. 사용자 원고 픽스처 없음.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCRIPT_PATH = os.path.join(PROJECT_ROOT, "scripts", "verify_gates.py")

_spec = importlib.util.spec_from_file_location("verify_gates", SCRIPT_PATH)
verify_gates = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify_gates)


def _write(dirpath: str, name: str, text: str) -> str:
    path = os.path.join(dirpath, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


# ===========================================================================
# P1 목표 달성 — judge_s1_targets 분기 (합성 z)
# ===========================================================================


class JudgeS1TargetsTests(unittest.TestCase):
    def _one(self, zb: float, za: float | None) -> tuple[dict, bool]:
        results, warn = verify_gates.judge_s1_targets(
            {"ending_comma_rate": zb}, {"ending_comma_rate": za}
        )
        self.assertEqual(len(results), 1)
        return results[0], warn

    def test_achieved(self) -> None:
        r, warn = self._one(6.29, 0.46)
        self.assertEqual(r["verdict"], "달성")
        self.assertFalse(warn)

    def test_missed_is_warn(self) -> None:
        """진단이 지목한 지표가 안 고쳐진 '조용한 실패' — WARN."""
        r, warn = self._one(6.29, 5.80)
        self.assertEqual(r["verdict"], "미달")
        self.assertTrue(warn)

    def test_overcorrected_is_warn(self) -> None:
        r, warn = self._one(6.29, -2.10)
        self.assertEqual(r["verdict"], "과교정")
        self.assertTrue(warn)

    def test_partial_improvement_passes(self) -> None:
        r, warn = self._one(6.29, 1.50)
        self.assertEqual(r["verdict"], "부분 개선")
        self.assertFalse(warn)

    def test_after_none_is_undecidable_not_warn(self) -> None:
        r, warn = self._one(6.29, None)
        self.assertIn("판정불가", r["verdict"])
        self.assertFalse(warn)

    def test_no_anchor_when_before_below_threshold(self) -> None:
        results, warn = verify_gates.judge_s1_targets(
            {"ending_comma_rate": 1.33, "comma_usage_rate": -0.6},
            {"ending_comma_rate": 0.4, "comma_usage_rate": -0.5},
        )
        self.assertEqual(results, [])
        self.assertFalse(warn)

    def test_lexical_diversity_never_selected(self) -> None:
        """높을수록 사람 글 — 감축 대상이 아니므로 S1 후보에서 제외."""
        results, _ = verify_gates.judge_s1_targets(
            {"lexical_diversity": 5.0}, {"lexical_diversity": 5.0}
        )
        self.assertEqual(results, [])

    def test_multiple_anchors_reported(self) -> None:
        results, warn = verify_gates.judge_s1_targets(
            {"ending_comma_rate": 6.0, "comma_inclusion_rate": 3.0},
            {"ending_comma_rate": 0.5, "comma_inclusion_rate": 2.5},
        )
        self.assertEqual(len(results), 2)
        verdicts = {r["metric"]: r["verdict"] for r in results}
        self.assertEqual(verdicts["ending_comma_rate"], "달성")
        self.assertEqual(verdicts["comma_inclusion_rate"], "미달")
        self.assertTrue(warn)


# ===========================================================================
# P4 터치율 — sentence_touch_rate
# ===========================================================================


class SentenceTouchRateTests(unittest.TestCase):
    def test_identity_is_zero(self) -> None:
        text = "오늘은 비가 온다. 길이 미끄럽다. 우산을 챙겼다."
        rate, touched, total = verify_gates.sentence_touch_rate(text, text)
        self.assertEqual(rate, 0.0)
        self.assertEqual(touched, 0)
        self.assertEqual(total, 3)

    def test_partial_touch_counted(self) -> None:
        before = "오늘은 비가 온다. 길이 미끄럽다. 우산을 챙겼다."
        after = "오늘은 비가 온다. 길이 몹시 미끄럽다. 우산을 챙겼다."
        rate, touched, total = verify_gates.sentence_touch_rate(before, after)
        self.assertEqual((touched, total), (1, 3))
        self.assertAlmostEqual(rate, 1 / 3)

    def test_empty_before_is_safe(self) -> None:
        self.assertEqual(verify_gates.sentence_touch_rate("", "출력."), (0.0, 0, 0))


# ===========================================================================
# main() end-to-end — exit code 통합 (소형 합성 텍스트)
# ===========================================================================

# 어휘 S1 앵커가 생기지 않는 평이한 텍스트 (쉼표 없음·대구 없음·수치 없음).
_PLAIN = (
    "오늘은 비가 온다. 길이 미끄럽다. 우산을 챙겨야 한다. "
    "버스가 늦게 온다. 정류장에는 사람이 많다."
)

# C-8 대구 6회 — 전멸 판정용.
_ANTITHESIS_HEAVY = (
    "문제는 속도가 아니라 방향이다. 핵심은 기술이 아니라 태도다. "
    "관건은 자본이 아니라 신뢰다. 목표는 규모가 아니라 지속이다. "
    "본질은 형식이 아니라 내용이다. 답은 통제가 아니라 자율이다."
)

# 위 대구를 전부 해체하되 나머지 표면은 최대한 보존 (문자율 < 30%).
_ANTITHESIS_WIPED = (
    "문제는 속도보다 방향이다. 핵심은 기술보다 태도다. "
    "관건은 자본보다 신뢰다. 목표는 규모보다 지속이다. "
    "본질은 형식보다 내용이다. 답은 통제보다 자율이다."
)


class MainExitCodeTests(unittest.TestCase):
    def _run(self, before: str, after: str, extra: list[str] | None = None) -> int:
        with tempfile.TemporaryDirectory() as d:
            b = _write(d, "before.txt", before)
            a = _write(d, "after.md", after)
            argv = ["--before", b, "--after", a] + (extra or [])
            return verify_gates.main(argv)

    def test_exit_0_identity(self) -> None:
        self.assertEqual(self._run(_PLAIN, _PLAIN), 0)

    def test_exit_1_annihilation(self) -> None:
        """대구 전멸(before>=5, after==0)은 문자율이 낮아도 경고."""
        self.assertEqual(self._run(_ANTITHESIS_HEAVY, _ANTITHESIS_WIPED), 1)

    def test_annihilation_skipped_when_before_sparse(self) -> None:
        before = "문제는 속도가 아니라 방향이다. 오늘은 비가 온다."
        after = "문제는 속도보다 방향이다. 오늘은 비가 온다."
        self.assertEqual(self._run(before, after), 0)

    def test_exit_1_golden_number_injection(self) -> None:
        after = _PLAIN + " 기온은 3.5도였다."
        self.assertEqual(self._run(_PLAIN, after), 1)

    def test_number_drop_is_report_only_exit_0(self) -> None:
        """수치 소실은 P4 관측 전용 — 정상 윤문 + 수치 소실은 exit 0 유지."""
        before = _PLAIN + " 물가는 2.4% 올랐다."
        after = _PLAIN  # 수치 문장 병합으로 소실됐다고 가정
        self.assertEqual(self._run(before, after), 0)

    def test_korean_unit_swap_not_injected(self) -> None:
        """"1만" → "10,000" 표기 교체는 주입/소실 어느 쪽도 아님 — exit 0."""
        before = _PLAIN + " 이용자는 1만 명이다."
        after = _PLAIN + " 이용자는 10,000 명이다."
        self.assertEqual(self._run(before, after), 0)

    def test_exit_2_total_rewrite_takes_priority(self) -> None:
        after = (
            "완전히 새로 쓴 글이며 2050년의 수치 99%를 주입했다. "
            "원문과 겹치는 표면이 거의 없어서 문자율이 오십 퍼센트를 넘는다."
        )
        self.assertEqual(self._run(_PLAIN, after), 2)

    def test_exit_3_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            b = _write(d, "before.txt", _PLAIN)
            missing = os.path.join(d, "nope.md")
            self.assertEqual(
                verify_gates.main(["--before", b, "--after", missing]), 3
            )

    def test_summary_block_stripped_before_judging(self) -> None:
        after = _PLAIN + "\n\n<!-- HUMANIZE-SUMMARY\n변경률 3% | 수치 2건\n-->\n"
        self.assertEqual(self._run(_PLAIN, after), 0)

    def test_json_flag_emits_parseable_report(self) -> None:
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as d:
            b = _write(d, "before.txt", _PLAIN)
            a = _write(d, "after.md", _PLAIN)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = verify_gates.main(["--before", b, "--after", a, "--json"])
        self.assertEqual(code, 0)
        out = buf.getvalue()
        start = out.index("{")
        report = json.loads(out[start:])
        self.assertEqual(report["gate"]["exit_code"], 0)
        self.assertIn("change_rate", report)
        self.assertIn("antithesis", report)
        self.assertIn("sentence_touch", report)
        self.assertIn("numbers_dropped", report)



# ===========================================================================
# P5 서법 보존 — 당위·추측 표지 총수 (v2.4)
# ===========================================================================


class ModalityGateTests(unittest.TestCase):
    """실행자 자기 점검이 놓친 서법 변경을 결정적으로 잡는가.

    A/B 실측에서 실행자가 "게이트 롤백 0건"이라 보고했으나 의무 표지가
    실제로는 줄어든 사례가 2건 있었다(6→5, 9→8). 자기 점검을 신뢰하지
    않고 코드로 세는 것이 이 축의 존재 이유다.
    """

    def test_counts_deontic_and_hedge(self) -> None:
        deo, hed = verify_gates.count_modality(
            "정부는 규제를 정비해야 한다. 효과는 시간이 걸릴 수 있다."
        )
        self.assertEqual(deo, 1)
        self.assertEqual(hed, 1)

    def test_move_preserves_markers(self) -> None:
        """I-4가 허용하는 '이동'은 표지 총수를 바꾸지 않는다."""
        before = "예산을 늘려야 한다. 효과는 크다."
        after = "효과는 크다. 예산을 늘려야 한다."
        self.assertEqual(
            verify_gates.count_modality(before)[0],
            verify_gates.count_modality(after)[0],
        )

    def test_merge_drops_marker(self) -> None:
        """금지된 '병합'은 의무 2건을 표지 1개로 줄인다 — 게이트가 잡아야 할 형태."""
        before = "예산을 늘려야 한다. 인력을 확충해야 한다."
        after = "예산을 늘리고 인력을 확충해야 한다."
        self.assertGreater(
            verify_gates.count_modality(before)[0],
            verify_gates.count_modality(after)[0],
        )

    def test_deontic_to_assertion_drops_marker(self) -> None:
        """당위 → 단정 전환(구 I-4 처방 (a)(b))도 표지 감소로 잡힌다."""
        before = "정부는 지원을 확대해야 한다."
        after = "정부는 지원을 확대한다."
        self.assertEqual(verify_gates.count_modality(before)[0], 1)
        self.assertEqual(verify_gates.count_modality(after)[0], 0)

    def test_hedge_to_assertion_drops_marker(self) -> None:
        before = "성장률이 반등할 수 있다."
        after = "성장률이 반등한다."
        self.assertEqual(verify_gates.count_modality(before)[1], 1)
        self.assertEqual(verify_gates.count_modality(after)[1], 0)

    def test_hedge_inventory_covers_observation_endings(self) -> None:
        """완곡 사전은 관측·추측 종결을 폭넓게 잡아야 한다.

        구 사전(수 있다·것으로 보인다·가능성이 있다·ㄹ 수도)은 실측 입력의 완곡 7건 중
        1건만 셌다. 게이트가 서법 보존을 표방하면서 위반을 못 보던 상태라, 유보를 단정으로
        바꾼 출력이 그대로 통과했다.
        """
        for marker in (
            "낮은 것으로 판단된다",
            "타당하다고 여겨진다",
            "충분한 듯하다",
            "가능성도 배제할 수 없다",
            "성장률을 2.7%로 전망했다",
            "개선될 수도 있다",
            "비용이 늘어날 것으로 추정된다",
            "개선될 여지가 있다",
        ):
            with self.subTest(marker=marker):
                self.assertGreaterEqual(
                    verify_gates.count_modality(marker)[1], 1, f"완곡 미검출: {marker}"
                )

    def test_deontic_inventory_covers_closing_obligation(self) -> None:
        """당위 사전은 **문단을 끝맺는 당위**를 잡아야 한다 — I-4의 표적이 바로 그것이다.

        구 사전은 "~야 한다"·"필요가 있다"뿐이라 결말 당위를 통째로 놓쳤고,
        P5가 I-4 위반(당위 삭제·서법 치환)을 검출할 수 없었다.
        """
        for marker in (
            "정부는 공유 플랫폼을 구축해야 한다",
            "제도의 틀을 다시 짜야 합니다",
            "규제 정비가 시급하다",
            "대책이 필요하다",
            "설계할 필요가 있다",
            "정비가 바람직하다",
            "지금 손봐야만 한다",
            "정비가 요구된다",
            "규제를 풀지 않으면 안 된다",
            "우리는 제도를 함께 손질한다고 촉구한다",
        ):
            with self.subTest(marker=marker):
                self.assertGreaterEqual(
                    verify_gates.count_modality(marker)[0], 1, f"당위 미검출: {marker}"
                )

    def test_deontic_inventory_excludes_copula_and_demonstratives(self) -> None:
        """계사 -이야와 지시어 그때·이때는 당위가 아니다."""
        for text in (
            "불이야 하고 외쳤다",
            "내 스타일이야 하지만 별수 없다",
            "바로 그때다",
            "이때다 싶어 뛰었다",
            "그건 다른 일이다",
            # 아래는 **의도적으로 사전에서 뺀** 갈래다(적대적 검토에서 오검출 확인).
            # -ㄹ 때다/시점이다: 순수 시점 서술과 형태가 같고, D-6이 승인한 편집을
            #   서법 소실로 오판하게 만든다.
            "그 사진은 내가 어릴 때다",
            "문제가 터진 건 방심했을 때다",
            "지금은 중요한 시점이다",
            # 부사형: 완료된 행위의 방식이지 당위가 아니다.
            "환자를 시급히 이송했다",
            "공사가 불가피하게 연기됐다",
            # 맨몸 명사·제3자 발화 보도: 필자의 서법이 아니다.
            "시민단체의 촉구 집회가 열렸다",
            "정부에 대책 마련을 촉구했다",
        ):
            with self.subTest(text=text):
                self.assertEqual(
                    verify_gates.count_modality(text)[0], 0, f"당위 과탐: {text}"
                )

    def test_hedge_inventory_excludes_catalog_removal_targets(self) -> None:
        """카탈로그가 제거를 지시하는 상투구는 완곡으로 세지 않는다.

        세면 규칙이 시킨 편집(D-2·I-1)을 게이트가 되돌리라고 요구하는 상충이 된다.
        일반 명사·동사로도 흔한 말(견해차·관측 장비·합의에 이르다)도 과탐이라 제외.
        """
        for text in (
            "시사하는 바가 크다",
            "중요한 요인인 것이다",
            "양측의 견해차가 컸다",
            "관측 장비를 새로 들였다",
            "결국 합의에 이르렀다",
        ):
            with self.subTest(text=text):
                self.assertEqual(
                    verify_gates.count_modality(text)[1], 0, f"완곡 과탐: {text}"
                )

    def test_hedge_inventory_excludes_perception_and_compound_nouns(self) -> None:
        """맨몸 어휘로 넓히면 지각 동사·복합명사가 걸린다(적대적 검토에서 확인)."""
        for text in (
            "창밖으로 남산이 보인다",
            "성장 가능성 평가 지표를 개편했다",
        ):
            with self.subTest(text=text):
                self.assertEqual(
                    verify_gates.count_modality(text)[1], 0, f"완곡 과탐: {text}"
                )

    def test_gate_warns_on_modality_loss(self) -> None:
        """main() 통합 판정에서 서법 감소가 exit code에 반영되는가."""
        with tempfile.TemporaryDirectory() as d:
            b = _write(d, "b.md", "정부는 예산을 늘려야 한다. 인력도 확충해야 한다.")
            a = _write(d, "a.md", "정부는 예산을 늘리고 인력도 확충한다.")
            code = verify_gates.main(["--before", b, "--after", a])
        self.assertGreaterEqual(code, 1)

    def test_pairwise_catches_loss_masked_by_offsetting_gain(self) -> None:
        """상쇄 은폐 — 총수 기준이면 통과하지만 실제로는 서법이 바뀐 경우.

        한 문장에서 유보가 단정으로 바뀌고, 무관한 다른 문장에서 사전 어휘가
        우연히 생기면 총수는 그대로다. 문장쌍 판정은 이걸 잡아야 한다.
        """
        before = "고용 효과는 제한적일 것으로 판단된다. 통계는 다음 주에 나온다."
        after = "고용 효과는 제한적이다. 통계는 다음 주에 나올 수 있다."
        # 총수는 상쇄돼 변화 없음 — 옛 기준이라면 통과했다.
        self.assertEqual(
            verify_gates.count_modality(before)[1],
            verify_gates.count_modality(after)[1],
        )
        with tempfile.TemporaryDirectory() as d:
            b = _write(d, "b.md", before)
            a = _write(d, "a.md", after)
            code = verify_gates.main(["--before", b, "--after", a])
        self.assertGreaterEqual(code, 1, "상쇄에 가려진 서법 소실을 놓쳤다")

    def test_pairwise_ignores_deleted_cliche_sentence(self) -> None:
        """카탈로그가 삭제를 지시한 상투구 문장은 서법 위반이 아니다.

        D-2 "시사하는 바가 크다" 삭제는 총수 기준에서는 곧바로 완곡 감소였다.
        문장이 통째로 사라지면 짝이 없으므로 문장쌍 판정의 대상이 아니다.
        """
        before = (
            "국내 클라우드 시장은 지난해 크게 성장했다. "
            "이는 시사하는 바가 크다고 할 수 있다. "
            "사업자들은 투자를 늘리고 있다."
        )
        after = (
            "국내 클라우드 시장은 지난해 크게 성장했다. "
            "사업자들은 투자를 늘리고 있다."
        )
        from restore_modality import find_losses

        confident = [l for l in find_losses(before, after) if not l.get("low_sim")]
        self.assertEqual(confident, [], f"삭제된 상투구를 위반으로 셌다: {confident}")

    def test_gate_ok_when_modality_kept(self) -> None:
        """이동만 한 경우 P5는 통과한다.

        짧은 텍스트에서 문장 순서만 바꿔도 P0 문자율이 튀므로, 여기서는
        통합 exit code가 아니라 P5 축의 판정만 본다(축 간 독립성).
        """
        before = (
            "재정 여력은 한정돼 있다. 그래서 우선순위를 세워야 한다. "
            "지역 격차도 함께 봐야 한다. 통계는 매년 개선되고 있다."
        )
        after = (
            "재정 여력은 한정돼 있다. 그래서 우선순위를 세워야 한다. "
            "통계는 매년 개선되고 있다. 지역 격차도 함께 봐야 한다."
        )
        deo_b, hed_b = verify_gates.count_modality(before)
        deo_a, hed_a = verify_gates.count_modality(after)
        self.assertEqual(deo_b, deo_a)
        self.assertEqual(hed_b, hed_a)
        self.assertLessEqual(
            deo_b - deo_a, verify_gates.MODALITY_TOLERANCE
        )

    def test_deontic_inventory_covers_haeyo_forms(self) -> None:
        """해체·해요체 당위 활용도 검출해야 한다 — 구 사전은 합쇼체·해라체만 잡았다.

        실측: `"그 둘을 묶어줄 무언가가 더 있어야 한다는 것."` → `"...있어야 해요."`
        윤문에서 P5가 "서법 소실 1문장"을 냈으나, 당위(`있어야`)는 그대로 살아 있어
        오탐이다. CLAUDE.md 철칙 #5(register 보존)에 따라 구어체 종결도 당위로 세야 한다.
        """
        for marker in (
            "그 둘을 묶어줄 무언가가 더 있어야 해요",
            "지금 손봐야 해",
            "제도를 다시 짜야 했어요",
            "규제를 풀어야 해서 늦어졌다",
            "예산을 늘려야 했어",
            "이 문제는 고쳐야 해도 방법이 없다",
            "지금 당장 바꿔야 하죠",
            "우리가 먼저 나서야 하지요",
        ):
            with self.subTest(marker=marker):
                self.assertGreaterEqual(
                    verify_gates.count_modality(marker)[0], 1, f"해요체 당위 미검출: {marker}"
                )

    def test_deontic_excludes_noun_plus_hae_word(self) -> None:
        """명사 + `해-` 어절을 당위로 세지 않는다 (2026-09-24 실측 과탐).

        #132 가 해체·해요체 활용을 추가한 방향은 옳았으나, `야` 앞 음절을 한글
        전체로 열어 둬서 `분야 해설서`·`시야 해석`·`광야 해가` 가 전부 당위로
        잡혔다. 기존 `(?!이)` lookahead 는 계사 `-이야` 만 막는다.

        당위는 `-아/어/여야 하다` 의 축약이므로 `야` 앞 음절은 종성이 없고
        중성이 ㅏㅐㅓㅔㅕㅘㅙㅚㅝㅞ 중 하나여야 한다 — `분`(종성 ㄴ)·`시`(중성
        ㅣ)·`광`(종성 ㅇ)은 그 조건에서 탈락한다.
        """
        for text in (
            "이 분야 해설서를 읽었다",
            "시야 해석이 중요하다",
            "전 분야 해외 진출을 노린다",
            "광야 해가 진다",
            "분야 해체를 논의했다",
            "우리 분야 해묵은 과제",
        ):
            with self.subTest(text=text):
                self.assertEqual(
                    verify_gates.count_modality(text)[0], 0, f"명사 과탐: {text}"
                )

    def test_deontic_covers_contracted_stems(self) -> None:
        """축약 어간 전반을 잡는다 — 어간 조건이 참 당위를 깎지 않았는지 확인."""
        for text in (
            "꼭 마시어야 한다",
            "읽어야 합니다",
            "쉬어야 한다",
            "모아야 한다",
            "뛰어야 한다",
            "자야 한다",
            "건너야 한다",
            "반드시 해야만 한다",
        ):
            with self.subTest(text=text):
                self.assertGreaterEqual(
                    verify_gates.count_modality(text)[0], 1, f"당위 미검출: {text}"
                )

    def test_deontic_inventory_excludes_copula_iya_with_haeyo(self) -> None:
        """계사 -이야 + 해요체 활용은 당위가 아니다.

        기존 `(?!이)` 계사 배제가 해요체 활용을 추가한 뒤에도 작동하는지 확인한다.
        `-이야 하다` 형태에서 `이`가 계사일 때만 배제한다.
        """
        for text in (
            "불이야 해서 뛰쳐나갔다",
            "내 스타일이야 해도 별수 없다",
        ):
            with self.subTest(text=text):
                self.assertEqual(
                    verify_gates.count_modality(text)[0], 0, f"계사 과탐: {text}"
                )

    def test_p5_passes_when_deontic_changes_register_only(self) -> None:
        """격식체 당위가 해요체 당위로 바뀌면 P5는 통과해야 한다 (축 간 독립성).

        회귀 방지: 구 사전에서 before=`"...있어야 한다는 것."`, after=`"...있어야 해요."`
        일 때 당위 1→0으로 세어 P5가 FAIL을 냈고, 복원기가 격식체로 되돌렸다.
        register 변환은 서법 소실이 아니다(CLAUDE.md 철칙 #5).
        """
        before = "그 둘을 묶어줄 무언가가 더 있어야 한다는 것."
        after = "그 둘을 묶어줄 무언가가 더 있어야 해요."
        deo_b = verify_gates.count_modality(before)[0]
        deo_a = verify_gates.count_modality(after)[0]
        self.assertGreaterEqual(deo_b, 1, "before에서 당위 미검출")
        self.assertGreaterEqual(deo_a, 1, "after에서 해요체 당위 미검출")
        self.assertLessEqual(
            deo_b - deo_a, verify_gates.MODALITY_TOLERANCE,
            f"register 변환이 서법 소실로 잡힘: {deo_b}→{deo_a}"
        )


# ===========================================================================
# P6 편집 발자국 — footprint_profile / judge_footprint / main() 통합
# ===========================================================================

import contextlib  # noqa: E402
import io  # noqa: E402

# 문장 길이·종결어미가 들쭉날쭉한 원문 (사람 글의 불규칙성을 흉내 낸 합성 텍스트).
_FP_ORIGINAL = (
    "비가 왔다. 길은 미끄러웠고 버스는 오지 않았다. 정류장에 선 사람들은 저마다 "
    "휴대전화를 들여다보며 아무 말도 하지 않았는데 그 침묵이 이상하게 편했다. 춥다. "
    "누군가 우산을 접었다. 그제야 비가 그쳤다는 걸 알았어요.\n\n"
    "집에 오니 아홉 시였다. 밥을 안쳤고 창을 열었다. 젖은 흙냄새가 올라왔는데 "
    "그게 하루 중 가장 좋은 순간이었다는 생각이 들었다. 내일도 비가 온다고 했다. "
    "우산을 현관에 뒀다.\n\n"
    "다음 날 아침 비는 오지 않았다. 대신 바람이 불었다. 우산은 그대로 현관에 있었고 "
    "나는 그걸 보고 잠깐 웃었다. 괜히 챙겼다는 생각은 들지 않았다."
)

# 같은 내용을 문장 길이가 고르고 종결어미가 '-다'로만 끝나게 균일화한 윤문본.
_FP_UNIFORMISED = (
    "비가 와서 길이 미끄러웠다. 버스는 오지 않았고 사람들은 조용했다. "
    "정류장의 침묵은 이상하게 편안했다. 날씨는 춥고 누군가 우산을 접었다. "
    "그제야 비가 그쳤다는 것을 알았다. 집에 도착하니 아홉 시였다.\n\n"
    "밥을 안치고 창문을 열어 두었다. 젖은 흙냄새가 방으로 올라왔다. "
    "그 순간이 하루 중 가장 좋았다. 내일도 비가 온다고 예보했다. "
    "우산을 현관에 두고 잠들었다. 다음 날 아침에는 비가 오지 않았다.\n\n"
    "대신 바람이 세게 불었다. 우산은 그대로 현관에 놓여 있었다. "
    "나는 그것을 보고 잠깐 웃었다. 괜히 챙겼다는 생각은 들지 않았다. "
    "비는 결국 오지 않았다. 우산은 다음 비를 기다렸다."
)


class FootprintProfileTests(unittest.TestCase):
    def test_profile_keys_and_counts(self) -> None:
        prof = verify_gates.footprint_profile(_FP_ORIGINAL)
        for key in verify_gates.FOOTPRINT_METRIC_ORDER:
            self.assertIn(key, prof)
        self.assertEqual(prof["n_paragraphs"], 3)
        self.assertGreaterEqual(prof["n_sentences"], 10)

    def test_empty_text_is_safe(self) -> None:
        prof = verify_gates.footprint_profile("")
        self.assertEqual(prof["n_sentences"], 0)
        for key in verify_gates.FOOTPRINT_METRIC_ORDER:
            self.assertEqual(prof[key], 0.0)

    def test_ending_entropy_reuses_ending_keys(self) -> None:
        """ending_entropy 는 ending_diversity 와 같은 종결 키를 써야 한다."""
        import metrics_v2 as m

        text = "오늘은 비가 온다. 길이 미끄럽다. 우산을 챙겼다. 버스가 늦게 왔어요."
        self.assertEqual(m.ending_diversity(text), 1.0)
        self.assertAlmostEqual(m.ending_entropy(text), 2.0)
        flat = "오늘은 비가 온다. 길이 미끄럽다. 우산이 필요하다. 버스가 온다."
        self.assertLess(m.ending_entropy(flat), 2.0)
        self.assertEqual(m.ending_entropy(""), 0.0)

    def test_restatement_rate_detects_echoed_closing_sentence(self) -> None:
        plain = "배포 속도가 핵심이다. 그래서 팀은 매주 배포한다. 고객 반응도 빨라졌다."
        rate, n = verify_gates.paragraph_restatement_rate(plain)
        self.assertEqual((rate, n), (0.0, 1))
        echoed = (
            "배포 속도가 핵심이다. 그래서 팀은 매주 배포한다. 결국 배포 속도가 핵심이다."
        )
        rate, n = verify_gates.paragraph_restatement_rate(echoed)
        self.assertEqual(n, 1)
        self.assertEqual(rate, 1.0)

    def test_restatement_ignores_two_eojeol_openers(self) -> None:
        """2어절 첫 문장은 어절 하나만 겹쳐도 50% 라 재지 않는다(과탐 방지)."""
        text = "비가 왔다. 길이 미끄러웠다. 그제야 비가 그쳤다는 걸 알았다."
        rate, n = verify_gates.paragraph_restatement_rate(text)
        self.assertEqual((rate, n), (0.0, 1))

    def test_single_sentence_paragraphs_are_not_eligible(self) -> None:
        rate, n = verify_gates.paragraph_restatement_rate("한 문장.\n\n또 한 문장.")
        self.assertEqual((rate, n), (0.0, 0))


class JudgeFootprintTests(unittest.TestCase):
    def _prof(self, **over) -> dict:
        base = {
            "n_sentences": 20, "n_paragraphs": 5, "n_restatement_eligible": 5,
            "sentence_length_cv": 0.50, "ending_entropy": 2.5, "lexical_density": 0.05,
            "paragraph_length_cv": 0.40, "paragraph_restatement_rate": 0.0,
        }
        base.update(over)
        return base

    def test_identity_passes(self) -> None:
        results, warn = verify_gates.judge_footprint(self._prof(), self._prof())
        self.assertFalse(warn)
        self.assertEqual(len(results), len(verify_gates.FOOTPRINT_METRIC_ORDER))
        self.assertTrue(all(r["verdict"] == "OK" for r in results))

    def test_sentence_cv_collapse_is_warn(self) -> None:
        results, warn = verify_gates.judge_footprint(
            self._prof(), self._prof(sentence_length_cv=0.20)
        )
        self.assertTrue(warn)
        by = {r["metric"]: r["verdict"] for r in results}
        self.assertTrue(by["sentence_length_cv"].startswith("WARN"))

    def test_entropy_drop_is_warn(self) -> None:
        _, warn = verify_gates.judge_footprint(
            self._prof(), self._prof(ending_entropy=1.5)
        )
        self.assertTrue(warn)

    def test_lexical_density_rise_is_warn(self) -> None:
        _, warn = verify_gates.judge_footprint(
            self._prof(), self._prof(lexical_density=0.09)
        )
        self.assertTrue(warn)

    def test_paragraph_cv_collapse_is_warn(self) -> None:
        _, warn = verify_gates.judge_footprint(
            self._prof(), self._prof(paragraph_length_cv=0.10)
        )
        self.assertTrue(warn)

    def test_restatement_injection_is_warn(self) -> None:
        _, warn = verify_gates.judge_footprint(
            self._prof(), self._prof(paragraph_restatement_rate=0.4)
        )
        self.assertTrue(warn)

    def test_opposite_direction_never_warns(self) -> None:
        """더 불규칙해지는 쪽(엔트로피 상승·CV 상승·밀도 하락)은 대상이 아니다."""
        _, warn = verify_gates.judge_footprint(
            self._prof(),
            self._prof(sentence_length_cv=0.9, ending_entropy=3.5, lexical_density=0.01,
                       paragraph_length_cv=0.9),
        )
        self.assertFalse(warn)

    def test_small_relative_move_below_threshold_passes(self) -> None:
        """잡음 바닥(정상 윤문 픽스처에서 관측된 ≤12% CV 하락)은 통과해야 한다."""
        _, warn = verify_gates.judge_footprint(
            self._prof(), self._prof(sentence_length_cv=0.44)
        )
        self.assertFalse(warn)

    def test_relative_only_move_on_tiny_values_passes(self) -> None:
        """작은 값에서 비율만 튀는 것(0.01→0.02)은 abs 임계가 걸러낸다."""
        _, warn = verify_gates.judge_footprint(
            self._prof(lexical_density=0.01), self._prof(lexical_density=0.02)
        )
        self.assertFalse(warn)

    def test_small_sample_is_skipped_not_warn(self) -> None:
        results, warn = verify_gates.judge_footprint(
            self._prof(n_sentences=3, n_paragraphs=1, n_restatement_eligible=0),
            self._prof(n_sentences=3, n_paragraphs=1, n_restatement_eligible=0,
                       sentence_length_cv=0.1, ending_entropy=0.5),
        )
        self.assertFalse(warn)
        self.assertTrue(all(r["verdict"].startswith("스킵") for r in results))

    def test_default_thresholds_report_uncalibrated(self) -> None:
        th, calibrated, source = verify_gates.load_footprint_thresholds()
        self.assertFalse(calibrated, "코퍼스 임계가 없는데 보정됐다고 보고하면 안 된다")
        self.assertIn("미보정", source)
        self.assertEqual(set(th), set(verify_gates.FOOTPRINT_METRIC_ORDER))

    def test_baseline_override_is_honoured(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = _write(td, "bv2.json", json.dumps({
                "footprint_thresholds": {
                    "source": "unit-test",
                    "sentence_length_cv": {"rel": 0.10, "abs": 0.01},
                }
            }))
            th, calibrated, source = verify_gates.load_footprint_thresholds(path)
        self.assertTrue(calibrated)
        self.assertEqual(source, "unit-test")
        self.assertEqual(th["sentence_length_cv"]["rel"], 0.10)
        # 덮어쓰지 않은 지표는 기본값 유지
        self.assertEqual(
            th["ending_entropy"]["rel"],
            verify_gates.FOOTPRINT_DEFAULT_THRESHOLDS["ending_entropy"]["rel"],
        )

    def test_placeholder_cell_is_treated_as_uncalibrated(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = _write(td, "bv2.json", json.dumps({
                "footprint_thresholds": {"_placeholder": True}
            }))
            _, calibrated, _ = verify_gates.load_footprint_thresholds(path)
        self.assertFalse(calibrated)


def _run_main_json(before: str, after: str, *extra: str) -> tuple[int, dict]:
    """main(--json) 을 실행해 (exit code, report dict) 를 돌려준다."""
    with tempfile.TemporaryDirectory() as td:
        b = _write(td, "b.txt", before)
        a = _write(td, "a.md", after)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = verify_gates.main(["--before", b, "--after", a, "--json", *extra])
    out = buf.getvalue()
    report = json.loads(out[out.index("{"):])
    return code, report


class FootprintGateIntegrationTests(unittest.TestCase):
    def test_identical_input_passes_with_footprint_ok(self) -> None:
        """(i) 동일 입력 → exit 0, 발자국 축 OK, --json 에 전후 값 포함."""
        code, report = _run_main_json(_FP_ORIGINAL, _FP_ORIGINAL)
        self.assertEqual(code, 0)
        fp = report["footprint"]
        self.assertEqual(fp["verdict"], "OK")
        self.assertFalse(fp["calibrated"])
        for key in verify_gates.FOOTPRINT_METRIC_ORDER:
            self.assertIn(key, fp["before"])
            self.assertIn(key, fp["after"])
            self.assertEqual(fp["before"][key], fp["after"][key])

    def test_uniformised_rewrite_is_warn(self) -> None:
        """(ii) 문장 길이·종결어미를 일부러 균일화한 윤문본 → exit 1 + 발자국 WARN."""
        code, report = _run_main_json(_FP_ORIGINAL, _FP_UNIFORMISED)
        fp = report["footprint"]
        self.assertTrue(fp["verdict"].startswith("WARN"), fp)
        flagged = {r["metric"] for r in fp["metrics"] if r["verdict"].startswith("WARN")}
        self.assertTrue(
            {"sentence_length_cv", "ending_entropy"} & flagged,
            f"균일화를 잡지 못함: {flagged}",
        )
        self.assertEqual(code, 1)
        self.assertEqual(report["gate"]["exit_code"], 1)

    def test_footprint_warn_never_escalates_to_abort(self) -> None:
        """발자국은 WARN 까지만 — exit 2 는 문자율 전용이다."""
        code, _ = _run_main_json(_FP_ORIGINAL, _FP_UNIFORMISED)
        self.assertLess(code, 2)

    def test_existing_axes_unchanged_on_plain_identity(self) -> None:
        """(iii) 기존 축 회귀 — 평이한 동일 입력은 여전히 exit 0 이고 축 키가 모두 남아 있다."""
        code, report = _run_main_json(_PLAIN, _PLAIN)
        self.assertEqual(code, 0)
        for key in ("change_rate", "s1_targets", "antithesis", "golden",
                    "sentence_touch", "numbers_dropped", "modality", "gate"):
            self.assertIn(key, report)
        self.assertEqual(report["change_rate"]["verdict"], "OK")
        self.assertEqual(report["modality"]["verdict"], "OK")

    def test_legitimate_fixture_rewrites_do_not_trip_footprint(self) -> None:
        """저장소의 정상 윤문 픽스처(golden good_output + fixtures.json)는 발자국 WARN 이 없어야 한다.

        기본 임계가 이 잡음 바닥 위에 있다는 증거. 임계를 낮출 때 이 테스트가 먼저 깨진다.
        """
        pairs: list[tuple[str, str, str]] = []
        golden = os.path.join(PROJECT_ROOT, "tests", "golden", "fixtures")
        for name in sorted(os.listdir(golden)):
            d = os.path.join(golden, name)
            with open(os.path.join(d, "input.txt"), encoding="utf-8") as f:
                inp = f.read()
            with open(os.path.join(d, "good_output.txt"), encoding="utf-8") as f:
                good = f.read()
            pairs.append((name, inp, good))
        with open(os.path.join(PROJECT_ROOT, "tests", "fixtures.json"), encoding="utf-8") as f:
            for fx in json.load(f)["fixtures"]:
                if fx.get("output_text"):
                    pairs.append((fx["id"], fx["input_text"], fx["output_text"]))
        self.assertGreaterEqual(len(pairs), 6)
        for name, inp, good in pairs:
            with self.subTest(fixture=name):
                results, warn = verify_gates.judge_footprint(
                    verify_gates.footprint_profile(inp),
                    verify_gates.footprint_profile(good),
                )
                self.assertFalse(warn, [r for r in results if r["verdict"].startswith("WARN")])


if __name__ == "__main__":
    unittest.main()
