#!/usr/bin/env python3
"""두 기준선 스냅샷을 대조해 '실제 변화'만 골라낸다.

왜 필요한가
-----------
윤문은 비결정적이라 두 번 돌리면 지표가 항상 조금씩 다르다. 그 흔들림을
변화로 착각하면 없는 회귀를 쫓게 된다(= n=1 룰렛). 그래서 이 도구는
**각 스냅샷이 K회 반복으로 스스로 잰 표준편차를 잡음 바닥**으로 삼고,
그 바닥을 넘는 차이만 유의하다고 표시한다.

판정 규칙
---------
  pooled = sqrt((sd_a^2 + sd_b^2) / 2)        # 두 스냅샷의 잡음을 합친 바닥
  delta  = mean_b - mean_a
  - pooled == 0 이고 delta == 0   → 동일
  - pooled == 0 이고 delta != 0   → 판정 불가 (K=1 이었다는 뜻. 다시 재라)
  - |delta| <= threshold * pooled → 잡음 범위
  - 그 외                          → 유의 (▲/▼)

threshold 기본 2.0 (대략 2 표준편차). 표본이 작으므로 이건 통계적 검정이
아니라 **보수적 눈금**이다. 유의 표시가 떠도 곧장 결론이 아니라 재촬영·
표본 증가의 신호로 읽어야 한다.

사용
----
  python3 scripts/eval_compare.py 이전.json 이후.json
  python3 scripts/eval_compare.py a.json b.json --threshold 3 --json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

# 지표별 "좋은 방향". 비교 결과에 개선/악화를 붙이기 위한 것.
#  None = 방향 판단 없음(맥락 의존).
BETTER = {
    "change_rate": None,  # 높다고 좋지도 낮다고 좋지도 않다 — 과윤문/무윤문 양방향 위험
    "len_ratio": None,
    "sig_conclusion_pivot_count_out": "lower",
    "sig_safe_balance_count_out": "lower",
    "sig_double_passive_count_out": "lower",
    "sig_by_passive_count_out": "lower",
    "sig_have_make_literal_count_out": "lower",
    "sig_double_particle_count_out": "lower",
}

RATE_KEYS = ["protected_ok_rate", "register_preserved_rate"]


def load(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        sys.exit(f"스냅샷을 찾을 수 없습니다: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def verdict(delta: float, pooled: float, threshold: float) -> str:
    if pooled == 0:
        return "동일" if abs(delta) < 1e-9 else "판정불가"
    if abs(delta) <= threshold * pooled:
        return "잡음"
    return "유의"


def compare_metric(a: dict, b: dict, key: str, threshold: float) -> dict | None:
    ma, mb = a.get(key), b.get(key)
    if not isinstance(ma, dict) or not isinstance(mb, dict):
        return None
    delta = mb["mean"] - ma["mean"]
    pooled = math.sqrt((ma["stdev"] ** 2 + mb["stdev"] ** 2) / 2)
    v = verdict(delta, pooled, threshold)
    direction = ""
    if v == "유의":
        good = BETTER.get(key)
        if good == "lower":
            direction = "개선" if delta < 0 else "악화"
        elif good == "higher":
            direction = "개선" if delta > 0 else "악화"
    return {
        "metric": key,
        "before": ma["mean"],
        "after": mb["mean"],
        "delta": round(delta, 4),
        "noise_floor": round(pooled, 4),
        "verdict": v,
        "direction": direction,
        "n_before": ma.get("n"),
        "n_after": mb.get("n"),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="기준선 스냅샷 2개 대조")
    p.add_argument("before", help="이전 스냅샷 JSON")
    p.add_argument("after", help="이후 스냅샷 JSON")
    p.add_argument("--threshold", type=float, default=2.0, help="잡음 바닥 배수 (기본 2.0)")
    p.add_argument("--json", action="store_true", help="JSON 으로 출력")
    a = p.parse_args(argv)

    sa, sb = load(a.before), load(a.after)

    print(f"이전: {sa.get('label')} @ {sa.get('captured_at')} (commit {sa.get('git_commit')}, K={sa.get('k')})")
    print(f"이후: {sb.get('label')} @ {sb.get('captured_at')} (commit {sb.get('git_commit')}, K={sb.get('k')})")

    if sa.get("k", 0) < 2 or sb.get("k", 0) < 2:
        print(
            "\n경고: 한쪽 이상이 K<2 입니다. 잡음 바닥을 못 재므로 대부분 '판정불가'가 됩니다.",
            file=sys.stderr,
        )

    rows: list[dict] = []
    models = [m for m in sb.get("models", []) if m in sa.get("aggregates", {})]
    if not models:
        print("\n두 스냅샷에 공통 모델이 없습니다.", file=sys.stderr)
        return 2

    for model in models:
        for fxid, agg_b in sb["aggregates"].get(model, {}).items():
            agg_a = sa["aggregates"].get(model, {}).get(fxid)
            if not agg_a:
                continue
            for key in sb.get("signal_names", []):
                r = compare_metric(agg_a, agg_b, f"sig_{key}_out", a.threshold)
                if r:
                    rows.append({"model": model, "fixture": fxid, **r})
            for key in ("change_rate", "len_ratio"):
                r = compare_metric(agg_a, agg_b, key, a.threshold)
                if r:
                    rows.append({"model": model, "fixture": fxid, **r})
            # 불변식 비율은 잡음 개념이 없다 — 떨어지면 그 자체로 사고
            for key in RATE_KEYS:
                va, vb = agg_a.get(key), agg_b.get(key)
                if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and vb < va:
                    rows.append(
                        {
                            "model": model,
                            "fixture": fxid,
                            "metric": key,
                            "before": va,
                            "after": vb,
                            "delta": round(vb - va, 4),
                            "noise_floor": 0.0,
                            "verdict": "불변식하락",
                            "direction": "악화",
                        }
                    )

    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    sig = [r for r in rows if r["verdict"] in ("유의", "불변식하락")]
    unknown = [r for r in rows if r["verdict"] == "판정불가"]

    print(f"\n비교 지표 {len(rows)}건 — 유의 {len(sig)} · 판정불가 {len(unknown)} · 나머지 잡음/동일")

    if sig:
        print("\n── 유의한 변화 ──")
        w = max(len(r["metric"]) for r in sig)
        for r in sorted(sig, key=lambda x: -abs(x["delta"])):
            arrow = "▲" if r["delta"] > 0 else "▼"
            tag = f" [{r['direction']}]" if r["direction"] else ""
            print(
                f"  {arrow} {r['model']:18s} {r['fixture']:28s} {r['metric']:{w}s} "
                f"{r['before']} → {r['after']} (Δ{r['delta']:+}, 잡음바닥 {r['noise_floor']}){tag}"
            )
    else:
        print("\n유의한 변화 없음 — 두 스냅샷은 잡음 범위 안에서 같습니다.")

    if unknown:
        print(f"\n판정불가 {len(unknown)}건 — K를 늘려 다시 재세요.")

    print(
        "\n주의: 이건 통계적 검정이 아니라 보수적 눈금입니다. 유의 표시는 결론이 아니라 "
        "재촬영·표본 증가의 신호로 읽으세요."
    )
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
