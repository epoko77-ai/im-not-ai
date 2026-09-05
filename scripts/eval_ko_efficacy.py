#!/usr/bin/env python3
"""한국어 윤문 효능 측정 — 영어에서 역수입한 방법.

**한국어도 효능을 잰 적이 없다.** 81패턴·8장르 셀·golden 픽스처·live 테스트가
전부 "망가지지 않았나"와 "AI 글을 골라내는가"를 잰다. "고친 뒤 사람 글에
가까워졌는가"는 어디에도 없었다.

판정 기준은 `docs/2026-09-05-ko-efficacy-preregistration.md` 에 실행 전에 확정했다.
한국어가 유리한 점: **인간 baseline 이 이미 있어** z-score 로 직접 잰다.

사용:
    python3 scripts/eval_ko_efficacy.py --gen 12     # 입력 AI 초안 생성
    python3 scripts/eval_ko_efficacy.py --run        # 두 팔 윤문
    python3 scripts/eval_ko_efficacy.py --report
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
sys.path.insert(0, os.path.join(_ROOT, "skills", "humanize-korean", "references"))
sys.path.insert(0, os.path.join(_ROOT, "tests"))
sys.path.insert(0, _HERE)

import metrics_v2 as _m  # noqa: E402
import checks as _checks  # noqa: E402


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_base = _sibling("build_en_baseline")   # 센티넬·오염 필터·환경 격리

_WORK = os.path.join(_ROOT, "_workspace", "ko_efficacy")
_MODEL = "claude-sonnet-5"
_GENRE = "essay"
_WORKERS = 3

# 사전 등록: S1 후보 5종(verify_gates.py 와 같은 목록). |z| > 1.0 인 것만 판정 대상.
PRIMARY = (
    "comma_inclusion_rate", "comma_usage_rate", "ending_comma_rate",
    "comma_segment_length", "hanja_nominalizer_density",
)
Z_TARGET = 1.0     # 이 위였던 지표만 본다
SIG_P = 0.05

_TOPICS = [
    "재택근무가 팀 문화에 남긴 것", "구독 경제가 소비자에게 준 착시",
    "생성형 AI 도입이 실무에 미친 영향", "도시 재개발과 원주민 이주 문제",
    "기후 대응에서 지방정부의 역할", "플랫폼 노동자의 사회보험 사각지대",
    "학교 평가 제도가 만든 부작용", "공공 데이터 개방의 현재",
    "스타트업 투자 혹한기의 신호", "고령화가 지역 상권에 남긴 변화",
    "온라인 커뮤니티의 자정 능력", "전기차 보급 속도와 충전 인프라",
]


def _gen_one(claude: str, workdir: str, topic: str) -> dict | None:
    prompt = (
        f"'{topic}'를 주제로 한국어 칼럼을 800자 내외로 써라. "
        f"본문만 {_base._START} 와 {_base._END} 사이에 출력하고 다른 말은 하지 마라."
    )
    for _ in range(_base._GEN_MAX_TRIES):
        proc = subprocess.run(
            [claude, "--model", _MODEL, "-p", prompt],
            capture_output=True, text=True, timeout=600,
            cwd=workdir, env=_base._clean_env(), stdin=subprocess.DEVNULL,
        )
        text = _base.extract_sentinel(proc.stdout)
        if text and len(text) >= 400 and not _base.is_contaminated(text):
            return {"topic": topic, "text": text}
    print(f"포기: {topic}", file=sys.stderr)
    return None


def gen(n: int) -> None:
    claude = _base._which_claude()
    workdir = tempfile.mkdtemp(prefix="ko_eff_gen_")
    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        rows = [r for r in pool.map(lambda t: _gen_one(claude, workdir, t), _TOPICS[:n]) if r]
    _save("inputs.json", rows)
    print(f"입력 AI 초안 {len(rows)}편")


def _bare_one(claude: str, workdir: str, row: dict) -> dict | None:
    prompt = (
        "다음 글을 AI 티 없이 사람이 쓴 것처럼 자연스럽게 고쳐줘. "
        f"고친 본문만 {_base._START} 와 {_base._END} 사이에 출력해.\n\n" + row["text"]
    )
    for _ in range(_base._GEN_MAX_TRIES):
        proc = subprocess.run(
            [claude, "--model", _MODEL, "-p", prompt],
            capture_output=True, text=True, timeout=600,
            cwd=workdir, env=_base._clean_env(), stdin=subprocess.DEVNULL,
        )
        out = _base.extract_sentinel(proc.stdout)
        if out and len(out) >= 200 and not _base.is_contaminated(out):
            return {"topic": row["topic"], "arm": "bare", "before": row["text"], "after": out}
    return None


def run() -> None:
    """팔 A(스킬)·B(맨 프롬프트)를 돌린다. 이미 있는 건 건너뛴다."""
    import humanize_runner as hr  # noqa: PLC0415 — tests/ 의존을 늦게 건다

    rows = _load("inputs.json")
    if not rows:
        raise SystemExit("먼저 --gen 을 실행할 것")
    done = _load("pairs.json")
    have = {(r["topic"], r["arm"]) for r in done}
    claude = _base._which_claude()
    workdir = tempfile.mkdtemp(prefix="ko_eff_run_")

    def skill_one(row: dict) -> dict | None:
        try:
            out, _ = hr.run_humanize_pipeline(
                row["text"], skill="humanize-korean", model=_MODEL, timeout=1800
            )
        except Exception as exc:  # noqa: BLE001
            print(f"실패(skill): {type(exc).__name__} {str(exc)[:80]}", file=sys.stderr)
            return None
        return {"topic": row["topic"], "arm": "skill", "before": row["text"], "after": out}

    jobs = [(r, "skill") for r in rows if (r["topic"], "skill") not in have]
    jobs += [(r, "bare") for r in rows if (r["topic"], "bare") not in have]
    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        got = [
            r for r in pool.map(
                lambda j: skill_one(j[0]) if j[1] == "skill" else _bare_one(claude, workdir, j[0]),
                jobs,
            ) if r
        ]
    _save("pairs.json", done + got)
    print(f"윤문 신규 {len(got)}쌍 · 총 {len(done) + len(got)}쌍")


# ── 판정 ────────────────────────────────────────────────────────────────
def _z(text: str) -> dict:
    return _m.compute_all(text, genre=_GENRE).get("z_scores", {})


def _sign_test(better: int, worse: int) -> float:
    n = better + worse
    if n == 0:
        return 1.0
    k = min(better, worse)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n))


def _arm(pairs: list[dict]) -> dict:
    better = worse = 0
    targets = 0
    for p in pairs:
        zb, za = _z(p["before"]), _z(p["after"])
        for k in PRIMARY:
            b, a = zb.get(k), za.get(k)
            if b is None or a is None or abs(b) <= Z_TARGET:
                continue  # 이미 인간 범위면 고칠 이유가 없다
            targets += 1
            if abs(a) == abs(b):
                continue
            better += abs(a) < abs(b)
            worse += abs(a) > abs(b)
    fails = [len(_checks.run_checks(p["before"], p["after"])) for p in pairs]
    rates = [_m.change_rate(p["before"], p["after"]) for p in pairs]
    return {
        "n": len(pairs),
        "z_targets": targets,
        "better": better, "worse": worse,
        "p": round(_sign_test(better, worse), 5),
        "significant": _sign_test(better, worse) < SIG_P and better > worse,
        "checks_violations": sum(1 for f in fails if f),
        "change_rate": {
            "median": round(statistics.median(rates), 3) if rates else 0.0,
            "max": round(max(rates), 3) if rates else 0.0,
            "over_50pct": sum(1 for r in rates if r >= 0.5),
        },
    }


def _load(name: str) -> list[dict]:
    p = os.path.join(_WORK, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []


def _save(name: str, rows: list[dict]) -> None:
    os.makedirs(_WORK, exist_ok=True)
    with open(os.path.join(_WORK, name), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)


def report() -> dict:
    pairs = _load("pairs.json")
    if not pairs:
        raise SystemExit("먼저 --run 을 실행할 것")
    arms = {
        arm: _arm([p for p in pairs if p["arm"] == arm])
        for arm in ("skill", "bare")
        if any(p["arm"] == arm for p in pairs)
    }
    skill = arms.get("skill", {})
    bare = arms.get("bare", {})
    verdict = {
        "K1_이동": bool(skill.get("significant")),
        "K2_안전": skill.get("checks_violations", 1) == 0,
        "K3_과윤문_아님": skill.get("change_rate", {}).get("median", 1) < 0.30
        and skill.get("change_rate", {}).get("over_50pct", 1) == 0,
        "K4_대조군_우위": skill.get("checks_violations", 99)
        <= bare.get("checks_violations", 0),
    }
    verdict["효능_확인"] = all(verdict.values())
    doc = {
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "preregistration": "docs/2026-09-05-ko-efficacy-preregistration.md",
        "model": _MODEL, "genre": _GENRE,
        "arms": arms, "verdict": verdict,
    }
    _save("report.json", [doc])
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="한국어 윤문 효능 측정")
    ap.add_argument("--gen", type=int, metavar="N")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)
    if args.gen:
        gen(args.gen)
    if args.run:
        run()
    if args.report:
        print(json.dumps(report(), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
