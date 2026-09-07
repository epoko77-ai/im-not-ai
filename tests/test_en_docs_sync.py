"""영어 수치의 문서 drift 방지 — 손으로 옮긴 수치는 조용히 낡는다.

README·SKILL 이 라우터 분리도를 인용한다. 그 값의 출처는 `lang/en/baseline.json`
(스크립트가 쓴다)과 `lang/en/metrics_en.py`(THRESHOLD_SETS)다. 셋이 어긋나면
사용자는 우리가 재보지 않은 수치를 근거로 읽는다. `build_quick_rules.py --check`
가 룰북 drift 를 막는 것과 같은 방식으로 코드가 막는다.
"""
from __future__ import annotations

import importlib.util
import json
import os
import unittest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_BASELINE = os.path.join(_ROOT, "lang", "en", "baseline.json")
_DOCS = (
    os.path.join(_ROOT, "README.md"),
    os.path.join(_ROOT, "README.en.md"),
    os.path.join(_ROOT, "skills", "humanize-english", "SKILL.md"),
)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _metrics_en():
    spec = importlib.util.spec_from_file_location(
        "_men", os.path.join(_ROOT, "lang", "en", "metrics_en.py")
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class SeparationSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = json.loads(_read(_BASELINE))
        self.m = _metrics_en()

    def test_blog_separation_matches_measurement(self) -> None:
        measured = (
            self.baseline["genres"]["blog_essay_r2"]["router_blog_calibrated"]["separation"]
        )
        self.assertEqual(self.m.THRESHOLD_SETS["blog"]["separation"], measured)

    def test_blog_threshold_matches_measurement(self) -> None:
        measured = self.baseline["genres"]["blog_essay_r2"]["router_blog_calibrated"]["seg_max"]
        self.assertEqual(self.m.THRESHOLD_SETS["blog"]["comma_segment_max"], measured)

    def test_docs_quote_the_same_numbers(self) -> None:
        wanted = [str(cfg["separation"]) for cfg in self.m.THRESHOLD_SETS.values()]
        gpt = self.baseline["genres"]["blog_essay_r2"]["cross_family_gpt"]
        if gpt:
            wanted.append(str(gpt["router"]["separation"]))
        for path in _DOCS:
            text = _read(path)
            for value in wanted:
                self.assertIn(value, text, f"{os.path.basename(path)} 에 {value} 없음")

    def test_genre_cells_carry_their_corpus(self) -> None:
        """분리도만 적고 표본을 안 적으면 근거가 아니라 숫자다."""
        for name, cfg in self.m.THRESHOLD_SETS.items():
            self.assertRegex(cfg["source"], r"\d+", name)


if __name__ == "__main__":
    unittest.main()
