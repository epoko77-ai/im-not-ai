# Evidence — how the patterns were validated

> English edition of `skills/humanize-korean/references/empirical-validation.md` (measured 2026-07). The Korean file is authoritative.
>
> Read this before deciding whether to trust the taxonomy. It includes the rules we **rejected**, the measurement error we made, and the limits of the design.

## Why we ran a corpus study

A literature review found less support than the taxonomy had been claiming:

- 김정우 (2007), which the taxonomy cited, is a **typological and prescriptive** paper, not a quantitative one. It reports no frequency or discriminative statistics. Valid as typological grounding; citing it as empirical evidence is over-attribution.
- **Effectively no Korean translationese study reports statistical significance.** Even 최희경 (2016) gives normalized frequencies only — no chi-square, no log-likelihood.
- The only Korean features with measured discriminative power come from 김혜영 (2009), a 1M-eojeol contrastive study: syntactic passives (`-아/어 지다`, `-에 의하여`), 2nd/3rd person pronouns, and the bound nouns `것`/`때문`.
- KatFish (ACL 2025), the only Korean LLM-text detection benchmark, validates **spacing, POS n-gram diversity and commas** — a different layer (orthographic and morphological distribution) from what the taxonomy describes.

So most patterns had typological grounding but no discriminative evidence. We measured our own.

## Design

- **AI corpus** — 20 topics (column, essay, report, news analysis, policy, book review, academic summary) sent to Fable 5, GPT-5.6-sol and Haiku 4.5, giving 60 pieces of 400–900 characters each. **Bare prompts**: first response, no genre coaching, no self-editing instruction. Three models so that one model's habits aren't mistaken for "AI-ness".
- **Human corpus** — 60 Korean prose pieces verifiably published **before 2022-01-01** (pre-ChatGPT, so no AI contamination), from 40 outlets (한겨레, 시사IN, KDI 나라경제, 오마이뉴스, 프레시안, 브런치…), averaging 842 characters, publication dates double-checked against Wayback Machine captures. Translations excluded.
- **Genre control** — opinion, essay and analysis only. Straight news reporting was excluded because its past-tense `했다` distribution confounds the comparison.
- **Test** — log-likelihood ratio G² (Dunning 1993). G² > 3.84 = p<0.05, > 6.63 = p<0.01, > 10.83 = p<0.001, > 15.13 = p<0.0001.

### Known limitations — carry these with any citation

1. The human corpus is **edited professional prose**. Its abundance of quotations, parentheses and long sentences may reflect professionalism and editing rather than humanness. On a 15-piece personal-blog subset the gaps shrank sharply (long sentences 113.5 → 27.7 per 1000). Read this as a contrast with **published good writing**, not with "humans in general".
2. The two corpora are **not topic-matched**. Content-word differences are a byproduct of topic and were excluded from the conclusions; only structural and functional layers (sentence endings, punctuation, sentence length, antithesis) inform them.
3. n = 60 per side. Conclusions about low-frequency patterns are provisional until re-confirmed at higher frequency.
4. This compares **natively written Korean**. The design does not test "Korean produced by translating or summarizing an English source". Translation-context rules such as A-16 are out of range.

## Confirmed — significantly over-represented in AI, structural layer

| Pattern | AI /1k | Human /1k | Ratio | G² |
|---|---|---|---|---|
| **C-8/C-14 negative antithesis `A가 아니라 B`** | 5.8 | 0.6 | **9.2×** | 41.7 **** |
| **Comma excess** | 49.1 | 33.4 | 1.5× | 25.5 **** |
| **Share of sentences containing commas** | 394.8 | 285.5 | 1.4× | 13.3 *** |
| **`~한다` ending concentration** | 95.0 | 52.2 | 1.8× | 9.5 ** |

The antithesis result is the strongest signal in the study — 18× against the personal-blog subset, and consistent across all three model families, so it is not one vendor's habit. The comma result reproduces KatFish's direction (human 26% vs LLM 61%).

## New candidates — what AI *fails* to do

Absence is as strong a signal as excess. We rule-ify only what can be prescribed; the rest is observed but never prescribed, because a prescription to produce something absent invites semantic drift.

| Candidate | AI /1k | Human /1k | G² | Prescribable? |
|---|---|---|---|---|
| **Missing long sentences** (100+ chars) | 8.1 | 91.3 | 60.9 **** | ✅ join adjacent sentences (adding content forbidden). This is what E-1 really is: not "uniformity" but *absence of long sentences* |
| **Missing quotations** | 0.0 | 8.7 | 96.4 **** | ❌ observe only — inventing quotations is unacceptable |
| **Missing parentheses** | 1.2 | 10.6 | 69.5 **** | ❌ observe only |
| **Past-tense avoidance** (`했다`, `었다`) | 29.9 | 135.6 | 54.7 **** | △ genre-confounded (opinion vs narrative); provisional |

Magnitudes here risk inflation from limitation ①. On the personal-blog subset, long sentences run 4× rather than 11×, though quotations remain at 0.0. **Direction certain, multipliers to be read conservatively.**

## Rejected — rules the data killed

Each rejection was adversarial: GPT-5.6-sol (ultra) was instructed to defend the pattern as strongly as possible, and only defences that lost to the data were recorded as rejections.

| Pattern | Evidence | Outcome |
|---|---|---|
| **A-2 — always redistribute `~를 통해`** | 최희경 (2016): non-translated 84.4 vs translated 42.1 — native writers use it **twice as often**. Barely present in our AI corpus either | Defence self-assessed as "not beating 'barely present'" → **rejected**. Suppress only repetition within a document; preserve 1–2 uses |
| **I-1 — always flatten `것이다` endings** | Precise measurement of `~것이다`: AI 20.4 vs human 43.0 (G²=6.2) — humans use it twice as often. The defence's positional and repetition hypotheses also failed (paragraph-final 0.3×, consecutive repetition AI 0.0) | **Rejected**. Flatten only at 3+ consecutive occurrences |

⚠️ **Measurement error, corrected.** Our first I-1 measurement counted the final two characters of the ending (`이다`), which swept in every `~이다` ending (reported at the time as AI 137.0 vs human 142.1, G²=0.1). Measuring `~것이다` specifically gives AI 20.4 vs human 43.0. The conclusion (rejection) is unchanged; the supporting numbers are corrected here.

## Kept after re-examination — deliberately not rejected

| Pattern | Why it survived |
|---|---|
| **A-16 pronoun over-translation** | The rule is scoped to **translation contexts** (every example is English→Korean). Our corpus is natively written prose, which never creates the rule's triggering condition — so it was **not under test**. That humans use `그는/그의` more in native prose (AI 0.0 vs human 1.9) supports "do not fire in native contexts"; it does not refute the rule. Even in a 200-character clustering window, the event the rule defines (3+ per paragraph) is more common in humans, 3.9% vs 0.7% |
| **C-1 enumeration markers** | Human occurrences were 0 in our sample — but **opinion and essay genres rarely enumerate at all**. Academic, manual and expository writing differ. The taxonomy already holds this conservatively (demoted S1→S2 in v2.0.1, default preserve), and we will not overturn that on a genre-biased sample. Recorded narrowly as "an AI signal within opinion and essay genres" |

## What this means for an implementation

- The strongest, most portable signal is **C-8/C-14 antithesis**. If you implement one thing, implement that.
- **Do not treat frequency rules as bans** — A-2 and I-1 are the cautionary cases, and both target constructions that good human writers use *more* than models do.
- **Never prescribe absence-filling** except sentence joining, which adds no content.
- Reproduction: `imnotai-web/scripts/stress-analyze.ts` with corpora at `scripts/{gen-*,human-corpus}.json`. The corpora themselves are not committed here for copyright reasons; method and results are.

**No rule is retired on one sample or one test.** Rejections are recorded only after re-measurement and an adversarial defence.
