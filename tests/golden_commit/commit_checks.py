"""Deterministic golden-fixture scorer for commit-ko.

Same philosophy as scripts/checks.py (humanize-korean), scaled down to
the commit-message register: LLM output is non-deterministic, so every check
is a DIRECTIONAL GATE ("did a known regression appear?"), never an exact
string match. A legitimate rewrite always passes; only documented failure
modes fail.

stdlib only. Usage as a library:

    from commit_checks import run_checks
    failures = run_checks(original_text, rewritten_text)
    # empty list == PASS

or from the CLI:

    python3 commit_checks.py input.txt output.txt

Failure codes (stable API — tests and fixtures reference these):
    empty_output            output is blank
    prefix_altered           Conventional Commits `type(scope)!:` prefix changed
    trailer_lost             a git trailer (Co-authored-by, Closes, ...) disappeared
    trailer_altered          a trailer key survived but its value changed
    code_span_altered        a backtick code span (file/function/identifier) is
                             no longer verbatim in the output
    hayeot_injection         '하였' count increased vs original (과공손 상향 주입)
    bureaucratic_injection   사무적 격식 동사(수행/진행/실시) count increased —
                             regresses the very thing commit-ko exists to remove
    number_injected          a numeric value (incl. issue refs like #123) appears
                             in the output that never occurred in the original
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass


@dataclass
class Failure:
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# ===========================================================================
# Conventional Commits prefix — type(scope)!: must survive verbatim
# ===========================================================================

_PREFIX_RE = re.compile(r"^([A-Za-z]+)(\([^)]*\))?(!)?:\s*")


def extract_prefix(text: str) -> tuple[str, str, bool] | None:
    lines = text.splitlines()
    if not lines:
        return None
    m = _PREFIX_RE.match(lines[0])
    if not m:
        return None
    return (m.group(1), m.group(2) or "", bool(m.group(3)))


def check_prefix(original: str, output: str) -> list[Failure]:
    orig_prefix = extract_prefix(original)
    if orig_prefix is None:
        return []  # not Conventional Commits format — nothing to protect
    out_prefix = extract_prefix(output)
    if out_prefix != orig_prefix:
        return [Failure(
            "prefix_altered",
            f"Conventional Commits 접두사가 {orig_prefix} → {out_prefix}로 바뀌었습니다",
        )]
    return []


# ===========================================================================
# Git trailers — Co-authored-by / Signed-off-by / Closes / BREAKING CHANGE …
# ===========================================================================

_TRAILER_KEYS = (
    "Co-authored-by", "Signed-off-by", "Reviewed-by", "Reported-by",
    "Tested-by", "Acked-by", "Closes", "Fixes", "Resolves", "Refs",
    "BREAKING CHANGE",
)
_TRAILER_RE = re.compile(
    # colon is optional — Co-authored-by/Signed-off-by use "Key: value" (git
    # trailer spec) but GitHub's issue-closing keywords conventionally omit
    # it ("Closes #482"). Either way a key needs a colon or whitespace after
    # it, so "Closesfoo:" or "Closest #1" never match.
    r"^(" + "|".join(re.escape(k) for k in _TRAILER_KEYS) + r")\s*:?\s+(.+)$",
    re.MULTILINE,
)


def extract_trailers(text: str) -> dict[str, list[str]]:
    trailers: dict[str, list[str]] = {}
    for m in _TRAILER_RE.finditer(text):
        trailers.setdefault(m.group(1), []).append(_norm_ws(m.group(2)))
    return trailers


def check_trailers(original: str, output: str) -> list[Failure]:
    fails: list[Failure] = []
    in_trailers = extract_trailers(original)
    out_trailers = extract_trailers(output)
    for key, values in in_trailers.items():
        out_values = out_trailers.get(key)
        if not out_values:
            fails.append(Failure(
                "trailer_lost",
                f"트레일러 '{key}:'가 윤문본에서 사라졌습니다",
            ))
            continue
        for v in values:
            if v not in out_values:
                fails.append(Failure(
                    "trailer_altered",
                    f"트레일러 '{key}: {v}'의 내용이 윤문본에서 달라졌습니다",
                ))
    return fails


# ===========================================================================
# Code spans — backtick 안의 파일·함수·식별자명은 고유 토큰으로 불변
# ===========================================================================

_CODE_SPAN_RE = re.compile(r"`([^`]+)`")


def extract_code_spans(text: str) -> list[str]:
    return _CODE_SPAN_RE.findall(text)


def check_code_spans(original: str, output: str) -> list[Failure]:
    fails: list[Failure] = []
    out_spans = set(extract_code_spans(output))
    for span in extract_code_spans(original):
        if span not in out_spans:
            fails.append(Failure(
                "code_span_altered",
                f"코드 스팬 `{span}`이 윤문본에 그대로 없습니다 (고유 토큰 보존 철칙)",
            ))
    return fails


# ===========================================================================
# Register — 과공손·과격식 방향 주입 금지 (SKILL.md 철칙 #3)
# ===========================================================================

_HAYEOT_RE = re.compile(r"하였")


def check_register(original: str, output: str) -> list[Failure]:
    a, b = len(_HAYEOT_RE.findall(original)), len(_HAYEOT_RE.findall(output))
    if b > a:
        return [Failure(
            "hayeot_injection",
            f"'하였' 계열이 원문 {a}회 → 윤문본 {b}회로 늘었습니다 (과공손 상향 주입 금지)",
        )]
    return []


# ===========================================================================
# Bureaucratic verbs — 수행/진행/실시 증가는 commit-ko 존재 이유에 반하는 역주행
# ===========================================================================

_BUREAUCRATIC_RE = re.compile(r"수행|진행|실시")


def check_bureaucratic(original: str, output: str) -> list[Failure]:
    a = len(_BUREAUCRATIC_RE.findall(original))
    b = len(_BUREAUCRATIC_RE.findall(output))
    if b > a:
        return [Failure(
            "bureaucratic_injection",
            f"사무적 격식 동사(수행/진행/실시)가 원문 {a}회 → 윤문본 {b}회로 늘었습니다",
        )]
    return []


# ===========================================================================
# Numbers — 이슈 번호 등 수치 주입만 FAIL (방향성 게이트, 삭제는 게이트하지 않음)
# ===========================================================================

_NUM_TOKEN = re.compile(r"#?\d+(?:[.,]\d+)*")


def _number_values(text: str) -> set[str]:
    return {m.group(0).lstrip("#").replace(",", "") for m in _NUM_TOKEN.finditer(text)}


def check_numbers(original: str, output: str) -> list[Failure]:
    injected = sorted(_number_values(output) - _number_values(original))
    if injected:
        return [Failure(
            "number_injected",
            f"원문에 없던 수치가 윤문본에 등장했습니다: {injected}",
        )]
    return []


# ===========================================================================
# Entry point
# ===========================================================================


def run_checks(original: str, output: str) -> list[Failure]:
    if not output.strip():
        return [Failure("empty_output", "커밋 메시지가 비어 있습니다")]
    fails: list[Failure] = []
    fails += check_prefix(original, output)
    fails += check_trailers(original, output)
    fails += check_code_spans(original, output)
    fails += check_register(original, output)
    fails += check_bureaucratic(original, output)
    fails += check_numbers(original, output)
    return fails


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: python3 commit_checks.py <original.txt> <rewritten.txt>", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        original = f.read()
    with open(argv[2], encoding="utf-8") as f:
        output = f.read()
    failures = run_checks(original, output)
    if failures:
        for x in failures:
            print(f"FAIL {x}")
        return 1
    print("PASS (알려진 실패 모드 없음)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
