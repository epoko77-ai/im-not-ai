#!/usr/bin/env python3
"""장문 셀 — 규칙이 걸리는 빈도가 길이에 비례하는가.

**왜 필요한가.** 효능 측정에서 스킬의 변경률 중앙값이 0.5% 였다. 원인의 절반은
근거가 적은 것이고, 나머지 절반은 **표본이 짧은 것**일 수 있다. 300단어 발췌에서는
AI 글의 **50% 만 tricolon 이 있고 42% 만 분사절이 있다** — 규칙이 걸릴 자리 자체가
없는 글이 절반이다.

이 셀은 그 가설을 잰다: 길이를 1,000단어급으로 늘리면 글당 규칙 적중률이 오르는가.
오르면 "편집량이 작다"는 결론은 **발췌 길이의 산물**이고, 안 오르면 근거 부족이
유일한 원인이다.

⚠️ 본문은 커밋하지 않는다. 파생 통계만 `lang/en/baseline.json` 에 남긴다.

사용:
    python3 scripts/build_en_long_cell.py --fetch-human 40
    python3 scripts/build_en_long_cell.py --gen-ai 12
    python3 scripts/build_en_long_cell.py --report
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import statistics
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_base = _sibling("build_en_baseline")
_r2 = _sibling("build_en_blog_r2")

_WORK = os.path.join(_ROOT, "_workspace", "en_blog_long")
_OUT = os.path.join(_ROOT, "lang", "en", "baseline.json")
_LONG_WORDS = 1000        # 목표 길이 — R2 발췌(300)의 3배 이상
_MIN_LONG_WORDS = 700     # 이보다 짧으면 장문 셀에 넣지 않는다
_WORKERS = 3

# 규칙 적중률을 볼 지표. 승격된 둘 + EN-1.
_RULES = ("tricolon", "en1_participial")


def fetch_human(n: int) -> list[dict]:
    """R2 와 같은 3출처에서, **자르지 않고** 받는다."""
    rows: list[dict] = []
    for name, fn, share in (("lw", _r2.fetch_lw, 0.4), ("pg", _r2.fetch_pg, 0.3),
                            ("ssc", _r2.fetch_ssc, 0.3)):
        # R2 캐시는 발췌본이라 쓸 수 없다 — 같은 수집 함수로 다시 받는다.
        rows += fn(round(n * share))
    out = []
    for r in rows:
        # R2 fetch_* 는 발췌를 넣어 준다. 장문 셀은 원문 길이가 필요하므로
        # 발췌 전 본문이 있는 건만 쓴다(`full` 키). 없으면 발췌라도 길이로 거른다.
        text = r.get("full") or r["text"]
        if len(text.split()) >= _MIN_LONG_WORDS:
            out.append({**r, "text": " ".join(text.split()[:_LONG_WORDS])})
    return out[:n]


def gen_ai(titles: list[str]) -> list[dict]:
    claude = _base._which_claude()
    workdir = tempfile.mkdtemp(prefix="humanize_long_")

    def one(title: str) -> dict | None:
        prompt = (
            f'Write an engaging blog post titled "{title}" for our website. '
            f"About {_LONG_WORDS} words. "
            f"Output the post between {_base._START} and {_base._END} and nothing else."
        )
        for _ in range(_base._GEN_MAX_TRIES):
            proc = subprocess.run(
                [claude, "--model", "claude-sonnet-5", "-p", prompt],
                capture_output=True, text=True, timeout=900,
                cwd=workdir, env=_base._clean_env(), stdin=subprocess.DEVNULL,
            )
            text = _base.extract_sentinel(proc.stdout)
            if text and len(text.split()) >= _MIN_LONG_WORDS and not _base.is_contaminated(text):
                return {"title": title, "text": " ".join(text.split()[:_LONG_WORDS]),
                        "model": "claude-sonnet-5"}
        print(f"포기: {title[:40]}", file=sys.stderr)
        return None

    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        return [r for r in pool.map(one, titles) if r]


def _incidence(rows: list[dict]) -> dict:
    """글당 규칙 적중률 — '규칙이 걸릴 자리가 있는 글'의 비율."""
    out = {}
    for rule in _RULES:
        hits = [_r2._metrics(r["text"], None)[rule] for r in rows]
        out[rule] = {
            "글당_적중률": round(sum(1 for h in hits if h > 0) / (len(rows) or 1), 3),
            "중앙값_per_1k": round(statistics.median(hits), 2) if hits else 0.0,
        }
    out["단어수_중앙"] = round(statistics.median(len(r["text"].split()) for r in rows)) if rows else 0
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="장문 셀 — 길이와 규칙 적중률")
    ap.add_argument("--fetch-human", type=int, metavar="N")
    ap.add_argument("--gen-ai", type=int, metavar="N")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)

    os.makedirs(_WORK, exist_ok=True)
    if args.fetch_human:
        rows = fetch_human(args.fetch_human)
        with open(os.path.join(_WORK, "human.json"), "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
        print(f"장문 인간 {len(rows)}편 · 중앙 {_incidence(rows)['단어수_중앙']}단어")
    if args.gen_ai:
        human = _r2._load(os.path.join(_WORK, "human.json"))
        if not human:
            raise SystemExit("먼저 --fetch-human 을 실행할 것")
        rows = gen_ai([r["title"] for r in human[: args.gen_ai]])
        with open(os.path.join(_WORK, "ai.json"), "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
        print(f"장문 AI {len(rows)}편")
    if args.report:
        human = _r2._load(os.path.join(_WORK, "human.json"))
        ai = _r2._load(os.path.join(_WORK, "ai.json"))
        short_ai = (_r2._load(os.path.join(_ROOT, "_workspace", "en_blog_r2", "ai.json"))
                    + _r2._load(os.path.join(_ROOT, "_workspace", "en_blog_r2", "ai_gpt.json")))
        cell = {
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "purpose": (
                "편집량이 작은 원인이 근거 부족인지 발췌 길이인지 가른다. "
                "300단어에서는 AI 글의 절반만 규칙이 걸린다."
            ),
            "human_n": len(human), "ai_n": len(ai),
            "장문_AI": _incidence(ai) if ai else None,
            "장문_인간": _incidence(human) if human else None,
            "단문_AI(R2 300단어)": _incidence(short_ai),
        }
        doc = json.load(open(_OUT, encoding="utf-8"))
        doc.setdefault("genres", {})["blog_long"] = cell
        with open(_OUT, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        print(json.dumps(cell, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
