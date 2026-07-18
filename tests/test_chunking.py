"""청킹·재조립 (prepare_monolith_input.py --chunk / reassemble_chunks.py) 검증.

최상위 불변식: 분할은 손실이 없어야 한다 — 모든 청크(passthrough 포함)를
순서대로 이으면 원문과 공백·개행까지 정확히 일치. 한 글자 유실 = fidelity 사고.

웹앱(imnotai.kr)의 알려진 버그(제목 줄이 본문과 한 청크로 묶여 병합 윤문됨)
재발 방지가 헤딩 승격 테스트의 목적이다.

pytest / unittest 양쪽에서 실행된다.
"""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")


def _load(module_name: str, filename: str):
    path = os.path.join(SCRIPTS, filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


PREP = _load("prepare_monolith_input", "prepare_monolith_input.py")
REASM = _load("reassemble_chunks", "reassemble_chunks.py")


# ---------------------------------------------------------------------------
# 합성 한국어 샘플
# ---------------------------------------------------------------------------

SHORT = (
    "안녕하세요. 이것은 짧은 글입니다.\n\n"
    "두 번째 문단은 청킹 없이 한 덩어리로 남아야 합니다."
)

ACADEMIC = (
    "서론에 해당하는 도입부다. 연구의 배경을 밝힌다.\n\n"
    "## 1장 배경\n\n"
    "배경 문단이다. 선행 연구를 정리한다. 이 문단은 헤딩 바로 뒤에 온다.\n\n"
    "추가 배경 문단이다. 논의를 이어간다.\n\n"
    "Ⅱ. 방법론\n\n"
    "방법론 문단이다. 자료 수집 절차를 설명한다.\n\n"
    "제 3 장 결과\n\n"
    "결과 문단이다. 주요 발견을 요약한다.\n\n"
    "3. 소결\n\n"
    "소결 문단이다. 함의를 정리한다.\n"
)

FOOTNOTED = (
    "본문 첫 문단이다. 김철수의 주장을 인용한다.1) 논의를 이어간다.\n\n"
    "본문 둘째 문단이다. 다른 연구도 참조한다.[2] 결론으로 향한다.\n\n"
    "1) 김철수, 『가상의 책』, 가상출판사, 2020, 45쪽.\n"
    "2) 이영희, \"가상의 논문\", 가상학회지 12(3), 2021.\n"
    "3) 박민수 외, 『또 다른 가상의 책』, 2022.\n"
)


def _make_long_doc() -> str:
    """헤딩·각주가 섞인 2만자급 합성 학술 문서."""
    sent = (
        "이 문단은 청킹 검증을 위해 만든 합성 문장이다. "
        "서로 다른 길이의 문장을 섞어 경계 폴백과 리듬 신호를 확인한다. "
        "대구와 병렬 같은 구조 신호는 문단을 가로지르므로 청크가 커야 잡힌다. "
    )
    parts: list[str] = []
    for s in range(1, 9):
        parts.append(f"{s}. 섹션 제목 {s}")
        for para in range(1, 5):
            parts.append(f"섹션 {s} 문단 {para}의 시작이다. " + (sent * 6).strip())
    body = "\n\n".join(parts)
    footnotes = "\n".join(
        f"{i}) 각주 {i}번의 가상 출처 표기다. 가상출판사, 202{i}." for i in range(1, 6)
    )
    return body + "\n\n" + footnotes + "\n"


LONG20K = _make_long_doc()

# 문장 경계는 있으나 문단(빈 줄)이 없는 9,000자급 통짜 문단.
GIANT_SENTENCED_PARA = (
    "통짜 문단의 시작이다. " + ("문장 경계 폴백을 검증하는 합성 문장이다. " * 400)
).strip()

# 종결 부호가 전혀 없는 5,000자급 초장 구간 — 쪼갤 수 없어 경고 대상.
UNSPLITTABLE = "가나다라마바사아자차카타파하" * 358  # 5,012자, 문장부호 없음


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


def _body_spans(spans):
    return [sp for sp in spans if not sp["passthrough"]]


def _last_nonblank_line(chunk: str) -> str:
    stripped = chunk.rstrip()
    return stripped.rsplit("\n", 1)[-1] if stripped else ""


class ChunkSplitTests(unittest.TestCase):
    def _split(self, text):
        return PREP.compute_chunk_spans(text)

    # --- 손실 없는 분할 ---------------------------------------------------

    def test_lossless_all_samples(self) -> None:
        """모든 샘플: 청크를 순서대로 이으면 원문과 정확히 일치."""
        samples = {
            "short": SHORT,
            "academic": ACADEMIC,
            "footnoted": FOOTNOTED,
            "long20k": LONG20K,
            "giant_sentenced": GIANT_SENTENCED_PARA,
            "unsplittable": UNSPLITTABLE,
        }
        self.assertGreaterEqual(len(LONG20K), 20000, "2만자급 샘플이어야 한다")
        for name, text in samples.items():
            spans, _ = self._split(text)
            joined = "".join(text[sp["start"] : sp["end"]] for sp in spans)
            self.assertEqual(joined, text, f"{name}: 분할 손실 발생")
            # 구간이 빈틈·겹침 없이 연속인지도 확인
            pos = 0
            for sp in spans:
                self.assertEqual(sp["start"], pos, f"{name}: 구간 불연속")
                self.assertGreater(sp["end"], sp["start"], f"{name}: 빈 구간")
                pos = sp["end"]
            self.assertEqual(pos, len(text), f"{name}: 말미 유실")

    def test_short_text_single_chunk(self) -> None:
        spans, warnings = self._split(SHORT)
        self.assertEqual(len(spans), 1)
        self.assertFalse(spans[0]["passthrough"])
        self.assertEqual(warnings, [])

    # --- 헤딩 승격 (웹앱 버그 차단) --------------------------------------

    def test_heading_starts_chunk_never_ends_chunk(self) -> None:
        """헤딩은 청크의 첫 줄로 귀속되고, 어떤 청크도 헤딩으로 끝나지 않는다."""
        for name, text in {"academic": ACADEMIC, "long20k": LONG20K}.items():
            spans, _ = self._split(text)
            body = _body_spans(spans)
            for sp in body:
                chunk = text[sp["start"] : sp["end"]]
                last = _last_nonblank_line(chunk)
                self.assertFalse(
                    PREP.HEADING_LINE_RE.match(last),
                    f"{name}: 청크가 헤딩으로 끝남 — 웹앱 버그 재발: {last!r}",
                )
            # 본문 내 모든 헤딩 줄은 자기가 속한 청크의 선두(헤딩 런 포함)에 있어야 한다.
            fn_start = PREP.find_footnote_block_start(text)
            body_end = fn_start if fn_start is not None else len(text)
            for ls, le in PREP._line_spans(text[:body_end]):
                line = text[ls:le]
                if not PREP.HEADING_LINE_RE.match(line):
                    continue
                holder = next(sp for sp in body if sp["start"] <= ls < sp["end"])
                prefix = text[holder["start"] : ls]
                for pl in prefix.splitlines():
                    self.assertTrue(
                        not pl.strip() or PREP.HEADING_LINE_RE.match(pl),
                        f"{name}: 헤딩 {line.strip()!r} 이 청크 중간에 묻힘 "
                        f"(앞선 본문: {pl!r})",
                    )

    def test_heading_variants_promoted(self) -> None:
        """마크다운·로마숫자·제N장·숫자 헤딩이 모두 강제 경계로 승격된다."""
        spans, _ = self._split(ACADEMIC)
        body = _body_spans(spans)
        heads = [
            ACADEMIC[sp["start"] :].lstrip("\n").split("\n", 1)[0] for sp in body
        ]
        for expected in ("## 1장 배경", "Ⅱ. 방법론", "제 3 장 결과", "3. 소결"):
            self.assertIn(expected, heads, f"헤딩 {expected!r} 이 청크 선두로 승격 안 됨")

    # --- 각주 passthrough -------------------------------------------------

    def test_footnote_block_passthrough(self) -> None:
        for name, text in {"footnoted": FOOTNOTED, "long20k": LONG20K}.items():
            spans, _ = self._split(text)
            self.assertTrue(spans[-1]["passthrough"], f"{name}: 각주 블록 미태깅")
            block = text[spans[-1]["start"] : spans[-1]["end"]]
            self.assertTrue(block.lstrip().startswith("1) "), f"{name}: 블록 시작 오류")
            # 본문 청크에는 각주 정의 줄이 없어야 한다 (참조 번호는 남아도 됨).
            for sp in _body_spans(spans):
                for ln in text[sp["start"] : sp["end"]].splitlines():
                    self.assertFalse(
                        PREP.FOOTNOTE_LINE_RE.match(ln)
                        and ("출판사" in ln or "학회지" in ln or "가상" in ln),
                        f"{name}: 각주 정의가 본문 청크에 섞임: {ln!r}",
                    )

    def test_no_footnotes_no_passthrough(self) -> None:
        spans, _ = self._split(ACADEMIC)
        self.assertFalse(any(sp["passthrough"] for sp in spans))

    # --- 크기 상한 --------------------------------------------------------

    def test_size_cap(self) -> None:
        """정상 문서의 본문 청크는 상한(4,000자)을 넘지 않는다."""
        for name, text in {
            "long20k": LONG20K,
            "giant_sentenced": GIANT_SENTENCED_PARA,
        }.items():
            spans, warnings = self._split(text)
            for sp in _body_spans(spans):
                self.assertLessEqual(
                    sp["end"] - sp["start"],
                    PREP.MAX_CHUNK_CHARS,
                    f"{name}: 청크 크기 상한 초과",
                )
            self.assertEqual(warnings, [], f"{name}: 예상 밖 경고 {warnings}")

    def test_unsplittable_run_warns(self) -> None:
        """문장 경계가 없는 초장 구간은 통짜 허용 + 경고."""
        spans, warnings = self._split(UNSPLITTABLE)
        self.assertEqual(len(spans), 1)
        self.assertTrue(warnings, "초장 구간인데 경고가 없다")
        self.assertTrue(any("초과" in w for w in warnings))


class ChunkCliRoundTripTests(unittest.TestCase):
    """--chunk CLI → (원문 그대로를 윤문 결과로 사용) → 재조립 = 원문."""

    def _run_pipeline(self, text: str) -> None:
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "01_input.txt"), "w", encoding="utf-8") as f:
                f.write(text)
            rc = PREP.main(["--chunk", "--run-dir", td])
            self.assertEqual(rc, 0)

            with open(
                os.path.join(td, "chunk_manifest.json"), encoding="utf-8"
            ) as f:
                manifest = json.load(f)
            self.assertEqual(manifest["source_chars"], len(text))
            self.assertEqual(manifest["lossless_check"], "ok")

            for entry in manifest["chunks"]:
                if entry["passthrough"]:
                    self.assertIsNone(entry["input_file"])
                    self.assertIsNone(entry["rewritten_file"])
                    continue
                # 청크 입력 파일이 존재하고 원문 조각을 담고 있어야 한다.
                ipath = os.path.join(td, entry["input_file"])
                self.assertTrue(os.path.exists(ipath), f"{entry['input_file']} 누락")
                with open(ipath, encoding="utf-8") as f:
                    combined = f.read()
                self.assertIn("[원문 시작]", combined)
                self.assertIn("[청크 컨텍스트]", combined)
                # "윤문 없이 원문 그대로"를 윤문 결과로 저장.
                chunk_text = text[entry["start"] : entry["end"]]
                with open(
                    os.path.join(td, entry["rewritten_file"]), "w", encoding="utf-8"
                ) as f:
                    f.write(chunk_text)

            rc = REASM.main(["--run-dir", td, "--strict"])
            self.assertEqual(rc, 0)
            with open(os.path.join(td, "03_reassembled.md"), encoding="utf-8") as f:
                out = f.read()
            self.assertEqual(out, text, "왕복 재조립이 원문과 불일치")

            with open(
                os.path.join(td, "03_reassembly_report.json"), encoding="utf-8"
            ) as f:
                report = json.load(f)
            self.assertEqual(report["warnings"], [])
            self.assertEqual(report["output_chars"], len(text))

    def test_roundtrip_long20k(self) -> None:
        self._run_pipeline(LONG20K)

    def test_roundtrip_footnoted(self) -> None:
        self._run_pipeline(FOOTNOTED)

    def test_roundtrip_academic(self) -> None:
        self._run_pipeline(ACADEMIC)

    def test_reassemble_whitespace_restoration(self) -> None:
        """LLM이 앞뒤 공백을 흘려도 원문 청크의 공백이 복원된다."""
        text = LONG20K
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "01_input.txt"), "w", encoding="utf-8") as f:
                f.write(text)
            PREP.main(["--chunk", "--run-dir", td])
            with open(
                os.path.join(td, "chunk_manifest.json"), encoding="utf-8"
            ) as f:
                manifest = json.load(f)
            for entry in manifest["chunks"]:
                if entry["passthrough"]:
                    continue
                chunk_text = text[entry["start"] : entry["end"]]
                # LLM 흉내: 앞뒤 공백을 지우고 개행 하나만 붙여 저장.
                with open(
                    os.path.join(td, entry["rewritten_file"]), "w", encoding="utf-8"
                ) as f:
                    f.write(chunk_text.strip() + "\n")
            rc = REASM.main(["--run-dir", td, "--strict"])
            self.assertEqual(rc, 0)
            with open(os.path.join(td, "03_reassembled.md"), encoding="utf-8") as f:
                out = f.read()
            self.assertEqual(out, text, "공백 복원 실패 — 문단 구분이 훼손됨")

    def test_reassemble_detects_loss(self) -> None:
        """청크 하나가 절반 이하로 줄면 유실 의심 경고(strict 에서 exit 1)."""
        text = LONG20K
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "01_input.txt"), "w", encoding="utf-8") as f:
                f.write(text)
            PREP.main(["--chunk", "--run-dir", td])
            with open(
                os.path.join(td, "chunk_manifest.json"), encoding="utf-8"
            ) as f:
                manifest = json.load(f)
            body = [e for e in manifest["chunks"] if not e["passthrough"]]
            for i, entry in enumerate(body):
                chunk_text = text[entry["start"] : entry["end"]]
                if i == 0:  # 첫 청크만 뭉텅 유실시킨다.
                    chunk_text = chunk_text[: len(chunk_text) // 4]
                with open(
                    os.path.join(td, entry["rewritten_file"]), "w", encoding="utf-8"
                ) as f:
                    f.write(chunk_text)
            rc = REASM.main(["--run-dir", td, "--strict"])
            self.assertEqual(rc, 1, "유실을 감지하지 못했다")
            with open(
                os.path.join(td, "03_reassembly_report.json"), encoding="utf-8"
            ) as f:
                report = json.load(f)
            self.assertTrue(any("유실 의심" in w for w in report["warnings"]))

    def test_reassemble_refuses_stale_manifest(self) -> None:
        """청킹 이후 입력이 바뀌면 재조립을 거부한다 (sha256 대조)."""
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "01_input.txt"), "w", encoding="utf-8") as f:
                f.write(FOOTNOTED)
            PREP.main(["--chunk", "--run-dir", td])
            with open(os.path.join(td, "01_input.txt"), "a", encoding="utf-8") as f:
                f.write("\n추가된 문장이다.\n")
            with self.assertRaises(SystemExit):
                REASM.main(["--run-dir", td])

    def test_legacy_mode_unchanged(self) -> None:
        """--chunk 없이 호출하면 기존 단일 combined 파일 동작 그대로."""
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "01_input.txt"), "w", encoding="utf-8") as f:
                f.write(SHORT)
            rc = PREP.main(["--run-dir", td])
            self.assertEqual(rc, 0)
            combined = os.path.join(td, "01_input_with_metrics.txt")
            self.assertTrue(os.path.exists(combined))
            with open(combined, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("[원문 시작]", content)
            self.assertIn(SHORT.rstrip("\n"), content)
            self.assertFalse(
                os.path.exists(os.path.join(td, "chunk_manifest.json")),
                "--chunk 없이 manifest 가 생기면 안 된다",
            )


if __name__ == "__main__":
    unittest.main()
