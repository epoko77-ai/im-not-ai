#!/usr/bin/env python3
"""영어 인간 기준선 — arXiv 초록(2015~2021) vs 같은 제목으로 생성한 AI 초록.

왜 필요한가
-----------
영어 룰북의 모든 임계가 E3(자체 스파이크 1회)였다. "분산 8.59 가 인간 범위인가"에
답할 수 없었다(`lang/en/scholarship.md` Caveat C4). 이 스크립트가 그 기준선을 만든다.

인간 판정 기준은 **시점**이다. ChatGPT 공개(2022-11) 이전 텍스트는 AI 혼입이
구조적으로 불가능하다. arXiv 는 제출일이 API 로 확정되고 자유롭게 받을 수 있다.
한국어가 "2022-01-01 이전 발행 + Wayback 이중 확인"으로 한 것과 같은 원리다.

**G2 과업 통제**: AI 쪽은 같은 논문의 **실제 제목**을 주고 초록을 쓰게 한다.
주제·장르·분량이 맞물려야 문체 차이를 문체 차이로 읽을 수 있다
(`core/principles.md` G2 — 한국어 J-2 가 과업 편향으로 뒤집힌 전례).

⚠️ **본문은 커밋하지 않는다.** 파생 통계만 남긴다 — `build_calibration.py` 와 같은 규약.

사용:
    python3 scripts/build_en_baseline.py --fetch-human 40      # 인간 초록 수집
    python3 scripts/build_en_baseline.py --gen-ai 5            # 제목당 3모델 생성
    python3 scripts/build_en_baseline.py --report              # 통계 산출
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "core"))
from metrics_universal import compute_universal  # noqa: E402

# 본문은 gitignored 작업 폴더에만 둔다.
_WORK = os.path.join(_ROOT, "_workspace", "en_baseline")
_OUT = os.path.join(_ROOT, "lang", "en", "baseline.json")

# ChatGPT 공개(2022-11) 이전으로 창을 못박는다. 여유를 둬 2021 말까지만 쓴다.
_DATE_WINDOW = "[201501010000+TO+202112310000]"
_MODELS = ("claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5-20251001")
_GEN_MAX_TRIES = 4   # 오염이 비결정적이라 재시도로 채운다

_TAG = re.compile(r"<(title|summary|published)>(.*?)</\1>", re.S)


_YEARS = (2015, 2016, 2017, 2018, 2019, 2020, 2021)


def fetch_human(n: int) -> list[dict]:
    """arXiv cs.CL 초록을 받는다. 제목·제출일 동반.

    **연도별로 흩어 뽑는다.** 최신순 한 번에 받으면 표본이 며칠에 몰린다
    (초판 실측: 40편이 전부 2021-12-27~30). 한국어 코퍼스가 40개 매체·
    20년으로 흩은 것과 같은 이유 — 한 시점의 유행이 기준선이 되면 안 된다.
    """
    got: list[dict] = []
    per_year = max(1, n // len(_YEARS) + 1)
    for year in _YEARS:
        window = f"[{year}01010000+TO+{year}12312359]"
        url = (
            "http://export.arxiv.org/api/query?"
            f"search_query=cat:cs.CL+AND+submittedDate:{window}"
            f"&start=0&max_results={per_year * 3}"
            "&sortBy=submittedDate&sortOrder=ascending"
        )
        with urllib.request.urlopen(url, timeout=60) as r:
            xml = r.read().decode()
        entries = xml.split("<entry>")[1:]
        taken = 0
        for e in entries:
            fields = {k: v for k, v in _TAG.findall(e)}
            abstract = " ".join(fields.get("summary", "").split())
            published = fields.get("published", "")
            if len(abstract.split()) < 120 or not published:
                continue  # 너무 짧으면 분산이 무의미하다
            assert published < "2022", f"날짜 창 위반: {published}"
            got.append({
                "title": " ".join(fields.get("title", "").split()),
                "text": abstract,
                "published": published,
            })
            taken += 1
            if taken >= per_year:
                break
    return got[:n]


# 생성물이 요청한 글이 아니라 **모델의 메타 발화**인 경우를 걸러낸다.
# 실사고(2026-09-03): 저장소 안에서 `claude -p` 를 돌렸더니 CLI 가 프로젝트
# 컨텍스트·plan mode 상태를 물어, 초록 대신 "this isn't a coding task, plan mode
# doesn't apply…" 를 냈다. arXiv AI 7/21(sonnet 전부)·blog AI 13/38 이 오염됐다.
# 문서 주의사항으로는 못 막는다 — 코드가 거른다.
# ⚠️ 넓게 잡으면 사람 글을 거른다. 초판에 넣은 `I can't` 가 HN 인간 댓글
# ("...that I accepted the job...despite I can't...")을 오탐했다. 실제 오염 사례에는
# 그 표현이 없었다 — **도구·과업 프레이밍 어휘만** 남긴다.
_META_RE = re.compile(
    r"\b(?:plan mode|planning-mode|Explore agents?|Plan agents?"
    r"|this (?:request|task) (?:is|isn'?t|seems)"
    r"|isn'?t a (?:coding|planning) task|not a coding/planning task"
    r"|codebase|as an AI|Here'?s (?:a|the) (?:comment|abstract))\b",
    re.I,
)


def is_contaminated(text: str) -> bool:
    """앞부분에 메타 발화가 있으면 코퍼스에 넣지 않는다."""
    return bool(_META_RE.search(text[:400]))


# 센티넬 — 1차 방어. 한국어 `tests/humanize_runner.py` 가 이미 쓰는 방식이고,
# 영어 생성기가 그걸 안 가져와서 오염이 조용히 통과했다. 모델이 요청한 글 대신
# 메타 발화를 하면 마커가 없으므로 즉시 거부된다. `is_contaminated` 는 2차 방어다
# (마커 안에까지 메타 발화를 넣는 경우).
_START, _END = "<<<A>>>", "<<</A>>>"
_SENTINEL_RE = re.compile(re.escape(_START) + r"(.*?)" + re.escape(_END), re.S)


def extract_sentinel(stdout: str) -> str | None:
    """센티넬 사이 본문만 꺼낸다. 마커가 없으면 None(거부)."""
    match = _SENTINEL_RE.search(stdout)
    return " ".join(match.group(1).split()) if match else None


def gen_ai(titles: list[str]) -> list[dict]:
    """같은 제목으로 초록을 생성한다 — G2 과업 통제.

    **저장소 밖에서 실행한다.** cwd 가 저장소면 CLI 가 프로젝트 컨텍스트를 물어
    모델이 메타 발화를 낸다(위 _META_RE 주석의 실사고).
    """
    claude = _which_claude()
    workdir = tempfile.mkdtemp(prefix="humanize_gen_")
    out: list[dict] = []
    rejected = 0
    for title in titles:
        for model in _MODELS:
            prompt = (
                "Write the abstract for a computational linguistics paper titled "
                f'"{title}". 150-200 words. Output the abstract text between '
                f"{_START} and {_END} and nothing else."
            )
            # 오염은 비결정적이다 — 환경 격리로 크게 줄지만 완전히는 안 막힌다
            # (실측: sonnet 격리 전 1/7 → 격리 후 4/7 정상). 재시도로 채운다.
            # 셀마다 표본 수가 같아야 모델 간 비교가 성립하므로 빈칸을 두지 않는다.
            for _ in range(_GEN_MAX_TRIES):
                proc = subprocess.run(
                    [claude, "--model", model, "-p", prompt],
                    capture_output=True, text=True, timeout=300,
                    cwd=workdir, env=_clean_env(),
                )
                text = extract_sentinel(proc.stdout)
                if text and len(text.split()) >= 100 and not is_contaminated(text):
                    out.append({"title": title, "text": text, "model": model})
                    break
                rejected += 1
            else:
                print(f"포기: {model} / {title[:40]}", file=sys.stderr)
    if rejected:
        print(f"거부 {rejected}건 (분량 미달 또는 메타 발화, 재시도 포함)",
              file=sys.stderr)
    return out


# 부모 Claude Code 세션의 상태가 자식 `claude -p` 로 새면, 모델이 요청한 글 대신
# 자기 도구에 대한 메타 발화를 낸다("plan mode doesn't apply here…").
# 실측(2026-09-03): 이 넷을 지우면 즉시 정상 산출이 나온다. cwd 격리만으로는
# 부족했다 — sonnet 이 저장소 밖에서도 6/7 오염이었다.
_LEAKY_ENV = (
    "CLAUDE_CODE_MESSAGING_SOCKET",
    "CLAUDE_CODE_MESSAGING_TOKEN",
    "CLAUDE_CODE_EMIT_SESSION_STATE_EVENTS",
    "CLAUDE_CODE_ENABLE_TASKS",
)


def _clean_env() -> dict:
    env = dict(os.environ)
    for key in _LEAKY_ENV:
        env.pop(key, None)
    return env


def _which_claude() -> str:
    import shutil

    path = shutil.which("claude")
    if not path:
        raise SystemExit("claude CLI 없음 — --gen-ai 는 CLI 가 필요하다")
    return path


def _stats(rows: list[dict]) -> dict:
    import statistics

    keys = ("sentence_length_dispersion", "long_sentence_rate",
            "comma_inclusion_rate", "comma_segment_length")
    per = {k: [] for k in keys}
    for r in rows:
        u = compute_universal(r["text"], long_threshold=35, unit="tokens")
        for k in keys:
            per[k].append(u[k])
    return {
        "n": len(rows),
        **{
            k: {
                "median": round(statistics.median(v), 2),
                "mean": round(statistics.mean(v), 2),
                "sd": round(statistics.pstdev(v), 2),
                "min": round(min(v), 2),
                "max": round(max(v), 2),
            }
            for k, v in per.items() if v
        },
    }


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
    ap = argparse.ArgumentParser(description="영어 인간 기준선 생성")
    ap.add_argument("--fetch-human", type=int, metavar="N")
    ap.add_argument("--gen-ai", type=int, metavar="N", help="제목 N개 × 3모델")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)

    if args.fetch_human:
        rows = fetch_human(args.fetch_human)
        _save("human.json", rows)
        print(f"인간 초록 {len(rows)}편 · "
              f"{min(r['published'] for r in rows)[:10]} ~ "
              f"{max(r['published'] for r in rows)[:10]}")
    if args.gen_ai:
        human = _load("human.json")
        if not human:
            raise SystemExit("먼저 --fetch-human 을 실행할 것")
        rows = gen_ai([r["title"] for r in human[: args.gen_ai]])
        _save("ai.json", rows)
        print(f"AI 초록 {len(rows)}편 (제목 {args.gen_ai} × 모델 {len(_MODELS)})")
    if args.report:
        human, ai = _load("human.json"), _load("ai.json")
        if not human:
            raise SystemExit("human.json 없음")
        doc = {
            "version": "0.1",
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "evidence": "E1 — 자체 대조 코퍼스. 인간 판정 기준은 시점(ChatGPT 공개 이전).",
            "genre": "academic abstract (arXiv cs.CL)",
            "caveat": (
                "장르가 학술 초록이다. 칼럼·블로그 임계로 바로 쓰면 안 된다. "
                "G2 과업 통제를 위해 AI 쪽은 같은 논문 제목으로 생성했다."
            ),
            "human": {"source": f"arXiv cs.CL, submittedDate {_DATE_WINDOW}",
                      **_stats(human)},
        }
        if ai:
            doc["ai"] = {"models": list(_MODELS), **_stats(ai)}
            doc["ratios"] = {
                k: round(doc["ai"][k]["median"] / doc["human"][k]["median"], 3)
                for k in doc["human"]
                if isinstance(doc["human"].get(k), dict)
                and doc["human"][k]["median"]
            }
        os.makedirs(os.path.dirname(_OUT), exist_ok=True)
        with open(_OUT, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        print(json.dumps(doc, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
