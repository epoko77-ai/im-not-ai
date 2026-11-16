#!/usr/bin/env python3
"""어휘 레이어 — 독자가 어색하게 느끼는 낱말을 문맥에 따라 다룬다. LLM 콜 0회.

## 왜 필요한가

문장 구조(대구·결말 공식) 윤문과 별개로, AI 글에는 한국어 독자가 읽다가 걸리는 낱말이
있다 — "~의 렌즈로 보면", "세 개의 축으로", "성공을 달성한다", "논의에 결을
더한다". 목록은 `references/lexicon.json`(메인테이너 블라인드 평가 148개 중 어색하다고 판정된
111개 + 메인테이너 추가 2개, v2.4.5). **일괄 치환하지 않는다** — 같은 낱말도 장르·문맥·정당 용법에 따라 두어야 할 때가
있고, 고정 대체어는 그 자체가 새 상투어가 된다.

## 두 가지 일

1. `hints` — 원문에서 발견된 항목만 골라 `[어휘 점검]` 블록을 만든다. 윤문 입력(결합 파일)에
   실려, 실행자가 항목마다 "바꿀 때 / 둘 때 / 방식"을 보고 판단한다. 발견되지 않은 항목은
   싣지 않으므로 프롬프트 비용은 발견 수에 비례한다. 공통 입력 단계(prepare_monolith_input)가
   부르므로 light·standard·heavy 전 경로에 적용된다.
2. `restore` — 윤문이 **원문 문서에 없던** `restore=true` 표제어(평가 2점)를 새로 만들면
   그 문장만 원문 문장으로 되돌린다. 힌트와 같은 넓은 정규식을 쓴다(v2.4.2 — 원문 부재 조건이 안전장치). 프롬프트 금지 조항은 확률적이라 샌다(실측: 같은 설정
   두 번 실행에 주입 문서 6편 ↔ 17편). 정렬·안전 원칙은 restore_modality.py와 같다.

## 안전 원칙 (restore)

애매하면 건드리지 않고 보고만 한다: 짝 문장 유사도가 낮거나, 결과에서 유일하게 특정되지
않거나, 문장 병합·분할이 의심될 때. 되돌린 문장의 다른 윤문도 함께 돌아온다(실측 비용:
문서당 0.3~0.5문장, 변경 정도 1~2%p).

## 사용

    python3 scripts/lexical_layer.py hints --input 01_input.txt --genre column
    python3 scripts/lexical_layer.py restore --before 01_input.txt --after final.md --out final.md [--json]

종료 코드는 항상 0 — 게이트가 아니다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_PLUGIN_REFS = os.path.join(_ROOT, "skills", "humanize-korean", "references")
_REFS = _PLUGIN_REFS if os.path.isdir(_PLUGIN_REFS) else os.path.join(_ROOT, "references")
LEXICON_PATH = os.path.join(_REFS, "lexicon.json")

# 스킬 장르 키 → 사전 장르
GENRE_MAP = {"report": "보고서", "abstract": "논문", "paper": "논문"}
DEFAULT_GENRE = "일반"
# 정당 용법 제외 창: 매치 앞뒤 12자(매치 포함) — 측정 코드와 같은 규약
EXCLUDE_WINDOW = 12
# 블록 상한 — 발견이 많아도 프롬프트가 폭주하지 않게
MAX_HINTS = 15

_LEX_CACHE: dict | None = None


def load_lexicon(path: str | None = None) -> dict:
    global _LEX_CACHE
    if path is None and _LEX_CACHE is not None:
        return _LEX_CACHE
    with open(path or LEXICON_PATH, encoding="utf-8") as f:
        lex = json.load(f)
    for e in lex["entries"]:
        # 복원용(좁고 정밀) — 결정적 변형에 쓴다
        e["_re"] = re.compile(e["regex"])
        e["_ex"] = re.compile(e["regex_exclude"]) if e.get("regex_exclude") else None
        # 힌트용(넓은 재현율) — 최종 판단은 실행자가 문맥으로 한다. 없으면 복원용을 쓴다
        if e.get("regex_detect"):
            e["_dre"] = re.compile(e["regex_detect"])
            e["_dex"] = re.compile(e["regex_detect_exclude"]) if e.get("regex_detect_exclude") else None
        else:
            e["_dre"], e["_dex"] = e["_re"], e["_ex"]
    if path is None:
        _LEX_CACHE = lex
    return lex


def genre_key(genre: str | None) -> str:
    return GENRE_MAP.get((genre or "").strip().lower(), DEFAULT_GENRE)


def _matches(entry: dict, text: str, detect: bool = False) -> list[re.Match]:
    rx, ex = (entry["_dre"], entry["_dex"]) if detect else (entry["_re"], entry["_ex"])
    out = []
    for m in rx.finditer(text):
        if m.end() == m.start():
            continue
        if ex is not None:
            w = text[max(0, m.start() - EXCLUDE_WINDOW): m.end() + EXCLUDE_WINDOW]
            if ex.search(w):
                continue
        out.append(m)
    return out


# 직접 인용 구간 — Do-NOT list(인용 원형 보존). 인용 안의 낱말은 힌트에서 뺀다.
# 실측(v2.4.1): AI 티를 설명하는 글이 "잠금 해제한다" 같은 예문을 인용하자 그 인용까지
# 힌트로 실려 실행자가 인용을 고칠 뻔했다. 한 줄 안, 200자 이내의 짝 맞는 인용부만 본다.
_QUOTE_RE = re.compile(
    r'"[^"\n]{1,200}"|“[^”\n]{1,200}”|‘[^’\n]{1,200}’|「[^」\n]{1,200}」|『[^』\n]{1,200}』'
    r"|(?<![A-Za-z0-9])'[^'\n]{1,200}'(?![A-Za-z0-9])"
)


def quote_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in _QUOTE_RE.finditer(text)]


def _outside_quotes(ms: list[re.Match], spans: list[tuple[int, int]]) -> list[re.Match]:
    return [m for m in ms if not any(a <= m.start() < b for a, b in spans)]


def find_hits(text: str, genre: str | None = None, lexicon: dict | None = None) -> list[dict]:
    """원문에서 발견된 항목. 장르가 skip_genres에 있으면 제외하고, 직접 인용 안의 낱말은 세지 않는다."""
    lex = lexicon or load_lexicon()
    g = genre_key(genre)
    spans = quote_spans(text)
    hits = []
    for e in lex["entries"]:
        if g in e.get("skip_genres", []):
            continue
        ms = _outside_quotes(_matches(e, text, detect=True), spans)
        if not ms:
            continue
        hits.append({
            "id": e["id"], "headword": e["headword"], "tier": e["tier"], "count": len(ms),
            "examples": [text[m.start():m.end()] for m in ms[:2]],
            "change_when": e["change_when"].get(g, ""), "keep_when": e["keep_when"].get(g, ""),
            "how": e["how"].get(g, ""),
        })
    # 2점(change) 먼저, 같은 등급 안에서는 반복이 많은 순
    hits.sort(key=lambda h: (h["tier"] != "change", -h["count"]))
    return hits


def render_hint_block(hits: list[dict], max_items: int = MAX_HINTS) -> str:
    if not hits:
        return ""
    lines = [
        "[어휘 점검]",
        "아래는 원문에서 발견된, 한국어 독자가 어색하게 느끼는 표현이다(독자 평가 기반). "
        "항목마다 문맥을 보고 판단한다 — 일괄 치환하지 않는다. '둘 때'에 해당하면 그대로 둔다. "
        "바꿀 때는 '방식'을 따르되 문장의 사실·주장 강도·서법은 그대로 두고, 이 목록의 다른 표현으로 바꾸지 않는다. "
        "[우선]은 쓰였으면 바꾸는 쪽을 먼저 검토하고, [조건부]는 반복되거나 장르에 맞지 않을 때만 바꾼다.",
    ]
    for h in hits[:max_items]:
        tag = "우선" if h["tier"] == "change" else "조건부"
        found = " / ".join(f'"{x}"' for x in h["examples"])
        rep = f" ×{h['count']}" if h["count"] > 1 else ""
        lines.append(f"- [{tag}] {h['headword']} — 원문: {found}{rep}")
        if h["change_when"]:
            lines.append(f"  바꿀 때: {h['change_when']}")
        if h["keep_when"]:
            lines.append(f"  둘 때: {h['keep_when']}")
        if h["how"]:
            lines.append(f"  방식: {h['how']}")
    if len(hits) > max_items:
        lines.append(f"(그 밖에 {len(hits) - max_items}개 항목은 생략 — 위 항목을 우선한다)")
    lines.append("[어휘 점검 끝]")
    return "\n".join(lines)


def hint_block_for(text: str, genre: str | None = None) -> str:
    """prepare_monolith_input 용 진입점. 사전이 없거나 깨져도 윤문을 막지 않는다.

    HUMANIZE_LEXICAL=0 이면 블록을 만들지 않는다(A/B 대조·장애 시 끄기용).
    """
    if os.environ.get("HUMANIZE_LEXICAL", "1") == "0":
        return ""
    try:
        return render_hint_block(find_hits(text, genre))
    except Exception:  # noqa: BLE001 — graceful degrade
        return ""


# ---------------------------------------------------------------------------
# restore — 원문에 없던 2점 표제어가 생긴 문장만 원문 문장으로
# ---------------------------------------------------------------------------

def restore(before: str, after: str, lexicon: dict | None = None) -> tuple[str, list[dict], list[dict]]:
    sys.path.insert(0, _HERE)
    import restore_modality as rm  # 정렬·유사도·병합 판정 단일 출처
    lex = lexicon or load_lexicon()
    targets = [e for e in lex["entries"] if e.get("restore")]
    before_body = rm._checks.strip_summary_block(before)
    # 복원도 힌트와 같은 넓은 정규식을 쓴다. 안전장치는 '원문 문서 전체에 없던 낱말'이라는 조건이다 —
    # 좁은 정규식은 활용형을 놓쳤다(실측: "세 가지 렌즈로 살펴본다" 주입을 못 되돌림). r4 120건 재적용:
    # 되돌림 6→8, 평균 변화량 0.0014→0.0018, 애매한 1건(문자 그대로의 '갈린다')도 원문 문장으로 돌아갈 뿐이다.
    absent = [e for e in targets if not _matches(e, before_body, detect=True)]
    if not absent:
        return after, [], []
    body, summary = rm._checks.split_summary_block(after)
    pairs = rm.align(rm._m._split_sentences(before_body), rm._m._split_sentences(body))
    restored: list[dict] = []
    skipped: list[dict] = []
    for idx, (b, a) in enumerate(pairs):
        b, a = b.strip(), a.strip()
        if not a:
            continue
        new = [e["headword"] for e in absent if _matches(e, a, detect=True)]
        if not new:
            continue
        rec = {"after": a, "before": b, "headwords": new}
        if not b:
            skipped.append({**rec, "reason": "짝 원문 문장 없음(삽입 문장)"})
            continue
        # 원문 문장에 '바꿈 우선' 표제어가 있었고 윤문이 그것을 고치던 중이면 되돌리지 않는다 —
        # 되돌리면 고치려던 표제어가 부활한다(실측: "두 렌즈를" → 윤문 "두 층위를" → 복원 시 '렌즈' 부활).
        # 표제어→표제어 치환 자체는 [어휘 점검] 규칙 위반이므로 보류로 보고만 한다.
        fixing = [e["headword"] for e in targets if _matches(e, b, detect=True) and not _matches(e, a, detect=True)]
        if fixing:
            skipped.append({**rec, "reason": f"원문 문장의 표제어({', '.join(fixing)})를 고치던 중 — 되돌리면 그것이 돌아온다"})
            continue
        if rm._sim(b, a) < rm.MIN_PAIR_SIM:
            skipped.append({**rec, "reason": "짝 유사도 낮음 — 정렬 아티팩트 가능성"})
            continue
        if body.count(a) != 1:
            skipped.append({**rec, "reason": "결과에서 유일하게 특정되지 않음"})
            continue
        # 분할 — 원문 한 문장이 둘로 쪼개지면 짝 없는 출력 문장이 이웃에 끼어든다. 되돌리면
        # 쪼개진 나머지 조각이 남아 명제가 중복된다. restore_modality의 split_gap과 같은 판정
        # (삽입 이웃이 원문 문장의 내용어 2개 이상을 나눠 가졌을 때만).
        b_tokens = rm._tokens(b)
        split_gap = any(
            not pairs[j][0].strip() and pairs[j][1].strip()
            and len([t for t in rm._tokens(pairs[j][1]) & b_tokens if len(t) > 1]) >= 2
            for j in (idx - 1, idx + 1) if 0 <= j < len(pairs))
        if split_gap:
            skipped.append({**rec, "reason": "문장 분할 의심 — 되돌리면 명제가 중복된다"})
            continue
        neighbor_gap = (idx > 0 and not pairs[idx - 1][1].strip()) or (
            idx + 1 < len(pairs) and not pairs[idx + 1][1].strip())
        foreign = [t for t in rm._tokens(a) - rm._tokens(b) if len(t) > 1]
        longer = len(a) >= len(b) * rm.MERGE_LEN_RATIO
        if neighbor_gap or (longer and len(foreign) >= rm.MERGE_FOREIGN_TOKENS):
            skipped.append({**rec, "reason": "문장 병합 의심 — 되돌리면 다른 명제가 사라진다"})
            continue
        body = body.replace(a, b, 1)
        restored.append(rec)
    return body + summary, restored, skipped


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hints")
    h.add_argument("--input", required=True)
    h.add_argument("--genre", default=None)
    h.add_argument("--json", action="store_true")
    r = sub.add_parser("restore")
    r.add_argument("--before", required=True)
    r.add_argument("--after", required=True)
    r.add_argument("--out", default=None)
    r.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "hints":
            text = open(a.input, encoding="utf-8").read()
            hits = find_hits(text, a.genre)
            print(json.dumps(hits, ensure_ascii=False, indent=1) if a.json else render_hint_block(hits))
            return 0
        before = open(a.before, encoding="utf-8").read()
        after = open(a.after, encoding="utf-8").read()
        fixed, restored, skipped = restore(before, after)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as f:
                f.write(fixed)
        else:
            sys.stdout.write(fixed)
        report = {"restored": len(restored), "skipped": len(skipped),
                  "restored_items": restored, "skipped_items": skipped}
        if a.json:
            print(json.dumps(report, ensure_ascii=False, indent=1), file=sys.stderr)
        else:
            print(f"[lexical-restore] 되돌림 {len(restored)}건 · 보류 {len(skipped)}건", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 — 변형기는 윤문을 막지 않는다
        print(f"[lexical-layer] 건너뜀: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
