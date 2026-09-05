#!/usr/bin/env python3
"""마케팅 장르 셀 — 사람들이 실제로 붙여넣는 글에서도 서는가.

**왜 이 장르인가.** 지금까지 검증한 셀은 학술 초록과 분석적 블로그 에세이다.
둘 다 영미 테크 계열 산문이고, 휴머나이저에 가장 많이 들어오는 글 — 회사 블로그·
콘텐츠 마케팅 — 은 한 번도 재지 않았다. 레지스터가 다르면 임계도 다르다는 것을
이미 두 번 확인했다(초록 임계를 블로그에 쓰면 라우터가 죽는다).

**날짜 확정은 Wayback CDX 로 한다.** 마케팅 블로그는 글을 조용히 갱신하므로
현재 페이지의 날짜를 믿을 수 없다. 2019~2021 스냅샷을 직접 받으면 ChatGPT 공개
이전 텍스트임이 스냅샷 시각으로 증명된다. 한국어 코퍼스의 "Wayback 이중 확인"과
같은 원리다.

⚠️ 본문은 커밋하지 않는다. 파생 통계만 `lang/en/baseline.json` 에 남긴다.

사용:
    python3 scripts/build_en_marketing_cell.py --fetch-human 40
    python3 scripts/build_en_marketing_cell.py --gen-ai 20
    python3 scripts/build_en_marketing_cell.py --report
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
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
_r1 = _sibling("build_en_blog_cell")   # _prose·_JUNK 재사용

_WORK = os.path.join(_ROOT, "_workspace", "en_marketing")
_OUT = os.path.join(_ROOT, "lang", "en", "baseline.json")
_UA = {"User-Agent": "humanize-en-baseline/0.1"}
_MODELS = ("claude-sonnet-5", "claude-haiku-4-5-20251001")
_WORKERS = 4

# 출처 — 콘텐츠 마케팅의 대표 둘. 저자가 여럿이고 편집 가이드가 뚜렷하다.
_SOURCES = {
    "hubspot": "blog.hubspot.com/marketing/*",
    "buffer": "buffer.com/resources/*",
}
# 목록·카테고리·태그 페이지는 글이 아니다.
_SKIP_URL = re.compile(r"/(?:page|category|tag|author|topic)/|\?|#", re.I)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)

# ⚠️ 페이지 전체에 _prose 를 씌우면 **내비게이션·푸터가 본문이 된다**
# (실측: "Subscribe via Email Subscribe on Slack … Free Courses & Certifications").
# 마케팅 사이트는 메뉴·CTA 가 본문보다 길다. 이 저장소가 SSC 수집기에서 이미 한 번
# 겪은 실패 유형이다(docs/recurring-failure-modes.md 2번).
#
# 출처별 컨테이너를 찾는 대신 **문단 요소만 뽑는다** — 산문은 <p> 안에 있고
# 메뉴·버튼·폼은 그렇지 않다. 사이트가 바뀌어도 견딘다.
_CHROME = re.compile(r"<(nav|header|footer|aside|form|figure|noscript)\b.*?</\1>", re.S | re.I)
_PARA = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)
_SENTENCE_END = re.compile(r"[.!?][\"'\u201d\u2019)\]]*(?:\s|$)")


def _article_prose(html: str) -> str:
    body = _CHROME.sub(" ", html)
    paras = []
    for raw in _PARA.findall(body):
        text = _r1._prose(raw)
        # 문단 한 개짜리 CTA·캡션을 거른다 — 문장부호가 있고 길어야 산문이다.
        if len(text.split()) >= 12 and _SENTENCE_END.search(text):
            paras.append(text)
    return "\n".join(paras)


def _get(url: str, timeout: int = 60, tries: int = 3) -> str:
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=_UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            time.sleep(3 + 4 * attempt)
    return ""


def _cdx(prefix: str, limit: int) -> list[tuple[str, str]]:
    """(스냅샷 시각, 원본 URL) 목록. 2019~2021 로 못박는다."""
    url = (
        "http://web.archive.org/cdx/search/cdx?url=" + prefix
        + "&from=2019&to=2021&filter=statuscode:200&collapse=urlkey"
        f"&limit={limit}&output=json&fl=timestamp,original"
    )
    rows = json.loads(_get(url))
    return [(ts, orig) for ts, orig in rows[1:] if not _SKIP_URL.search(orig)]


def fetch_human(n: int) -> list[dict]:
    per = max(1, n // len(_SOURCES))
    out: list[dict] = []
    for name, prefix in _SOURCES.items():
        got = 0
        for ts, orig in _cdx(prefix, per * 8):
            if got >= per:
                break
            try:
                # `id_` 는 Wayback 툴바를 빼고 원본 HTML 을 준다.
                page = _get(f"http://web.archive.org/web/{ts}id_/{orig}")
            except Exception:  # noqa: BLE001 — 스냅샷 하나가 없어도 계속한다.
                continue
            prose = _article_prose(page)
            if not _r2._ok(prose):
                continue
            title = _TITLE.search(page)
            out.append({
                "title": re.sub(r"\s*[|–-]\s*(?:HubSpot|Buffer).*$", "",
                                (title.group(1) if title else orig).strip())[:120],
                "text": _r2._excerpt(prose),
                "tail": _r2._tail(prose),
                "published": f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}",
                "source": name,
            })
            got += 1
        print(f"  {name}: {got}편", file=sys.stderr)
    assert all(r["published"] < "2022" for r in out), "날짜 창 위반"
    return out[:n]


def gen_ai(titles: list[str]) -> list[dict]:
    claude = _base._which_claude()
    workdir = tempfile.mkdtemp(prefix="humanize_mkt_")

    def one(job) -> dict | None:
        title, model = job
        prompt = (
            f'Write an engaging blog post titled "{title}" for our company blog. '
            f"Around 700 words. "
            f"Output the post between {_base._START} and {_base._END} and nothing else."
        )
        for _ in range(_base._GEN_MAX_TRIES):
            proc = subprocess.run(
                [claude, "--model", model, "-p", prompt],
                capture_output=True, text=True, timeout=900,
                cwd=workdir, env=_base._clean_env(), stdin=subprocess.DEVNULL,
            )
            text = _base.extract_sentinel(proc.stdout)
            if text and len(text.split()) >= 300 and not _base.is_contaminated(text):
                return {"title": title, "text": _r2._excerpt(text),
                        "tail": _r2._tail(text), "model": model}
        print(f"포기: {model} / {title[:40]}", file=sys.stderr)
        return None

    jobs = [(t, m) for t in titles for m in _MODELS]
    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        return [r for r in pool.map(one, jobs) if r]


def _load(name: str) -> list[dict]:
    p = os.path.join(_WORK, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []


def _save(name: str, rows: list[dict]) -> None:
    os.makedirs(_WORK, exist_ok=True)
    with open(os.path.join(_WORK, name), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="마케팅 장르 셀")
    ap.add_argument("--fetch-human", type=int, metavar="N")
    ap.add_argument("--gen-ai", type=int, metavar="N", help="제목 N개 × 2모델")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)

    if args.fetch_human:
        rows = fetch_human(args.fetch_human)
        _save("human.json", rows)
        from collections import Counter
        print(f"마케팅 인간 {len(rows)}편 · {dict(Counter(r['source'] for r in rows))} · "
              f"{min(r['published'] for r in rows)} ~ {max(r['published'] for r in rows)}")
    if args.gen_ai:
        human = _load("human.json")
        if not human:
            raise SystemExit("먼저 --fetch-human 을 실행할 것")
        titles = list(dict.fromkeys(r["title"] for r in human))[: args.gen_ai]
        done = _load("ai.json")
        have = {(r["title"], r["model"]) for r in done}
        rows = [r for r in gen_ai([t for t in titles]) if (r["title"], r["model"]) not in have]
        _save("ai.json", done + rows)
        print(f"마케팅 AI 신규 {len(rows)}편 · 총 {len(done) + len(rows)}편")
    if args.report:
        human, ai = _load("human.json"), _load("ai.json")
        if not human or not ai:
            raise SystemExit("human.json / ai.json 이 필요하다")
        keys = list(_r2._metrics(human[0]["text"], human[0].get("tail")))
        vals = lambda rows, k: [  # noqa: E731
            _r2._metrics(r["text"], r.get("tail"))[k] for r in rows
        ]
        aucs = {k: _r2.auc(vals(ai, k), vals(human, k)) for k in keys}
        per_model = {
            m: {k: _r2.auc(vals(sub, k), vals(human, k)) for k in keys}
            for m in _MODELS
            for sub in ([r for r in ai if r["model"] == m],)
            if sub
        }
        strong = {
            k: v for k, v in aucs.items()
            if abs(v - 0.5) >= 0.20
            and len({per_model[m][k] > 0.5 for m in per_model}) == 1
        }
        seg_max = _r2._blog_router(human, ai)["seg_max"]
        cell = {
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": "판별 가능" if strong else "**판별 실패**",
            "human_n": len(human), "ai_n": len(ai),
            "source_human": "HubSpot·Buffer 마케팅 블로그, Wayback 2019~2021 스냅샷",
            "models": list(_MODELS),
            "auc": aucs,
            "auc_per_model": per_model,
            "promoted": sorted(strong),
            "router_blog_thresholds": _r2._blog_router(human, ai),
            "seg_max_here": seg_max,
            "caveat": (
                "블로그 셀 임계(쉼표 절 < 8.57)가 이 장르에서도 맞는지 함께 본다. "
                "레지스터가 다르면 임계도 다르다 — 초록→블로그에서 이미 겪었다."
            ),
        }
        doc = json.load(open(_OUT, encoding="utf-8"))
        doc.setdefault("genres", {})["marketing"] = cell
        with open(_OUT, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        print(json.dumps({k: cell[k] for k in
                          ("status", "human_n", "ai_n", "promoted", "auc")},
                         ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
