"""Humanize KR v1.6 quantitative metrics calculator.

External pre-processor for the monolith fast path. Run BEFORE the monolith
agent — its output (prepended to the input text) gives the LLM a numerical
baseline read so it does not waste tool-call budget computing comma rates
or counting hanja suffixes.

Hard rule: standard library ONLY (json/re/math/collections/os/sys/argparse).
No konlpy/bareun/mecab/spaCy. We approximate morphological analysis with
regex + a small hanja suffix dictionary. Final judgement is monolith's job.

CLI:
    python metrics.py --input run/01_input.txt \
        --genre essay --output run/00_metrics.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter
from typing import Any

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

VERSION = "v1.6"

# Connective endings (-고, -며, -지만, -면서, -아서, -어서) followed by a comma.
# All of these end at a syllable boundary, so we anchor to the syllable + ",".
# Use a non-capturing group; allow space before comma (Korean writers
# sometimes type "...고 ,").
_ENDING_COMMA_RE = re.compile(
    r"(?:고|며|지만|면서|아서|어서)\s*,"
)

# Eojeol = whitespace-separated token. Strip trailing punctuation for length
# accounting but keep raw token for diversity / suffix tests.
_EOJEOL_SPLIT_RE = re.compile(r"\s+")

# Sentence boundary: . ! ? + closing quote/bracket optional + whitespace or EOS.
# Korean text rarely uses semicolons; we keep them out to avoid false splits.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.!?。])\s+")

# Hanja-style nominalizer suffixes: 성, 적, 화. We only count them when the
# *token* ends with one of these AND has at least 2 chars before — that
# excludes the standalone particles "적" / "성" / "화" and short adverbial
# uses. We also skip pure-Hangul exact matches in a small block-list.
_HANJA_SUFFIXES = ("성", "적", "화")
_HANJA_BLOCK = {
    # Common false positives — bare verbs / nouns that happen to end in these
    # syllables but are not -성/-적/-화 nominalizations.
    "있는화", "되는화",  # placeholder — extend as needed
    "맞아", "와서",  # not actually -화 but caught for safety
}

# Tokens we never count for hanja density: numerals, English, single-char.
_PUNCT_STRIP_RE = re.compile(r"[\.,!?;:\(\)\[\]\{\}\"'`~、。“”‘’\-]+")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts = _SENTENCE_SPLIT_RE.split(text)
    # Each `parts[i]` may contain newlines; flatten on \n too.
    out: list[str] = []
    for p in parts:
        for line in p.split("\n"):
            line = line.strip()
            if line:
                out.append(line)
    return out


def _eojeols(text: str) -> list[str]:
    return [tok for tok in _EOJEOL_SPLIT_RE.split(text.strip()) if tok]


def _strip_punct(token: str) -> str:
    return _PUNCT_STRIP_RE.sub("", token)


# ---------------------------------------------------------------------------
# 6 + 2 metric functions (signatures requested in the brief)
# ---------------------------------------------------------------------------


def comma_inclusion_rate(text: str) -> float:
    """Ratio of sentences containing 1+ commas (0~1)."""
    sents = _split_sentences(text)
    if not sents:
        return 0.0
    with_comma = sum(1 for s in sents if "," in s)
    return with_comma / len(sents)


def comma_usage_rate(text: str) -> float:
    """Average comma count per sentence."""
    sents = _split_sentences(text)
    if not sents:
        return 0.0
    return sum(s.count(",") for s in sents) / len(sents)


def ending_comma_rate(text: str) -> float:
    """Ratio of connective-ending positions immediately followed by a comma.

    Denominator = total connective-ending occurrences (with or without comma).
    Numerator   = ending + comma matches.
    Returns 0.0 when the denominator is 0.
    """
    if not text.strip():
        return 0.0
    # All occurrences of the endings (with optional trailing comma).
    all_endings = re.findall(r"(?:고|며|지만|면서|아서|어서)(?:\s*,)?", text)
    # Filter to those that actually represent a connective ending. The bare
    # syllable can occur inside other words (e.g. "고기"), so we require that
    # the syllable sit at an eojeol's end OR be followed by space/punct.
    # Approximation: count regex hits whose match ends at a token boundary.
    boundary_endings = re.findall(
        r"(?:고|며|지만|면서|아서|어서)(?=[\s,\.!?、。]|$)", text
    )
    if not boundary_endings:
        return 0.0
    # Count those followed by comma.
    with_comma = len(_ENDING_COMMA_RE.findall(text))
    return with_comma / len(boundary_endings)


def comma_segment_length(text: str) -> float:
    """Average eojeol-count of comma-delimited segments across sentences."""
    sents = _split_sentences(text)
    seg_lens: list[int] = []
    for s in sents:
        if "," not in s:
            seg_lens.append(len(_eojeols(s)))
            continue
        for seg in s.split(","):
            seg = seg.strip()
            if seg:
                seg_lens.append(len(_eojeols(seg)))
    if not seg_lens:
        return 0.0
    return sum(seg_lens) / len(seg_lens)


def conclusion_pivot_count(text: str, lexicon: list[str] | None = None) -> int:
    """Count occurrences of conclusion-pivot lexicon items."""
    items = lexicon or ["결론적으로", "따라서", "이를 통해", "그러므로"]
    return sum(text.count(w) for w in items)


def safe_balance_count(text: str, lexicon: list[str] | None = None) -> int:
    """Count occurrences of safe-balance hedge lexicon."""
    items = lexicon or ["양쪽 모두", "두 가지 모두", "장점도 있지만", "신중하게", "균형"]
    return sum(text.count(w) for w in items)


def hanja_nominalizer_density(text: str) -> float:
    """Token-level density of -성 / -적 / -화 endings (0~1).

    Token = whitespace-split eojeol after stripping trailing punctuation.
    A token "counts" only if it has >= 2 chars total (so bare "성", "적",
    "화" don't count) and its final char is one of the three suffixes.
    """
    tokens = [_strip_punct(t) for t in _eojeols(text)]
    tokens = [t for t in tokens if t]
    if not tokens:
        return 0.0
    hits = 0
    for t in tokens:
        if len(t) < 2:
            continue
        if t in _HANJA_BLOCK:
            continue
        if t[-1] in _HANJA_SUFFIXES:
            hits += 1
    return hits / len(tokens)


def lexical_diversity(text: str) -> float:
    """Type-token ratio over eojeols (unique / total)."""
    toks = [_strip_punct(t) for t in _eojeols(text)]
    toks = [t for t in toks if t]
    if not toks:
        return 0.0
    return len(set(toks)) / len(toks)


# ---------------------------------------------------------------------------
# Baseline + z-score
# ---------------------------------------------------------------------------


def _default_baseline_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    # Baseline ships next to metrics.py: references/baseline.json
    return os.path.join(here, "baseline.json")


def _load_baseline(path: str | None) -> dict[str, Any]:
    p = path or _default_baseline_path()
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_genre_cells(
    baseline: dict[str, Any], genre: str
) -> tuple[dict[str, Any], str | None]:
    """Return (cells, fallback_warning_or_None).

    Cells = mapping metric_key -> {"human": x, "ai": y, ...} merged across
    requested genre with global_average fill for missing fields.
    """
    genres = baseline.get("genres", {}) or {}
    requested = genres.get(genre)
    fallback = None
    if requested is None:
        fallback = f"baseline_genre_null:{genre}->essay"
        requested = genres.get("essay") or {}
    # Merge with global average for any missing keys.
    g = baseline.get("global_average", {}) or {}
    merged: dict[str, Any] = {}
    keys = set(requested.keys()) | set(g.keys())
    for k in keys:
        cell = requested.get(k) or g.get(k)
        if cell:
            merged[k] = cell
    return merged, fallback


def _z(value: float, human: float, ai: float, *, percent: bool) -> float | None:
    """Approximate z-score using (ai - human) / 2 as standard deviation.

    The KatFish report only gives two means per metric; with no spread
    published, we treat half the human-vs-AI gap as a one-sigma proxy.
    Direction: positive z means closer to AI. percent=True converts the
    measured value (0~1) to percent before subtracting human.
    """
    if human is None or ai is None:
        return None
    val = value * 100 if percent else value
    sd = abs(ai - human) / 2.0
    if sd == 0:
        return 0.0
    return (val - human) / sd


def _classify_risk(z_scores: dict[str, float | None], lexicon_hits: dict[str, int]) -> tuple[str, int]:
    score = 0
    for key in ("comma_inclusion_rate", "ending_comma_rate", "comma_segment_length"):
        z = z_scores.get(key)
        if z is not None and z > 1.0:
            score += 2
    ld = z_scores.get("lexical_diversity")
    if ld is not None and ld < -1.0:
        score += 1
    if lexicon_hits.get("conclusion_pivot_count", 0) >= 2:
        score += 1
    if lexicon_hits.get("safe_balance_count", 0) >= 2:
        score += 1
    hz = z_scores.get("hanja_nominalizer_density")
    if hz is not None and hz > 1.0:
        score += 1
    if score >= 6:
        band = "high"
    elif score >= 4:
        band = "medium"
    else:
        band = "low"
    return band, score


def _evidence_spans(text: str, lexicon: list[str]) -> list[str]:
    found: list[str] = []
    for w in lexicon:
        if w in text:
            found.append(w)
    return found


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def compute_all(
    text: str,
    genre: str = "essay",
    baseline_path: str | None = None,
) -> dict[str, Any]:
    """Compute all v1.6 metrics + z-scores + risk band for a single document."""
    baseline = _load_baseline(baseline_path)
    cells, fallback_warning = _resolve_genre_cells(baseline, genre)
    lex = baseline.get("lexicons", {}) or {}
    pivot_lex = lex.get("conclusion_pivot") or [
        "결론적으로", "따라서", "이를 통해", "그러므로",
    ]
    safe_lex = lex.get("safe_balance") or [
        "양쪽 모두", "두 가지 모두", "장점도 있지만", "신중하게", "균형",
    ]

    metrics: dict[str, float | int] = {
        "comma_inclusion_rate": comma_inclusion_rate(text),
        "comma_usage_rate": comma_usage_rate(text),
        "ending_comma_rate": ending_comma_rate(text),
        "comma_segment_length": comma_segment_length(text),
        "conclusion_pivot_count": conclusion_pivot_count(text, pivot_lex),
        "safe_balance_count": safe_balance_count(text, safe_lex),
        "hanja_nominalizer_density": hanja_nominalizer_density(text),
        "lexical_diversity": lexical_diversity(text),
    }

    # baseline cells use percent for inclusion/ending rates.
    z_scores: dict[str, float | None] = {}
    for key, percent in (
        ("comma_inclusion_rate", True),
        ("comma_usage_rate", False),
        ("ending_comma_rate", True),
        ("comma_segment_length", False),
    ):
        cell = cells.get(key)
        if cell:
            z_scores[key] = _z(metrics[key], cell.get("human"), cell.get("ai"), percent=percent)
        else:
            z_scores[key] = None

    # hanja_nominalizer_density baseline: report says 12 occurrences per doc
    # = S2 strong signal. We approximate by treating density 0.06 as human
    # reference and 0.12 as AI reference (rough proxy when no per-doc cells).
    z_scores["hanja_nominalizer_density"] = _z(
        metrics["hanja_nominalizer_density"] * 100, 6.0, 12.0, percent=False
    )
    # lexical_diversity has no baseline cell either; use rough 0.65 human /
    # 0.55 AI from typical Korean essay corpora as a placeholder. AI tends
    # to repeat tokens slightly more.
    z_scores["lexical_diversity"] = _z(metrics["lexical_diversity"], 0.65, 0.55, percent=False)

    lexicon_hits = {
        "conclusion_pivot_count": int(metrics["conclusion_pivot_count"]),
        "safe_balance_count": int(metrics["safe_balance_count"]),
    }
    risk_band, risk_score = _classify_risk(z_scores, lexicon_hits)

    out: dict[str, Any] = {
        "version": VERSION,
        "genre": genre,
        "char_count": len(text),
        "metrics": metrics,
        "z_scores": z_scores,
        "risk_band": risk_band,
        "risk_score": risk_score,
        "evidence": {
            "conclusion_pivots": _evidence_spans(text, pivot_lex),
            "safe_balances": _evidence_spans(text, safe_lex),
        },
    }
    if fallback_warning:
        out["warning"] = fallback_warning
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Humanize KR v1.6 metric runner")
    parser.add_argument("--input", required=True, help="Input text file path")
    parser.add_argument("--genre", default="essay", help="essay/poetry/abstract/...")
    parser.add_argument("--output", default=None, help="Output JSON path (optional)")
    parser.add_argument(
        "--baseline", default=None, help="Override baseline JSON path"
    )
    args = parser.parse_args(argv)

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()

    result = compute_all(text, genre=args.genre, baseline_path=args.baseline)

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    print(result["risk_band"])
    return 0


if __name__ == "__main__":
    sys.exit(_main())
