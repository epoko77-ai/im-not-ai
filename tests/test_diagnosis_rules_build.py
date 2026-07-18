"""diagnosis-rules.md 가 taxonomy(SSOT)에서 재생성 가능하고 최신인지 검증한다.

진단 콜이 74.8KB taxonomy 전량을 읽던 것을 슬림 인덱스로 교체한 뒤,
인덱스가 SSOT와 어긋나면(drift) 진단의 ID 핸드오프 계약이 깨진다.
quick-rules와 동일한 --check 게이트 + 71패턴 전수 커버 + 빈 항목 0 +
부피 상한을 여기서 고정한다.

pytest / unittest 양쪽에서 실행된다. LLM 콜 0 — 빌더만 검증한다.
(LLM 진단 회귀는 별도 회차 — 이 스위트의 범위가 아니다.)
"""

from __future__ import annotations

import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")

# 부피 게이트: taxonomy(74.8KB) 대비 대폭 절감이 이 파일의 존재 이유.
# 한글 UTF-8 3바이트 특성상 71패턴 × 2줄의 물리 하한이 있어 상한 14KB.
MAX_BYTES = 14 * 1024
MIN_BYTES = 5 * 1024  # 지나치게 작으면 내용 소실 의심


def _load_builder():
    path = os.path.join(SCRIPTS, "build_diagnosis_rules.py")
    spec = importlib.util.spec_from_file_location("build_diagnosis_rules", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class DiagnosisRulesBuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = _load_builder()
        self.rendered, self.patterns = self.builder.build()

    def test_diagnosis_rules_is_up_to_date(self) -> None:
        """diagnosis-rules.md 가 SSOT 재생성 결과와 일치해야 한다 (drift 차단)."""
        with open(self.builder._OUT, encoding="utf-8") as f:
            existing = f.read()
        self.assertEqual(
            existing.rstrip(),
            self.rendered.rstrip(),
            "diagnosis-rules.md 가 taxonomy와 어긋난다. "
            "`python3 scripts/build_diagnosis_rules.py` 로 재생성하라.",
        )

    def test_all_71_ids_covered(self) -> None:
        """taxonomy의 패턴 ID 전수(quick:false 문서레벨 포함)가 인덱스에 있다."""
        taxo_ids = {p["id"] for p in self.patterns}
        out_ids = set(
            re.findall(r"^- \*\*([A-J]-\d+)\*\*", self.rendered, re.M)
        )
        self.assertEqual(len(taxo_ids), 71)
        self.assertEqual(taxo_ids, out_ids)

    def test_document_level_patterns_included(self) -> None:
        """quick-rules로 대체 불가한 문서 레벨 패턴이 반드시 포함된다."""
        for pid in ("C-8", "E-1", "D-6", "A-17"):
            self.assertRegex(self.rendered, rf"- \*\*{pid}\*\*")

    def test_no_empty_definitions_or_signatures(self) -> None:
        """패턴당 시그니처 줄이 정확히 71개, 빈 값 0."""
        sig_lines = re.findall(r"^  시그니처:\s*(.*)$", self.rendered, re.M)
        self.assertEqual(len(sig_lines), 71)
        self.assertEqual([s for s in sig_lines if not s.strip()], [])

    def test_size_within_budget(self) -> None:
        size = len(self.rendered.encode("utf-8"))
        self.assertLessEqual(size, MAX_BYTES, f"인덱스 부피 초과: {size}B")
        self.assertGreaterEqual(size, MIN_BYTES, f"인덱스 부피 과소: {size}B")

    def test_build_is_deterministic(self) -> None:
        """같은 SSOT에서 두 번 빌드하면 바이트 동일 (멱등)."""
        rendered2, _ = self.builder.build()
        self.assertEqual(self.rendered, rendered2)

    def test_hold_pattern_marked(self) -> None:
        """A-17 hold는 '지배 패턴 지목 금지'가 명시돼야 한다 (오진 방지)."""
        m = re.search(r"^- \*\*A-17\*\*.*$", self.rendered, re.M)
        self.assertIsNotNone(m)
        self.assertIn("지목 금지", m.group(0))

    def test_taxonomy_not_modified_by_build(self) -> None:
        """빌드는 SSOT를 절대 쓰지 않는다 (read-only 불가침)."""
        with open(self.builder._TAXONOMY, encoding="utf-8") as f:
            before = f.read()
        self.builder.build()
        with open(self.builder._TAXONOMY, encoding="utf-8") as f:
            after = f.read()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
