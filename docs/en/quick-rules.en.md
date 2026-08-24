# Quick Rules (English edition) — the single-call rulebook

> Mirrors `skills/humanize-korean/references/quick-rules.md` at **v2.3.2**.
> The Korean file is **generated** from the taxonomy SSOT (`ai-tell-taxonomy.md`) by `scripts/build_quick_rules.py`, which emits only patterns flagged `quick: true`. This English edition is hand-maintained; if the two disagree, the Korean file wins.
>
> **This is a system prompt, not documentation.** It is what a single-call implementation loads. Korean pattern strings are the asset and are reproduced verbatim — translating them would destroy them. Everything around them (trigger condition, prescription) is in English.

Format: one line per pattern — `ID [severity] trigger → prescription`. No examples (they live in the taxonomy). IDs map 1:1 to the SSOT; the build guarantees it.

## Standing constraints

**Do-NOT list (excluded from both detection and rewriting):** proper nouns, product names, model names, organization names; numbers, dates, units; direct speech inside double quotes; statutory text; mathematical, chemical and statistical notation; standard English acronyms (LLM, GPU, MCP, API…).

**Content anchors (enumerate internally *before* detecting):** from each sentence's subject, object and complement, extract the content nouns and concept words that carry the claim. Particles and endings may change; the base lexeme must survive at least once in the output. When stripping AI stock phrases and abstractions, remove only modifiers and dummy nouns — never delete a content anchor or swap it for a synonym. If unsure, roll the sentence back.

**Over-edit guard:** change rate above 30% = warning, above 50% = hard stop and rollback. The verdict is **not** self-reported — `scripts/verify_change_rate.py` decides it deterministically (orchestrator Phase 2.5).

## A. Translationese — S1~S2

- **A-1** [S1] `~에 대해(서)` overused → attach the object particle directly (`X에 대해 논의` → `X를 논의`)
- **A-2** [S2] `~를 통해/통하여` **3+ times in one paragraph** → keep 1–2, redistribute the rest as `~로`, `~해서`, `~함으로써`
- **A-3** [S1] `~에 있어(서)` → `~에서` or `~을 볼 때`
- **A-4** [S2] `~라는 점에서` 3+ → `~서`, `~라는 이유로`
- **A-5** [S2] `~와 관련하여/관련된` → `~에`, `~의`
- **A-6** [S2] `~에 기반하여/바탕으로` overused → `~로`, `~을 보고`
- **A-7** [S1] `가지고 있다`; literal have/make/take/give + noun → reduce to adjective or verb, or double-subject construction (`강한 경쟁력을 가지고 있다` → `경쟁력이 강하다`)
- **A-8** [S1] double passive `~되어진다/~지게 된다` → active, or single passive (`판단되어진다` → `판단된다`)
- **A-9** [S2] `~에 의해` passive → promote the agent to subject (`AI에 의해 생성` → `AI가 만든`)
- **A-10** [S2] `~할 수 있다` overused → assert (`높일 수 있다` → `높인다`)
- **A-11** [S2] `~을 위해` purpose clauses overused → `~려고`, `~도록`, `~위한`
- **A-15** abstract subject + all-purpose verb (`보여준다/제공한다/가져온다`); literal causative and cognition verbs → restore a concrete subject; render causatives as adverbial `X 때문에/덕분에/로 인해`; render suggest/show/indicate as `~에 따르면 ~이다`
- **A-16** `그/그녀/그것/그들` 3+ per paragraph — literal English pronouns → drop 50%+ (Korean's zero pronoun) or use a name/noun phrase
- **A-18** pre-nominal modifier or relative clause of 3+ eojeol, left-branching from English → split the sentence, or postpose as an appositive (`X를 만났는데, 그 X는 ~`)
- **A-19** stacked particles `~에서의/~에로의/~으로의/~에의/~으로부터의` → unfold into a clause or phrase; plain `~의` is not a target
- **A-20** inanimate or abstract subject + `~게 만들다` causative (`가격이 검토를 시작하게 만들다`) → recast as a cause adverbial (`가격 때문에 검토를 시작했다`); human subjects are not targets

## B. English over-quoting — S2

- **B-1** [S2] Korean + parenthetical English repeated on every occurrence (`~(Sovereign AI)`) → gloss on first mention only, Korean alone thereafter
- **B-2** [S2] unexplained marketing buzzwords (seamless, robust, leverage…) → render the marketing words in Korean; **keep** standard technical terms in the original (API, prompt, token…); no mechanical literal translation

## C. Structural AI patterns (formatting and layout) — S1~S2

- **C-2** [S2] 3+ consecutive bullet blocks in a column or report → merge into prose paragraphs; keep lists only where enumeration carries meaning
- **C-5** [S1] emoji overload (list heads, headings, emphasis) → delete all of them in column/report genres
- **C-7** paragraph-initial `먼저–반면–결국` three-beat formula → cut to 1–2 connectives or dissolve into the prose
- **C-8** `A인가, B인가` / `A가 아니라 B` antithesis 3+ → keep one, convert the rest to asymmetric declaratives or direct assertions
- **C-9** parenthesized number indexing `1) 2) 3)` → dissolve into prose or vary lexically (`우선~`, `다음으로~`)
- **C-10** repeated colon-subtitle headings `X: Y` → compress each heading to a single noun phrase; preserve genuine section titles in academic and report genres
- **C-11** comma immediately after a connective ending (`-고/-며/-지만/-면서/-아서/-어서`) → delete the comma; 6+ occurrences is a strong signal (4.84× separability, KatFish)

## D. AI signature phrases — S1

- **D-1** summation lexicon `결론적으로/따라서/이를 통해/그러므로/요약하면/정리하자면` → above 3 occurrences, keep 1–2 and delete or replace the rest
- **D-2** significance inflation `시사하는 바가 크다/주목할 만하다/매우 중요하다` → delete, or replace with the concrete conclusion
- **D-3** enumeration preamble `크게 세 가지로 나눌 수 있다/다음과 같은` → delete the preamble and start the substance directly
- **D-4** hype vocabulary (`혁신적/획기적/압도적/파격적/폭발적/전례 없는`) 3+ → reduce to concrete figures and facts
- **D-5** personified abstract subjects (`기술이 묻는다`, `시대가 부른다`) → swap in a human or institutional subject, or weaken the personifying verb
- **D-6** closing formula `~할 때입니다/~시점입니다/~할 순간입니다` → concrete verb assertion; at most once per document
- **D-7** transformation formula `X에서 Y로` / `X을 넘어 Y로` repeated → direct assertion; at most once per document

## E. Rhythm and sentence-length uniformity — S2

- **E-1** uniform sentence length, no 100+ character sentence → per paragraph, add 1–2 short sentences and one long sentence built by joining adjacent ones (**adding content is forbidden**)
- **E-2** same sentence ending 4+ in a row; automatic progressive `~고 있다` → vary the endings; reduce `~고 있다` to simple tense where possible (`읽고 있다` → `읽는다`)
- **E-7** addressee honorific levels (해라/하게/하오/해요/합쇼) mixed within one document (dialogue and speech only) → hold one formality grade throughout

## F. Excess modification and redundancy — S2

- **F-4** Sino-Korean nominalizers `-성/-적/-화` plus literal English `-tion/-ment/-ness/-ity`, cumulative 12+ per document → restore verb or adjective roots ("the implementation of the policy" → `정책 시행`)
- **F-5** `~적 N` abstraction chains (`전략적 함의`, `실천적 기반`) 3+ → noun+noun compound or unfold (`전략 함의`, `실천의 기반`)

## G. Hedging pile-up — S2

- **G-1** speculative endings `~로 보인다/~로 판단된다/~라고 여겨진다/~인 듯하다` overused → assert wherever assertion is warranted
- **G-2** double and triple hedges `~할 가능성이 있을 수 있다/~로 보여질 수 있다` → keep exactly one hedge
- **G-3** balance lexicon `양쪽 모두/두 가지 모두/장점도 있지만/신중하게/균형` 4+ → commit to one side, give a concrete comparison, or make it conditional

## H. Connective spam — S2

- **H-1** sentence-initial `또한/따라서/즉/나아가/아울러/게다가/더욱이` 5+ → delete most of them; let the sentences carry the flow
- **H-3** meta lead-ins `이는 ~/이 점에서/이 관점에서/이 말은` 3+ → dissolve into the prose or delete
- **H-4** `즉` overused → vary (`곧`, `말하자면`) or drop; at most twice per document

## I. Dummy and bound nouns — S2

- **I-1** `~한 것이다/~일 것이다` **3+ consecutive** → convert some to plain declarative `~다` (default is to preserve)
- **I-2** dummy-noun emphasis `주목할 점은/X은 ~라는 점에 있다` → direct `X는 ~다`
- **I-3** `~다는 것이다/~다는 뜻이다` endings → end directly with `~다`; at most 2 combined
- **I-4** prescriptive endings `~해야 한다/~할 필요가 있다` 5+ → concrete verb assertions, name the actor, vary with conditionals

## J. Visual decoration — S2~S3

- **J-1** key word bolded in every sentence → in column/report genres remove nearly all body bold
- **J-2** scare quotes 5+ → keep only real quotations, plain text otherwise
- **J-3** em-dash asides in every sentence → break out into commas, parentheses or separate sentences — but **preserve dashes that were in the source**

## Self-verification checklist (run immediately after rewriting)

Check all six within seconds of producing the rewrite. **Any single violation rolls that edit back.**

1. **Proper nouns, numbers, dates, quotes and content anchors 100% preserved** — not one character different from the source. Does each sentence's core content noun survive in its base form at least once?
   - Standard technical terms (API, prompt, token, pipeline…) stay in the original or as loanwords — no mechanical translation (prompt → `지시문` ✗)
2. **Change rate** ≤ 30%. The binding verdict comes from orchestrator Phase 2.5 (`verify_change_rate.py`); the self-computed figure is advisory only
3. **No genre drift** — a column has not become a literary essay; a report has not slid into blog voice
4. **Register preserved, in both directions** — formal source stays formal, colloquial source stays colloquial. Do not drop to plain style, and do not raise formality (`-했-` → `-하였-`)
5. **Zero residual S1 patterns** — specifically D-1~D-3, A-7, A-8, A-16, C-5, C-10, C-11, H-1, I-1, J-2
6. **No invented expression (subtraction only)** — no metaphor, rhetorical flourish or stock phrase that wasn't in the source (`기록적인 성과`, `~로 평가된다`). Living speech — explanatory dashes, short interjections, rhetorical questions — is preserved

On violation: roll back the edit → rewrite → re-check. **Self-loop runs at most once.** If it still fails, emit the result anyway and record "N self-verification items failed" in the `<!-- HUMANIZE-SUMMARY -->` block of `final.md`.

## Grades (self-scored)

- **A** — 0 residual S1, ≤2 residual S2, change rate 10–25%, all 6 checklist items pass
- **B** — 0 residual S1, ≤4 residual S2, ≥5 checklist items pass
- **C** — 1–2 residual S1, or ≤4 checklist items pass → recommend strict mode to the user
- **D** — 3+ residual S1, or change rate above 50% → recommend aborting
