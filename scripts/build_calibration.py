#!/usr/bin/env python3
"""역치 캘리브레이션 기준선 생성 — 사람 글 vs AI 생성글의 패턴 밀도.

왜 필요한가
-----------
택소노미의 횟수 역치("한 문서 5회+", "단락 3회+")는 **문서 길이에 무관한
절대 횟수**다. 그래서 900자 칼럼에서는 영원히 발동하지 않고, 9,000자
보고서에서는 한 번 걸리면 과잉 발동한다. 실측(2026-08-23):

    규칙          실재 건수   발동 문서   역치 도달 최소 길이
    I-4 당위        70건      4/24       ~1,560자
    F-5 추상체인     37건      4/24       ~1,771자
    C-8 대구        27건      1/24       ~2,428자

즉 **가장 중요한 규칙 셋이 가장 안 걸린다.** 역치를 밀도(건/1000어절)로
바꾸려면 "사람 글의 정상 범위"가 필요하고, 이 스크립트가 그 기준선을
만든다.

데이터 출처
-----------
사람: 2001~2021년 발행 한국어 산문 (칼럼·에세이·리포트·해설·정책기고·
      서평·학술요약). 발행일은 메타태그·웨이백 캡처로 검증. ChatGPT 이전
      이라 AI 문체 오염이 없다.
AI:   같은 주제·장르·분량으로 생성한 글. 주제 추출 세션과 생성 세션을
      분리해 생성 모델이 사람 원문을 보지 못하게 했다(문체 모방 차단).

⚠️ **본문은 이 레포에 넣지 않는다.** 사람 글이 언론사 저작물이므로
파생 통계만 커밋한다. 본문은 로컬 코퍼스 경로에서 읽는다.

사용:
    python3 scripts/build_calibration.py --human <path> --ai <path> [-o <out>]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(
    HERE, "..", "tests", "baselines", "2026-08-23-threshold-calibration.json"
)

# 택소노미의 횟수 역치 규칙들 — 밀도 전환 대상.
# (규칙 ID, 현행 역치, 정규식, 역치 단위)
PATTERNS: list[tuple[str, int, str, str]] = [
    ("I-4", 5, r"[가-힣]야\s*(?:한다|합니다)|[가-힣]\s*필요가\s*있다|요구된다", "문서"),
    ("C-8", 3, r"[가이]\s*아니라|인가[,\s]|[을를]\s*넘어", "문서"),
    ("F-5", 3, r"[가-힣]적\s+[가-힣]{2,}", "문서"),
    ("H-1", 5, r"(?:^|\n|\.\s+)(?:또한|따라서|즉|나아가|아울러|게다가|더욱이)", "문서"),
    ("A-2", 3, r"[을를]\s*통(?:해|하여)", "문단"),
    ("A-16", 3, r"(?:^|\s)(?:그|그녀|그것|그들|이것|이들)(?:[은는이가을를의]|\s)", "단락"),
    ("D-4", 3, r"혁신적|획기적|압도적|파격적|폭발적|전례\s*없는", "문서"),
    ("G-3", 4, r"양쪽\s*모두|두\s*가지\s*모두|장점도\s*있지만|신중하게|균형", "문서"),
    ("J-2", 5, r"[\"“”]", "문서"),
    ("H-3", 3, r"(?:^|\.\s+)(?:이는|이\s*점에서|이\s*관점에서|이\s*말은)", "문서"),
    ("A-4", 3, r"라는\s*점에서", "문서"),
    ("I-1", 3, r"[가-힣]한\s*것이다|[가-힣]일\s*것이다", "문서"),
]


def _load(path: str) -> list[dict]:
    raw = open(path, encoding="utf-8").read()
    data = json.loads(raw[raw.index("[") : raw.rindex("]") + 1])
    return [d for d in data if len(str(d.get("text", ""))) > 50]


def _words(t: str) -> int:
    return len([w for w in t.strip().split() if w])


def _stats(docs: list[dict], label: str) -> dict:
    total_w = sum(_words(d["text"]) for d in docs)
    out: dict = {
        "label": label,
        "docs": len(docs),
        "words": total_w,
        "avg_chars": round(sum(len(d["text"]) for d in docs) / len(docs)),
        "patterns": {},
    }
    for pid, thr, pat, unit in PATTERNS:
        rx = re.compile(pat)
        per_doc = [len(rx.findall(d["text"])) for d in docs]
        total = sum(per_doc)
        rate = (total / total_w) * 1000 if total_w else 0.0
        out["patterns"][pid] = {
            "total": total,
            "per_1k_words": round(rate, 2),
            "docs_over_current_threshold": sum(1 for n in per_doc if n >= thr),
            "current_threshold": thr,
            "threshold_unit": unit,
            # 현행 절대 역치에 도달하려면 몇 어절이 필요한가
            "words_to_reach_threshold": round(thr / rate * 1000) if rate else None,
        }
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="역치 캘리브레이션 기준선 생성")
    p.add_argument("--human", required=True, help="사람 글 코퍼스 JSON")
    p.add_argument("--ai", required=True, help="AI 생성글 코퍼스 JSON")
    p.add_argument("-o", "--out", default=DEFAULT_OUT)
    p.add_argument("--note", default="", help="캡처 메모")
    args = p.parse_args(argv)

    human, ai = _load(args.human), _load(args.ai)
    h, a = _stats(human, "human"), _stats(ai, "ai")

    # 모델별 분해. 종전 기준선의 caveat("생성 모델이 단일이라 모델별 편차 미반영")을
    # 해소하려면 모델을 섞은 총계만으로는 부족하다 — 한 모델의 습관이 전체를 끌고 갈 수 있다.
    # 규칙의 근거로 쓰려면 **모델을 가리지 않고 나타나는가**를 봐야 한다.
    by_model: dict = {}
    models = sorted({str(d.get("model", "unknown")) for d in ai})
    if len(models) > 1:
        for m in models:
            docs = [d for d in ai if str(d.get("model", "unknown")) == m]
            by_model[m] = _stats(docs, m)

    ratios = {}
    for pid, *_ in PATTERNS:
        hv = h["patterns"][pid]["per_1k_words"]
        av = a["patterns"][pid]["per_1k_words"]
        ratios[pid] = {
            "human_per_1k": hv,
            "ai_per_1k": av,
            "ratio_ai_over_human": round(av / hv, 2) if hv else None,
            # 밀도 역치 제안: 사람 기준선의 2배. 사람 값이 0이면 AI 값의 절반.
            "suggested_density_threshold": (
                round(hv * 2, 2) if hv else (round(av / 2, 2) if av else None)
            ),
        }
        if by_model:
            per = {m: st["patterns"][pid]["per_1k_words"] for m, st in by_model.items()}
            ratios[pid]["by_model_per_1k"] = per
            # 모든 모델에서 사람보다 많으면 모델 계열과 무관한 신호로 본다.
            ratios[pid]["all_models_exceed_human"] = all(v > hv for v in per.values())

    doc = {
        "label": "threshold-calibration (사람 vs AI 패턴 밀도)",
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": args.note,
        "provenance": {
            "human": "2001~2021 발행 한국어 산문. 발행일 메타태그·웨이백 검증. "
                     "ChatGPT 이전이라 AI 문체 오염 없음. 본문은 저작권상 미수록.",
            "ai": "같은 주제·장르·분량으로 생성. 주제 추출 세션과 생성 세션 분리로 "
                  "문체 모방 차단.",
            "caveat": "사람 글은 편집·출판된 완성본, AI 글은 초고다. 따라서 이 격차를 "
                      "'AI 고유 지문'이라 부를 수 없고 '미편집 AI 초고의 교정 표적'으로 "
                      "한정해야 한다. 또한 생성 모델이 단일이라 모델별 편차는 미반영.",
        },
        "human": h,
        "ai": a,
        "ai_by_model": by_model,
        "ratios": ratios,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    print(f"기준선 저장 → {args.out}")
    print(f"  사람 {h['docs']}편/{h['words']}어절 · AI {a['docs']}편/{a['words']}어절\n")
    print(f"{'규칙':<7}{'사람/1k':<10}{'AI/1k':<10}{'배수':<8}{'현행역치':<10}{'도달길이(어절)':<16}{'밀도역치 제안'}")
    for pid, thr, *_ in PATTERNS:
        r = ratios[pid]
        need = a["patterns"][pid]["words_to_reach_threshold"]
        print(f"{pid:<7}{r['human_per_1k']:<10}{r['ai_per_1k']:<10}"
              f"{str(r['ratio_ai_over_human']):<8}{str(thr)+'회+':<10}"
              f"{str(need):<16}{r['suggested_density_threshold']}")
    if by_model:
        print(f"\n모델별 밀도(건/1k어절) — 사람 대비. 모든 모델에서 높아야 "
              f"모델 계열과 무관한 신호다.")
        head = f"{'규칙':<7}{'사람':<8}" + "".join(f"{m:<14}" for m in by_model)
        print(head)
        for pid, *_ in PATTERNS:
            r = ratios[pid]
            row = f"{pid:<7}{r['human_per_1k']:<8}"
            row += "".join(f"{r['by_model_per_1k'][m]:<14}" for m in by_model)
            print(row + ("  ← 전 모델 초과" if r.get("all_models_exceed_human") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
