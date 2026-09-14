# Integration guide — building this into a model or product

Written for engineers who want the behaviour natively, not as a CLI wrapper. MIT licensed; integrate, fork and ship it commercially. What follows is what we learned running this in production at [imnotai.kr](https://imnotai.kr), including the parts that went wrong.

## 1. What this actually is

**A post-editing rulebook, not a generation-time style guide.** That distinction drives every integration decision below.

Roughly a third of the rules are **frequency-conditional**: `~를 통해` 3+ times *in one paragraph*, sentence-initial connectives 5+ times *per document*, nominalizers 12+ times *per document*, `A가 아니라 B` antithesis 3+ times. These are not bans. `~를 통해` is good Korean — native non-translated prose uses it *twice as often* as translated prose (최희경 2016). Only the pile-up is a tell.

A generation-time system prompt cannot count occurrences in text that does not exist yet. Feed it a frequency rule and the model does the only thing it can: treats it as an absolute prohibition. **We shipped exactly this bug.** Rules phrased as tendencies came back as imperatives, and the output was worse than the input — stilted in a new way, avoiding perfectly ordinary constructions.

So:

| Rule type | Generation time | Post-editing pass |
|---|---|---|
| Absolute (A-8 double passive, C-5 emoji, D-2 significance inflation) | ✅ works as a constraint | ✅ |
| Frequency-conditional (A-2, H-1, F-4, C-8) | ❌ becomes a ban, degrades output | ✅ needs the finished text |
| Distributional (E-1 absent long sentences, E-2 ending monotony) | ❌ unmeasurable per-token | ✅ |

A native implementation should split the rulebook along that line rather than pasting all of it into a system prompt.

## 2. Three integration levels

**L1 — single rewrite pass.** Load [`quick-rules.en.md`](quick-rules.en.md) as the system prompt, pass the user's Korean text, take the rewrite. One call. This is what the Copilot CLI and Codex ports do, and it handles the large majority of real inputs. Start here.

**L2 — diagnose → targeted rewrite.** A first call identifies the 3–6 *dominant* patterns in this specific text and returns taxonomy IDs with prescriptions; a second call rewrites against that diagnosis. Two calls. This is materially better on structural tells (C-8 antithesis, E-1 rhythm), because a single pass reliably fixes particles and endings while leaving the structure of the piece untouched — a failure we measured in production before adding the diagnosis step.

**L3 — full pipeline with a finalizer.** Diagnose → rewrite → a final pass that compares against the **source** and applies local corrections only. Reserve for dense AI slop, texts over 15,000 characters, or when an audit trail is required.

Cost note: chunking is a trap. A 10,000-character piece run as 7 chunked calls cost 610K tokens; the same text in one call cost 134K at equal quality, because every chunk reloads the rulebook and the diagnosis. Single-call first, chunk only above ~15,000 characters.

## 3. Put the deterministic parts in code, not in the model

The single most important lesson: **meaning preservation cannot be enforced by prompt alone.** A prompt is probabilistic and it leaks. But "did a number appear that wasn't in the source", "did a quotation change", "did a footnote vanish", "how much of the text changed" are all decidable in code.

Reference implementations in this repo, all zero-LLM:

| Script | Job |
|---|---|
| `scripts/prepare_monolith_input.py` | Pre-scores the input, emits `route_hint` (light/standard/heavy) and chunk boundaries |
| `scripts/verify_change_rate.py` | Change-rate gate — 30% warning, 50% hard stop, communicated via exit code |
| `scripts/verify_gates.py` · `checks.py` | Structural convergence gates: antithesis count, number injection, golden-fixture checks |
| `scripts/sanitize_text.py` | Strips zero-width and bidi control characters, NFD→NFC normalization |

Two implementation details that cost us real debugging time:

- **Measure change rate on character bigrams, not word units.** Korean agglutinates: a light edit (`달했으며` → `였고`) replaces the whole eojeol, so word-level counting inflates the rate. Measured on the same texts: a legitimate rewrite scores 42% by word vs 35% by bigram, while a full rewrite scores 71% vs 61%. The bigram metric leaves a wider margin between "good edit" and "over-edit". Our first gate used word units and rejected legitimate rewrites.
- **Gates should judge, not repair.** On violation, fall back to the previous stage's output. A gate that tries to fix the sentence becomes a second, unaudited rewriter.

## 4. Failure modes we hit in production

Documented because they will recur in any implementation.

**Semantic drift is the dangerous one.** Removing empty rhetoric is subtractive in principle, but in practice a model asked to replace `시사하는 바가 크다` with "the concrete conclusion" will *invent* a conclusion. Related variants: hedge → assertion escalation beyond what the source supports (`~로 보인다` becoming a flat claim), and attribution verbs quietly changing ("said" → "warned"). Mitigations that worked: pass the **source text** to every stage including the final one (ours originally didn't — the naturalness pass never saw the original), make the last pass local-correction-only rather than a licensed full rewrite, and back it with the deterministic gates above.

**Structural rules get silently outvoted.** Precision-mode passes that received the rulebook but not the structural guide fixed particles and endings and never touched the antithesis pile-up the diagnosis had flagged. If your rewrite prompt is assembled from parts, verify that every path actually receives the structural rules.

**Genre-blind deletion.** "Remove mechanical 첫째/둘째/셋째" deleted legitimate enumeration anchors in expository and academic text, where enumeration is load-bearing. It regressed on us twice. Make this one genre-conditional and add a regression fixture.

**Evaluate with fixtures, not vibes.** Prompt changes are a slot machine at n=1. `tests/golden/` and `tests/fixtures.json` exist for exactly this; `scripts/eval_baseline.py` and `eval_compare.py` run before/after comparisons.

## 5. What the model needs that a rulebook can't give

Detection is the easy half. The hard half is knowing *when not to fire*, and that is a genre and provenance judgement:

- A-16 (pronoun overuse) is scoped to **translation contexts**. In natively written Korean, humans use `그는/그의` *more* than AI does — firing the rule there makes the text worse.
- C-1 (enumeration markers) is a tell in opinion and essay genres, and normal in manuals, academic and expository writing.
- Quotation and parenthesis scarcity are strong AI signals (G²=96.4 and 69.5 in our corpus) but are **observation-only** — a model that invents quotations to look human has committed a far worse error than sounding like AI.

See [`evidence.md`](evidence.md) for how each of these was measured, including the rules we **rejected** after testing.

## 6. Start here

1. Read [`quick-rules.en.md`](quick-rules.en.md) — that is the working artifact.
2. Read [`evidence.md`](evidence.md) — decide for yourself whether the rules are load-bearing.
3. Full taxonomy with detection conditions and worked examples: [`skills/humanize-korean/references/ai-tell-taxonomy.md`](../../skills/humanize-korean/references/ai-tell-taxonomy.md) (Korean; the pattern strings are the asset and are not translated).
4. Questions, or a tell we don't catch: [Issues](https://github.com/epoko77-ai/im-not-ai/issues).
