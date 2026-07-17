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
import json
import os
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
    args = p.parse_args(argv)

    diagnosis: str | None = None
    if args.diagnosis:
        diag_path = Path(args.diagnosis)
        if not diag_path.is_absolute():
            diag_path = PROJECT_ROOT / diag_path
        if not diag_path.exists():
            raise SystemExit(f"--diagnosis file not found: {diag_path}")
        diagnosis = diag_path.read_text(encoding="utf-8")

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
    print(
        f"run_dir={run_dir}\n"
        f"combined={combined_path}\n"
        f"risk_band={rb}  risk_score={rs}\n"
        f"degraded={metrics_obj is None}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
