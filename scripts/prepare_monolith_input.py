#!/usr/bin/env python3
"""Humanize KR v1.6 — monolith input shim.

Pre-processes user input by computing v1.6 quantitative metrics and
prepending the result to the text the monolith agent reads. The monolith
keeps its 4-tool-call cap (Read input + Read rules + Write final + Write
summary) because the metrics block is folded into the same input file.

Inputs:
  --run-dir DIR   existing run directory containing 01_input.txt
  --text STR      ad-hoc text; if --run-dir is omitted, a new run dir
                  `_workspace/<YYYY-MM-DD>-NNN/` is created and 01_input.txt
                  written.
  --genre STR     essay|column|report|blog|abstract|... (default: essay)

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
try:
    import metrics as _metrics_mod  # type: ignore
except Exception:  # pragma: no cover — module import itself failing.
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


def _render_block(metrics_obj: dict) -> str:
    m = metrics_obj.get("metrics", {})
    z = metrics_obj.get("z_scores", {})
    ev = metrics_obj.get("evidence", {})
    pivots = ev.get("conclusion_pivots") or []
    safe = ev.get("safe_balances") or []

    lines: list[str] = []
    lines.append("[정량 사전 점수 v1.6 / KatFish baseline]")
    lines.append(
        f"risk_band: {metrics_obj.get('risk_band', 'unknown')}  "
        f"(score {metrics_obj.get('risk_score', 0)})"
    )
    lines.append(f"genre: {metrics_obj.get('genre', 'essay')}")
    lines.append(f"char_count: {metrics_obj.get('char_count', 0)}")
    if metrics_obj.get("warning"):
        lines.append(f"warning: {metrics_obj['warning']}")
    lines.append("")
    lines.append("[지표]")

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
    lines.append("[근거 사용 가이드]")
    lines.append("- 위 점수는 *근거 보조*다. 단독 판정 금지(보고서 명시).")
    lines.append("- z>1.0 지표는 quick-rules.md S1·S2 패턴과 교차 확인 후 윤문할 것.")
    lines.append("- ending_comma_rate가 ★ S1 트리거인 경우 C-11(연결어미 뒤 쉼표) 우선 손질.")
    lines.append("- conclusion_pivot 매치 토큰은 D-1·H-1 처방 적용 대상.")
    lines.append("")
    return "\n".join(lines)


def _render_combined(text: str, metrics_obj: dict | None) -> str:
    parts: list[str] = []
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
    p = argparse.ArgumentParser(description="Humanize KR v1.6 monolith input shim")
    p.add_argument("--run-dir", help="Existing run directory (relative ok)")
    p.add_argument("--text", help="Inline text input (creates new run dir)")
    p.add_argument("--genre", default="essay", help="Genre hint (default: essay)")
    p.add_argument(
        "--baseline",
        default=None,
        help="Override baseline JSON path (default: project default)",
    )
    args = p.parse_args(argv)

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
    combined_path.write_text(_render_combined(text, metrics_obj), encoding="utf-8")

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
