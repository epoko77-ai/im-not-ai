"""route_hint 경로 판정 + 청킹 임계 상향(v2.1) 회귀 검증.

배경: 9,817자 실측 run(_workspace/2026-07-18-001)은 카운트형 어휘·피동 티가
전부 0, 구조 티(ending_comma z=+6.29)만 있는 글이었는데 6청크 정밀 경로가
610K 토큰을 썼다(단일 콜 134K·품질 동등). shim이 route_hint 로 "손댈 양"을
판정해 경로를 권고하고, 청킹은 진짜 장문(>15,000자)에서만 의미를 갖게 한다.

핵심 회귀 계약:
  1. 실측 글 프로파일(카운트형 0 · risk high · 9,817자)은 절대 heavy 가 아니다.
  2. route_hint 는 권고다 — 산출 실패가 파이프라인을 막지 않는다.
  3. 청킹 임계는 7,000/9,000 이상 — 1만자급 헤딩 없는 글은 1~2청크.

fresh clone 에서도 돌도록 합성 데이터 기반. 실측 run 파일은 있을 때만 검증.
pytest / unittest 양쪽 실행 가능.
"""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")
WORKSPACE_METRICS = os.path.join(
    HERE, "..", "_workspace", "2026-07-18-001", "00_metrics.json"
)


def _load_prep():
    path = os.path.join(SCRIPTS, "prepare_monolith_input.py")
    spec = importlib.util.spec_from_file_location("prepare_monolith_input", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


PREP = _load_prep()


def _metrics_stub(
    risk_band: str = "low",
    char_count: int = 5000,
    pivots: int = 0,
    balances: int = 0,
    double_passive: int = 0,
    by_passive: int = 0,
    have_make: int = 0,
    double_particle: int = 0,
) -> dict:
    """compute_all 산출 형태를 흉내 낸 최소 stub."""
    return {
        "risk_band": risk_band,
        "char_count": char_count,
        "metrics": {
            "conclusion_pivot_count": pivots,
            "safe_balance_count": balances,
        },
        "v2_metrics": {
            "double_passive_count": double_passive,
            "by_passive_count": by_passive,
            "have_make_literal_count": have_make,
            "double_particle_count": double_particle,
        },
    }


class RouteHintTests(unittest.TestCase):
    # --- 실측 글 프로파일 회귀 (이 테스트가 이 모듈의 존재 이유) -----------

    def test_well_written_but_structurally_risky_is_standard(self) -> None:
        """실측 글: 카운트형 0 · risk high(구조 지표만) · 9,817자 → standard.

        절대 heavy 가 아니어야 한다 — heavy 였던 것이 610K 토큰 사고의 원인.
        """
        obj = _metrics_stub(risk_band="high", char_count=9817)
        out = PREP.compute_route_hint(obj)
        self.assertEqual(out["route_hint"], "standard")
        self.assertNotEqual(out["route_hint"], "heavy")
        self.assertEqual(out["route_signals"]["lexical_tell_count"], 0)

    @unittest.skipUnless(
        os.path.exists(WORKSPACE_METRICS), "실측 run 없음 (fresh clone)"
    )
    def test_live_workspace_run_routes_light_or_standard(self) -> None:
        with open(WORKSPACE_METRICS, encoding="utf-8") as f:
            obj = json.load(f)
        out = PREP.compute_route_hint(obj)
        self.assertIn(out["route_hint"], ("light", "standard"))

    # --- 3-tier 경계 -------------------------------------------------------

    def test_clean_low_risk_is_light(self) -> None:
        out = PREP.compute_route_hint(_metrics_stub(risk_band="low"))
        self.assertEqual(out["route_hint"], "light")

    def test_light_boundary_two_tells_medium(self) -> None:
        obj = _metrics_stub(risk_band="medium", pivots=1, double_passive=1)
        self.assertEqual(PREP.compute_route_hint(obj)["route_hint"], "light")

    def test_three_tells_medium_is_standard(self) -> None:
        obj = _metrics_stub(risk_band="medium", pivots=2, by_passive=1)
        self.assertEqual(PREP.compute_route_hint(obj)["route_hint"], "standard")

    def test_dense_slop_high_risk_is_heavy(self) -> None:
        obj = _metrics_stub(
            risk_band="high",
            pivots=3,
            balances=2,
            double_passive=2,
            have_make=1,
        )
        out = PREP.compute_route_hint(obj)
        self.assertEqual(out["route_hint"], "heavy")
        self.assertEqual(out["route_signals"]["lexical_tell_count"], 8)

    def test_seven_tells_high_risk_is_standard_not_heavy(self) -> None:
        obj = _metrics_stub(risk_band="high", pivots=4, double_passive=3)
        self.assertEqual(PREP.compute_route_hint(obj)["route_hint"], "standard")

    def test_very_long_text_is_heavy_regardless(self) -> None:
        obj = _metrics_stub(risk_band="low", char_count=22000)
        out = PREP.compute_route_hint(obj)
        self.assertEqual(out["route_hint"], "heavy")

    def test_partial_metrics_degrade_to_standard(self) -> None:
        """키 누락·빈 입력에도 죽지 않고 보수적으로 standard."""
        out = PREP.compute_route_hint({})
        self.assertEqual(out["route_hint"], "standard")

    def test_reason_is_single_line(self) -> None:
        for stub in (
            _metrics_stub(),
            _metrics_stub(risk_band="high", char_count=9817),
            _metrics_stub(risk_band="high", pivots=9),
            _metrics_stub(char_count=30000),
        ):
            out = PREP.compute_route_hint(stub)
            self.assertNotIn("\n", out["route_reason"])
            self.assertTrue(out["route_reason"])

    # --- 렌더: metrics 블록에 권고로 표기 ----------------------------------

    def test_render_block_includes_advisory_route_hint(self) -> None:
        obj = _metrics_stub(risk_band="low")
        obj.update(PREP.compute_route_hint(obj))
        block = PREP._render_block(obj)
        self.assertIn("route_hint: light", block)
        self.assertIn("권고", block)
        self.assertIn("route_reason:", block)

    def test_render_block_without_route_hint_is_clean(self) -> None:
        """route 산출 실패(부재) 시 블록에 route 줄이 없어야 한다."""
        block = PREP._render_block(_metrics_stub())
        self.assertNotIn("route_hint", block)


class RouteHintCliTests(unittest.TestCase):
    @unittest.skipUnless(PREP._metrics_mod is not None, "metrics 모듈 없음")
    def test_single_mode_writes_route_hint(self) -> None:
        text = (
            "오늘 아침 골목에서 커피를 샀다. 주인이 새 원두 이야기를 한참 했다.\n\n"
            "돌아오는 길에는 비가 조금 내렸고, 나는 그게 싫지 않았다.\n"
        )
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "01_input.txt"), "w", encoding="utf-8") as f:
                f.write(text)
            rc = PREP.main(["--run-dir", td])
            self.assertEqual(rc, 0)
            with open(os.path.join(td, "00_metrics.json"), encoding="utf-8") as f:
                obj = json.load(f)
            self.assertIn(obj.get("route_hint"), ("light", "standard", "heavy"))
            self.assertTrue(obj.get("route_reason"))
            with open(
                os.path.join(td, "01_input_with_metrics.txt"), encoding="utf-8"
            ) as f:
                combined = f.read()
            self.assertIn("route_hint:", combined)

    @unittest.skipUnless(PREP._metrics_mod is not None, "metrics 모듈 없음")
    def test_chunk_mode_manifest_carries_route_and_advisory(self) -> None:
        """1.5만자 이하 --chunk 는 manifest 에 route_hint + 비권장 경고를 남긴다."""
        para = "청킹 게이트를 검증하는 합성 문단이다. 문장을 이어 붙인다. " * 8
        text = "\n\n".join(para.strip() for _ in range(12)) + "\n"
        self.assertLess(len(text), PREP.CHUNK_RECOMMEND_MIN_CHARS)
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "01_input.txt"), "w", encoding="utf-8") as f:
                f.write(text)
            rc = PREP.main(["--chunk", "--run-dir", td])
            self.assertEqual(rc, 0)
            with open(os.path.join(td, "chunk_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertIn(manifest["route_hint"], ("light", "standard", "heavy"))
            self.assertTrue(
                any("비권장" in w for w in manifest["warnings"]),
                "1.5만자 이하 청킹인데 비권장 권고 경고가 없다",
            )


class ChunkThresholdTests(unittest.TestCase):
    """청킹 임계 상향(3,000/4,000 → 7,000/9,000) 회귀 가드."""

    def test_thresholds_raised(self) -> None:
        self.assertGreaterEqual(PREP.TARGET_CHUNK_CHARS, 7000)
        self.assertGreaterEqual(PREP.MAX_CHUNK_CHARS, 9000)
        self.assertGreater(PREP.MAX_CHUNK_CHARS, PREP.TARGET_CHUNK_CHARS)
        self.assertGreaterEqual(PREP.CHUNK_RECOMMEND_MIN_CHARS, 15000)

    def test_10k_headingless_doc_splits_into_at_most_two_chunks(self) -> None:
        """1만자급 · 헤딩 없는 글은 1~2청크 (종전 임계에선 3~4청크)."""
        para = (
            "구조 신호는 문단을 가로지르므로 청크가 커야 잡힌다. "
            "이 문단은 청킹 임계 검증용 합성 문장으로 이루어져 있다. "
        )
        parts = [(para * 6).strip() for _ in range(26)]
        text = "\n\n".join(parts) + "\n"
        self.assertGreaterEqual(len(text), 9000)
        self.assertLessEqual(len(text), 12000)
        spans, warnings = PREP.compute_chunk_spans(text)
        self.assertLessEqual(len(spans), 2, f"청크 {len(spans)}개 — 임계 상향 무효")
        self.assertEqual(warnings, [])

    def test_heading_dense_doc_still_cuts_at_headings(self) -> None:
        """헤딩 강제 컷 불변식은 임계 상향과 무관하게 유지된다(무결성 가드)."""
        text = (
            "## 1. 서론\n\n첫 섹션 본문이다. 짧다.\n\n"
            "## 2. 본론\n\n둘째 섹션 본문이다. 역시 짧다.\n\n"
            "## 3. 결론\n\n셋째 섹션 본문이다.\n"
        )
        spans, _ = PREP.compute_chunk_spans(text)
        body = [sp for sp in spans if not sp["passthrough"]]
        self.assertEqual(len(body), 3, "헤딩 강제 컷이 사라졌다 — 병합 윤문 버그 위험")


if __name__ == "__main__":
    unittest.main()
