#!/usr/bin/env python3
"""Humanize KR v2.0 — monolith input shim.

Pre-processes user input by computing quantitative metrics (v1.6 8지표 +
v2.0 카운트형 지표) and prepending the result to the text the monolith
agent reads. The monolith keeps its 4-tool-call cap (Read input + Read
rules + Write final + Write summary) because the metrics block is folded
into the same input file.

Inputs:
  --run-dir DIR     existing run directory containing 01_input.txt
  --text STR        ad-hoc text; if --run-dir is omitted, a new run dir
                    `_workspace/<YYYY-MM-DD>-NNN/` is created and
                    01_input.txt written.
  --genre STR       essay|column|report|blog|abstract|... (default: essay)
  --diagnosis PATH  optional diagnosis text prepended before the metrics
                    block (정밀 3콜 구조의 진단 1콜 산출물 자리)
  --chunk           장문 청킹 모드. 01_input.txt 를 손실 없이 청크로 나눠
                    청크별 01_chunk_{NN}_input_with_metrics.txt 와
                    chunk_manifest.json 을 만든다. 경계 결정은 100% 코드
                    (LLM 개입 0). 재조립은 scripts/reassemble_chunks.py.

Outputs (in {run_dir}):
  00_metrics.json             — full compute_all() output (or error stub)
  01_input.txt                — original text (created if --text used)
  01_input_with_metrics.txt   — combined file the monolith Reads
  00_metrics.error            — only on graceful-degrade fallback

Hard rules:
  - stdlib only (argparse/json/os/sys/datetime/pathlib/traceback)
  - never modify the original text body inside the combined file
  - on metrics failure, write the combined file *without* the score block
    so the monolith degrades to v1.5 behaviour automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import traceback
from datetime import date
from pathlib import Path

# Resolve project layout. This file lives at:
#   {project_root}/scripts/prepare_monolith_input.py
# metrics.py is at:
#   {project_root}/.claude/skills/humanize-korean/references/metrics.py
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
METRICS_DIR = PROJECT_ROOT / ".claude" / "skills" / "humanize-korean" / "references"

# Make metrics.py importable without polluting global state.
sys.path.insert(0, str(METRICS_DIR))
# v2.0 우선 import — compute_all 별칭으로 v1.6 호환. metrics_v2 부재·로드 실패 시
# v1.6 metrics fallback. graceful degrade로 monolith 동작은 항상 보장.
try:
    import metrics_v2 as _metrics_mod  # type: ignore  # v2.0 (post-editese 14 metric)
except Exception:  # pragma: no cover
    try:
        import metrics as _metrics_mod  # type: ignore  # v1.6 fallback
    except Exception:
        _metrics_mod = None


# ---------------------------------------------------------------------------
# Run directory discovery / creation
# ---------------------------------------------------------------------------


def _next_run_dir(workspace: Path) -> Path:
    """Allocate _workspace/<today>-NNN/ with the smallest free NNN."""
    workspace.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    n = 1
    while True:
        candidate = workspace / f"{today}-{n:03d}"
        if not candidate.exists():
            return candidate
        n += 1


def _resolve_run_dir(run_dir_arg: str | None, text_arg: str | None) -> Path:
    if run_dir_arg:
        rd = Path(run_dir_arg)
        if not rd.is_absolute():
            rd = PROJECT_ROOT / rd
        rd.mkdir(parents=True, exist_ok=True)
        return rd
    if text_arg is None:
        raise SystemExit("Either --run-dir or --text is required")
    workspace = PROJECT_ROOT / "_workspace"
    rd = _next_run_dir(workspace)
    rd.mkdir(parents=True, exist_ok=True)
    return rd


# ---------------------------------------------------------------------------
# Route hint — shim이 "손댈 양"을 판정해 경로를 권고한다
# ---------------------------------------------------------------------------
#
# 배경: 9,817자 실측 run(_workspace/2026-07-18-001)은 어휘·피동 카운트형 티가
# 전부 0이고 구조 티(ending_comma z=+6.29)만 있는 "잘 쓴 글"이었는데도 최중량
# 6청크 경로를 돌아 610K 토큰을 썼다. 같은 글 단일 콜은 134K에 품질 동등.
# shim은 이미 그 판정에 필요한 점수를 전부 내고 있으므로, 여기서 route_hint 를
# 함께 산출해 오케스트레이터가 경로를 정하게 한다. route_hint 는 **권고**다 —
# 사용자·오케스트레이터가 무시할 수 있고, 산출 실패 시 없는 채로 진행한다.
#
# 3-tier 판정 (전부 결정적 · 실측 기반):
#   light    — 카운트형 어휘·피동 티 합 ≤ 2 AND risk_band low~medium.
#              이미 잘 쓴 글. 단일 콜·최소 파이프라인 권장.
#   standard — 그 외 (티가 섞여 있거나, 카운트형 0이어도 구조 지표로 risk high).
#              진단 + 단일 윤문 권장. 실측 글(카운트 0·risk high)이 여기 온다.
#   heavy    — risk high AND 카운트형 티 합 ≥ 8 (AI 슬롭 밀집),
#              또는 초장문(> CHUNK_RECOMMEND_MIN_CHARS). 진단 + 청킹 권장.
#
# 카운트형 티 = v1.6 conclusion_pivot·safe_balance + v2.0 이중피동·에의해피동·
# have/make직역·이중조사. 전부 정수 카운트라 baseline calibration 없이도 안정적.
# 밀도·z-score 지표는 판정에서 제외 — v2 baseline 이 placeholder 라 불안정하다.

ROUTE_LIGHT_MAX_TELLS = 2
ROUTE_HEAVY_MIN_TELLS = 8
# 초장문 기준. 아래 청킹 섹션의 CHUNK_RECOMMEND_MIN_CHARS 가 이 값을 공유한다
# — "heavy 판정"과 "청킹이 의미 있는 최소 분량"은 같은 실증에서 나온 한 기준.
ROUTE_HEAVY_MIN_CHARS = 15000

_ROUTE_TELL_KEYS_V16 = ("conclusion_pivot_count", "safe_balance_count")
_ROUTE_TELL_KEYS_V2 = (
    "double_passive_count",
    "by_passive_count",
    "have_make_literal_count",
    "double_particle_count",
)


def compute_route_hint(metrics_obj: dict) -> dict:
    """metrics_obj(compute_all 산출)로부터 route_hint 권고를 산출한다.

    반환 dict 는 metrics_obj 에 update 해서 00_metrics.json 에 함께 실린다.
    입력이 부분적이어도(키 누락) 죽지 않고 보수적으로 standard 로 수렴한다.
    """
    m = metrics_obj.get("metrics") or {}
    v2 = metrics_obj.get("v2_metrics") or {}
    tells = 0
    for key in _ROUTE_TELL_KEYS_V16:
        tells += int(m.get(key) or 0)
    for key in _ROUTE_TELL_KEYS_V2:
        tells += int(v2.get(key) or 0)
    chars = int(metrics_obj.get("char_count") or 0)
    risk = metrics_obj.get("risk_band", "unknown")

    if chars > ROUTE_HEAVY_MIN_CHARS:
        hint = "heavy"
        reason = (
            f"{chars:,}자 초장문(>{ROUTE_HEAVY_MIN_CHARS:,}) — 진단 + 청킹 권장"
        )
    elif risk == "high" and tells >= ROUTE_HEAVY_MIN_TELLS:
        hint = "heavy"
        reason = (
            f"risk_band high + 카운트형 티 {tells}건 — AI 슬롭 밀집, "
            f"진단 + 청킹 권장"
        )
    elif tells <= ROUTE_LIGHT_MAX_TELLS and risk in ("low", "medium"):
        hint = "light"
        reason = (
            f"카운트형 어휘·피동 티 {tells}건 · risk_band {risk} — "
            f"이미 잘 쓴 글, 단일 콜·최소 파이프라인 권장"
        )
    else:
        hint = "standard"
        reason = (
            f"카운트형 티 {tells}건 · risk_band {risk} — 진단 + 단일 윤문 권장"
        )
    return {
        "route_hint": hint,
        "route_reason": reason,
        "route_signals": {
            "lexical_tell_count": tells,
            "risk_band": risk,
            "char_count": chars,
        },
    }


# ---------------------------------------------------------------------------
# Combined-file rendering
# ---------------------------------------------------------------------------


def _fmt_z(z: float | None) -> str:
    if z is None:
        return "n/a"
    sign = "+" if z >= 0 else ""
    return f"z={sign}{z:.2f}"


def _z_marker(z: float | None) -> str:
    """Emit a small star for values clearly above the AI band."""
    if z is None:
        return ""
    if z >= 1.5:
        return "  ★ S1 트리거"
    if z >= 1.0:
        return "  · S2 시그널"
    return ""


# v2.0 카운트형 지표 — baseline 없이 원값만으로 유용한 지표들.
# (key, 한국어 라벨, taxonomy ID, 포맷) — ID는 ai-tell-taxonomy.md 본진.
_V2_COUNT_METRICS = (
    ("double_passive_count", "이중 피동", "A-8", "{:d}"),
    ("by_passive_count", "~에 의해 피동", "A-9", "{:d}"),
    ("pronoun_density", "인칭 대명사 밀도", "A-16", "{:.3f}"),
    ("have_make_literal_count", "have/make 직역", "A-7", "{:d}"),
    ("double_particle_count", "이중 조사 결합", "A-19", "{:d}"),
    ("relative_clause_nesting", "관형절 3중+ 중첩 문장 수", "A-18", "{:d}"),
    ("deul_overuse_rate", "'-들' 남용률", "A-17 hold", "{:.3f}"),
)


def _render_v2_counts(metrics_obj: dict) -> list[str]:
    """v2.0 카운트형 지표 원값 렌더.

    v2 z-score는 렌더하지 않는다 — baseline_v2.json 70셀 전부 placeholder
    (추정치)라 calibration 전까지 해석 보류. 카운트/밀도 원값은 baseline
    없이도 그 자체로 윤문 근거가 된다.
    """
    v2 = metrics_obj.get("v2_metrics")
    if not v2:
        return []
    lines: list[str] = []
    lines.append("[v2.0 카운트형 지표 — 원값 / baseline calibration 전 z-score 해석 보류]")
    for key, label, tell_id, fmt in _V2_COUNT_METRICS:
        val = v2.get(key)
        if val is None:
            lines.append(f"- {key}: n/a")
            continue
        if fmt == "{:d}":
            rendered = fmt.format(int(val))
        else:
            rendered = fmt.format(float(val))
        lines.append(f"- {key} ({label}, 본진 {tell_id}): {rendered}")
    lines.append("- 카운트 > 0 지표는 해당 본진 ID 처방(quick-rules.md·taxonomy)과 교차 확인 후 윤문할 것.")
    lines.append("")
    return lines


def _render_block(metrics_obj: dict) -> str:
    m = metrics_obj.get("metrics", {})
    z = metrics_obj.get("z_scores", {})
    ev = metrics_obj.get("evidence", {})
    pivots = ev.get("conclusion_pivots") or []
    safe = ev.get("safe_balances") or []

    lines: list[str] = []
    lines.append("[정량 사전 점수 v2.0 — v1.6 8지표(KatFish baseline) + v2.0 카운트형]")
    lines.append(
        f"risk_band: {metrics_obj.get('risk_band', 'unknown')}  "
        f"(score {metrics_obj.get('risk_score', 0)})"
    )
    if metrics_obj.get("route_hint"):
        lines.append(
            f"route_hint: {metrics_obj['route_hint']}  "
            f"(권고 — 사용자·오케스트레이터가 무시 가능)"
        )
        lines.append(f"route_reason: {metrics_obj.get('route_reason', '')}")
    lines.append(f"genre: {metrics_obj.get('genre', 'essay')}")
    lines.append(f"char_count: {metrics_obj.get('char_count', 0)}")
    if metrics_obj.get("warning"):
        lines.append(f"warning: {metrics_obj['warning']}")
    lines.append("")
    lines.append("[v1.6 지표]")

    def row(key: str, value_fmt: str, with_z: bool = True, suffix: str = "") -> str:
        val = m.get(key)
        if val is None:
            return f"- {key}: n/a"
        z_part = ""
        if with_z:
            z_part = f"  ({_fmt_z(z.get(key))} vs {metrics_obj.get('genre','essay')} 인간 baseline){_z_marker(z.get(key))}"
        return f"- {key}: {value_fmt.format(val)}{z_part}{suffix}"

    lines.append(row("comma_inclusion_rate", "{:.2f}"))
    lines.append(row("comma_usage_rate", "{:.2f}"))
    lines.append(row("ending_comma_rate", "{:.2f}"))
    lines.append(row("comma_segment_length", "{:.2f}"))

    pivot_suffix = f"  (lexicon 매치: {', '.join(repr(p) for p in pivots)})" if pivots else ""
    lines.append(
        f"- conclusion_pivot_count: {int(m.get('conclusion_pivot_count', 0))}{pivot_suffix}"
    )
    safe_suffix = f"  (lexicon 매치: {', '.join(repr(s) for s in safe)})" if safe else ""
    lines.append(
        f"- safe_balance_count: {int(m.get('safe_balance_count', 0))}{safe_suffix}"
    )
    lines.append(row("hanja_nominalizer_density", "{:.3f}"))
    lines.append(row("lexical_diversity", "{:.2f}"))
    lines.append("")
    lines.extend(_render_v2_counts(metrics_obj))
    lines.append("[근거 사용 가이드]")
    lines.append("- 위 점수는 *근거 보조*다. 단독 판정 금지(보고서 명시).")
    lines.append("- z>1.0 지표는 quick-rules.md S1·S2 패턴과 교차 확인 후 윤문할 것.")
    lines.append("- ending_comma_rate가 ★ S1 트리거인 경우 C-11(연결어미 뒤 쉼표) 우선 손질.")
    lines.append("- conclusion_pivot 매치 토큰은 D-1·H-1 처방 적용 대상.")
    lines.append("")
    return "\n".join(lines)


def _render_combined(
    text: str, metrics_obj: dict | None, diagnosis: str | None = None
) -> str:
    parts: list[str] = []
    if diagnosis:
        parts.append("[진단]")
        parts.append(diagnosis.rstrip("\n"))
        parts.append("[진단 끝]")
        parts.append("")
    if metrics_obj is not None:
        parts.append(_render_block(metrics_obj))
    parts.append("[원문 시작]")
    parts.append(text.rstrip("\n"))
    parts.append("[원문 끝]")
    parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# --chunk mode: 손실 없는 결정적 분할 (v2.0.1 — fast+청킹으로 strict 승급 폐지)
# ---------------------------------------------------------------------------
#
# 불변식 (최상위): 모든 청크(passthrough 포함)를 순서대로 이으면 원문과
# 공백·개행까지 정확히 일치한다. 이를 위해 청크는 문자열 조각이 아니라
# 원문 offset [start, end) 구간으로 정의하고, 쓰기 전에 self-check 한다.
#
# 경계 우선순위:
#   1. 헤딩 줄 앞 강제 컷 — 헤딩은 반드시 다음 청크의 첫 줄이 된다.
#      (웹앱 imnotai.kr 의 "제목이 본문과 한 청크로 묶여 병합 윤문" 버그 차단.
#       연속 헤딩 런 사이에는 컷하지 않아 청크가 헤딩으로 끝나는 일이 없다.)
#   2. 빈 줄(\n{2,}) 문단 경계 그리디 패킹 (목표 TARGET_CHUNK_CHARS).
#   3. 한 문단이 상한 초과 시에만 문장 경계 폴백.
#   4. 문서 말미 각주 블록은 passthrough 청크로 태깅해 윤문 대상에서 제외.
#
# 청크 크기: 목표 7,000 / 상한 9,000 (v2.1 상향 — 종전 3,000/4,000).
# 근거: 9,817자 실측 run(_workspace/2026-07-18-001)에서 6청크 정밀 파이프라인이
# 610K 토큰(7콜)을 쓴 반면 단일 콜은 134K로 품질 동등(ending_comma_rate 0.09/0.08)
# — 폭발 원인은 콜마다 룰북·컨텍스트 재로드이므로 청크 수 자체를 줄여야 한다.
# 단일 콜이 1만자를 검증된 품질로 처리하므로 청크도 그 급으로 키운다. 웹앱의
# 1800은 flash-lite 전제라 이식 금지 — 큰 모델은 대구·리듬 같은 문단 횡단
# 신호를 잡아야 하므로 청크가 커야 한다.
#
# 청킹 자체는 CHUNK_RECOMMEND_MIN_CHARS(15,000자) 초과 장문에서만 의미가 있다
# — 그 미만은 단일 콜 실증 범위라 run_chunk_mode 가 비권장 경고를 남긴다(권고,
# 강제 아님). 헤딩 강제 컷은 무결성 불변식이라 유지되므로, 헤딩이 촘촘한
# 문서는 크기 임계와 무관하게 섹션 수만큼 청크가 나온다 — 그런 문서일수록
# 단일 콜 경로(route_hint)가 답이다.

TARGET_CHUNK_CHARS = 7000
MAX_CHUNK_CHARS = 9000
# 문장 경계 폴백 트리거 겸 "쪼갤 수 없는 통짜 런" 경고 기준. 상한(9,000)과
# 분리해 종전 4,000을 유지한다 — 재조립 유실 검증(청크 절반 미만 감지)의
# granularity 와 종결부호 없는 초장 런 경고 감도를 보존하기 위함. 폴백으로
# 잘게 난 조각은 어차피 target 까지 그리디 재패킹되므로 콜 수는 늘지 않는다.
SENT_SPLIT_TRIGGER_CHARS = 4000
CHUNK_RECOMMEND_MIN_CHARS = ROUTE_HEAVY_MIN_CHARS

HEADING_LINE_RE = re.compile(
    r"^(#{1,6}\s"
    r"|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+\."
    r"|\d+\.\s"
    r"|\d+\)\s"
    r"|제\s*\d+\s*[장절편]"
    r"|[가나다라마바사아자차카타파하]\.\s"
    r"|\([0-9가-힣]+\))"
)
# 각주 정의 줄. \d+\) 는 헤딩 정규식과 겹치지만 각주 판정은 문서 말미의
# 연속 블록에만 적용되고 그 구간은 본문 청킹에서 제외되므로 충돌 없음.
FOOTNOTE_LINE_RE = re.compile(r"^(?:\d+\)\s|\[\d+\]\s)")

_PARA_SEP_RE = re.compile(r"\n{2,}")
# 문장 경계: 종결 부호(+닫는 따옴표류) 뒤 공백. 컷은 공백 런 끝 = 다음 문장 시작.
_SENT_END_RE = re.compile(r"[.!?。！？…]['\"”’』」)\]]*\s+")


class ChunkingError(RuntimeError):
    """손실 없는 분할 불변식 위반 — 즉시 중단해야 하는 fidelity 사고."""


def _line_spans(text: str) -> list[tuple[int, int]]:
    """개행 포함 줄 구간 [(start, end), ...]. 이으면 원문과 일치."""
    spans: list[tuple[int, int]] = []
    pos = 0
    n = len(text)
    while pos < n:
        nl = text.find("\n", pos)
        if nl == -1:
            spans.append((pos, n))
            break
        spans.append((pos, nl + 1))
        pos = nl + 1
    return spans


def find_footnote_block_start(text: str) -> int | None:
    """문서 말미의 각주 모음 블록 시작 offset. 없으면 None.

    끝에서 역방향으로 훑으며 빈 줄은 통과, 각주 패턴 줄은 블록에 포함,
    그 외 줄을 만나면 중단. 최소 1개의 각주 줄이 있어야 블록으로 본다.
    """
    spans = _line_spans(text)
    start: int | None = None
    for ls, le in reversed(spans):
        line = text[ls:le]
        if not line.strip():
            continue
        if FOOTNOTE_LINE_RE.match(line):
            start = ls
            continue
        break
    return start


def _has_substantive(body: str, a: int, b: int) -> bool:
    """[a, b) 구간에 헤딩도 빈 줄도 아닌 실제 본문 줄이 있는가."""
    for ln in body[a:b].splitlines():
        if ln.strip() and not HEADING_LINE_RE.match(ln):
            return True
    return False


def _ends_with_heading(body: str, start: int, end: int) -> bool:
    region = body[start:end].rstrip()
    if not region:
        return False
    last_line = region.rsplit("\n", 1)[-1]
    return bool(HEADING_LINE_RE.match(last_line))


def _sentence_pieces(
    text: str, start: int, end: int, target: int
) -> list[tuple[int, int]]:
    """상한 초과 문단을 문장 경계에서 target 크기로 그리디 분할.

    경계가 아예 없는 초장 구간은 통짜로 반환한다(호출부가 경고).
    """
    bounds = [
        m.end() for m in _SENT_END_RE.finditer(text, start, end) if m.end() < end
    ]
    pieces: list[tuple[int, int]] = []
    piece_start = start
    prev: int | None = None
    for b in bounds:
        if b - piece_start > target:
            cut = prev if (prev is not None and prev > piece_start) else b
            pieces.append((piece_start, cut))
            piece_start = cut
            prev = b if b > cut else None
        else:
            prev = b
    if end - piece_start > target and prev is not None and prev > piece_start:
        pieces.append((piece_start, prev))
        piece_start = prev
    pieces.append((piece_start, end))
    return pieces


def _pack_segment(
    body: str,
    seg_start: int,
    seg_end: int,
    target: int,
    max_chunk: int,
    warnings: list[str],
) -> list[tuple[int, int]]:
    """헤딩 강제 컷 사이의 한 세그먼트를 문단 단위로 그리디 패킹."""
    # 문단 단위: 빈 줄 런의 *끝*에서 자르므로 각 청크는 문단 시작에서 출발하고
    # 구분 개행은 앞 청크 꼬리에 붙는다 (손실 없음).
    units: list[tuple[int, int]] = []
    pos = seg_start
    for m in _PARA_SEP_RE.finditer(body, seg_start, seg_end):
        if m.end() >= seg_end:
            break
        units.append((pos, m.end()))
        pos = m.end()
    if pos < seg_end:
        units.append((pos, seg_end))

    pieces: list[tuple[int, int]] = []
    for us, ue in units:
        if ue - us > SENT_SPLIT_TRIGGER_CHARS:
            subs = _sentence_pieces(body, us, ue, target)
            for ss, se in subs:
                # 문장 경계가 전혀 없는 통짜 런은 재조립 유실 검증의 사각지대라
                # 크기 상한과 무관하게 종전 4,000 기준으로 계속 경고한다.
                if se - ss > SENT_SPLIT_TRIGGER_CHARS and not _SENT_END_RE.search(
                    body, ss, se
                ):
                    warnings.append(
                        f"문장 경계로 쪼갤 수 없는 초장 구간 {se - ss}자 "
                        f"(offset {ss}) — 경고 기준({SENT_SPLIT_TRIGGER_CHARS}) "
                        f"초과 허용, 검토 요망"
                    )
            pieces.extend(subs)
        else:
            pieces.append((us, ue))

    chunks: list[tuple[int, int]] = []
    cur_start: int | None = None
    cur_end = 0
    for ps, pe in pieces:
        if cur_start is None:
            cur_start, cur_end = ps, pe
            continue
        would = (cur_end - cur_start) + (pe - ps)
        # 헤딩 글루: 현재 청크가 헤딩으로 끝나는 상태면 크기와 무관하게 이어붙여
        # "청크가 헤딩으로 끝남"을 구조적으로 금지한다.
        if would > target and not _ends_with_heading(body, cur_start, cur_end):
            chunks.append((cur_start, cur_end))
            cur_start, cur_end = ps, pe
        else:
            cur_end = pe
    if cur_start is not None:
        chunks.append((cur_start, cur_end))
    return chunks


def compute_chunk_spans(
    text: str,
    target: int = TARGET_CHUNK_CHARS,
    max_chunk: int = MAX_CHUNK_CHARS,
) -> tuple[list[dict], list[str]]:
    """원문을 손실 없이 청크 구간으로 나눈다. LLM 개입 0, 100% 결정적.

    반환: ([{start, end, passthrough}, ...], warnings)
    불변식 위반 시 ChunkingError.
    """
    warnings: list[str] = []
    if not text:
        return [], warnings

    fn_start = find_footnote_block_start(text)
    body_end = fn_start if fn_start is not None else len(text)

    spans: list[dict] = []
    if body_end > 0:
        body = text[:body_end]
        # 헤딩 강제 컷 수집. 직전 컷 이후 실제 본문이 없으면(연속 헤딩 런 등)
        # 컷을 억제해 헤딩으로 끝나는 청크를 만들지 않는다.
        cuts = [0]
        for ls, le in _line_spans(body):
            if ls == 0:
                continue
            if HEADING_LINE_RE.match(body[ls:le]) and _has_substantive(
                body, cuts[-1], ls
            ):
                cuts.append(ls)
        cuts.append(body_end)
        for seg_start, seg_end in zip(cuts, cuts[1:]):
            for cs, ce in _pack_segment(
                body, seg_start, seg_end, target, max_chunk, warnings
            ):
                spans.append({"start": cs, "end": ce, "passthrough": False})

    if fn_start is not None:
        spans.append({"start": fn_start, "end": len(text), "passthrough": True})

    # 후검: 크기 상한 / 말미 헤딩 (본문이 헤딩으로 끝나는 퇴화 문서만 해당).
    for i, sp in enumerate(spans, 1):
        size = sp["end"] - sp["start"]
        if not sp["passthrough"] and size > max_chunk:
            warnings.append(f"청크 {i} 크기 {size}자 — 상한({max_chunk}) 초과")
        if not sp["passthrough"] and _ends_with_heading(
            text, sp["start"], sp["end"]
        ):
            warnings.append(
                f"청크 {i}가 헤딩으로 끝남 — 뒤따르는 본문이 없는 문서 말미 헤딩"
            )

    # 최상위 불변식 self-check: 한 글자라도 어긋나면 fidelity 사고로 중단.
    joined = "".join(text[sp["start"] : sp["end"]] for sp in spans)
    if joined != text:
        raise ChunkingError(
            "lossless self-check failed: 청크 연결 결과가 원문과 불일치 "
            f"(원문 {len(text)}자, 연결 {len(joined)}자)"
        )
    return spans, warnings


def _render_chunk_header(index: int, total: int, starts_with_heading: bool) -> str:
    lines = [
        f"[청크 컨텍스트] 이 텍스트는 한 문서를 나눈 청크 {index}/{total}이다.",
        "- 문서 전체가 아니므로 서두·결말·전환 문구를 새로 만들지 말 것. "
        "경계가 잘린 듯 보여도 그대로 둔다.",
    ]
    if starts_with_heading:
        lines.append(
            "- 첫 줄은 제목/헤딩이다. 번호·기호·형식을 그대로 보존하고 "
            "본문 문장과 병합하지 말 것."
        )
    lines.append("")
    return "\n".join(lines)


def run_chunk_mode(args: argparse.Namespace, diagnosis: str | None) -> int:
    run_dir = _resolve_run_dir(args.run_dir, args.text)
    input_path = run_dir / "01_input.txt"
    if args.text is not None:
        input_path.write_text(args.text, encoding="utf-8")
    if not input_path.exists():
        raise SystemExit(f"01_input.txt not found in {run_dir}; pass --text to create")
    text = input_path.read_text(encoding="utf-8")
    if not text.strip():
        raise SystemExit("01_input.txt is empty; nothing to chunk")

    spans, warnings = compute_chunk_spans(text)

    # 전문(全文) 기준 route_hint — 청킹 경로가 애초에 적절했는지 manifest 에
    # 남긴다. 판정 실패는 청킹을 막지 않는다 (graceful degrade).
    route: dict | None = None
    if _metrics_mod is not None:
        try:
            full_metrics = _metrics_mod.compute_all(
                text, genre=args.genre, baseline_path=args.baseline
            )
            route = compute_route_hint(full_metrics)
        except Exception:  # noqa: BLE001 — 권고 산출 실패는 치명 아님.
            route = None
    if len(text) <= CHUNK_RECOMMEND_MIN_CHARS:
        warnings.append(
            f"입력 {len(text):,}자 ≤ 청킹 권장 최소 {CHUNK_RECOMMEND_MIN_CHARS:,}자 "
            f"— 단일 콜 실증 범위라 --chunk 비권장 (권고, route_hint 참조)"
        )

    # 재청킹은 이전 청크 산출물(경계가 달라진 02_* 윤문 결과 포함)을 무효화한다.
    # 낡은 파일이 재조립에 잘못 섞이는 사고를 막기 위해 지우고 시작한다.
    removed: list[str] = []
    for pattern in (
        "00_chunk_*",
        "01_chunk_*",
        "02_chunk_*_rewritten.txt",
        "03_reassembled.md",
        "03_reassembly_report.json",
    ):
        for stale in sorted(run_dir.glob(pattern)):
            stale.unlink()
            removed.append(stale.name)

    total = len(spans)
    entries: list[dict] = []
    degraded = 0
    for i, sp in enumerate(spans, 1):
        chunk_text = text[sp["start"] : sp["end"]]
        first_line = chunk_text.lstrip("\n").split("\n", 1)[0]
        starts_with_heading = not sp["passthrough"] and bool(
            HEADING_LINE_RE.match(first_line)
        )
        entry = {
            "index": i,
            "start": sp["start"],
            "end": sp["end"],
            "char_count": sp["end"] - sp["start"],
            "starts_with_heading": starts_with_heading,
            "heading": first_line.strip() if starts_with_heading else None,
            "passthrough": sp["passthrough"],
            "input_file": None,
            "rewritten_file": None,
        }
        if not sp["passthrough"]:
            entry["input_file"] = f"01_chunk_{i:02d}_input_with_metrics.txt"
            entry["rewritten_file"] = f"02_chunk_{i:02d}_rewritten.txt"

            metrics_obj: dict | None = None
            metrics_path = run_dir / f"00_chunk_{i:02d}_metrics.json"
            error_path = run_dir / f"00_chunk_{i:02d}_metrics.error"
            if _metrics_mod is None:
                error_path.write_text(
                    "metrics module import failed; chunk emitted without score block",
                    encoding="utf-8",
                )
                degraded += 1
            else:
                try:
                    metrics_obj = _metrics_mod.compute_all(
                        chunk_text, genre=args.genre, baseline_path=args.baseline
                    )
                    metrics_path.write_text(
                        json.dumps(metrics_obj, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                except Exception as exc:  # noqa: BLE001 — graceful degrade.
                    metrics_obj = None
                    degraded += 1
                    error_path.write_text(
                        f"metrics_failed: {type(exc).__name__}: {exc}\n\n"
                        + traceback.format_exc(),
                        encoding="utf-8",
                    )
            combined = _render_chunk_header(
                i, total, starts_with_heading
            ) + _render_combined(chunk_text, metrics_obj, diagnosis=diagnosis)
            (run_dir / entry["input_file"]).write_text(combined, encoding="utf-8")
        entries.append(entry)

    manifest = {
        "version": 1,
        "created": date.today().isoformat(),
        "source_file": "01_input.txt",
        "source_chars": len(text),
        "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "genre": args.genre,
        "target_chunk_chars": TARGET_CHUNK_CHARS,
        "max_chunk_chars": MAX_CHUNK_CHARS,
        "route_hint": route["route_hint"] if route else None,
        "route_reason": route["route_reason"] if route else None,
        "chunk_count": total,
        "body_chunk_count": sum(1 for e in entries if not e["passthrough"]),
        "passthrough_chunk_count": sum(1 for e in entries if e["passthrough"]),
        "lossless_check": "ok",
        "warnings": warnings,
        "chunks": entries,
    }
    manifest_path = run_dir / "chunk_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    sizes = [e["char_count"] for e in entries]
    print(
        f"run_dir={run_dir}\n"
        f"manifest={manifest_path}\n"
        f"chunks={total} (body {manifest['body_chunk_count']} + "
        f"passthrough {manifest['passthrough_chunk_count']})\n"
        f"sizes={sizes}\n"
        f"route_hint={manifest['route_hint']}\n"
        f"metrics_degraded_chunks={degraded}\n"
        f"stale_removed={len(removed)}\n"
        f"warnings={len(warnings)}"
    )
    for w in warnings:
        print(f"WARNING: {w}")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Humanize KR v2.0 monolith input shim")
    p.add_argument("--run-dir", help="Existing run directory (relative ok)")
    p.add_argument("--text", help="Inline text input (creates new run dir)")
    p.add_argument("--genre", default="essay", help="Genre hint (default: essay)")
    p.add_argument(
        "--baseline",
        default=None,
        help="Override baseline JSON path (default: project default)",
    )
    p.add_argument(
        "--diagnosis",
        default=None,
        help="Path to a diagnosis text file; prepended before the metrics "
        "block (정밀 3콜 구조의 진단 1콜 산출물). Omit for legacy behaviour.",
    )
    p.add_argument(
        "--chunk",
        action="store_true",
        help="장문 청킹 모드: 01_input.txt 를 손실 없이 분할해 청크별 "
        "input_with_metrics 파일과 chunk_manifest.json 을 만든다.",
    )
    args = p.parse_args(argv)

    diagnosis: str | None = None
    if args.diagnosis:
        diag_path = Path(args.diagnosis)
        if not diag_path.is_absolute():
            diag_path = PROJECT_ROOT / diag_path
        if not diag_path.exists():
            raise SystemExit(f"--diagnosis file not found: {diag_path}")
        diagnosis = diag_path.read_text(encoding="utf-8")

    if args.chunk:
        return run_chunk_mode(args, diagnosis)

    run_dir = _resolve_run_dir(args.run_dir, args.text)
    input_path = run_dir / "01_input.txt"

    # Ensure 01_input.txt exists.
    if args.text is not None:
        input_path.write_text(args.text, encoding="utf-8")
    if not input_path.exists():
        raise SystemExit(f"01_input.txt not found in {run_dir}; pass --text to create")

    text = input_path.read_text(encoding="utf-8")

    metrics_obj: dict | None = None
    metrics_path = run_dir / "00_metrics.json"
    error_path = run_dir / "00_metrics.error"

    if _metrics_mod is None:
        error_path.write_text(
            "metrics module import failed; combined file emitted without score block",
            encoding="utf-8",
        )
    else:
        try:
            metrics_obj = _metrics_mod.compute_all(
                text, genre=args.genre, baseline_path=args.baseline
            )
            metrics_obj.update(compute_route_hint(metrics_obj))
            metrics_path.write_text(
                json.dumps(metrics_obj, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            # On success any stale error file is cleared.
            if error_path.exists():
                try:
                    error_path.unlink()
                except OSError:
                    pass
        except Exception as exc:  # noqa: BLE001 — graceful degrade is the point.
            metrics_obj = None
            error_path.write_text(
                f"metrics_failed: {type(exc).__name__}: {exc}\n\n"
                + traceback.format_exc(),
                encoding="utf-8",
            )

    combined_path = run_dir / "01_input_with_metrics.txt"
    combined_path.write_text(
        _render_combined(text, metrics_obj, diagnosis=diagnosis), encoding="utf-8"
    )

    rb = (metrics_obj or {}).get("risk_band", "absent")
    rs = (metrics_obj or {}).get("risk_score", "absent")
    rh = (metrics_obj or {}).get("route_hint", "absent")
    print(
        f"run_dir={run_dir}\n"
        f"combined={combined_path}\n"
        f"risk_band={rb}  risk_score={rs}\n"
        f"route_hint={rh}\n"
        f"degraded={metrics_obj is None}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
