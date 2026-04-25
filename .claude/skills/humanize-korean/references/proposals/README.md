# Voice-Aware Adapter Reference (Issue #1 follow-up)

A sanitized reference for a downstream caller wrapping `humanize-korean`
with author-specific voice context, fully aligned with the v1.2 권한 위계
defined in `references/ai-tell-taxonomy.md` (commit `bfcf676`, 2026-04-25).

This is the adapter reference the maintainer requested in the
[Issue #1](../../issues/1) thread. It documents how a downstream skill
honors the v1.2 contract while still preserving authorial intent on
long-form Korean manuscripts.

## Why this exists

`humanize-korean` is a strong general-purpose AI-tell remover. On a
long-form manuscript with a strong authorial voice, several patterns
generate **false positives** when the author's choices are intentional:

| humanize-korean pattern | Authorial intent that triggers false positive |
|---|---|
| E-2 동일 종결어미 반복 | Single-sentence-per-thought rhythm |
| J-3 대시 1~2회 제한 | Em-dash as a structural device |
| C-3 반복 헤딩 제거 | Verb-form chapter headings in book mode |
| C-4 문단 첫 문장 요약 공식 | Scene-first paragraph entries |
| A-10 "할 수 있다" 남발 | Book-specific mandate to use 할 수 있다 |

The adapter does not weaken humanize-korean. It carries the author's
explicit voice profile through the call so intended elements are preserved
while real AI tells are still caught.

## How this adapter complies with v1.2 권한 위계

| Clause | Maintainer's rule | Adapter behavior |
|---|---|---|
| §1 default-on | Objective taxonomy applies unless rebutted | Default run unchanged when no voice profile is passed |
| §2 opt-in | Voice profile activates only with explicit `author-context.yaml` | No path-based or sidecar auto-load |
| §3 allowed mechanisms | Pattern-ID on/off, threshold relaxation, Do-NOT keyword whitelist only | Schema rejects free-text fields |
| §4 forbidden patterns | A-8, C-5, D-1..D-6 cannot be disabled | Validator rejects these in `disabled_pattern_ids`; threshold relaxation for D-1..D-6 capped at multiplier 2.0 |
| §5 분리 검증 | naturalness-reviewer must not see voice profile | Adapter's call envelope strips voice-profile fields before invoking the reviewer layer |
| §6 회귀 게이트 | New disable options gated on external regression cases | This PR is intentionally proposal-only; merge gated on external test cases |

## Files

- [`humanize-adapter-reference.md`](humanize-adapter-reference.md) —
  adapter logic from the downstream caller's perspective, sanitized
- [`author-context-schema.proposal.yaml`](author-context.schema.yaml) —
  strawman schema implementing §3 allowed mechanisms (the maintainer's
  authoritative schema, when published, takes precedence)
- `README.md` (this file)

## What was stripped

The internal version of this adapter contained book-specific data (central
metaphors, mandate phrasings, brand-asset names) and personal paths. All
of that is replaced with `<PLACEHOLDER>` tokens. The structure — track
classification, voice profile injection, naturalness fence, hard-block
paths — is what the maintainer asked to see. Personal data is not part of
this contribution.

## Open questions for the maintainer

1. **Pattern ID stability** — `disabled_pattern_ids` requires a stable
   public pattern ID surface (E-1, E-2, J-3, C-3, C-4, A-10, etc.). The
   IDs in `references/ai-tell-taxonomy.md` look stable already; should
   they be treated as a public API and version-bumped on any rename?

2. **Voice-blind reviewer enforcement** — §5 says naturalness-reviewer
   must not receive voice profile. How is this enforced in the agent
   topology today? The adapter assumes a separate agent invocation; if
   the topology changes (e.g. shared context), §5 needs an architectural
   guarantee, not just a documentation note.

3. **Threshold multiplier bounds** — the strawman caps at [0.5, 2.0]. Is
   2.0 the right ceiling, or should threshold relaxation for
   permanent-on patterns (D-1..D-6) be capped lower (e.g. 1.5) to make
   threshold-abuse-as-disable harder?

4. **Hard-block paths** — adapter-side convention or codified into
   humanize-korean? The adapter treats them as caller-side; the
   maintainer might prefer a humanize-korean-side default-deny list for
   fiction.

## §6 external validation plan

The adapter author's prior in-the-wild result (350+ false positives
suppressed on a single manuscript) is **self-reported**. Merging this
reference and any follow-up disable options into v1.2 main is gated on
external regression cases per §6. We need 2–3 cases authored by people
**other than this PR's author**:

- [ ] Third-party AI-drafted essay (1)
- [ ] Plain-tone report or memo (1)
- [ ] Quote-heavy column or interview piece (1)

For each case: run humanize-korean **without** the adapter, then **with**
the adapter (using a voice profile authored for that other author), and
compare findings. The adapter is valid only if it preserves the other
author's voice-specific intent **and** still catches generic AI tells
(especially A-8, C-5, D-1..D-6, which must remain default-on).

We are recruiting case authors via a separate Issue thread; PR is held
in proposal state until at least 2 external cases are evaluated.

## Disclaimer

This is a **proposal**, not a request to merge as-is. The maintainer's
own authoritative `author-context.yaml` schema (planned per the v1.2
commit message: "v1.2 후속 작업 — author-context.yaml 스키마, 에이전트
주입 분리") supersedes this strawman. We submit this reference so the
contract is concretely documented from a downstream caller's
perspective and so the maintainer has a working example to react to.
