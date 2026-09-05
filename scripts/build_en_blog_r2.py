#!/usr/bin/env python3
"""블로그 셀 3회차(R2) — 1·2회차 음성 결과를 네 방향에서 강화한 재실험.

1·2 회차 요약: HN 댓글(1회차)·LessWrong 에세이(2회차) 양쪽에서 판별 실패.
그러나 **부트스트랩 CI 를 내보니 6지표 중 4개는 "무효과"가 아니라 "표본 부족"**
이었다(예: 분산 AUC 0.312, CI [0.202, 0.423] — 우리 문턱 0.20 밖까지 뻗는다).
그래서 "블로그에는 신호가 없다"는 아직 확정할 수 없다.

R2 가 바꾸는 것 넷 (`lang/en/scholarship.md` 「블로그 셀 2회차」의 후속):

1. **후보 재심사** — 초록 심사에서 "판정 불가(장르)"로 유예됐던 blader 후보
   7건을 처음으로 잰다. 지금 재는 6지표는 전부 **통사 표면**인데 블로그 슬롭은
   **담화층**에 산다. 없는 곳을 뒤지고 있었을 가능성이 이 실험의 주 가설이다.
2. **과업 현실성** — 2회차 AI 팔은 두 겹으로 너무 깨끗했다. 사람이 공들여 쓴
   제목 + "prose only, no headings" 금지. R2 는 **실사용자 프롬프트**로 뽑는다.
3. **표본·출처** — 인간 100편, 3출처(LessWrong 다저자 · Paul Graham · SSC).
   2회차의 "LW 단일 커뮤니티" 교란을 뺀다.
4. **발췌 위치** — 도입부는 인간도 가장 정형적인 구간이다. 양쪽 다
   **본문 중간**(200~500단어)을 쓴다. 그래서 AI 도 700단어로 뽑는다.

판정도 강화한다: 점추정 대신 **부트스트랩 CI + 모델별 방향(G1)** 병기.
승격 기준 = |AUC−0.5| ≥ 0.20 **그리고** CI 가 0.5 를 포함하지 않고
**그리고** 3모델 방향 일치.

⚠️ 본문은 커밋하지 않는다. 파생 통계만 `lang/en/baseline.json` 에 남긴다.

사용:
    python3 scripts/build_en_blog_r2.py --fetch-human 100
    python3 scripts/build_en_blog_r2.py --gen-ai 34
    python3 scripts/build_en_blog_r2.py --report
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import re
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "core"))
sys.path.insert(0, os.path.join(_ROOT, "lang", "en"))
from metrics_universal import compute_universal  # noqa: E402
from metrics_en import (  # noqa: E402
    LONG_SENTENCE_TOKENS,
    _EN1_RE,
    _EN2_RE,
    _TRICOLON_RE,
)


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_r1 = _sibling("build_en_blog_cell")   # _prose·_JUNK·auc 재사용
_base = _r1._base                       # 센티넬·오염 필터·환경 격리

_WORK = os.path.join(_ROOT, "_workspace", "en_blog_r2")
_OUT = os.path.join(_ROOT, "lang", "en", "baseline.json")

# 발췌 창 — 도입부(0~200단어)를 버리고 본문 중간 300단어를 쓴다.
_SKIP_WORDS, _TAKE_WORDS = 200, 300
_MIN_SOURCE_WORDS = _SKIP_WORDS + _TAKE_WORDS + 50
_GEN_WORDS = 700
_GEN_WORKERS = 4
_UA = {"User-Agent": "Mozilla/5.0 humanize-en-baseline/0.2"}


def _excerpt(text: str) -> str:
    return " ".join(text.split()[_SKIP_WORDS : _SKIP_WORDS + _TAKE_WORDS])


# 결말 공식(#25)은 **위치가 본질**이라 발췌 구간에는 원리적으로 없다. 1·2회차에서
# 이 후보가 인간·AI 모두 0.00 이었던 건 패턴이 없어서가 아니라 **끝을 안 봤기 때문**
# 이다. 글의 마지막 60단어를 따로 실어 둔다.
_TAIL_WORDS = 60


def _tail(text: str) -> str:
    return " ".join(text.split()[-_TAIL_WORDS:])


def _get(url: str, timeout: int = 45, tries: int = 3) -> str:
    """단발 실패로 수집 전체가 죽지 않게 재시도한다.

    실측: LessWrong 40편을 다 받은 뒤 paulgraham.com 인덱스에서
    RemoteDisconnected 한 번에 앞의 수집이 통째로 날아갔다.
    """
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=_UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            time.sleep(2 + 3 * attempt)
    return ""


# 사이드바·아카이브 목록이 본문으로 새는 것을 잡는다("August 2016 July 2016 …").
_NAV_JUNK = re.compile(
    r"(?:January|February|March|April|May|June|July|August|September|October"
    r"|November|December)\s+20\d\d\s+(?:January|February|March|April|May|June"
    r"|July|August|September|October|November|December)\s+20\d\d"
)


def _ok(prose: str) -> bool:
    return (
        len(prose.split()) >= _MIN_SOURCE_WORDS
        and not _r1._JUNK.search(prose)
        and not _NAV_JUNK.search(prose)
    )


# ── 출처 1: LessWrong (다저자) ──────────────────────────────────────────
_LW_YEARS = (2016, 2017, 2018, 2019, 2020, 2021)


def _graphql(query: str, tries: int = 3) -> list[dict]:
    """LessWrong GraphQL. 연결 초기화가 잦아 재시도한다."""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                "https://www.lesswrong.com/graphql",
                data=json.dumps({"query": query}).encode(),
                headers={"Content-Type": "application/json", **_UA},
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())["data"]["posts"]["results"]
        except Exception:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            time.sleep(3)
    return []


def fetch_lw(n: int) -> list[dict]:
    per_year = max(1, n // len(_LW_YEARS) + 1)
    got: list[dict] = []
    for year in _LW_YEARS:
        query = (
            '{posts(input:{terms:{view:"top",after:"%d-01-01",before:"%d-12-31",'
            # limit 을 크게 잡으면 htmlBody 전문이 그만큼 딸려와 요청이 수분씩 걸리고
            # 연결이 끊긴다(실측: per_year*8 로 4편 받는 데 133초). 여유는 3배까지만.
            "limit:%d}}){results{title postedAt htmlBody}}}" % (year, year, per_year * 3)
        )
        results = _graphql(query)
        taken = 0
        for post in results:
            title, body = post.get("title", ""), post.get("htmlBody") or ""
            if _r1._SKIP_TITLE.search(title):
                continue
            prose = _r1._prose(body)
            if not _ok(prose):
                continue
            assert post["postedAt"] < "2022", f"날짜 창 위반: {post['postedAt']}"
            got.append({"title": " ".join(title.split()), "text": _excerpt(prose),
                        "tail": _tail(prose), "published": post["postedAt"][:10],
                        "source": "lesswrong"})
            taken += 1
            if taken >= per_year:
                break
    return got[:n]


# ── 출처 2: Paul Graham (에세이 원형) ───────────────────────────────────
_PG_DATE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October"
    r"|November|December)\s+((?:19|20)\d{2})\b"
)


def fetch_pg(n: int) -> list[dict]:
    idx = _get("https://paulgraham.com/articles.html")
    links = [l for l in dict.fromkeys(re.findall(r'<a href="([a-z0-9_]+\.html)"', idx))
             if l not in ("index.html", "articles.html", "rss.html")]
    got: list[dict] = []
    for slug in links:
        if len(got) >= n:
            break
        try:
            page = _get("https://paulgraham.com/" + slug, timeout=30)
        except Exception:  # noqa: BLE001 — 개별 페이지 실패는 건너뛴다
            continue
        prose = _r1._prose(page)
        date = _PG_DATE.search(prose[:400])
        if not date or date.group(1) >= "2022":
            continue
        title = re.sub(r"[-<>]{2,}", " ", prose[: date.start()])
        title = " ".join(title.split()) or slug
        body = prose[date.end():].strip()
        # PG 에세이는 "Thanks to A, B for reading drafts" 로 끝난다. 결말 공식(#25)을
        # 재려면 논증의 끝이 필요하지 감사문이 필요한 게 아니다.
        cut = body.rfind("Thanks to ")
        if cut > len(body) * 0.75:
            body = body[:cut].strip()
        if not _ok(body):
            continue
        got.append({"title": title, "text": _excerpt(body), "tail": _tail(body),
                    "published": date.group(0), "source": "paulgraham"})
        time.sleep(0.4)
    return got


# ── 출처 3: Slate Star Codex (장문 논증) ────────────────────────────────
_SSC_POST = re.compile(r'href="(https://slatestarcodex\.com/(20\d\d)/\d\d/\d\d/[^"]+/)"')
# 본문 컨테이너는 `pjgm-postcontent` 다. 초판이 워드프레스 기본값(`entry-content`)을
# 넣어 매치에 실패했고, **실패 시 페이지 전체로 폴백**해서 사이드바 아카이브 목록
# ("August 2016 July 2016 …")과 광고가 코퍼스에 들어갔다. 폴백을 없애고 버린다.
_SSC_START = 'class="pjgm-postcontent"'
_SSC_END = ("This entry was posted", '<div id="comments"')
_SSC_SKIP = re.compile(
    r"open thread|links |highlights from the comments|meetup|survey|ot\d|classifieds",
    re.I,
)


def fetch_ssc(n: int) -> list[dict]:
    idx = _get("https://slatestarcodex.com/archives/", timeout=90)
    urls = list(dict.fromkeys(_SSC_POST.findall(idx)))
    random.Random(20260904).shuffle(urls)
    got: list[dict] = []
    for url, year in urls:
        if len(got) >= n:
            break
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        if _SSC_SKIP.search(slug.replace("-", " ")) or year >= "2022":
            continue
        try:
            page = _get(url, timeout=30)
        except Exception:  # noqa: BLE001
            continue
        start = page.find(_SSC_START, 3000)  # <style> 안의 같은 이름 정의를 건너뛴다
        if start < 0:
            continue  # 본문 컨테이너를 못 찾으면 버린다 — 통째 폴백 금지
        ends = [e for e in (page.find(m, start) for m in _SSC_END) if e > 0]
        prose = _r1._prose(page[start : min(ends) if ends else len(page)])
        if not _ok(prose):
            continue
        got.append({"title": slug.replace("-", " ").title(), "text": _excerpt(prose),
                    "tail": _tail(prose),
                    "published": url.split("slatestarcodex.com/")[1][:10].replace("/", "-"),
                    "source": "slatestarcodex"})
        time.sleep(0.4)
    return got


def fetch_human(n: int) -> list[dict]:
    """3출처를 4:3:3 으로 섞는다 — 2회차의 '단일 커뮤니티' 교란 제거.

    **출처별로 캐시에 적재한다.** 한 출처가 실패해도 앞의 수집을 잃지 않고,
    실패한 출처만 다시 돌리면 된다(위 _get 주석의 실사고).
    """
    rows: list[dict] = []
    for name, fn, share in (("lw", fetch_lw, 0.4), ("pg", fetch_pg, 0.3),
                            ("ssc", fetch_ssc, 0.3)):
        cached = _load(f"human_{name}.json")
        if cached:
            print(f"  {name}: 캐시 {len(cached)}편")
            rows += cached
            continue
        got = fn(round(n * share))
        _save(f"human_{name}.json", got)
        print(f"  {name}: {len(got)}편 수집")
        rows += got
    return rows


# ── AI 팔 — 실사용자 프롬프트 ───────────────────────────────────────────
def _one(claude: str, workdir: str, title: str, model: str) -> dict | None:
    # 2회차 프롬프트는 분량·형식을 지정해 구조 슬롭을 미리 막았다. 실사용자는
    # 그렇게 쓰지 않는다 — "engaging" 같은 지시가 슬롭을 부르는 쪽이다.
    prompt = (
        f'Write an engaging blog post titled "{title}" for our website. '
        f"Around {_GEN_WORDS} words. "
        f"Output the post between {_base._START} and {_base._END} and nothing else."
    )
    for _ in range(_base._GEN_MAX_TRIES):
        proc = subprocess.run(
            [claude, "--model", model, "-p", prompt],
            capture_output=True, text=True, timeout=600,
            cwd=workdir, env=_base._clean_env(),
        )
        text = _base.extract_sentinel(proc.stdout)
        if text and len(text.split()) >= _MIN_SOURCE_WORDS and not _base.is_contaminated(text):
            return {"title": title, "text": _excerpt(text), "tail": _tail(text),
                    "model": model}
    print(f"포기: {model} / {title[:40]}", file=sys.stderr)
    return None


def gen_ai(titles: list[str]) -> list[dict]:
    claude = _base._which_claude()
    workdir = tempfile.mkdtemp(prefix="humanize_r2_")
    jobs = [(t, m) for t in titles for m in _base._MODELS]
    with ThreadPoolExecutor(max_workers=_GEN_WORKERS) as pool:
        rows = pool.map(lambda j: _one(claude, workdir, *j), jobs)
    return [r for r in rows if r]


# ── 후보 인코더 — 초록 셀에서 "판정 불가(장르)"로 유예됐던 것들 ─────────
#
# ⚠️ 우리 전과 3범: **표면 예시를 박고 통사 프레임을 놓쳤다**(C-8 재현율 0/6,
# 렉시콘 전수 오발화, EN-1 초판 0.00). 가능한 것은 전부 프레임으로 쓴다.
_CAND = {
    # blader #23 filler — 담화 채움말. 프레임화가 안 되는 어휘류라 대표형만.
    "filler_phrase": re.compile(
        r"\bit(?:'s| is) (?:important|worth) (?:to note|noting)\b"
        r"|\bat the end of the day\b|\bwhen it comes to\b"
        r"|\bin today'?s (?:world|landscape|environment)\b"
        r"|\bneedless to say\b|\bthe fact of the matter\b|\bthat (?:being |)said\b",
        re.I,
    ),
    # #5 vague sources — 무주체 전거. 주어+발화동사 프레임.
    "vague_source": re.compile(
        r"\b(?:studies|research|experts|scientists|data|evidence|surveys)\s+"
        r"(?:show|shows|suggest|suggests|indicate|indicates|say|says|reveal|reveals)\b"
        r"|\b(?:many|some|most)\s+(?:argue|believe|say|think|agree)\b"
        r"|\bit is (?:widely |generally |often |)(?:believed|thought|known|accepted)\b",
        re.I,
    ),
    # #12 false ranges — "from X to Y" 열거 공식.
    "range_formula": re.compile(r"\bfrom\s+[\w-]+(?:\s+[\w-]+){0,2}\s+to\s+[\w-]+", re.I),
    # #10 tricolon — 3항 등위. 쉼표 2개 + and 프레임.
    # **런타임(metrics_en)과 같은 객체를 쓴다.** 연구 스크립트와 라우터가 서로
    # 다른 정규식을 갖게 되면 실측치와 제품 동작이 조용히 갈린다.
    "tricolon": _TRICOLON_RE,
    # #27 deeper truth — "진짜는 이거다" 제스처.
    "deeper_truth": re.compile(
        r"\bhere'?s the (?:thing|catch|problem)\b"
        r"|\bthe (?:real|deeper|bigger) (?:question|issue|problem|truth|point) is\b"
        r"|\bwhat'?s really (?:going on|happening)\b|\bthe truth is\b",
        re.I,
    ),
    # #1·#4 hype — 의의 과장·판매 어휘.
    "hype_word": re.compile(
        r"\b(?:revolution\w*|transformat\w*|unlock\w*|game.chang\w*|cutting.edge"
        r"|powerful|profound|remarkable|crucial|essential|vital|unprecedented)\b",
        re.I,
    ),
}
# #25 generic positive ending — **위치가 본질**이라 마지막 3문장에서만 센다.
_CLOSING = re.compile(
    r"\bone thing is clear\b|\btime will tell\b|\bremains to be seen\b"
    r"|\bthe future (?:is|of|belongs)\b|\bis here to stay\b|\bthe journey\b"
    r"|\bstart(?:ing)? today\b|\bat the end of the day\b|\bwhatever (?:happens|the)\b",
    re.I,
)


def _metrics(text: str, tail: str | None = None) -> dict:
    u = compute_universal(text, long_threshold=LONG_SENTENCE_TOKENS, unit="tokens")
    tokens = u["tokens"] or 1
    from metrics_universal import split_sentences  # noqa: PLC0415

    sents = split_sentences(text)
    per_1k = lambda rx: round(len(rx.findall(text)) / tokens * 1000, 2)  # noqa: E731
    out = {
        "sentence_length_dispersion": u["sentence_length_dispersion"],
        "comma_inclusion_rate": u["comma_inclusion_rate"],
        "comma_usage_rate": u["comma_usage_rate"],
        "comma_segment_length": u["comma_segment_length"],
        "en1_participial": per_1k(_EN1_RE),
        "en2_be_verbs": per_1k(_EN2_RE),
        # #31 dramatic fragment — 4단어 이하 문장 비율(POS 없이 근사).
        "fragment_rate": round(
            100 * sum(1 for s in sents if len(s.split()) <= 4) / max(len(sents), 1), 2
        ),
        # 탐색 지표(커뮤니티·학술 앵커 없음 — 단독 승격 불가, 관측용).
        "rhetorical_question": round(text.count("?") / tokens * 1000, 2),
        "second_person": per_1k(re.compile(r"\byou(?:r|rs|rself)?\b", re.I)),
    }
    out.update({k: per_1k(rx) for k, rx in _CAND.items()})
    # 결말 공식은 **글의 끝**에서만 의미가 있다 — 발췌 구간이 아니라 tail 을 본다.
    out["closing_formula"] = float(bool(_CLOSING.search(tail))) if tail else 0.0
    return out


# ── 장르 보정 라우터 ────────────────────────────────────────────────────
#
# 지표 하나하나는 약해도, **장르에 맞게 보정한 신호 3개를 합치면** 라우터가 선다.
# 초록 임계(comma_segment < 10.82)를 블로그에 그대로 쓰면 인간 중앙값(9.68)이
# 통째로 AI 쪽에 떨어진다 — 분리도가 0.29 로 죽는 이유가 이것이다.
_ROUTER_SIGNALS = ("comma_segment_length", "tricolon", "en1_participial")


def _blog_route(m: dict, seg_max: float) -> str:
    sig = (m["comma_segment_length"] < seg_max) + (m["tricolon"] > 0) + (m["en1_participial"] > 0)
    return "heavy" if sig >= 2 else "standard" if sig == 1 else "light"


def _route_dist(rows: list[dict], seg_max: float) -> dict:
    from collections import Counter  # noqa: PLC0415

    c = Counter(_blog_route(_metrics(r["text"], r.get("tail")), seg_max) for r in rows)
    n = len(rows) or 1
    return {k: round(c.get(k, 0) / n, 2) for k in ("light", "standard", "heavy")}


def _separation(human: dict, ai: dict) -> float:
    return round(ai["heavy"] - human["heavy"] + human["light"] - ai["light"], 2)


# ── GPT 팔 — 모델 계열 교차 검증 ────────────────────────────────────────
#
# R2 까지의 AI 팔은 **Claude 3모델뿐**이었다. 사용자가 붙여넣는 글의 상당수는
# GPT 인데, 우리 신호가 Claude 개인어인지 모델 무관한 AI 티인지 구분이 안 됐다.
# G1(전 모델 생존)의 원래 취지는 **계열을 건너뛰는 것**이다.
_CODEX_BIN = "codex"


def _one_gpt(workdir: str, title: str) -> dict | None:
    prompt = _gpt_prompt(title)
    for _ in range(_base._GEN_MAX_TRIES):
        proc = subprocess.run(
            [_CODEX_BIN, "exec", "--skip-git-repo-check", prompt],
            capture_output=True, text=True, timeout=900,
            cwd=workdir, env=_base._clean_env(), stdin=subprocess.DEVNULL,
        )
        text = _base.extract_sentinel(proc.stdout)
        if text and len(text.split()) >= _MIN_SOURCE_WORDS and not _base.is_contaminated(text):
            return {"title": title, "text": _excerpt(text), "tail": _tail(text),
                    "model": "gpt(codex-cli)"}
    print(f"포기: gpt / {title[:40]}", file=sys.stderr)
    return None


def _gpt_prompt(title: str) -> str:
    return (
        f'Write an engaging blog post titled "{title}" for our website. '
        f"Around {_GEN_WORDS} words. "
        f"Output the post between {_base._START} and {_base._END} and nothing else."
    )


def gen_gpt(titles: list[str]) -> list[dict]:
    workdir = tempfile.mkdtemp(prefix="humanize_gpt_")
    with ThreadPoolExecutor(max_workers=_GEN_WORKERS) as pool:
        rows = pool.map(lambda t: _one_gpt(workdir, t), titles)
    return [r for r in rows if r]


def _blog_router(human: list[dict], ai: list[dict]) -> dict:
    """장르 보정 임계로 라우터를 다시 세우고, 과적합이 아닌지 두 방향으로 본다.

    ① 모델별 분리도 — 3모델 전부에서 서는가(G1).
    ② 인간 출처 홀드아웃 — 한 출처로 임계를 잡아 **다른 출처**에 적용해도 서는가.
       인간 코퍼스가 3출처라 이 검사가 가능하다.
    """
    seg_all = sorted(_metrics(r["text"], r.get("tail"))["comma_segment_length"] for r in human)
    seg_max = round(statistics.quantiles(seg_all, n=4)[0], 2)  # 인간 하위 25%
    h_dist, a_dist = _route_dist(human, seg_max), _route_dist(ai, seg_max)

    per_model = {}
    for model in _base._MODELS:
        sub = [r for r in ai if r.get("model") == model]
        if sub:
            per_model[model] = _separation(h_dist, _route_dist(sub, seg_max))

    holdout = {}
    sources = sorted({r.get("source", "?") for r in human})
    for src in sources:
        fit = [r for r in human if r.get("source") == src]
        test = [r for r in human if r.get("source") != src]
        if not fit or not test:
            continue
        q1 = round(
            statistics.quantiles(
                sorted(_metrics(r["text"], r.get("tail"))["comma_segment_length"] for r in fit),
                n=4,
            )[0], 2,
        )
        holdout[f"fit={src}"] = {
            "seg_max": q1,
            "separation": _separation(_route_dist(test, q1), _route_dist(ai, q1)),
        }

    return {
        "signals": list(_ROUTER_SIGNALS),
        "rule": f"comma_segment < {seg_max} · tricolon > 0 · en1 > 0 — 2개 이상 heavy, 1개 standard, 0개 light",
        "seg_max": seg_max,
        "human": h_dist,
        "ai": a_dist,
        "separation": _separation(h_dist, a_dist),
        "separation_by_model": per_model,
        "holdout_by_human_source": holdout,
    }


def auc(ai: list[float], human: list[float]) -> float:
    if not ai or not human:
        return 0.5
    wins = sum((a > h) + 0.5 * (a == h) for a in ai for h in human)
    return round(wins / (len(ai) * len(human)), 3)


def auc_ci(ai: list[float], human: list[float], boots: int = 2000) -> tuple[float, float]:
    """부트스트랩 95% CI. **이게 없어서 2회차가 '표본 부족'을 '무효과'로 읽었다.**"""
    rng = random.Random(11)
    vals = sorted(
        auc([rng.choice(ai) for _ in ai], [rng.choice(human) for _ in human])
        for _ in range(boots)
    )
    return vals[int(boots * 0.025)], vals[int(boots * 0.975) - 1]


def _values(rows: list[dict], key: str) -> list[float]:
    return [_metrics(r["text"], r.get("tail"))[key] for r in rows]


def _load(name: str) -> list[dict]:
    p = os.path.join(_WORK, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []


def _save(name: str, rows: list[dict]) -> None:
    os.makedirs(_WORK, exist_ok=True)
    with open(os.path.join(_WORK, name), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="블로그 셀 R2")
    ap.add_argument("--fetch-human", type=int, metavar="N")
    ap.add_argument("--gen-ai", type=int, metavar="N", help="제목 N개 × 3모델")
    ap.add_argument("--gen-gpt", type=int, metavar="N",
                    help="GPT 팔 — 제목 N개 × codex CLI (모델 계열 교차 검증)")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)

    if args.fetch_human:
        rows = fetch_human(args.fetch_human)
        _save("human.json", rows)
        from collections import Counter

        print(f"인간 {len(rows)}편 · {Counter(r['source'] for r in rows)}")
    if args.gen_ai:
        human = _load("human.json")
        if not human:
            raise SystemExit("먼저 --fetch-human 을 실행할 것")
        # **출처별로 비례 추출한다.** human.json 은 출처 순서대로 쌓여 있어서
        # 단순 간격 추출은 뒤쪽 출처를 통째로 빠뜨린다(첫 시도에서 SSC 0편).
        from collections import Counter  # noqa: PLC0415

        shares = Counter(r["source"] for r in human)
        titles: list[str] = []
        for src, cnt in shares.items():
            rows = [r for r in human if r["source"] == src]
            want = max(1, round(args.gen_ai * cnt / len(human)))
            step = max(1, len(rows) // want)
            titles += [r["title"] for r in rows[::step]][:want]
        titles = titles[: args.gen_ai]
        _save("ai.json", gen_ai(titles))
        print(f"AI {len(_load('ai.json'))}편")
    if args.gen_gpt:
        human = _load("human.json")
        if not human:
            raise SystemExit("먼저 --fetch-human 을 실행할 것")
        ai = _load("ai.json")
        titles = list(dict.fromkeys(r["title"] for r in ai))[: args.gen_gpt] or [
            r["title"] for r in human[: args.gen_gpt]
        ]
        # **이어 받는다.** 이미 생성한 제목은 다시 부르지 않는다 — 팔을 넓힐 때마다
        # 전량 재생성하면 비용이 배로 들고, 앞서 받은 표본을 버릴 이유도 없다.
        done = _load("ai_gpt.json")
        have = {r["title"] for r in done}
        todo = [t for t in titles if t not in have]
        if todo:
            done += gen_gpt(todo)
            _save("ai_gpt.json", done)
        print(f"GPT {len(done)}편 (신규 {len(todo)} · 기존 {len(have)})")
    if args.report:
        human, ai = _load("human.json"), _load("ai.json")
        if not human or not ai:
            raise SystemExit("human.json / ai.json 이 필요하다")
        keys = list(_metrics(human[0]["text"], human[0].get("tail")))
        # **승격 판정에는 측정한 모든 계열을 넣는다.** GPT 팔이 생긴 뒤에도 Claude 만
        # 보면, 계열을 건너뛰는 신호를 계열 하나의 표본 부족 탓에 탈락시킨다 —
        # tricolon 이 Claude 단독 0.681 로 기준에 0.019 모자랐다가, GPT 34편을
        # 더하자 0.737 로 넘었다. 기준을 낮춘 것이 아니라 표본을 넓힌 것이다.
        gpt_arm = _load("ai_gpt.json")
        ai_all = ai + gpt_arm
        hv = {k: _values(human, k) for k in keys}
        av = {k: _values(ai_all, k) for k in keys}
        arms = {m: [r for r in ai if r.get("model") == m] for m in _base._MODELS}
        if gpt_arm:
            arms["gpt(codex-cli)"] = gpt_arm  # 계열 교차 — G1 의 원래 취지
        per_model = {
            m: {k: auc([_metrics(r["text"], r.get("tail"))[k] for r in sub], hv[k])
                for k in keys}
            for m, sub in arms.items()
            if sub
        }
        rows = {}
        for k in keys:
            point = auc(av[k], hv[k])
            lo, hi = auc_ci(av[k], hv[k])
            models = {m: per_model[m][k] for m in per_model}
            consistent = len({v > 0.5 for v in models.values()}) == 1
            rows[k] = {
                "auc": point,
                "ci95": [lo, hi],
                "per_model": models,
                "direction_consistent": consistent,
                "verdict": (
                    "승격 후보" if abs(point - 0.5) >= 0.20
                    and (lo > 0.5 or hi < 0.5) and consistent
                    else "표본 부족" if not (lo > 0.5 or hi < 0.5)
                    else "모델 개인어" if not consistent
                    else "약함"
                ),
                "human_median": round(statistics.median(hv[k]), 2),
                "ai_median": round(statistics.median(av[k]), 2),
            }
        promoted = [k for k, v in rows.items() if v["verdict"] == "승격 후보"]

        # 계열별 상세는 따로 싣는다(라우터 분리도 비교용).
        gpt = gpt_arm
        cross_family = None
        if gpt:
            g_dist = _route_dist(gpt, _blog_router(human, ai)["seg_max"])
            h_dist = _route_dist(human, _blog_router(human, ai)["seg_max"])
            cross_family = {
                "n": len(gpt),
                "generator": "codex-cli (OpenAI GPT)",
                "auc": {k: auc(_values(gpt, k), hv[k]) for k in keys},
                "router": {"human": h_dist, "gpt": g_dist,
                           "separation": _separation(h_dist, g_dist)},
            }
        from collections import Counter

        cell = {
            "status": "판별 가능" if promoted else "**판별 실패**",
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "human_n": len(human),
            "ai_n": len(ai_all),
            "ai_n_by_arm": {"claude(3모델)": len(ai), "gpt(codex-cli)": len(gpt_arm)},
            "source_human": dict(Counter(r["source"] for r in human)),
            "excerpt": f"본문 {_SKIP_WORDS}~{_SKIP_WORDS + _TAKE_WORDS}단어 (도입부 제외)",
            "ai_prompt": "실사용자 프롬프트 — engaging blog post, 700단어, 형식 무지정",
            "metrics": rows,
            "promoted": promoted,
            "cross_family_gpt": cross_family,
            "router_current": {
                "note": "현행 라우터(초록 보정 임계)를 블로그 입력에 그대로 쓴 결과",
                "human": _r1._route_dist(human),
                "ai": _r1._route_dist(ai),
            },
            "router_blog_calibrated": _blog_router(human, ai),
            "design": (
                "1·2회차 음성 결과를 네 방향에서 강화: 후보 7건 신규 계측 · "
                "실사용자 프롬프트 · 인간 100편 3출처 · 본문 중간 발췌. "
                "판정은 부트스트랩 CI + G1 모델별 방향."
            ),
        }
        cell["router_current"]["separation"] = _separation(
            cell["router_current"]["human"], cell["router_current"]["ai"]
        )
        doc = json.load(open(_OUT, encoding="utf-8"))
        doc.setdefault("genres", {})["blog_essay_r2"] = cell
        with open(_OUT, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        print(json.dumps(cell, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
