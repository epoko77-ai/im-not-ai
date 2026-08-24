# Korean AI-Tell Taxonomy (English edition) — all 72 patterns

> English reference for `skills/humanize-korean/references/ai-tell-taxonomy.md` (v2.0.1, valid as of 2026-07). **The Korean file is the SSOT**; where the two disagree, it wins.
>
> Korean pattern strings are the asset and appear verbatim — translating them would destroy them. Triggers, prescriptions, genre guards and evidence notes are in English. Every ID here maps 1:1 to the Korean SSOT; the fast rulebook ([`quick-rules.en.md`](quick-rules.en.md)) is *generated* from it and carries roughly 50 of these.

## Severity

- **S1 critical** — one occurrence is nearly enough to conclude "this is AI". Remove unconditionally.
- **S2 high** — 1–2 occurrences can be natural; 3+ in a document reads as AI. Density-based removal.
- **S3 low** — not a problem alone; reinforces the AI impression when stacked with others. Rhythm-level adjustment.

## `quick` flag

`quick: true` marks patterns detectable from **surface signals alone** — those compile into the single-call rulebook (held to ~50 to protect the token budget). `quick: false` marks patterns needing **document-level judgement** (rhythm, structure, distribution, POS analysis), so they run only on the strict path. New patterns default to `false`.

---

## A. Translationese (A-1 ~ A-20)

Traces of English or Japanese syntax forced through Korean word order and particles. The most decisive AI signature.

| ID | Sev | Trigger | Prescription | quick |
|---|---|---|---|---|
| **A-1** | S1 | `~에 대하여/대해서` overused | Attach the object particle directly: `X에 대해 논의` → `X를 논의` | ✅ |
| **A-2** | S2 | `~를 통하여/통해` 3+ per paragraph | Keep 1–2; redistribute as `~로`, `~해서`, `~함으로써`. **Not a ban** — see the rejection note below | ✅ |
| **A-3** | S1 | `~에 있어(서)` | `~에서` or `~을 볼 때` | ✅ |
| **A-4** | S2 | `~라는 점에서` 3+ | `~서`, `~라는 이유로` | ✅ |
| **A-5** | S2 | `~와 관련하여` / `~와 관련된` | `~에`, `~의` | ✅ |
| **A-6** | S2 | `~에 기반하여` / `~을 바탕으로` overused | `~로`, `~을 보고` | ✅ |
| **A-7** | S1 | `가지고 있다`; light-verb constructions (have/make/take/give + noun) translated literally | Reduce to adjective or verb, or double-subject: `강한 경쟁력을 가지고 있다` → `경쟁력이 강하다` | ✅ |
| **A-8** | S1 | Double passive `~되어진다` / `~지게 된다` | Active if possible, else single passive: `판단되어진다` → `판단된다` | ✅ |
| **A-9** | S2 | `~에 의해` passive | Promote the agent: `AI에 의해 생성` → `AI가 만든` | ✅ |
| **A-10** | S2 | `~할 수 있다` overused | Assert: `높일 수 있다` → `높인다` | ✅ |
| **A-11** | S2 | `~을 위해` purpose clauses overused | `~려고`, `~도록`, `~위한` | ✅ |
| **A-12** | S2 | Automated passives `만들어지다` / `이루어지다` | `합의가 이루어졌다` → `합의했다` / `합의에 이르렀다` | ❌ |
| **A-13** | S2 | English-style noun stacking with particles dropped | Restore particles: `AI 기술 발전 속도 가속화` → `AI 기술의 발전 속도가 빨라지고 있다` | ❌ |
| **A-14** | S2 | `그리고` joining clauses like English *and* | Compress with connective endings `-고`, `-며`, `-면서`: `그는 보고했다. 그리고 자리에 앉았다.` → `그는 보고하고 자리에 앉았다.` | ❌ |
| **A-15** | S2 | Abstract subject + all-purpose verb (`보여준다/제공한다/가져온다`); literal causative, cognition and speech verbs | Restore a concrete subject; causatives → adverbial `X 때문에/덕분에/로 인해`; suggest/show/indicate → `~에 따르면 ~이다` | ✅ |
| **A-16** | S1 | `그/그녀/그것/그들` 3+ per paragraph — 1:1 mapping of he/she/it/they | Delete 50–70% (Korean's zero pronoun); name the referent only at speaker or scene changes; `they` → `사람들·우리·일부·어떤 이들` | ✅ |
| **A-17** | — | *(held)* Mechanical `-들` plural marking on inanimate and abstract nouns | **On hold since v2.0** — strong scholarly anchors, but zero positives in our corpora. ID reserved so pattern IDs stay stable; the `deul_overuse_rate` metric keeps measuring it | ❌ |
| **A-18** | S2 | Left-branching pre-nominal modifier / relative clause, 3+ eojeol | Split the sentence, or postpose as apposition: `X를 만났는데, 그 X는 ~` | ✅ |
| **A-19** | S2 | Stacked particles `~에서의·~에로의·~으로의·~에의·~으로부터의` | Unfold into a clause or phrase. **Plain `~의` is explicitly excluded** (no scholarly consensus — caveat C5) | ✅ |
| **A-20** | S2 | Inanimate or abstract subject + periphrastic causative `~게 만들다` — English `X makes Y do` mapped one-to-one (`가격은 검토를 시작하게 만들 뿐`) | Demote the subject to a cause adverbial and restore the human agent: `가격 때문에 검토를 시작했다`. Keep the causative only as `-게 하다`, or compress into one transitive verb. **Human or institutional subjects are not targets.** Genre guard: formal expository prose from the first occurrence, essay/review/spoken copy above 3 per document | ✅ |

**A-16 scope guard (important).** This rule applies **only to translation contexts** — text rendered or summarized from an English source. It must not fire on natively written Korean: in our contrastive measurement humans used `그는/그의` *more* than AI (1.9 vs 0.0 per 1000 eojeol), and even the rule's own triggering event (3+ in a 200-character window) occurred in 3.9% of human texts vs 0.7% of AI. Modern LLMs suppress pronouns when writing Korean natively, so firing this outside translation contexts damages human writing.

**A-2 rejection note.** "Always redistribute `~를 통해`" was **rejected** on evidence: native non-translated Korean uses it at 84.4 vs 42.1 in translated Korean (최희경 2016) — twice as often — and it barely appeared in our AI corpus. Only in-document repetition is suppressed. See [`evidence.md`](evidence.md).

## B. English over-quoting and terminology (B-1 ~ B-4)

| ID | Sev | Trigger | Prescription | quick |
|---|---|---|---|---|
| **B-1** | S2 | Parenthetical English gloss repeated on every occurrence (`~(Sovereign AI)`) | Gloss on first mention only; Korean alone thereafter | ✅ |
| **B-2** | S2 | Unexplained marketing buzzwords (seamless, robust, leverage) | Render marketing words in Korean; **keep** standard technical terms in the original (API, prompt, token). No mechanical literal translation | ✅ |
| **B-3** | S2 | Whole English sentences embedded as quotations with a translation alongside | Unless the original wording genuinely matters, paraphrase in Korean and cite the source | ❌ |
| **B-4** | S3 | `~라고 알려진`, `~로 일컬어지는` — literal *known as / so-called* | `'AGI'라고 알려진 범용 인공지능` → `범용 인공지능(AGI)` | ❌ |

## C. Structural patterns — formatting and layout (C-1 ~ C-12)

| ID | Sev | Trigger | Prescription | quick |
|---|---|---|---|---|
| **C-1** | S2 | `첫째, ~. 둘째, ~. 셋째, ~.` dominating a paragraph | **Default is to preserve.** Enumeration is legitimate Korean rhetoric; dissolving it wholesale damages the text. Only when 4+ items make a paragraph read like a metronome, prose-ify 1–2 or vary lexically (`우선 / 다음으로 / 마지막으로`). When keeping the list, deliberately vary item length and structure | ❌ |
| **C-2** | S2 | 3+ consecutive bullet blocks in a column or report | Merge into prose; keep lists only where enumeration carries meaning | ✅ |
| **C-3** | S2 | Schematic headings `## 도입 ## 본론 ## 결론` | In prose genres remove the headings; in reports make them specific (`AI 규제의 세 가지 균열점`). **Exception:** genuine numbered section titles in academic and report writing (`Ⅱ.`, `(3)`, chapter titles) are structure — never remove or absorb them | ❌ |
| **C-4** | S2 | Every paragraph opening with its own topic sentence (English composition-textbook shape) | Let some paragraphs open with a case, a scene or a quotation | ❌ |
| **C-5** | S1 | Emoji overload (list heads, headings, emphasis) | Delete all in column and report genres | ✅ |
| **C-6** | S2 | A one-line summary box under every heading (`이 섹션에서는 ~를 다룬다`) | Delete. Korean prose starts with the substance | ❌ |
| **C-7** | S2 | Paragraph-initial `먼저–반면–결국` three-beat formula | Cut to 1–2 connectives or dissolve into the prose | ✅ |
| **C-8** | S1 | `A인가, B인가` antithesis 3+, including the negative variant `A가 아니라 B` / `A라기보다 B다` | Keep one; make the rest asymmetric — mix a question with a declarative, or make one side long and the other short. `A가 아니라 B` → `B가 핵심이다`, preserving meaning | ✅ |
| **C-9** | S2 | Parenthesized number indexing `1) 2) 3)` | Dissolve into prose, or vary with `우선~`, `다음으로~` | ✅ |
| **C-10** | S2 | Repeated colon-subtitle headings `X: Y` or `X: A에서 B로` | Compress to a single noun phrase — but preserve genuine academic and report section titles | ✅ |
| **C-11** | S1 | Comma directly after a connective ending (`-고/-며/-지만/-면서/-아서/-어서`) | Delete the comma. 6+ occurrences is a strong signal | ✅ |
| **C-12** | S2 | Document-level: more than 50% of sentences contain at least one comma | Convert some to (a) split short sentences, (b) absorption into connective endings, (c) plain deletion. Human baseline 26–33%; score above z>1.0 | ❌ |

**C-8 is the strongest measured signal in the entire taxonomy.** Negative antithesis density ran 5.8 per 1000 in AI vs 0.6 in humans — **9.2×**, G²=41.7, p<0.0001, and 18× against personal blogs — consistent across Fable, GPT and Haiku, so it is not one vendor's habit. If you implement one rule, implement this one.

**C-11 and C-12 are different measurements.** C-11 is positional (comma after a connective ending); C-12 is distributional (share of sentences with any comma). C-11 carries 4.84× separability in KatFish (ACL 2025) — the strongest single indicator found in the external literature.

**C-1 severity history.** Demoted S1 → S2 in v2.0.1. Combined with the S1 definition ("remove unconditionally"), it was dissolving even three-item enumerations — over-editing that generated real user complaints in the production web service. Human writers use enumeration constantly; density-based judgement is correct.

## D. AI signature phrases (D-1 ~ D-7) — S1

Stock expressions Korean human writers rarely produce and LLMs emit repeatedly. Replace on sight.

> **Reverse insertion is forbidden.** This category is a **removal target, never a generation target.** Introducing D-class stock phrases that were not in the source (`기록적인 성과를 거두었다`, `괄목할 만한`, `~로 평가된다`, `주목받았다`, `의미가 크다`) during rewriting is self-contradictory and banned. Replacing a source's living voice (`얼마나 대단했냐면 —`, `확정지은 겁니다`) with these is not polishing; it is driving in reverse.

| ID | Trigger | Prescription | quick |
|---|---|---|---|
| **D-1** | Summation lexicon `결론적으로/따라서/이를 통해/그러므로/요약하면/정리하자면`, 3+ combined | Keep 1–2, delete or replace the rest. Scores additively with A-2 and H-1 | ✅ |
| **D-2** | Significance inflation `시사하는 바가 크다/주목할 만하다/매우 중요하다` | Delete, or state the concrete conclusion | ✅ |
| **D-3** | Enumeration preamble `크게 세 가지로 나눌 수 있다/다음과 같은` | Delete the preamble; start the substance | ✅ |
| **D-4** | Hype vocabulary `혁신적/획기적/압도적/파격적/폭발적/전례 없는`, 3+ | Reduce to concrete figures and facts | ✅ |
| **D-5** | Personified abstract subjects (`기술이 묻는다`, `시대가 부른다`) | Human or institutional subject; or weaken the verb | ✅ |
| **D-6** | Closing formula `~할 때입니다/~시점입니다/~할 순간입니다` | Concrete verb assertion; ≤1 per document | ✅ |
| **D-7** | Transformation formula `X에서 Y로` / `X을 넘어 Y로`, repeated | Direct assertion; ≤1 per document | ✅ |

## E. Rhythm and sentence-length uniformity (E-1 ~ E-7)

| ID | Sev | Trigger | Prescription | quick |
|---|---|---|---|---|
| **E-1** | S2 | Uniform sentence length; **no sentence over 100 characters** | Per paragraph: 1–2 short sentences plus one long sentence built by joining adjacent ones. **Adding content is forbidden** | ✅ |
| **E-2** | S2 | Same sentence ending 4+ consecutively; automatic progressive `~고 있다` | Vary endings; reduce `~고 있다` to simple tense where possible (`읽고 있다` → `읽는다`) | ✅ |
| **E-3** | — | Every paragraph 3–4 sentences long | Deliberately mix a one-sentence paragraph and a six-sentence one | ❌ |
| **E-4** | S2 | Nothing but simple sentences — almost no compound or complex structure. Common when the model was told to "be concise" | Bind 2–3 adjacent simple sentences with connective endings (`-며·-고·-는데·-면서·-자`), adnominal clauses or quotative clauses. Target ~60% simple, 30%+ complex; save simple sentences for emphasis and turns | ❌ |
| **E-5** | S2 | Average clause length between commas grows long — English-style long sentences with stacked subordinate clauses (KatFish: human 4.35 eojeol vs AI 8.56, 1.97×) | Score above 7 eojeol average; split 8+ eojeol clauses at a period, or compress English subordination into a Korean adnominal clause. Weighted when co-occurring with E-4 | ❌ |
| **E-6** | S2 | POS diversity around commas explodes — commas inserted indiscriminately at every kind of boundary (KatFish: human 24.38 vs AI 59.39, 2.44×) | Restrict commas to (a) main-clause boundaries and (b) clear appositives. **Genre guard: essays, news, blogs, QA and reports only** — in poetry and fiction the signal disappears (1.03×) | ❌ |
| **E-7** | S2 *(estimated)* | Addressee honorific levels (해라/하게/하오/해요/합쇼) mixed within one document or dialogue | Fix one grade at the outset and hold it. Render *Will you help me?* as one appropriate level (`좀 도와주시겠어요?` / `도와줄래?`), not both. Don't flatten modality to `~수 있다` — vary with `~을지 모른다·~을 가능성도 있다·~을 수도 있겠다` | ✅ |

**E-4 and E-5 are opposite poles of the same axis** — all-simple-sentences on one end, English-style long sentences on the other. Both are AI signatures. E-1 measures length variance; E-4 measures structural monotony.

**E-7 carries an `estimated` flag (caveat C1)**: the quantitative figures in 김혜영 (2019) were inferred from the KCI English abstract, not the full PDF. Threshold stays `estimated` until the source is obtained. **Genre guard**: dialogue and speech only (fiction dialogue, interview transcripts, quoted speech). Uniformly formal genres such as reports and policy documents are exempt.

## F. Excess modification and redundancy (F-1 ~ F-5)

| ID | Sev | Trigger | Prescription | quick |
|---|---|---|---|---|
| **F-1** | — | Degree-adverb addiction: `매우`, `정말`, `진짜로`, `대단히`, `극히` | Mostly delete; use concrete figures for emphasis. **Exception:** when the source is colloquial and the adverb is part of the writer's voice (`정말 그랬다니까`), preserve it — this applies only to adverbs the AI bolted on | ❌ |
| **F-2** | — | Synonym doubling: `중요하고 핵심적인 역할`, `새롭고 혁신적인 접근`, `지속적이고 꾸준한 노력` | Keep one of the two modifiers | ❌ |
| **F-3** | — | Function+role compounds: `~로서의 역할과 기능`, `~의 의미와 가치` | Keep one | ❌ |
| **F-4** | S2 | Sino-Korean nominalizers `-성/-적/-화` plus literal English `-tion/-ment/-ness/-ity`, 12+ per document | Restore verb and adjective roots: "the implementation of the policy" → `정책 시행` | ✅ |
| **F-5** | S2 | `~적 N` abstraction chains (`전략적 함의`, `실천적 기반`), 3+ | Noun+noun compound or unfold: `전략 함의`, `실천의 기반` | ✅ |

## G. Hedging (G-1 ~ G-3) — S2

| ID | Trigger | Prescription | quick |
|---|---|---|---|
| **G-1** | Speculative endings `~로 보인다/~로 판단된다/~라고 여겨진다/~인 듯하다` overused | Assert wherever assertion is warranted | ✅ |
| **G-2** | Double and triple hedges `~할 가능성이 있을 수 있다`, `~로 보여질 수 있다` | Keep exactly one hedge | ✅ |
| **G-3** | Safe-balance lexicon `양쪽 모두/두 가지 모두/장점도 있지만/신중하게/균형`, 4+ | Commit to one side, give a concrete comparison, or make it conditional. **Genre-scoped to policy and report writing** | ✅ |

## H. Connective spam (H-1 ~ H-4) — S2

| ID | Trigger | Prescription | quick |
|---|---|---|---|
| **H-1** | Sentence-initial `또한/따라서/즉/나아가/아울러/게다가/더욱이`, 5+ | Delete most; let the sentences carry the flow | ✅ |
| **H-2** | `하지만` and `그러나` in every paragraph | Delete more than half — an obvious contrast needs no connective | ❌ |
| **H-3** | Meta lead-ins `이는 ~/이 점에서/이 관점에서/이 말은`, 3+ | Dissolve into the prose or delete | ✅ |
| **H-4** | `즉` overused | Vary (`곧`, `말하자면`) or drop; ≤2 per document | ✅ |

## I. Dummy and bound nouns (I-1 ~ I-6) — S2

| ID | Trigger | Prescription | quick |
|---|---|---|---|
| **I-1** | `~한 것이다/~일 것이다` **3+ consecutive** | Convert some to plain `~다`. **Default is preserve** — see the rejection note | ✅ |
| **I-2** | Dummy-noun emphasis `주목할 점은`, `X은 ~라는 점에 있다` | Direct `X는 ~다` | ✅ |
| **I-3** | `~다는 것이다/~다는 뜻이다` endings | End with `~다`; ≤2 combined | ✅ |
| **I-4** | Prescriptive endings `~해야 한다/~할 필요가 있다`, 5+ | Concrete verb assertions; name the actor; vary with conditionals | ✅ |
| **I-5** | `~이/가 필요하다` (`혁신이 필요하다`, `변화가 필요하다`) | Specify who must do what, as subject and verb | ❌ |
| **I-6** | `N 능력` 3+ per document — literal *ability to X / X capability* | Unfold into verbs: `사고 능력은 뛰어나다` → `잘 사고한다`; `워크플로우 수행 능력` → `워크플로우를 얼마나 잘 처리하는지`. Cap at 2 per document | ❌ |

**I-1 rejection note.** "Always flatten `것이다` endings" was **rejected**: precise measurement of `~것이다` gives AI 20.4 vs human 43.0 (G²=6.2) — humans use it twice as often. Flatten only at 3+ consecutive occurrences. See [`evidence.md`](evidence.md), including the measurement error we corrected.

## J. Visual decoration (J-1 ~ J-4) — S2~S3

| ID | Trigger | Prescription | quick |
|---|---|---|---|
| **J-1** | A bolded key word in every sentence | In column and report genres remove nearly all body bold | ✅ |
| **J-2** | Scare quotes, 5+ per document | Keep real quotations only; plain text otherwise | ✅ |
| **J-3** | Em-dash asides in every sentence | Break into commas, parentheses or separate sentences — **but preserve dashes that were already in the source** | ✅ |
| **J-4** | Parenthetical elaboration overload (`(이는 ~을 의미한다)`) | Move most into the body or delete | ❌ |

---

## Detector output schema

The detector and the rewriter share this contract:

```json
{
  "meta": {
    "input_length": 1820,
    "detected_count": 37,
    "ai_tell_density": 0.203,
    "severity_weighted_score": 71.5
  },
  "findings": [
    {
      "id": "f001",
      "category": "A-2",
      "category_label": "번역투: ~를 통해 남발",
      "severity": "S1",
      "text_span": "데이터 분석을 통해",
      "start": 142,
      "end": 153,
      "reason": "'통해'가 본문에서 6회 반복되어 경로 서술이 기계적",
      "suggested_fix": "데이터를 분석해서"
    }
  ],
  "category_summary": { "A": 12, "B": 3, "C": 2, "D": 8, "E": 1, "F": 4, "G": 2, "H": 3, "I": 1, "J": 1 }
}
```

- `severity_weighted_score` — weighted sum with S1=5, S2=2, S3=0.5, normalized to 0–100.
- `ai_tell_density` — total characters in detected spans / total characters.

## The post-editese track (metric-only, deliberately unnumbered)

Toral's (2019) three post-editese axes — simplification, normalisation, interference — are run as **metrics without pattern IDs**. The reason is caveat C3: Toral covered en→de, de→en, es→de, en→fr and zh→en; **Korean was not among them.** Extending the conclusion to Korean is a reasonable inference but is quantitatively unverified, so pattern IDs carry only token- and syntax-matchable signals, and the composite axes stay separate.

`references/metrics_v2.py` implements 14 functions across the three axes (all flagged `speculative: true`):

- **Simplification** — `lexical_diversity_ttr`, `lexical_density`, `ending_diversity` (Baker 1993; Toral 2019)
- **Normalisation** — `normalisation_score`, `da_streak_rate` (Baker 1993)
- **Interference** — eight detection signals plus `interference_index` (Toury 1995): `inanimate_subject_rate` (↔A-15, D-5), `by_passive_count` / `double_passive_count` (↔A-8, A-9, A-12), `pronoun_density` (↔A-16), `deul_overuse_rate` (↔A-17, held), `relative_clause_nesting` (↔A-18), `have_make_literal_count` (↔A-7, A-20, F-4), `double_particle_count` (↔A-19), `progressive_aspect_rate` (↔E-2, E-7)

The linkage runs both ways: pattern counts over threshold drive the diagnosis and rewrite calls, while metric composites deviating from baseline trigger extra verification in the finalize call.

## Scholarly grounding

Full citations live in `skills/humanize-korean/references/scholarship.md`: the Korean translation-studies lineage (이영옥 2001, 김정우 2007, 김도훈 2009, 김순영 2012, 박옥수 2018, 김혜영 2019), international theory (Baker, Toury, Laviosa, Chesterman, Toral), and six verbatim caveats constraining what may be claimed. Patterns carry `source_anchor` and `see_scholarship` metadata pointing into it.

Our own contrastive measurement — including **which rules it killed** — is in [`evidence.md`](evidence.md).

**Expansion rule:** a sub-pattern is added only when it reproduces 2+ times in real inputs *and* human writers almost never produce it.
