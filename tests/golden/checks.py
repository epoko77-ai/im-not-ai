"""Deterministic golden-fixture scorer for humanize-korean.

LLM output is non-deterministic, so these checks are DIRECTIONAL GATES,
never exact-string expectations. Each check asks "did a known failure mode
appear?" — e.g. a count that must not increase, or a structural element
that must not disappear. A legitimate rewrite always passes; only the
documented failure modes fail.

stdlib only. Usage as a library:

    from checks import run_checks
    failures = run_checks(original_text, rewritten_text)
    # empty list == PASS

or from the CLI:

    python3 checks.py input.txt output.txt

Failure codes (stable API — tests and fixtures reference these):
    empty_output       output is blank
    hayeot_injection   '하였' count increased vs original
    cliche_injection   a boilerplate phrase appeared/increased vs original
    colloquial_erased  colloquial sentence endings (해요체) wiped out
    heading_lost       a heading line disappeared entirely
    heading_absorbed   a heading line was merged into body prose
    footnote_count     inline footnote markers decreased
    footnote_numbers   the set of footnote numbers changed
    footnote_def       a footnote definition line was lost or altered
    footnote_anchor    a footnote marker moved to a different sentence
                       (detected via the nearest preceding number token)
    quote_altered      a direct quote is no longer verbatim
    number_injected    a numeric value appears in the output that never
                       occurred in the original (수치 주입)

Advisory (NOT a failure code): 원문 수치의 소실은 문장 병합·표기 통합의
정상 부산물일 수 있어 게이트하지 않는다. `dropped_numbers()`가 소실 값
목록을 반환하며, verify_gates.py가 리포트 전용 축(P4)에서 관측만 한다.
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
# Register checks — the "격식 역주행" failure mode
# ===========================================================================

HAYEOT_RE = re.compile(r"하였")

# Boilerplate phrases the rewriter must never ADD. Increase-only gate:
# if the original already contains one, keeping it is not a failure.
CLICHE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("기록적인 성과", re.compile(r"기록적인\s*성과")),
    ("괄목할 만한", re.compile(r"괄목할\s*만한")),
    ("~로 평가된다", re.compile(r"로\s*평가(?:된다|받|되)")),
    ("주목받-", re.compile(r"주목받")),
    ("크게 기여", re.compile(r"크게\s*기여")),
    ("중요한 역할을 한다", re.compile(r"중요한\s*역할을\s*(?:한다|했다|할)")),
    ("시사하는 바가 크다", re.compile(r"시사하는\s*바가\s*크")),
    ("의미가 크다", re.compile(r"의미가\s*크다")),
]

# Sentence-final 요 (해요체/구어 종결). Counts "~인데요." "~거든요?" etc.
YO_ENDING_RE = re.compile(r"요\s*(?:[.?!…]|$)", re.MULTILINE)

# colloquial_erased fires only when the original is clearly colloquial
# (>= MIN_YO endings) AND the output keeps less than KEEP_RATIO of them.
# Sentence merging in a legitimate rewrite stays well above this floor.
MIN_YO = 3
KEEP_RATIO = 0.5


def check_register(original: str, output: str) -> list[Failure]:
    fails: list[Failure] = []

    a = len(HAYEOT_RE.findall(original))
    b = len(HAYEOT_RE.findall(output))
    if b > a:
        fails.append(Failure(
            "hayeot_injection",
            f"'하였' 계열이 원문 {a}회 → 윤문본 {b}회로 늘었습니다 (격식 상향 주입)",
        ))

    for name, pat in CLICHE_PATTERNS:
        a = len(pat.findall(original))
        b = len(pat.findall(output))
        if b > a:
            fails.append(Failure(
                "cliche_injection",
                f"상투구 '{name}'이 원문 {a}회 → 윤문본 {b}회로 늘었습니다 (주입 금지)",
            ))

    a = len(YO_ENDING_RE.findall(original))
    b = len(YO_ENDING_RE.findall(output))
    if a >= MIN_YO and b < a * KEEP_RATIO:
        fails.append(Failure(
            "colloquial_erased",
            f"구어 종결(~요)이 원문 {a}회 → 윤문본 {b}회로 격감했습니다 "
            f"(격식 역주행; register는 Before/After 동일이 철칙)",
        ))

    return fails


# ===========================================================================
# Structure checks — the "학술 구조·각주 파괴" failure mode
# ===========================================================================

_HEADING_PREFIX = re.compile(
    r"^(?:#{1,6}\s+"                      # markdown: ## 제목
    r"|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ]+\.\s*"          # 로마 숫자: Ⅱ. 제목
    r"|\d{1,2}\.\s+"                      # 아라비아: 1. 제목
    r"|\(\d{1,2}\)\s*"                    # 괄호: (3) 제목
    r"|제\d+[장절]\s*"                    # 제3장 제목
    r")"
)
_PROSE_ENDING = re.compile(r"(?:다|요|음|함|까)\s*[.?!]$")
_DEF_LINE = re.compile(r"^\s*\d{1,3}\)\s")


def extract_headings(text: str) -> list[tuple[str, str]]:
    """Return [(heading_line, core_title_without_numbering), ...]."""
    heads = []
    for line in text.splitlines():
        s = line.strip()
        if not s or len(s) > 50:
            continue
        if _DEF_LINE.match(s):  # footnote definition, not a heading
            continue
        if not _HEADING_PREFIX.match(s):
            continue
        if _PROSE_ENDING.search(s):  # short prose sentence, not a heading
            continue
        core = _HEADING_PREFIX.sub("", s).strip()
        if not core:
            continue
        heads.append((_norm_ws(s), core))
    return heads


def check_headings(original: str, output: str) -> list[Failure]:
    fails: list[Failure] = []
    out_lines = {_norm_ws(l) for l in output.splitlines() if l.strip()}
    out_joined = _norm_ws(output)
    for line, core in extract_headings(original):
        if line in out_lines:
            continue
        if core in out_joined:
            fails.append(Failure(
                "heading_absorbed",
                f"제목 '{line}'이 독립 줄에서 사라지고 본문에 흡수됐습니다",
            ))
        else:
            fails.append(Failure(
                "heading_lost",
                f"제목 '{line}'이 윤문본에서 사라졌습니다",
            ))
    return fails


# Inline marker: digits + ')' ATTACHED to the preceding character
# ("...증가했다.1)"). A space-preceded or line-leading "N) " is a footnote
# DEFINITION label, not an inline marker. '(3)' style headings are excluded
# by the '(' lookbehind; '(2024)' style years by the digit lookbehind.
_INLINE_MARKER = re.compile(r"(?<=\S)(?<![(\d])(\d{1,3})\)")
_DEF_LABEL = re.compile(r"(?:^|(?<=\s))(\d{1,3})\)\s")
_NUM_TOKEN = re.compile(r"\d+(?:[.,]\d+)*")

ANCHOR_WINDOW = 50  # chars scanned backwards from a marker for its anchor number


def extract_inline_markers(text: str) -> list[tuple[str, int]]:
    """Return [(footnote_number, absolute_position), ...] in document order."""
    markers = []
    offset = 0
    for line in text.splitlines(keepends=True):
        if not _DEF_LINE.match(line):
            for m in _INLINE_MARKER.finditer(line):
                markers.append((m.group(1), offset + m.start(1)))
        offset += len(line)
    return markers


def extract_defs(text: str) -> dict[str, str]:
    """Return {footnote_number: normalized_definition_content}.

    Handles both one-definition-per-line and (broken) merged lines, so the
    content-identity check still works on merged-but-verbatim definitions.
    """
    defs: dict[str, str] = {}
    for line in text.splitlines():
        if not _DEF_LINE.match(line):
            continue
        labels = [(m.start(), m.group(1)) for m in _DEF_LABEL.finditer(line)]
        for i, (pos, num) in enumerate(labels):
            end = labels[i + 1][0] if i + 1 < len(labels) else len(line)
            content = re.sub(r"^\s*\d{1,3}\)\s*", "", line[pos:end])
            defs[num] = _norm_ws(content)
    return defs


def _nearest_num_before(text: str, pos: int) -> str | None:
    seg = text[max(0, pos - ANCHOR_WINDOW):pos]
    nums = _NUM_TOKEN.findall(seg)
    return nums[-1] if nums else None


def check_footnotes(original: str, output: str) -> list[Failure]:
    fails: list[Failure] = []
    in_markers = extract_inline_markers(original)
    out_markers = extract_inline_markers(output)
    if not in_markers and not extract_defs(original):
        return fails  # original has no footnotes; nothing to protect

    if len(out_markers) < len(in_markers):
        fails.append(Failure(
            "footnote_count",
            f"본문 각주 표시가 {len(in_markers)}개 → {len(out_markers)}개로 줄었습니다",
        ))

    in_nums = {n for n, _ in in_markers}
    out_nums = {n for n, _ in out_markers}
    if in_nums != out_nums:
        missing = sorted(in_nums - out_nums, key=int)
        invented = sorted(out_nums - in_nums, key=int)
        parts = []
        if missing:
            parts.append(f"소실 {missing}")
        if invented:
            parts.append(f"신규 {invented}")
        fails.append(Failure(
            "footnote_numbers",
            f"각주 번호 집합이 달라졌습니다: {', '.join(parts)}",
        ))

    # Anchor check: a marker must stay attached to the same sentence.
    # Proxy: the nearest number token within ANCHOR_WINDOW chars before the
    # marker (numbers are immutable under the skill's iron rules, so they
    # survive a legitimate rewrite). Markers with no nearby number in the
    # original are skipped — count/set checks still cover their existence.
    out_first_pos = {}
    for n, p in out_markers:
        out_first_pos.setdefault(n, p)
    for num, pos in in_markers:
        anchor = _nearest_num_before(original, pos)
        if anchor is None or num not in out_first_pos:
            continue
        out_anchor = _nearest_num_before(output, out_first_pos[num])
        if out_anchor != anchor:
            fails.append(Failure(
                "footnote_anchor",
                f"각주 {num})이 원위치를 벗어났습니다 "
                f"(인접 수치 앵커 '{anchor}' → '{out_anchor}'): 인용 출처 변조 위험",
            ))

    in_defs = extract_defs(original)
    out_defs = extract_defs(output)
    for num, content in in_defs.items():
        if num not in out_defs:
            fails.append(Failure(
                "footnote_def",
                f"각주 정의 {num})이 윤문본에서 사라졌습니다",
            ))
        elif out_defs[num] != content:
            fails.append(Failure(
                "footnote_def",
                f"각주 정의 {num})의 내용이 달라졌습니다 (서지사항은 불변이어야 함)",
            ))
    return fails


# ===========================================================================
# Number fidelity — 수치는 철칙상 불변. 주입만 FAIL (방향성 게이트).
# 삭제는 재구성 부산물일 수 있어 advisory(dropped_numbers)로만 관측.
# ===========================================================================

# 한글 수사 단위 — 숫자 토큰 직후에 바로 붙은 단일 글자만 환산 ("1만").
# "1만2천" 복합·띄어쓰기 케이스는 환산하지 않는다(양쪽 표기가 대칭이면
# 오탐 없음 — 과설계 금지).
_KO_UNIT_MULT = {
    "백": 100,
    "천": 1_000,
    "만": 10_000,
    "억": 100_000_000,
    "조": 1_000_000_000_000,
}


def _number_values(text: str) -> set[str]:
    """Canonical set of numeric VALUES in text.

    - `_NUM_TOKEN` 재사용 (콤마·소수점 포함 토큰: "10,000", "3.1").
    - 천단위 콤마는 정규화한다 ("10,000" == "10000") — 표기 변경은 수치
      변조가 아니다.
    - 숫자 토큰 직후에 바로 붙은 한글 수사 단위 1글자(만·억·조·천·백)는
      값으로 환산한다 ("1만" == "10,000" == 10000, "1억" == 100000000).
    - set(값 집합) 비교라서 헤딩 재번호·반복 횟수 변화(순서/multiset 차)는
      플래그하지 않는다. 오탐 최소화가 우선.
    """
    values: set[str] = set()
    for m in _NUM_TOKEN.finditer(text):
        tok = m.group(0).replace(",", "")
        mult = _KO_UNIT_MULT.get(text[m.end():m.end() + 1])
        if mult:
            try:
                val = float(tok) * mult
                values.add(str(int(val)) if val == int(val) else str(val))
                continue
            except ValueError:
                pass
        values.add(tok)
    return values


def dropped_numbers(original: str, output: str) -> list[str]:
    """원문에는 있는데 윤문본에서 사라진 수치 값 목록 (advisory 전용).

    Failure가 아니다 — 문장 병합·표기 통합에서도 수치가 사라질 수 있어
    게이트하면 양치기 소년이 된다. run_checks는 호출하지 않으며,
    verify_gates.py가 P4(리포트 전용 축)에서 관측만 한다.
    """
    return sorted(_number_values(original) - _number_values(output))


def check_numbers(original: str, output: str) -> list[Failure]:
    """수치 주입 방향성 게이트 — 주입(number_injected)만 FAIL."""
    fails: list[Failure] = []
    injected = sorted(_number_values(output) - _number_values(original))
    if injected:
        fails.append(Failure(
            "number_injected",
            f"원문에 없던 수치가 윤문본에 등장했습니다: {injected} "
            f"(수치 불변 철칙 — 없던 주장 주입 위험)",
        ))
    return fails


# ===========================================================================
# Quote fidelity — direct quotes are immutable under the iron rules
# ===========================================================================

MIN_QUOTE_LEN = 8


def extract_quotes(text: str, min_len: int = MIN_QUOTE_LEN) -> list[str]:
    quotes: list[str] = []
    for op, cl in (("「", "」"), ("『", "』"), ("“", "”")):
        quotes += re.findall(re.escape(op) + r"([^" + cl + r"]+)" + re.escape(cl), text)
    # Straight double quotes: only if balanced.
    parts = text.split('"')
    if len(parts) % 2 == 1:
        quotes += parts[1::2]
    return [q for q in quotes if len(q.strip()) >= min_len]


def check_quotes(original: str, output: str) -> list[Failure]:
    fails = []
    for q in extract_quotes(original):
        if q not in output:
            fails.append(Failure(
                "quote_altered",
                f"직접 인용 「{q[:30]}…」이 윤문본에 원문 그대로 없습니다 (인용 불변 철칙)",
            ))
    return fails


# ===========================================================================
# Entry point
# ===========================================================================

_SUMMARY_BLOCK_RE = re.compile(r"<!--\s*HUMANIZE-SUMMARY\b.*", re.DOTALL)


def strip_summary_block(text: str) -> str:
    """final.md 끝의 <!-- HUMANIZE-SUMMARY --> 메타 블록을 제거한다.

    이 블록은 윤문 산출물이 아니라 메타데이터다. 자체검증 문구에 '하였- 무'
    같은 표현이 들어가 채점기가 본문 주입으로 오판하는 것을 막는다
    (verify_change_rate.py와 동일한 처리).
    """
    return _SUMMARY_BLOCK_RE.sub("", text).strip()


def run_checks(original: str, output: str) -> list[Failure]:
    original = strip_summary_block(original)
    output = strip_summary_block(output)
    if not output.strip():
        return [Failure("empty_output", "윤문본이 비어 있습니다")]
    fails: list[Failure] = []
    fails += check_register(original, output)
    fails += check_headings(original, output)
    fails += check_footnotes(original, output)
    fails += check_quotes(original, output)
    fails += check_numbers(original, output)
    return fails


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: python3 checks.py <original.txt> <rewritten.txt>", file=sys.stderr)
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
