"""서법 국소 복원기(scripts/restore_modality.py) 단위 테스트.

이 스크립트는 판정기가 아니라 **결과물을 바꾸는 변형기**다. 잘못 치환하면 게이트가
아니라 새 오류의 원인이 되므로, "고쳐야 할 때 고치는가"만큼 "애매하면 손대지 않는가"를
같은 비중으로 고정한다.
"""
from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "scripts"))
import restore_modality as rm  # noqa: E402


class RestoreModalityTests(unittest.TestCase):
    def test_restores_hedge_flattened_to_assertion(self) -> None:
        """실측에서 반복된 유형 — 관측형 종결이 단정으로 바뀐 문장."""
        before = "이 수치는 이전 전망치보다 0.4%포인트 낮은 것으로 판단된다."
        after = "이 수치는 이전 전망치보다 0.4%포인트 낮은 수치다."
        out, restored, skipped = rm.restore(before, after)
        self.assertEqual(len(restored), 1, f"복원 안 됨: {skipped}")
        self.assertIn("낮은 것으로 판단된다", out)

    def test_restores_deontic_flattened_to_fact(self) -> None:
        """당위(필자가 요구한 것)가 이미 일어난 사실로 바뀐 문장."""
        before = "정부는 공유 플랫폼을 구축해야 한다."
        after = "정부는 공유 플랫폼을 구축한다."
        out, restored, _ = rm.restore(before, after)
        self.assertEqual(len(restored), 1)
        self.assertIn("구축해야 한다", out)

    def test_keeps_output_when_modality_preserved(self) -> None:
        """서법이 유지된 정상 윤문은 건드리지 않는다(형태만 바뀐 경우 포함)."""
        before = "초기 비용이 증가할 것으로 보인다."
        after = "초기 비용이 늘어날 듯하다."
        out, restored, _ = rm.restore(before, after)
        self.assertEqual(restored, [])
        self.assertEqual(out, after)

    def test_skips_when_sentences_merged(self) -> None:
        """병합 문장은 되돌리면 합쳐진 다른 명제가 삭제된다 — 손대지 않고 보류한다.

        병합의 정확한 신호는 어휘가 아니라 **정렬 구조**다. 두 원문 문장이 하나로 합쳐지면
        이웃 문장이 짝을 잃고 gap으로 남는다.
        """
        before = "정부는 재정 지출을 늘려야 한다. 세제도 함께 손질한다."
        after = "정부는 재정 지출을 늘리고 세제도 함께 손질한다."
        out, restored, _ = rm.restore(before, after)
        # 흡수된 문장이 짝을 잃고 gap으로 남거나(=서법 판정 대상 밖), 이웃 gap 때문에
        # 병합으로 보류되거나 — 어느 경로든 **출력은 그대로여야** 한다.
        self.assertEqual(restored, [])
        self.assertEqual(out, after)

    def test_skips_when_single_sentence_absorbs_new_content(self) -> None:
        """한 문장이 원문에 없던 명제를 흡수한 경우도 되돌리면 그 명제가 사라진다.

        저유사도 필터에 먼저 걸리든 병합 가드에 걸리든, 요구되는 것은 **출력 불변**이다.
        """
        before = "정부는 재정 지출을 늘려야 한다."
        after = "정부는 재정 지출을 늘리고 세제도 함께 손질하며 규제도 정비한다."
        out, restored, _ = rm.restore(before, after)
        self.assertEqual(restored, [])
        self.assertEqual(out, after)

    def test_skips_when_sentence_split_in_two(self) -> None:
        """한 문장이 둘로 쪼개진 경우 되돌리면 나머지 조각이 남아 명제가 중복된다.

        회귀 방지(적대적 검토 지적): 병합 가드가 before쪽 gap만 봐서 분할을 놓쳤고,
        복원 결과가 "…지적도 나온다. 그런 지적도 나온다."가 됐다.
        """
        before = "정부 개입이 시장 가격을 왜곡할 수 있다는 지적도 나온다."
        after = "정부 개입이 시장 가격을 왜곡한다. 그런 지적도 나온다."
        out, restored, skipped = rm.restore(before, after)
        self.assertEqual(restored, [])
        self.assertEqual(out, after)
        self.assertIn("분할", skipped[0]["reason"])

    def test_summary_block_does_not_hide_loss(self) -> None:
        """요약 블록 안의 원문 인용이 정렬 짝을 훔쳐 손실을 가리면 안 된다."""
        before = "성장세는 꺾일 수 있다."
        after = "성장세는 꺾인다.\n\n<!-- HUMANIZE-SUMMARY\n원문: 성장세는 꺾일 수 있다.\n-->"
        out, restored, _ = rm.restore(before, after)
        self.assertEqual(len(restored), 1)
        self.assertIn("꺾일 수 있다", out.split("<!--")[0])
        self.assertIn("HUMANIZE-SUMMARY", out, "요약 블록은 보존해야 한다")

    def test_low_similarity_pair_is_reported_not_silent(self) -> None:
        """유사도 미달로 손대지 않은 손실도 보고에는 남아야 한다."""
        before = "이 정책의 고용 효과는 제한적일 것으로 판단된다."
        after = "정책 고용 효과는 미미하다."
        _, restored, skipped = rm.restore(before, after)
        self.assertEqual(restored, [])
        self.assertTrue(skipped, "조용히 탈락하면 손실 추적이 불가능하다")
        self.assertIn("유사도", skipped[0]["reason"])

    def test_restored_sentence_drops_cliche_the_rewriter_removed(self) -> None:
        """서법은 되찾되, 윤문이 걷어낸 상투구까지 되살리지는 않는다.

        회귀 방지: 복원기가 "그러므로, 지금이야말로 ~할 때입니다."를 통째로 되살려
        D-1 결산 피벗과 D-6 결말 껍데기가 부활했다(같은 픽스처 3회 중 2회 재현).
        """
        before = "그러므로, 지금이야말로 변화를 추구해야 할 때입니다."
        after = "지금이 변화를 추구할 시점입니다."
        out, restored, _ = rm.restore(before, after)
        self.assertEqual(len(restored), 1)
        self.assertIn("추구해야", out, "서법은 되돌아와야 한다")
        self.assertNotIn("그러므로", out)
        self.assertNotIn("지금이야말로", out)

    def test_keeps_cliche_the_rewriter_kept(self) -> None:
        """윤문본이 남겨둔 상투구는 실행자의 판단이므로 건드리지 않는다."""
        before = "따라서 정부는 즉시 대응해야 한다."
        after = "따라서 정부가 즉시 대응한다."
        out, restored, _ = rm.restore(before, after)
        self.assertEqual(len(restored), 1)
        self.assertIn("따라서", out)
        self.assertIn("대응해야 한다", out)

    def test_ignores_unrelated_sentence_pairs(self) -> None:
        """유사도가 낮은 짝은 정렬 아티팩트 — 서법 판정 대상이 아니다."""
        before = "규제안의 영향은 아직 단정하기 어렵다."
        after = "부산 북구의 인구는 계속 줄었다."
        _, restored, _ = rm.restore(before, after)
        self.assertEqual(restored, [])

    def test_deleted_sentence_is_not_a_modality_case(self) -> None:
        """문장이 통째로 사라진 것은 내용 소실 — 다른 축이 본다."""
        before = "비용이 늘어날 것으로 보인다. 통계는 분기마다 갱신된다."
        after = "통계는 분기마다 갱신된다."
        _, restored, _ = rm.restore(before, after)
        self.assertEqual(restored, [])

    def test_keeps_output_when_deontic_changes_register_only(self) -> None:
        """격식체 당위가 해요체 당위로 바뀌면 되돌리지 않는다 (철칙 #5 register 보존).

        회귀 방지: 구 사전에서 `"...있어야 한다는 것."` → `"...있어야 해요."` 윤문을
        복원기가 격식체로 되돌렸다. 당위가 구어체 활용으로 남아 있으면 서법 소실이 아니다.
        """
        before = "그 둘을 묶어줄 무언가가 더 있어야 한다는 것."
        after = "그 둘을 묶어줄 무언가가 더 있어야 해요."
        out, restored, skipped = rm.restore(before, after)
        self.assertEqual(restored, [], f"해요체 당위를 복원하려 함: {restored}")
        self.assertEqual(out, after, "출력이 바뀌면 안 된다")

    def test_keeps_various_haeyo_deontic_forms(self) -> None:
        """해요체 당위 활용 8종이 서법으로 인정돼 복원 대상에서 빠진다."""
        cases = [
            ("지금 손봐야 한다.", "지금 손봐야 해."),
            ("제도를 다시 짜야 했습니다.", "제도를 다시 짜야 했어요."),
            ("규제를 풀어야 하고요.", "규제를 풀어야 해서요."),
            ("예산을 늘려야 한다.", "예산을 늘려야 해도."),
            ("지금 당장 바꿔야 합니다.", "지금 당장 바꿔야 하죠."),
            ("우리가 먼저 나서야 합니다.", "우리가 먼저 나서야 하지요."),
        ]
        for before, after in cases:
            with self.subTest(before=before, after=after):
                out, restored, _ = rm.restore(before, after)
                self.assertEqual(restored, [], f"해요체 복원 시도: {before} → {after}")
                self.assertEqual(out, after)


if __name__ == "__main__":
    unittest.main()
