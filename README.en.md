# im-not-ai (Humanize KR) — a de-AI-ifier for Korean text

> 한국어 문서: [`README.md`](README.md)

LLMs write Korean that *reads* like translated English. Native speakers spot it instantly, and no amount of prompting ("write naturally in Korean") fixes it — the tells are structural, not stylistic.

**im-not-ai** rewrites AI-written Korean into natural Korean **without changing a single fact** — style, rhythm and phrasing only. MIT licensed, runs as a CLI skill inside Claude Code, GitHub Copilot CLI, OpenAI Codex CLI and Gemini CLI.

```
"AI 기술을 통해 효율을 높일 수 있다"      →  "AI로 효율을 높인다"
"이에 있어서 중요한 점은"                 →  "여기서 중요한 건"
"~에 의해 생성된"                         →  "~가 만든"
"결론적으로, 이는 시사하는 바가 크다"      →  (deleted)
```

## Documentation

| | |
|---|---|
| [`docs/en/quick-rules.en.md`](docs/en/quick-rules.en.md) | **The working artifact** — the rulebook a single-call implementation loads as its system prompt |
| [`docs/en/taxonomy.md`](docs/en/taxonomy.md) | All 71 patterns: severity, trigger, prescription, genre guards, detector schema |
| [`docs/en/evidence.md`](docs/en/evidence.md) | The corpus study — what was confirmed, what was **rejected**, and the limits of the design |
| [`docs/en/integration.md`](docs/en/integration.md) | Building this into a model or product, and the failure modes we hit in production |
| [English support](#english-support-humanize-english-v02) | **Writing in English?** `humanize-english` v0.2 ships in the same package — re-measured against English corpora, not translated from Korean |

Engineers integrating this should start with `integration.md`.

## Why a Korean-specific tool

English humanizers (QuillBot, Undetectable AI, Hix) are weak on Korean because the giveaway isn't word choice — it's **translationese**: English syntax wearing Korean morphology. Double passives, `~를 통해` for every English "through/via", left-branching relative clauses imported from English, compulsive third-person pronouns (Korean normally drops them), mechanical "first / second / third" scaffolding, and a closing paragraph that always "carries significant implications."

We catalogued these as **10 categories × 70 sub-patterns**, each with a severity (S1 decisive / S2 strong / S3 weak) and a prescription, grounded in Korean translation-studies literature (KatFish, post-editese metrics, Wendler et al. ACL'24, Lost in Literalism ACL'25).

| ID | Category | Example tells |
|----|----------|---------------|
| A | Translationese | `~를 통해`, `~에 있어서`, double passive `~되어진다`, forced `그/그녀`, left-branching relative clauses |
| B | English over-quoting | Excessive parenthetical glosses, untranslated loanwords |
| C | Structural AI patterns | Mechanical 첫째/둘째/셋째, bullet & emoji overload, comma after connective endings |
| D | AI stock phrases | "결론적으로", "시사하는 바가 크다", "주목할 만하다", "혁신적인" |
| E | Rhythm uniformity | Low sentence-length variance, repeated sentence endings, honorific drift |
| F | Modifier redundancy | "매우/정말", synonym doubling, `~적/~성/~화` inflation |
| G | Hedging pile-up | "~할 수 있을 것으로 보인다" stacked hedges |
| H | Connective spam | Sentence-initial 또한/따라서/즉 in sequence |
| I | Dummy nouns | "것이다", "점", "수", "바", "~할 필요가 있다" |
| J | Visual decoration | Bold, quote marks and em-dash overuse |

All 71 patterns in English: [`docs/en/taxonomy.md`](docs/en/taxonomy.md). Korean SSOT with worked examples: [`ai-tell-taxonomy.md`](skills/humanize-korean/references/ai-tell-taxonomy.md) · playbook: [`rewriting-playbook.md`](skills/humanize-korean/references/rewriting-playbook.md) · sources: [`scholarship.md`](skills/humanize-korean/references/scholarship.md)

## Four hard rules

1. **Meaning is immutable** — facts, claims, numbers, proper nouns and direct quotes survive verbatim.
2. **Evidence-based edits** — only detected spans are touched; undetected text is left alone.
3. **Genre preserved** — a column doesn't become an essay, a report doesn't become prose poetry.
4. **No over-editing** — a deterministic gate warns above a 30% change rate and hard-stops above 50%.

Explicitly out of scope: numbers, units, dates, proper nouns, quoted speech, statutory text, academic terms of art.

## Architecture — the text decides the cost

A deterministic pre-scoring shim grades the input and emits a `route_hint`. The condition of the text picks the route; the route picks the number of LLM calls. Savings come from **fewer calls**, not from a cheaper model (model choice stays with the user).

| Route | LLM calls | When | Pipeline |
|---|---|---|---|
| **light** | **1** | Already well-written | Single conservative pass; exits early with "this is already fine" |
| **standard** | **2** | Ordinary AI draft | Diagnose → targeted rewrite (10k chars still fits one call) |
| **heavy** | **3+** | Dense AI slop, >15,000 chars, or audit trail required | Diagnose → rewrite (chunked only if needed) → finalize against the source |

```
input
  ↓ prepare_monolith_input.py     quantitative pre-score + route_hint
  ├─ light    → monolith ×1                                → final.md
  ├─ standard → diagnostician → targeted monolith          → final.md
  └─ heavy    → diagnostician → monolith → finalizer       → final.md
  ↓ verify_change_rate.py         deterministic gate (exit code), all routes
```

Measured: running a 10,000-character piece as 7 chunked calls cost 610K tokens; the same piece in a single call cost 134K at equal quality — reloading the rulebook per chunk eats the savings. Hence single-call-first.

## Install

**Claude Code** (plugin marketplace, no clone):

```
/plugin marketplace add epoko77-ai/im-not-ai
/plugin install humanize-korean@im-not-ai
```

**GitHub Copilot CLI**:

```bash
copilot plugin marketplace add epoko77-ai/im-not-ai
copilot plugin install humanize-korean@im-not-ai
```

**Claude Code / Codex CLI** (clone + script):

```bash
git clone https://github.com/epoko77-ai/im-not-ai.git
cd im-not-ai && ./install.sh
```

Then paste Korean text and ask for it in plain language ("이 글 AI 티 없애줘"), or call `/humanize-korean`. Copilot and Codex run the single-call path only; the multi-call diagnose/finalize paths are Claude Code-specific. Full guide: [`INSTALL.md`](INSTALL.md).

## English support (`humanize-english` v0.2)

The Korean rules were **not translated into English.** They were re-measured against English corpora — and that process caught three rules ported from Korean whose direction was **backwards**:

| Ported rule | What we assumed | What the research says |
|---|---|---|
| Remove agentless passives | LLMs overuse them | Reinhart et al. 2025 (*PNAS*): LLMs use them at **half** the human rate |
| Cut hedges (`may`, `might`) | LLMs hedge too much | Three studies converge: LLMs **underuse** hedges |
| Cut qualifiers | Same | Same — removing them makes text *more* AI-like, and changes claim strength |

All three were withdrawn. That correction is the point of the project: the rulebook carries an evidence grade per rule, and a rule with community support but contrary peer-reviewed evidence does not ship.

**Evidence, all published in-repo:**

| | |
|---|---|
| [`lang/en/quick-rules.md`](lang/en/quick-rules.md) | The rulebook — Tier A 8 + Tier B 7, evidence grade per rule |
| [`lang/en/scholarship.md`](lang/en/scholarship.md) | Academic anchors (Kobak 2025 *Science Advances*, Reinhart 2025 *PNAS*, Jiang & Hyland 2025 *ESP*) + a correction log |
| [`lang/en/candidate-pool.md`](lang/en/candidate-pool.md) | Community axis — the 41k★ `blader/humanizer` list, cross-checked against the research |
| [`lang/en/baseline.json`](lang/en/baseline.json) | Our own measurements: every AUC, CI, per-model split and null result |

**Two genres are validated.** Thresholds turned out to be genre-dependent, so the router picks a calibrated cell:

| Threshold cell | Corpus | Router separation |
|---|---|---|
| `abstract` | arXiv: 42 human vs 21 AI | **0.95** |
| `blog` (default) | LessWrong · Paul Graham · SSC: 100 human vs 102 AI | **0.65** |
| `blog` on GPT prose | same humans vs 34 from the codex CLI | **1.37** |

Anything outside those two cells is **unvalidated**, and the skill says so to the user instead of pretending otherwise. Three blog-cell metrics that looked strong turned out to be per-model idiolect and were dropped.

Five deterministic gates run on every path: change rate, content preservation (numbers, quotes, citations, headings), modality loss (hedges and obligations turning into flat assertions), tell re-injection, and under-editing. The `heavy` / verification path stays closed for English — we have no measured evidence to back the claim it would make.

## Ethics

This is a **Korean writing-quality tool**, not an "AI detector bypass." It is not a guarantee of academic or journalistic integrity, and it will not launder a text's provenance — it only removes the syntactic residue of English-shaped generation. The taxonomy is free to reuse for research, teaching and tool integration under MIT.

## License & contributing

MIT — see [`LICENSE`](LICENSE). Integration into other products, forks and commercial use are all permitted; ship the copyright notice and license copy.

Found a tell we don't catch? Open an [Issue](https://github.com/epoko77-ai/im-not-ai/issues) with two or more real examples (ideally from different models, genres or authors) and the taxonomist agent reviews it for promotion. See [`CONTRIBUTORS.md`](CONTRIBUTORS.md).
