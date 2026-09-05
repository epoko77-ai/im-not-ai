"""AI 코퍼스 위생 — 메타 발화가 코퍼스에 섞이지 않는지.

실사고(2026-09-03): `claude -p` 를 저장소 작업 디렉터리 안에서 실행해 CLI 가
프로젝트 컨텍스트·plan mode 상태를 물었고, 모델이 요청한 글 대신 자기 도구에
대한 메타 발화를 냈다. arXiv AI 7/21(33%, sonnet 전부)·blog AI 13/38(34%) 오염.

정제 후 결론은 유지됐으나(AUC 변화 ±0.06 이내) sonnet 이 통째로 빠져
G1(전 모델 생존)을 주장할 수 없게 됐다. **문서 주의로는 못 막는다 — 코드가 건다.**
"""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_BUILDER = os.path.join(_ROOT, "scripts", "build_en_baseline.py")

# 실제로 관측된 오염 문구 (실사고 원문에서 발췌)
OBSERVED_CONTAMINATION = (
    "This request is just \"write a comment\" — a small, self-contained writing task, "
    "not a coding/planning task, so none of the planning-mode machinery applies here.",
    "This is a simple creative writing request — no code changes, no plan needed. "
    "Plan mode doesn't apply here.",
    "I notice you're in plan mode from a previous task. This request seems unrelated.",
)
CLEAN_SAMPLES = (
    "Research into the stylistic properties of translations is an issue which has "
    "received some attention in computational stylistics.",
    "The old argument for public libraries was about scarcity. Books cost money.",
)


def _load():
    spec = importlib.util.spec_from_file_location("_builder", _BUILDER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class CorpusHygieneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.m = _load()

    def test_detects_observed_contamination(self) -> None:
        for text in OBSERVED_CONTAMINATION:
            self.assertTrue(
                self.m.is_contaminated(text), f"오염을 못 잡았다: {text[:60]}"
            )

    def test_passes_clean_text(self) -> None:
        for text in CLEAN_SAMPLES:
            self.assertFalse(
                self.m.is_contaminated(text), f"정상 글을 오염으로 잡았다: {text[:60]}"
            )

    def test_generator_runs_outside_repo(self) -> None:
        """생성은 격리 디렉터리에서 — cwd 가 저장소면 CLI 가 컨텍스트를 문다."""
        src = open(_BUILDER, encoding="utf-8").read()
        self.assertIn("tempfile.mkdtemp", src)
        self.assertIn("cwd=workdir", src)

    def test_sentinel_is_primary_defense(self) -> None:
        """센티넬이 1차 방어 — 한국어 humanize_runner 가 이미 쓰는 방식이다.

        영어 생성기가 이걸 안 가져와서 33~34% 오염이 조용히 통과했다.
        메타 발화는 마커를 안 붙이므로 여기서 걸린다.
        """
        m = _load()
        self.assertIsNone(
            m.extract_sentinel("This is a simple writing task, plan mode doesn't apply."),
            "마커 없는 출력은 거부돼야 한다",
        )
        self.assertEqual(
            m.extract_sentinel("noise <<<A>>> the real abstract <<</A>>> more noise"),
            "the real abstract",
        )
        src = open(_BUILDER, encoding="utf-8").read()
        self.assertIn("extract_sentinel(proc.stdout)", src, "생성 경로가 센티넬을 안 쓴다")

    def test_generator_strips_leaky_env(self) -> None:
        """cwd 격리만으로는 부족했다 — 부모 세션 메시징 상태가 새면 메타 발화가 난다.

        실측(2026-09-03): 저장소 밖에서도 sonnet 6/7 오염이었고, 아래 넷을
        지우자 즉시 정상 산출이 나왔다.
        """
        m = _load()
        for key in ("CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN",
                    "CLAUDE_CODE_EMIT_SESSION_STATE_EVENTS", "CLAUDE_CODE_ENABLE_TASKS"):
            self.assertIn(key, m._LEAKY_ENV, f"{key} 가 제거 목록에 없다")
        os.environ["CLAUDE_CODE_MESSAGING_TOKEN"] = "x"
        try:
            self.assertNotIn("CLAUDE_CODE_MESSAGING_TOKEN", m._clean_env())
        finally:
            os.environ.pop("CLAUDE_CODE_MESSAGING_TOKEN", None)

    def test_stored_corpora_are_clean(self) -> None:
        """이미 저장된 코퍼스에 오염이 남아 있지 않은지."""
        globs = ("en_baseline*", "en_blog_essay")
        for path in [p for g in globs
                     for p in glob.glob(os.path.join(_ROOT, "_workspace", g, "*.json"))]:
            if os.path.basename(path) == "ai.json" and "blog" not in path:
                continue  # 원본(오염 포함)은 사고 기록용으로 보존
            with open(path, encoding="utf-8") as f:
                rows = json.load(f)
            bad = [r for r in rows if self.m.is_contaminated(r.get("text", ""))]
            self.assertEqual(
                bad, [], f"{os.path.basename(path)} 에 오염 {len(bad)}건 잔존"
            )


class BlogCellHygieneTests(unittest.TestCase):
    """블로그 셀 인간 코퍼스 — 본문에 마크업 잔재가 섞이지 않는지.

    실사고(2026-09-04): `<style>` 를 안 걷어내 MathJax CSS 가 본문으로 들어갔고
    (".mjx-chtml {display: inline-block; line-height: 0; …}") 그 두 편이 인간
    문장길이 분산 107.78·67.30 으로 최상위를 찍었다. 문체가 아니라 스타일시트를
    측정한 값이다.
    """

    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "_blog", os.path.join(_ROOT, "scripts", "build_en_blog_cell.py")
        )
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)

    def test_style_block_is_stripped(self) -> None:
        html = "<p>Real prose here.</p><style>.mjx-chtml {display: inline-block;}</style>"
        self.assertNotIn("display", self.m._prose(html))

    def test_quotes_and_code_are_stripped(self) -> None:
        """인용·코드는 필자의 산문이 아니다 — 문체 측정에서 뺀다."""
        html = "<p>My words.</p><blockquote>Someone else's words.</blockquote><pre>x = 1</pre>"
        out = self.m._prose(html)
        self.assertIn("My words", out)
        self.assertNotIn("Someone else", out)
        self.assertNotIn("x = 1", out)

    def test_junk_survivor_is_rejected(self) -> None:
        self.assertTrue(self.m._JUNK.search("text .mjx-chtml leftovers"))
        self.assertFalse(self.m._JUNK.search("ordinary essay prose about display ads"))

    def test_stored_human_corpus_has_no_markup(self) -> None:
        path = os.path.join(_ROOT, "_workspace", "en_blog_essay", "human.json")
        if not os.path.exists(path):
            self.skipTest("코퍼스 미수집")
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
        bad = [r["title"] for r in rows if self.m._JUNK.search(r["text"])]
        self.assertEqual(bad, [], f"마크업 잔재 {len(bad)}편")


if __name__ == "__main__":
    unittest.main()
