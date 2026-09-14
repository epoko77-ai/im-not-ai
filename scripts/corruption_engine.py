#!/usr/bin/env python3
"""오염 엔진 — 깨끗한 한국어 문단에 AI 티를 역주입해 (오염본 → 원본) 학습쌍을 만든다.

왜 이 방향인가
--------------
파인튜닝에는 입력→출력 쌍이 필요하다. "AI 초안을 스킬로 윤문"해 쌍을 만들면 출력이
외부 LLM 산출물이라 약관 문제가 생기고, 스킬의 실수까지 데이터에 복사된다. 반대로
**규칙을 거꾸로 실행**하면: 원본이 정답이므로 의미 보존이 구성상 보장되고, 데이터가
전부 자체 IP이며, 규칙이 바뀌면 재생성만 하면 된다(문법 교정 학습의 고전적 방식,
corruption→restoration).

무엇을 주입하고 무엇을 안 하나
------------------------------
taxonomy 82패턴 중 **결정적·의미중립 변환이 가능한 것만** 주입한다.
넣지 않는 것 (이유가 중요하다):
- 서법 계열(A-10·G-1·G-2, 완곡 겹치기): 완곡을 주입한 오염본을 만들면 모델이
  "유보 제거"를 배운다 — 서법 보존 정책(철칙 #10)과 정면 충돌.
- 담화 결핍 계열(DS-*): 정황·인물을 지우는 오염은 원본 복원이 날조 학습이 된다.
- 구조 재배치(문단 순서 등): 역변환의 유일성이 없어 정답이 흔들린다.

자가 검증 (필수)
----------------
주입마다 두 검증을 통과해야 채택된다:
1. **탐지 검증**: 우리 탐지기(verify_gates·count_v26_tells 계열 정규식)가 오염본에서
   해당 티를 실제로 센다 — 탐지기에 안 걸리는 오염은 학습 신호가 없다.
2. **충실도 검증**: checks.py(수치·인용·각주·register)가 원본↔오염본에서 위반 0 —
   오염이 의미를 건드렸으면 폐기한다.

사용:
    python3 scripts/corruption_engine.py --in clean.jsonl --out pairs.jsonl \
        [--per-doc 2] [--noop-rate 0.2] [--seed 7]
입력 jsonl: {"id", "text", "license_track": "public|private"}
출력 jsonl: {"id", "corrupted", "clean", "tags": [...], "license_track"}
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import checks  # noqa: E402  (충실도 검증 — 프로덕션 게이트와 단일 출처)

# ---------------------------------------------------------------------------
# 주입기 정의
# 각 주입기: (tag, detect_rx — 오염 후 이 정규식이 늘어야 채택, apply(text, rng) -> text|None)
# apply가 None이면 이 문서에는 적용 불가(대상 없음).
# ---------------------------------------------------------------------------

# ⚠️ '다\s'로 끊으면 "총량보다 "의 '다'에서도 갈라져 접속사가 문장 중간에 박힌다(데모 실측).
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _sents(t: str) -> list[str]:
    return [s for s in _SENT_SPLIT.split(t) if s.strip()]


def _inj_double_passive(t: str, rng: random.Random) -> str | None:
    """A-8 이중 피동: ~된다/됐다 → ~되어진다/되어졌다."""
    cands = list(re.finditer(r"(?<![어아])(된다|됐다|되었다)(?=[.\s,])", t))
    if not cands:
        return None
    m = rng.choice(cands)
    rep = {"된다": "되어진다", "됐다": "되어졌다", "되었다": "되어졌다"}[m.group(1)]
    return t[: m.start()] + rep + t[m.end():]


def _inj_conclusion_pivot(t: str, rng: random.Random) -> str | None:
    """D-1 결산 피벗: 마지막 문단 첫 문장 앞에 '결론적으로,' 부착."""
    paras = t.split("\n\n")
    if len(paras) < 2:
        return None
    last = paras[-1].lstrip()
    if last.startswith(("결론적으로", "요약하면", "따라서")):
        return None
    word = rng.choice(["결론적으로, ", "요약하면 ", "결국 "])
    paras[-1] = word + last
    return "\n\n".join(paras)


def _inj_sentence_adverbs(t: str, rng: random.Random) -> str | None:
    """H-1 문두 접속사 밀집: 한 문단의 문장 앞에 '또한/따라서'를 2곳 삽입."""
    paras = t.split("\n\n")
    idx = [i for i, p in enumerate(paras) if len(_sents(p)) >= 3]
    if not idx:
        return None
    i = rng.choice(idx)
    ss = _sents(paras[i])
    marks = rng.sample(["또한 ", "따라서 ", "나아가 ", "아울러 "], k=2)
    for j, mark in zip((1, 2), marks):
        if not ss[j].startswith(("또한", "따라서", "나아가", "그리고", "아울러")):
            ss[j] = mark + ss[j]
    paras[i] = " ".join(ss)
    return "\n\n".join(paras)


def _inj_hype(t: str, rng: random.Random) -> str | None:
    """D-4/F-1 hype·정도부사: '중요한/큰' 앞에 '매우', 명사 앞 강조어."""
    cands = list(re.finditer(r"(?<![우])(중요한|커다란|큰\s|필요한)", t))
    if not cands:
        return None
    m = rng.choice(cands)
    word = rng.choice(["매우 ", "대단히 ", "그 어느 때보다 "])
    return t[: m.start()] + word + t[m.start():]


def _inj_comma_after_connective(t: str, rng: random.Random) -> str | None:
    """C-11 연결어미 뒤 쉼표: '-고 /-지만 /-면서 ' → '-고, ' (2곳)."""
    # '고 있다/싶다/보다/말다'는 보조용언 구성이라 쉼표를 찍으면 비문이 된다(데모 실측:
    # "제시하고, 있다"). 연결어미 뒤 실제 절이 이어지는 자리만 노린다.
    cands = list(re.finditer(r"(고|지만|면서|는데)\s(?![,]|있|싶|말|본|보이)", t))
    if len(cands) < 2:
        return None
    picks = rng.sample(cands, k=2)
    out = t
    for m in sorted(picks, key=lambda m: -m.start()):
        out = out[: m.end(1)] + ", " + out[m.end():]
    return out


def _inj_cleft(t: str, rng: random.Random) -> str | None:
    """D-8 분열문: '(N)이/가 필요하다' → '필요한 것은 (N)이다'."""
    cands = [(m, "필요한 것은 {}이다") for m in re.finditer(r"([가-힣]{2,8})[이가]\s*필요하다", t)]
    cands += [(m, "중요한 것은 {}이다") for m in re.finditer(r"([가-힣]{2,8})[이가]\s*중요하다", t)]
    cands += [(m, "핵심은 {}이다") for m in re.finditer(r"([가-힣]{2,8})[이가]\s*핵심이다", t)]
    if not cands:
        return None
    m, tmpl = rng.choice(cands)
    return t[: m.start()] + tmpl.format(m.group(1)) + t[m.end():]


def _inj_task_slot(t: str, rng: random.Random) -> str | None:
    """D-12 빈 반론 슬롯: 뒤쪽 문단 앞에 '그러나 과제도 남아 있다.' 삽입."""
    paras = t.split("\n\n")
    if len(paras) < 3:
        return None
    i = rng.randrange(len(paras) // 2, len(paras))
    lead = rng.choice(["그러나 과제도 남아 있다. ", "다만 한계도 분명하다. "])
    if paras[i].lstrip().startswith(("그러나", "다만", "하지만")):
        return None
    paras[i] = lead + paras[i].lstrip()
    return "\n\n".join(paras)


def _inj_horizon(t: str, rng: random.Random) -> str | None:
    """D-11 시간지평: 마지막 문단 첫머리에 '향후/중장기적으로' 부착."""
    paras = t.split("\n\n")
    last = paras[-1].lstrip()
    if re.match(r"향후|앞으로|중?장기", last):
        return None
    paras[-1] = rng.choice(["향후 ", "중장기적으로는 ", "앞으로 "]) + last
    return "\n\n".join(paras)


def _inj_progressive_passive(t: str, rng: random.Random) -> str | None:
    """A-20 피동 진행: 사전 쌍 치환 — '심해졌다'→'심화되고 있다' 류."""
    PAIRS = [("심해졌다", "심화되고 있다"), ("줄었다", "줄어들고 있다"),
             ("늘었다", "늘어나고 있다"), ("커졌다", "커지고 있다"),
             ("바뀌었다", "변화하고 있다"), ("나빠졌다", "악화되고 있다"),
             ("늘어났다", "증가하고 있다"), ("줄어들었다", "감소하고 있다"),
             ("높아졌다", "높아지고 있다"), ("낮아졌다", "낮아지고 있다"),
             ("확대됐다", "확대되고 있다"), ("개선됐다", "개선되고 있다"),
             ("확산했다", "확산되고 있다"), ("발전했다", "발전하고 있다"),
             ("성장했다", "성장하고 있다"), ("변했다", "변화하고 있다")]
    hits = [(a, b) for a, b in PAIRS if a in t]
    if not hits:
        return None
    a, b = rng.choice(hits)
    return t.replace(a, b, 1)


def _inj_generic_verb(t: str, rng: random.Random) -> str | None:
    """F-7 범용동사 수렴: 구체 동사 → 확대/강화/개선/구축."""
    PAIRS = [("늘려야", "확대해야"), ("키워야", "강화해야"), ("고쳐야", "개선해야"),
             ("만들어야", "구축해야"), ("넓혀야", "확대해야"), ("다듬어야", "개선해야"),
             ("늘리고", "확대하고"), ("고치고", "개선하고"),
             ("늘렸다", "확대했다"), ("키웠다", "강화했다"), ("고쳤다", "개선했다"),
             ("만들었다", "구축했다"), ("세웠다", "수립했다"), ("다졌다", "강화했다"),
             ("늘린다", "확대한다"), ("키운다", "강화한다"), ("세운다", "수립한다"),
             ("마련했다", "구축했다"), ("갖췄다", "확보했다"), ("얻었다", "확보했다")]
    hits = [(a, b) for a, b in PAIRS if a in t]
    if not hits:
        return None
    a, b = rng.choice(hits)
    return t.replace(a, b, 1)


def _inj_metaphor(t: str, rng: random.Random) -> str | None:
    """D-14 생성형 은유: 직역 표현 → 개념 은유 (직역화 처방의 역방향)."""
    PAIRS = [("점유율을 뺏", "시장을 잠식하"), ("점유율을 줄이", "시장을 잠식하"),
             ("몫을 줄이", "몫을 잠식하"), ("비용을 치르게 된다", "청구서를 받게 된다"),
             ("부담이 커진다", "부담이 어깨를 짓누른다"), ("자리를 잡", "뿌리를 내리"),
             ("계획을", "청사진을"), ("기반을 닦", "주춧돌을 놓"),
             ("경고가 나온다", "적신호가 켜진다"), ("위험 신호가", "경고등이"),
             ("시작을 알렸다", "신호탄을 쏘아 올렸다"), ("기회를 잡", "기회를 움켜쥐"),
             ("성과를 나눈다", "과실을 나눈다"), ("이익을 나눈다", "과실을 나눈다"),
             ("영역을 넓히", "영토를 넓히"), ("자리 잡았다", "뿌리내렸다")]
    hits = [(a, b) for a, b in PAIRS if a in t]
    if not hits:
        return None
    a, b = rng.choice(hits)
    return t.replace(a, b, 1)


def _inj_negation_parallel(t: str, rng: random.Random) -> str | None:
    """C-8/C-14 부정 대구: 'A보다 B가 중요하다' → '중요한 것은 A가 아니라 B다'."""
    m = re.search(r"([가-힣]{2,8})보다\s*([가-힣]{2,8})[이가]\s*(중요하다|필요하다|먼저다|크다)", t)
    if m:
        head = {"중요하다": "중요한 것은", "필요하다": "필요한 것은",
                "먼저다": "먼저인 것은", "크다": "큰 것은"}[m.group(3)]
        return t[: m.start()] + f"{head} {m.group(1)}이 아니라 {m.group(2)}이다" + t[m.end():]
    # "A 대신 B를" → "A가 아니라 B를" (대조 강조로의 전이 — 오염 측이므로 허용)
    m = re.search(r"([가-힣]{2,8})\s*대신\s*([가-힣]{2,8})[을를]", t)
    if m:
        return t[: m.start()] + f"{m.group(1)}이 아니라 {m.group(2)}를" + t[m.end():]
    return None


def _inj_reason_inversion(t: str, rng: random.Random) -> str | None:
    """D-10 역방향 결산: '그래서 (S)다.' → '(S)인 이유다.' — 안전한 좁은 형태만."""
    m = re.search(r"(?:그래서|그렇기에|이\s*때문에)\s+([가-힣][^.!?\n]{6,60}[가-힣])다\.", t)
    if not m:
        return None
    return t[: m.start()] + f"{m.group(1)}다는 이유다." + t[m.end():]


INJECTORS = [
    ("A-8",  re.compile(r"되어[진졌]"), _inj_double_passive),
    ("D-1",  re.compile(r"결론적으로|요약하면|(?:^|[.!?]\s)결국"), _inj_conclusion_pivot),
    ("H-1",  re.compile(r"(?:^|[.!?]\s+)(?:또한|따라서|나아가|아울러)"), _inj_sentence_adverbs),
    ("D-4",  re.compile(r"매우|대단히|그\s*어느\s*때보다"), _inj_hype),
    ("C-11", re.compile(r"(?:고|지만|면서|는데),\s"), _inj_comma_after_connective),
    ("D-8",  re.compile(r"필요한\s*것은"), _inj_cleft),
    ("D-12", re.compile(r"과제도\s*남아|한계도\s*분명"), _inj_task_slot),
    ("D-11", re.compile(r"(?:^|[.!?]\s+)(?:향후|중?장기적으로는?|앞으로)"), _inj_horizon),
    ("A-20", re.compile(r"(?:되|들|나|지|하)고\s*있"), _inj_progressive_passive),
    ("F-7",  re.compile(r"(?:확대|강화|개선|구축)하"), _inj_generic_verb),
    ("D-14", re.compile(r"잠식|청구서|짓누|뿌리를\s*내리|청사진"), _inj_metaphor),
    ("C-14", re.compile(r"아니라"), _inj_negation_parallel),
    ("D-10", re.compile(r"이유다\."), _inj_reason_inversion),
]


def corrupt(text: str, rng: random.Random, n_tags: int = 3) -> tuple[str, list[str]] | None:
    """문서 하나에 1~n_tags개 주입. (오염본, 적용 태그) 또는 None(적용 불가)."""
    applied: list[str] = []
    cur = text
    order = INJECTORS[:]
    rng.shuffle(order)
    for tag, detect, fn in order:
        if len(applied) >= n_tags:
            break
        before_n = len(detect.findall(cur))
        nxt = fn(cur, rng)
        if nxt is None or nxt == cur:
            continue
        # 자가 검증 1 — 탐지: 주입 후 탐지 카운트가 실제로 늘어야 한다.
        if len(detect.findall(nxt)) <= before_n:
            continue
        # 자가 검증 2 — 충실도: 수치·인용·각주·register가 원본과 동일해야 한다.
        if checks.run_checks(text, nxt):
            continue
        cur = nxt
        applied.append(tag)
    if not applied:
        return None
    return cur, applied


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-doc", type=int, default=2, help="문서당 생성할 오염 변주 수")
    ap.add_argument("--noop-rate", type=float, default=0.2,
                    help="무오염 쌍 비율 — '깨끗한 글은 그대로 둔다'를 가르친다")
    ap.add_argument("--max-tags", type=int, default=3)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)
    rng = random.Random(args.seed)

    n_pairs = n_noop = n_skip = 0
    from collections import Counter
    tag_count: Counter[str] = Counter()
    with open(args.inp, encoding="utf-8") as f, open(args.out, "w", encoding="utf-8") as out:
        for line in f:
            if not line.strip():
                continue
            doc = json.loads(line)
            text = doc["text"].strip()
            if len(text) < 200:
                n_skip += 1
                continue
            for k in range(args.per_doc):
                if rng.random() < args.noop_rate:
                    rec = {"id": f'{doc["id"]}#{k}', "corrupted": text, "clean": text,
                           "tags": [], "license_track": doc.get("license_track", "private")}
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n_noop += 1
                    continue
                got = corrupt(text, rng, n_tags=rng.randint(1, args.max_tags))
                if got is None:
                    n_skip += 1
                    continue
                corrupted, tags = got
                tag_count.update(tags)
                rec = {"id": f'{doc["id"]}#{k}', "corrupted": corrupted, "clean": text,
                       "tags": tags, "license_track": doc.get("license_track", "private")}
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n_pairs += 1
    print(f"쌍 {n_pairs} · no-op {n_noop} · 스킵 {n_skip}")
    print("태그 분포:", dict(tag_count.most_common()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
