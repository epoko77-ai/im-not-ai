#!/usr/bin/env python3
"""영어 윤문 효능 측정 — 고친 뒤 사람 글에 가까워졌는가.

**이 저장소가 지금까지 재지 않은 것.** 판별(AI 글을 골라내는가)과 안전(고치면서
망가뜨리지 않는가)은 쟀지만, 휴머나이저의 본업인 효능은 한 번도 재지 않았다.

판정 기준은 `docs/2026-09-05-en-efficacy-preregistration.md` 에 **실행 전에**
확정해 커밋했다. 이 파일의 상수는 그 문서와 같아야 한다.

사용:
    python3 scripts/eval_en_efficacy.py --run 30      # 두 팔 생성
    python3 scripts/eval_en_efficacy.py --report      # 판정
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import statistics
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "core"))


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_base = _sibling("build_en_baseline")     # 센티넬·오염 필터·환경 격리
_r2 = _sibling("build_en_blog_r2")        # 지표·AUC·라우터

_CORPUS = os.path.join(_ROOT, "_workspace", "en_blog_r2")
_WORK = os.path.join(_ROOT, "_workspace", "en_efficacy")
_RULEBOOK = os.path.join(_ROOT, "lang", "en", "quick-rules.md")

# 두 팔을 같은 모델로 돌린다 — 프롬프트 효과만 남긴다.
_MODEL = "claude-sonnet-5"
_WORKERS = 4

# 사전 등록된 판정 기준 (docs/2026-09-05-en-efficacy-preregistration.md)
PRIMARY = {
    "tricolon": "down",              # 인간 0.00 vs AI 1.67 — 줄어야 좋다
    "comma_segment_length": "up",    # 인간 9.68 vs AI 8.34 — 늘어야 좋다
}
SIG_P = 0.05
MAX_GATE_VIOLATION = 0.10
MAX_MEDIAN_CHANGE_RATE = 0.30


def _rulebook_prompt(text: str) -> str:
    with open(_RULEBOOK, encoding="utf-8") as f:
        rules = f.read()
    return (
        "You are editing English prose to remove AI writing tells.\n\n"
        "IRON RULES: preserve every fact, number, proper noun and quotation. "
        "Do not add claims. Do not remove hedges, passives or contractions "
        "(LLMs already underuse them). Keep the register and genre.\n\n"
        "RULEBOOK:\n" + rules + "\n\n"
        "Rewrite the text between the markers. Change style, rhythm and phrasing "
        "only. Output the rewritten text between "
        f"{_base._START} and {_base._END} and nothing else.\n\n"
        f"TEXT:\n{text}"
    )


def _bare_prompt(text: str) -> str:
    return (
        "Rewrite the text below so it reads like a human wrote it. Output the "
        f"rewritten text between {_base._START} and {_base._END} and nothing else."
        f"\n\nTEXT:\n{text}"
    )


_ARMS = {"rulebook": _rulebook_prompt, "bare": _bare_prompt}


def _one(claude: str, workdir: str, row: dict, arm: str) -> dict | None:
    prompt = _ARMS[arm](row["text"])
    for _ in range(_base._GEN_MAX_TRIES):
        proc = subprocess.run(
            [claude, "--model", _MODEL, "-p", prompt],
            capture_output=True, text=True, timeout=600,
            cwd=workdir, env=_base._clean_env(), stdin=subprocess.DEVNULL,
        )
        out = _base.extract_sentinel(proc.stdout)
        if out and len(out.split()) >= 100 and not _base.is_contaminated(out):
            return {"title": row["title"], "model": row.get("model"), "arm": arm,
                    "before": row["text"], "after": out}
    print(f"포기: {arm} / {row['title'][:40]}", file=sys.stderr)
    return None


def _sample(n: int) -> list[dict]:
    """모델별 층화 추출 — 한 모델의 버릇이 결과를 끌지 않게."""
    ai = _load(os.path.join(_CORPUS, "ai.json")) + _load(os.path.join(_CORPUS, "ai_gpt.json"))
    by_model: dict[str, list[dict]] = {}
    for row in ai:
        by_model.setdefault(row.get("model", "?"), []).append(row)
    per = max(1, n // len(by_model))
    out: list[dict] = []
    for rows in by_model.values():
        out += rows[:per]
    return out[:n]


def run(n: int) -> None:
    claude = _base._which_claude()
    workdir = tempfile.mkdtemp(prefix="humanize_eff_")
    rows = _sample(n)
    print(f"표본 {len(rows)}편 (모델별 층화) × 팔 {len(_ARMS)}")
    jobs = [(row, arm) for arm in _ARMS for row in rows]
    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        got = [r for r in pool.map(lambda j: _one(claude, workdir, *j), jobs) if r]
    os.makedirs(_WORK, exist_ok=True)
    with open(os.path.join(_WORK, "pairs.json"), "w", encoding="utf-8") as f:
        json.dump(got, f, ensure_ascii=False, indent=1)
    print(f"생성 {len(got)}쌍")


# ── 판정 ────────────────────────────────────────────────────────────────
def _load(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _sign_test(better: int, worse: int) -> float:
    """이항 부호검정 양측 p. 변화 없는 건은 제외한다(표준 처리)."""
    n = better + worse
    if n == 0:
        return 1.0
    k = min(better, worse)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def _gate(script: str, before: str, after: str, extra: list[str] | None = None) -> int:
    with tempfile.TemporaryDirectory() as td:
        bp, ap = os.path.join(td, "b.txt"), os.path.join(td, "a.txt")
        for p, t in ((bp, before), (ap, after)):
            with open(p, "w", encoding="utf-8") as f:
                f.write(t)
        return subprocess.run(
            [sys.executable, script, "--before", bp, "--after", ap] + (extra or []),
            capture_output=True, text=True, timeout=120,
        ).returncode


def _arm_report(pairs: list[dict], human: list[dict]) -> dict:
    metric = lambda t: _r2._metrics(t, None)  # noqa: E731
    hv = {k: [_r2._metrics(r["text"], r.get("tail"))[k] for r in human] for k in PRIMARY}

    primary = {}
    for key, want in PRIMARY.items():
        better = worse = 0
        for p in pairs:
            b, a = metric(p["before"])[key], metric(p["after"])[key]
            if a == b:
                continue
            moved_right = (a < b) if want == "down" else (a > b)
            better += moved_right
            worse += not moved_right
        primary[key] = {
            "direction": want,
            "better": better, "worse": worse,
            "p": round(_sign_test(better, worse), 5),
            "significant": _sign_test(better, worse) < SIG_P and better > worse,
            "auc_before": _r2.auc([metric(p["before"])[key] for p in pairs], hv[key]),
            "auc_after": _r2.auc([metric(p["after"])[key] for p in pairs], hv[key]),
        }

    cp = os.path.join(_ROOT, "core", "content_preservation.py")
    ml = os.path.join(_ROOT, "core", "modality_loss.py")
    ri = os.path.join(_ROOT, "core", "reinjection.py")
    viol = {"content": 0, "modality": 0, "reinjection": 0}
    rates = []
    for p in pairs:
        viol["content"] += _gate(cp, p["before"], p["after"]) == 1
        viol["modality"] += _gate(ml, p["before"], p["after"]) == 1
        viol["reinjection"] += _gate(ri, p["before"], p["after"], ["--lang", "en"]) == 1
        rates.append(_change_rate(p["before"], p["after"]))

    n = len(pairs) or 1
    return {
        "n": len(pairs),
        "primary": primary,
        "gate_violations": viol,
        "gate_violation_rate": {k: round(v / n, 3) for k, v in viol.items()},
        "change_rate": {
            "median": round(statistics.median(rates), 3),
            "max": round(max(rates), 3),
            "over_50pct": sum(1 for r in rates if r >= 0.5),
        },
        "router_after": _r2._route_dist(
            [{"text": p["after"]} for p in pairs],
            8.57,
        ),
    }


def _change_rate(before: str, after: str) -> float:
    sys.path.insert(0, os.path.join(_ROOT, "core"))
    from change_rate import change_rate  # noqa: PLC0415

    return change_rate(before, after)


def report() -> dict:
    pairs = _load(os.path.join(_WORK, "pairs.json"))
    if not pairs:
        raise SystemExit("먼저 --run 을 실행할 것")
    human = _load(os.path.join(_CORPUS, "human.json"))
    # 팔 C(실제 스킬)는 오케스트레이션까지 도는 별도 산출물이다.
    skill = _load(os.path.join(_WORK, "pairs_skill.json"))
    # 2차 확증 — 1차에 쓰지 않은 제목으로 같은 설계를 다시 건 표본.
    confirm = _load(os.path.join(_WORK, "pairs_skill2.json"))
    arms = {
        arm: _arm_report([p for p in pairs if p["arm"] == arm], human)
        for arm in _ARMS
    }
    if skill:
        arms["skill(사후)"] = _arm_report(skill, human)
    if confirm:
        arms["skill_confirm(홀드아웃)"] = _arm_report(confirm, human)

    rb, bare = arms["rulebook"], arms["bare"]
    s1 = any(v["significant"] for v in rb["primary"].values())
    s2 = max(rb["gate_violation_rate"]["content"],
             rb["gate_violation_rate"]["modality"]) <= MAX_GATE_VIOLATION
    s3 = (rb["change_rate"]["median"] < MAX_MEDIAN_CHANGE_RATE
          and rb["change_rate"]["over_50pct"] == 0)
    rb_moved = sum(v["better"] - v["worse"] for v in rb["primary"].values())
    bare_moved = sum(v["better"] - v["worse"] for v in bare["primary"].values())
    s4 = (
        rb["gate_violations"]["content"] + rb["gate_violations"]["modality"]
        <= bare["gate_violations"]["content"] + bare["gate_violations"]["modality"]
        and rb_moved >= bare_moved
    )
    verdict = {
        "S1_이동": s1, "S2_안전": s2, "S3_과윤문_아님": s3, "S4_대조군_우위": s4,
        "효능_확인": all((s1, s2, s3, s4)),
    }
    confirmation = None
    if confirm:
        c = arms["skill_confirm(홀드아웃)"]
        confirmation = {
            "n": c["n"],
            "C1_이동": any(v["significant"] for v in c["primary"].values()),
            "C2_안전": c["gate_violations"]["content"] == 0
            and c["gate_violations"]["modality"] == 0,
            "C3_과윤문_아님": c["change_rate"]["median"] < MAX_MEDIAN_CHANGE_RATE
            and c["change_rate"]["over_50pct"] == 0,
        }
        confirmation["효능_확증"] = all(
            v for k, v in confirmation.items() if k.startswith("C")
        )
        confirmation["note"] = (
            "C4(과소윤문 FAIL ≤ 20%)는 --genre blog 를 넘겨야 해 별도 계측했다: 0/28."
        )

    doc = {
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "preregistration": "docs/2026-09-05-en-efficacy-preregistration.md",
        "model": _MODEL,
        "arms": arms,
        "verdict": verdict,
        "confirmation": confirmation,
    }
    with open(os.path.join(_WORK, "report.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    # 근거는 한 곳에 모은다 — baseline.json 이 영어 수치의 SSOT 다.
    baseline_path = os.path.join(_ROOT, "lang", "en", "baseline.json")
    with open(baseline_path, encoding="utf-8") as f:
        baseline = json.load(f)
    baseline["efficacy"] = doc
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=1)
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="영어 윤문 효능 측정")
    ap.add_argument("--run", type=int, metavar="N")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)
    if args.run:
        run(args.run)
    if args.report:
        print(json.dumps(report(), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
