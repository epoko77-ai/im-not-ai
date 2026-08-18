#!/usr/bin/env python3
"""워터마크 이전 기준선 계측 — 한국어 윤문 품질 스냅샷.

왜 지금 찍는가
--------------
Anthropic 은 2026-08-11 텍스트 워터마킹(SynthID-Text) 도입을 발표했다.
적용 대상은 **2026-08-02 이후 출시 모델**이고, 그 이전 모델(Sonnet 5 = 6/30,
Opus 5 = 7/24)에는 "수개월에 걸쳐" 소급 적용한다고 밝혔다.

즉 지금 이 순간은 현행 모델이 아직 워터마킹 이전 상태인 마지막 구간이다.
소급 적용이 끝난 뒤에는 "워터마킹 때문에 한국어가 어색해졌는가"를 물어도
비교 대상이 없다. 그래서 지금 지문(fingerprint)을 떠 둔다.

이 도구가 하는 일 / 하지 않는 일
--------------------------------
하는 일: 고정된 픽스처 × 모델 × K회 반복으로 결정적 지표를 재고, 스냅샷 JSON 을
남긴다. 나중에 같은 명령을 다시 돌려 eval_compare.py 로 대조한다.

하지 않는 일: **오늘 워터마킹의 영향을 측정하지 못한다.** 오늘은 비교군이 없다.
이 스크립트는 측정 도구를 세워 두는 것이지, 오늘 답을 내는 게 아니다.
그 한계를 스냅샷 메타(`caveat`)에 박아 둔다.

핵심 규율: n=1 금지
-------------------
윤문은 비결정적이라 1회 실행 차이는 대부분 잡음이다. K회 반복의 표준편차를
'잡음 바닥'으로 함께 기록하고, eval_compare.py 는 그 바닥을 넘는 변화만
실제 변화로 판정한다.

사용
----
  python3 scripts/eval_baseline.py --models claude-sonnet-5,claude-opus-5 --k 3
  python3 scripts/eval_baseline.py --k 5 --out _workspace/baselines/pre-wm.json
  python3 scripts/eval_baseline.py --dry-run     # 호출 없이 계획만 출력
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT / "tests"))
sys.path.insert(0, str(_ROOT / "skills" / "humanize-korean" / "references"))

import humanize_asserts as ha  # noqa: E402
import humanize_runner as hr  # noqa: E402

try:
    import metrics as _metrics  # noqa: E402
except Exception:  # noqa: BLE001
    _metrics = None

FIXTURES_PATH = _ROOT / "tests" / "fixtures.json"

# 워터마킹 소급 적용 이전 상태를 남겨 둘 대상. 기본은 현행 주력 2종.
DEFAULT_MODELS = ["claude-sonnet-5", "claude-opus-5"]

# 각 픽스처에서 재는 결정적 신호. metrics.py 에 있는 이름만 쓴다.
SIGNAL_NAMES = [
    "conclusion_pivot_count",
    "safe_balance_count",
    "double_passive_count",
    "by_passive_count",
    "have_make_literal_count",
    "double_particle_count",
]


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _safe_signal(text: str, name: str) -> float | None:
    try:
        return ha.signal(text, name)
    except Exception:  # noqa: BLE001
        return None


def _risk(text: str, genre: str) -> dict:
    """metrics.compute_all 의 종합 점수 — 실패해도 계측 전체를 막지 않는다."""
    if _metrics is None:
        return {}
    try:
        r = _metrics.compute_all(text, genre=genre)
        return {
            "risk_score": r.get("risk_score"),
            "risk_band": r.get("risk_band"),
        }
    except Exception:  # noqa: BLE001
        return {}


def measure(src: str, out: str, fx: dict) -> dict:
    """원문·윤문본 한 쌍에서 결정적 지표를 뽑는다."""
    genre = fx.get("genre", "essay")
    m: dict = {
        "change_rate": round(ha.change_rate(src, out), 4),
        "len_src": len(src),
        "len_out": len(out),
        "len_ratio": round(len(out) / len(src), 4) if src else None,
        "missing_protected": ha.missing_protected_tokens(out, fx.get("protected_tokens", [])),
        "register_src": ha.register_of(src),
        "register_out": ha.register_of(out),
    }
    m["register_preserved"] = m["register_src"] == m["register_out"]
    for name in SIGNAL_NAMES:
        m[f"sig_{name}_src"] = _safe_signal(src, name)
        m[f"sig_{name}_out"] = _safe_signal(out, name)
    m.update({f"risk_out_{k}": v for k, v in _risk(out, genre).items()})
    return m


# 집계 대상 수치 지표 (문자열·리스트 지표는 별도 처리)
_NUMERIC = ["change_rate", "len_ratio"] + [f"sig_{n}_out" for n in SIGNAL_NAMES]


def aggregate(runs: list[dict]) -> dict:
    """K회 반복을 평균·표준편차로 요약. 표준편차 = 이 지표의 잡음 바닥."""
    ok = [r for r in runs if r.get("ok")]
    agg: dict = {"n_ok": len(ok), "n_fail": len(runs) - len(ok)}
    if not ok:
        return agg
    for key in _NUMERIC:
        vals = [r["metrics"].get(key) for r in ok]
        vals = [v for v in vals if isinstance(v, (int, float))]
        if not vals:
            continue
        agg[key] = {
            "mean": round(statistics.fmean(vals), 4),
            # 표본 1개면 stdev 계산 불가 → 0.0. 비교 시 잡음 바닥이 0이면
            # eval_compare 가 '판정 불가'로 처리한다.
            "stdev": round(statistics.stdev(vals), 4) if len(vals) > 1 else 0.0,
            "min": round(min(vals), 4),
            "max": round(max(vals), 4),
            "n": len(vals),
        }
    # 불변식 계열은 비율로
    agg["protected_ok_rate"] = round(
        sum(1 for r in ok if not r["metrics"]["missing_protected"]) / len(ok), 4
    )
    agg["register_preserved_rate"] = round(
        sum(1 for r in ok if r["metrics"]["register_preserved"]) / len(ok), 4
    )
    return agg


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="워터마크 이전 한국어 품질 기준선 계측")
    p.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help=f"쉼표 구분 모델 ID (기본: {','.join(DEFAULT_MODELS)})",
    )
    p.add_argument("--k", type=int, default=3, help="픽스처·모델당 반복 횟수 (기본 3, n=1 금지)")
    p.add_argument("--only", default="", help="쉼표 구분 픽스처 ID 부분 실행")
    p.add_argument("--strict", action="store_true", help="정밀(heavy) 경로로 실행")
    p.add_argument("--timeout", type=int, default=300, help="호출당 타임아웃 초")
    p.add_argument("--out", default="", help="스냅샷 저장 경로 (기본: _workspace/baselines/<날짜>.json)")
    p.add_argument("--label", default="pre-watermark", help="스냅샷 라벨")
    p.add_argument("--dry-run", action="store_true", help="호출 없이 실행 계획만 출력")
    a = p.parse_args(argv)

    if a.k < 2 and not a.dry_run:
        print("경고: --k 1 은 잡음 바닥을 못 재 비교가 불가능합니다. 2 이상 권장.", file=sys.stderr)

    fixtures = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))["fixtures"]
    only = {s.strip() for s in a.only.split(",") if s.strip()}
    if only:
        fixtures = [f for f in fixtures if f["id"] in only]
    if not fixtures:
        print("실행할 픽스처가 없습니다.", file=sys.stderr)
        return 2

    models = [m.strip() for m in a.models.split(",") if m.strip()]
    total = len(models) * len(fixtures) * a.k

    print(f"모델 {len(models)}종 × 픽스처 {len(fixtures)}개 × {a.k}회 = 총 {total}회 호출")
    print(f"모델: {', '.join(models)}")
    print(f"픽스처: {', '.join(f['id'] for f in fixtures)}")
    if a.dry_run:
        return 0
    if hr.CLAUDE_BIN is None:
        print("claude CLI 없음 — 계측 불가", file=sys.stderr)
        return 2

    records: list[dict] = []
    started = time.time()
    done = 0
    for model in models:
        for fx in fixtures:
            src = fx["input_text"]
            for i in range(a.k):
                done += 1
                t0 = time.time()
                rec: dict = {"model": model, "fixture": fx["id"], "run": i}
                try:
                    out = hr.run_humanize(
                        src, strict=a.strict, timeout=a.timeout, model=model
                    )
                    rec["ok"] = True
                    rec["metrics"] = measure(src, out, fx)
                    rec["output"] = out  # 나중에 사람이·LLM이 다시 볼 수 있게 원문 보존
                except Exception as exc:  # noqa: BLE001
                    rec["ok"] = False
                    rec["error"] = f"{type(exc).__name__}: {exc}"
                rec["elapsed_s"] = round(time.time() - t0, 1)
                records.append(rec)
                status = "ok" if rec["ok"] else "FAIL"
                print(
                    f"[{done}/{total}] {model} {fx['id']} #{i} {status} "
                    f"({rec['elapsed_s']}s)",
                    flush=True,
                )

    # ── 집계 ────────────────────────────────────────────────────────
    aggregates: dict = {}
    for model in models:
        aggregates[model] = {}
        for fx in fixtures:
            runs = [r for r in records if r["model"] == model and r["fixture"] == fx["id"]]
            aggregates[model][fx["id"]] = aggregate(runs)

    snapshot = {
        "label": a.label,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "k": a.k,
        "strict": a.strict,
        "models": models,
        "fixtures": [f["id"] for f in fixtures],
        "signal_names": SIGNAL_NAMES,
        "caveat": (
            "이 스냅샷은 워터마킹 '이전' 상태를 남겨 두기 위한 것이다. "
            "Sonnet 5(2026-06-30)·Opus 5(2026-07-24)는 워터마킹 기준일(2026-08-02) "
            "이전 출시라 촬영 시점에는 워터마크가 없었을 가능성이 높다. 다만 Anthropic 이 "
            "구형 모델에도 소급 적용 중이라고 밝혔으므로, 촬영 시점의 실제 적용 여부는 "
            "탐지 API 가 공개되기 전까지 확인할 수 없다. 따라서 이 스냅샷 하나로는 "
            "어떤 결론도 내릴 수 없고, 소급 적용 이후 재촬영본과 대조해야만 의미가 있다."
        ),
        "elapsed_total_s": round(time.time() - started, 1),
        "aggregates": aggregates,
        "records": records,
    }

    # 기본 저장 위치는 **git 이 추적하는** tests/baselines/ 다.
    # _workspace/ 는 .gitignore 대상이라, 몇 달 뒤 대조해야 할 스냅샷을 거기 두면
    # 이 기계에서만 존재하다 사라진다. 기준선은 레포에 남아야 의미가 있다.
    out_path = Path(a.out) if a.out else (
        _ROOT / "tests" / "baselines" / f"{datetime.now().strftime('%Y-%m-%d')}-{a.label}.json"
    )
    if not out_path.is_absolute():
        out_path = _ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    n_fail = sum(1 for r in records if not r["ok"])
    print(f"\n스냅샷 저장: {out_path}")
    print(f"성공 {len(records) - n_fail} / 실패 {n_fail} / 총 {len(records)}")
    print(f"소요 {snapshot['elapsed_total_s']}s")
    return 0


# ── 콘솔 하드닝 (#84) ───────────────────────────────────────────────
# Windows(cp949)에서 한글·em-dash 출력이 UnicodeEncodeError 로 죽는 것을 막는다.
import os as _os  # noqa: E402
import sys as _sys  # noqa: E402

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import console as _console  # noqa: E402

if __name__ == "__main__":
    _console.force_utf8_console()
    raise SystemExit(main())
