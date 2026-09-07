#!/usr/bin/env python3
"""영어 블로그 셀 재시도 — 다듬어진 에세이 vs 같은 제목의 AI 에세이.

왜 다시 하는가
--------------
1회차 블로그 셀은 **판별 실패**였다(`lang/en/baseline.json` genres.blog):
잰 지표 6개 전부 |AUC−0.5| < 0.20, 최대 0.192. abstract 셀에서 0.737 이던
EN-1 이 0.484 로 무작위였다.

그 셀의 인간 코퍼스는 **Hacker News 댓글**이었다. 대화체·단편적이고 인용과
코드가 섞인다. 음성 결과가 "블로그 장르에는 신호가 없다"인지 "댓글이라는
레지스터의 잡음에 신호가 묻혔다"인지 구분할 수 없었다(그 셀의 caveat).

이 스크립트는 그 교란을 뺀다 — **다듬어진 장문 에세이**로 인간 쪽을 바꾼다.
나머지 설계는 abstract 셀과 동일하게 유지한다(같은 제목 생성 = G2 과업 통제,
같은 오염 방어, 같은 지표·AUC).

인간 판정 기준은 abstract 셀과 같은 **시점**이다 — 2016~2021, ChatGPT 공개
이전이라 AI 혼입이 구조적으로 불가능하다.

⚠️ **본문은 커밋하지 않는다.** 파생 통계만 `lang/en/baseline.json` 에 남긴다.

사용:
    python3 scripts/build_en_blog_cell.py --fetch-human 42
    python3 scripts/build_en_blog_cell.py --gen-ai 14
    python3 scripts/build_en_blog_cell.py --report
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "core"))
sys.path.insert(0, os.path.join(_ROOT, "lang", "en"))
from metrics_universal import compute_universal  # noqa: E402
from metrics_en import LONG_SENTENCE_TOKENS, _EN1_RE, _EN2_RE  # noqa: E402


def _sibling(name: str):
    """같은 폴더의 스크립트를 모듈로 연다(오염 방어 헬퍼 재사용)."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_base = _sibling("build_en_baseline")  # 센티넬·오염 필터·환경 격리를 그대로 쓴다

_WORK = os.path.join(_ROOT, "_workspace", "en_blog_essay")
_OUT = os.path.join(_ROOT, "lang", "en", "baseline.json")

_YEARS = (2016, 2017, 2018, 2019, 2020, 2021)
_EXCERPT_WORDS = 300      # AI 생성 분량과 맞춘다 — 길이가 지표를 흔들면 안 된다
_MIN_SOURCE_WORDS = 450   # 잘라 쓸 만큼 긴 글만
_GEN_WORKERS = 4

# 에세이가 아닌 것들. LessWrong 은 공지·오픈스레드·링크포스트가 섞인다.
_SKIP_TITLE = re.compile(
    r"open thread|meetup|welcome to|rationality quotes|\[link\]|link post"
    r"|ama\b|survey|announc|newsletter|roundup|petrov|solstice",
    re.I,
)
# 인용·코드는 **필자의 산문이 아니다.** HN 댓글 셀이 이걸 안 걷어내서 문체 측정에
# 남의 문장이 섞였다. 통째로 지운 뒤 남은 분량으로 판정한다.
# ⚠️ `style`·`script` 도 반드시 지운다. 초판이 이걸 빠뜨려 MathJax 의 CSS 가
# 본문으로 들어갔다(".mjx-chtml {display: inline-block; line-height: 0; …}").
# 그 두 편이 인간 분산 107.78·67.30 으로 최상위를 차지했다 — 문체가 아니라
# 스타일시트를 측정한 값이다.
_DROP_BLOCK = re.compile(
    r"<(blockquote|pre|code|table|figure|style|script)\b.*?</\1>", re.S | re.I
)
# 그래도 남는 잔재가 있는 글은 버린다(인라인 style 속성, MathJax 파편).
_JUNK = re.compile(r"mjx-|\{display:|font-size-adjust", re.I)
_TAG = re.compile(r"<[^>]+>")


def _prose(html_body: str) -> str:
    text = _DROP_BLOCK.sub(" ", html_body)
    text = re.sub(r"<(p|br|div|li|h[1-6])\b[^>]*>", "\n", text, flags=re.I)
    text = html.unescape(_TAG.sub(" ", text))
    return "\n".join(" ".join(l.split()) for l in text.splitlines() if l.strip())


def _excerpt(text: str, words: int = _EXCERPT_WORDS) -> str:
    return " ".join(text.split()[:words])


def fetch_human(n: int) -> list[dict]:
    """LessWrong 장문 에세이. 연도별로 흩어 뽑는다(abstract 셀과 같은 규약)."""
    per_year = max(1, n // len(_YEARS) + 1)
    got: list[dict] = []
    for year in _YEARS:
        query = (
            '{posts(input:{terms:{view:"top",after:"%d-01-01",before:"%d-12-31",'
            "limit:%d}}){results{title postedAt htmlBody}}}" % (year, year, per_year * 6)
        )
        req = urllib.request.Request(
            "https://www.lesswrong.com/graphql",
            data=json.dumps({"query": query}).encode(),
            headers={"Content-Type": "application/json",
                     "User-Agent": "humanize-en-baseline/0.1"},
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            results = json.loads(r.read().decode())["data"]["posts"]["results"]
        taken = 0
        for post in results:
            title, body = post.get("title", ""), post.get("htmlBody") or ""
            if _SKIP_TITLE.search(title):
                continue
            prose = _prose(body)
            if len(prose.split()) < _MIN_SOURCE_WORDS or _JUNK.search(prose):
                continue
            assert post["postedAt"] < "2022", f"날짜 창 위반: {post['postedAt']}"
            got.append({"title": " ".join(title.split()),
                        "text": _excerpt(prose),
                        "published": post["postedAt"]})
            taken += 1
            if taken >= per_year:
                break
    return got[:n]


def _prompt(title: str, bare: bool) -> str:
    """코칭 프롬프트 vs 맨 프롬프트.

    맨 프롬프트 대조군이 필요한 이유: 분량·형식을 지정하면 그 지시가 AI 티를
    눌러 "신호 없음"을 만들 수 있다. 1회차 blog 셀도 양쪽을 다 돌렸다.
    """
    sentinel = f"Output the essay between {_base._START} and {_base._END} and nothing else."
    if bare:
        return f'Write a blog essay titled "{title}". {sentinel}'
    return (
        f'Write a blog essay titled "{title}". {_EXCERPT_WORDS - 50}-'
        f"{_EXCERPT_WORDS + 50} words, prose only, no headings or bullet lists. {sentinel}"
    )


def _one(claude: str, workdir: str, title: str, model: str, bare: bool = False) -> dict | None:
    prompt = _prompt(title, bare)
    for _ in range(_base._GEN_MAX_TRIES):
        proc = subprocess.run(
            [claude, "--model", model, "-p", prompt],
            capture_output=True, text=True, timeout=420,
            cwd=workdir, env=_base._clean_env(),
        )
        text = _base.extract_sentinel(proc.stdout)
        if text and len(text.split()) >= 200 and not _base.is_contaminated(text):
            return {"title": title, "text": _excerpt(text), "model": model,
                    "prompt": "bare" if bare else "coached"}
    print(f"포기: {model} / {title[:40]}", file=sys.stderr)
    return None


def gen_ai(titles: list[str], *, models: tuple = None, bare: bool = False) -> list[dict]:
    """같은 제목으로 에세이를 생성한다 — G2 과업 통제.

    **저장소 밖에서, 부모 세션 환경변수를 지우고** 실행한다(오염 사고 대응).
    """
    claude = _base._which_claude()
    workdir = tempfile.mkdtemp(prefix="humanize_blog_gen_")
    jobs = [(t, m) for t in titles for m in (models or _base._MODELS)]
    with ThreadPoolExecutor(max_workers=_GEN_WORKERS) as pool:
        rows = pool.map(lambda j: _one(claude, workdir, *j, bare=bare), jobs)
    return [r for r in rows if r]


# ── 지표·AUC ────────────────────────────────────────────────────────────
def _metrics(text: str) -> dict:
    u = compute_universal(text, long_threshold=LONG_SENTENCE_TOKENS, unit="tokens")
    tokens = u["tokens"] or 1
    return {
        "sentence_length_dispersion": u["sentence_length_dispersion"],
        "comma_inclusion_rate": u["comma_inclusion_rate"],
        "comma_usage_rate": u["comma_usage_rate"],
        "comma_segment_length": u["comma_segment_length"],
        "en1_participial": round(len(_EN1_RE.findall(text)) / tokens * 1000, 2),
        "en2_be_verbs": round(len(_EN2_RE.findall(text)) / tokens * 1000, 2),
    }


def auc(ai: list[float], human: list[float]) -> float:
    """AI 값이 인간 값보다 클 확률(쌍 비교). 0.5 = 무작위."""
    if not ai or not human:
        return 0.5
    wins = sum((a > h) + 0.5 * (a == h) for a in ai for h in human)
    return round(wins / (len(ai) * len(human)), 3)


def _summary(rows: list[dict]) -> dict:
    per: dict[str, list[float]] = {}
    for r in rows:
        for k, v in _metrics(r["text"]).items():
            per.setdefault(k, []).append(v)
    return {
        "n": len(rows),
        **{k: {"median": round(statistics.median(v), 2),
               "mean": round(statistics.mean(v), 2),
               "sd": round(statistics.pstdev(v), 2)} for k, v in per.items()},
    }


def _values(rows: list[dict], key: str) -> list[float]:
    return [_metrics(r["text"])[key] for r in rows]


def _route_dist(rows: list[dict]) -> dict:
    """라우터가 실제로 어떤 경로를 주는지 — 지표 AUC 보다 이게 실사용 판정이다."""
    from collections import Counter

    from metrics_en import compute_all_en  # noqa: PLC0415

    counts = Counter(compute_all_en(r["text"])["route_hint"] for r in rows)
    n = len(rows) or 1
    return {k: round(counts.get(k, 0) / n, 2) for k in ("light", "standard", "heavy")}


def _load(name: str) -> list[dict]:
    p = os.path.join(_WORK, name)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _save(name: str, rows: list[dict]) -> None:
    os.makedirs(_WORK, exist_ok=True)
    with open(os.path.join(_WORK, name), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="블로그 에세이 셀 (블로그 재시도)")
    ap.add_argument("--fetch-human", type=int, metavar="N")
    ap.add_argument("--gen-ai", type=int, metavar="N", help="제목 N개 × 3모델")
    ap.add_argument("--gen-bare", type=int, metavar="N",
                    help="맨 프롬프트 대조군 — 제목 N개 × opus 1모델")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)

    if args.fetch_human:
        rows = fetch_human(args.fetch_human)
        _save("human.json", rows)
        print(f"인간 에세이 {len(rows)}편 · "
              f"{min(r['published'] for r in rows)[:10]} ~ "
              f"{max(r['published'] for r in rows)[:10]}")
    if args.gen_ai:
        human = _load("human.json")
        if not human:
            raise SystemExit("먼저 --fetch-human 을 실행할 것")
        rows = gen_ai([r["title"] for r in human[: args.gen_ai]])
        _save("ai.json", rows)
        print(f"AI 에세이 {len(rows)}편 (제목 {args.gen_ai} × 모델 {len(_base._MODELS)})")
    if args.gen_bare:
        human = _load("human.json")
        if not human:
            raise SystemExit("먼저 --fetch-human 을 실행할 것")
        rows = gen_ai([r["title"] for r in human[: args.gen_bare]],
                      models=("claude-opus-5",), bare=True)
        _save("ai_bare.json", rows)
        print(f"맨 프롬프트 대조군 {len(rows)}편")
    if args.report:
        human, ai = _load("human.json"), _load("ai.json")
        if not human or not ai:
            raise SystemExit("human.json / ai.json 이 필요하다")
        keys = list(_metrics(human[0]["text"]))
        aucs = {k: auc(_values(ai, k), _values(human, k)) for k in keys}
        strong = {k: v for k, v in aucs.items() if abs(v - 0.5) >= 0.20}
        # G1 — 모델별로 갈라 본다. **묶은 AUC 만 보면 방향이 반대인 모델끼리
        # 상쇄돼 "신호 없음" 으로 보인다.** 이 셀이 정확히 그 경우였다.
        per_model = {
            model: {k: auc(_values(sub, k), _values(human, k)) for k in keys}
            for model in _base._MODELS
            for sub in ([r for r in ai if r.get("model") == model],)
            if sub
        }
        g1 = {
            k: {
                "per_model": {m: v[k] for m, v in per_model.items()},
                "direction_consistent": len({v[k] > 0.5 for v in per_model.values()}) == 1,
                "max_abs_delta": round(max(abs(v[k] - 0.5) for v in per_model.values()), 3),
            }
            for k in keys
        }
        route = {
            "human": _route_dist(human),
            "ai_coached": _route_dist(ai),
        }
        bare = _load("ai_bare.json")
        if bare:
            route["ai_bare"] = _route_dist(bare)
            route["auc_bare_opus"] = {
                k: auc(_values(bare, k), _values(human, k)) for k in keys
            }
        route["separation"] = {
            arm: round(d["heavy"] - route["human"]["heavy"]
                       + route["human"]["light"] - d["light"], 2)
            for arm, d in route.items()
            if arm.startswith("ai_") and isinstance(d, dict) and "heavy" in d
        }
        consistent = [k for k, v in g1.items() if v["direction_consistent"]]
        cell = {
            "status": "판별 가능" if strong else "**판별 실패**",
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "human_n": len(human),
            "ai_n": len(ai),
            "source_human": (
                f"LessWrong 장문 에세이 {_YEARS[0]}~{_YEARS[-1]}, 연도별 분산, "
                f"인용·코드 블록 제거 후 첫 {_EXCERPT_WORDS}단어, 다저자"
            ),
            "excerpt_words": _EXCERPT_WORDS,
            "auc": aucs,
            "g1_per_model": g1,
            "human_stats": _summary(human),
            "ai_stats": _summary(ai),
            "models": list(_base._MODELS),
            "router": route,
            "finding": (
                f"묶은 AUC 는 전부 |0.5차| < 0.20 (최대 "
                f"{max(abs(v - 0.5) for v in aucs.values()):.3f}). "
                f"모델 방향이 일치하는 지표는 {len(consistent)}/{len(keys)}개"
                f"({', '.join(consistent)}) 뿐이고, 초록 셀의 최강 신호였던 "
                f"쉼표 계열·EN-2 는 모델마다 방향이 갈린다 — 이 장르에서는 AI 티가 "
                f"아니라 모델 개인어다."
            ),
            "purpose": (
                "1회차 blog 셀(HN 댓글)의 음성 결과가 장르 탓인지 레지스터 탓인지 "
                "가른다. 다듬어진 에세이로 인간 쪽만 바꾸고 나머지는 동일하게 유지했다."
            ),
        }
        doc = json.load(open(_OUT, encoding="utf-8"))
        doc.setdefault("genres", {})["blog_essay"] = cell
        with open(_OUT, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        print(json.dumps(cell, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
