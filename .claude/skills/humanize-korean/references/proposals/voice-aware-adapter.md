# Voice-Aware Adapter — Downstream Caller Reference (sanitized)

A reference implementation for **downstream callers** that wrap
`humanize-korean` with author-specific voice context, fully aligned with the
v1.2 권한 위계 (Authority Hierarchy) defined in
`references/ai-tell-taxonomy.md` (commit `bfcf676`, 2026-04-25).

> This is the reference the maintainer requested in Issue #1 thread. It is
> **not** a proposal to replace humanize-korean's built-in mechanisms; it is
> the contract a wrapping skill (in our case, a writing-style skill) needs
> to honor when invoking humanize-korean on long-form, author-voiced
> manuscripts.

## What this adapter is for

`humanize-korean` is a strong general-purpose AI-tell remover. Run it raw on
a long-form manuscript with a strong authorial voice and it flags
**intended** style elements as AI tells:

- Repeated `~다.` endings (chosen as a "single sentence one thought" rhythm)
  → flagged as **E-2** (동일 종결어미 반복)
- Em-dashes used as a structural rhythm device
  → flagged as **J-3** (대시 1~2회 제한)
- Single-sentence paragraphs as deliberate beats
  → potentially conflated with **C-4** (문단 첫 문장 요약 공식)

The adapter sits **in front of** humanize-korean and injects an explicit
voice profile so these intended elements survive the pass, while real AI
tells (번역투, hype 어휘, 영구 default-on patterns) still get caught.

## v1.2 권한 위계 compliance map

The adapter is bound by every clause of §1–§6:

| Clause | Adapter behavior |
|---|---|
| §1 객관 분류 우선 | Default humanize-korean run is unchanged. Adapter only takes effect when a valid `author-context.yaml` is explicitly passed. |
| §2 opt-in 주입 | No path-based or sidecar auto-discovery. The adapter requires an explicit `author_context` argument; absence = no injection. |
| §3 허용 메커니즘 | Adapter passes only three things: `disabled_pattern_ids`, `threshold_relaxations`, `do_not_keywords`. No free-text mandates. |
| §4 무력화 불가 | Adapter's schema validator rejects any `disabled_pattern_ids` containing **A-8, C-5, D-1..D-6**. Threshold relaxation for D-1..D-6 is allowed but capped (multiplier ≤ 2.0). |
| §5 분리 검증 | Adapter never passes voice-profile fields into the `naturalness-reviewer` invocation. This is enforced by the call envelope, not by convention. |
| §6 회귀 게이트 | Adapter changes are gated on external regression cases (see this PR's discussion thread). |

## Call-time inputs

```text
input_path:        path to the manuscript
author_context:    explicit path to author-context.yaml (required for any
                   voice-aware behavior; absence falls through to default
                   humanize-korean run)
genre:             one of humanize-korean's published genres
output_workspace:  scratch directory outside any indexed vault
```

The adapter never discovers context implicitly. There is no path-based
auto-load.

## Pipeline

```
input → [adapter pre-pass] → humanize-korean → [adapter post-pass] → report
            │                                       │
            │                                       └── filters findings
            │                                           against voice profile
            │                                           and do_not_keywords;
            │                                           NEVER adds findings.
            │
            └── pre-pass:
                  1. Hard-block check (reject and explain)
                  2. Track classification (column / report / blog / book / etc.)
                  3. Schema-validate author-context.yaml
                  4. Build the humanize-korean call envelope:
                       - genre
                       - disabled_pattern_ids       (validated, §4 enforced)
                       - threshold_relaxations      (validated, capped)
                       - do_not_keywords            (added to standard Do-NOT)
                  5. Invoke humanize-korean
```

The `naturalness-reviewer` layer inside humanize-korean **must remain
voice-blind** per §5 — the adapter does not pass `author_context` into that
layer. This is a contract, not a convenience: it preserves an independent
check on whether the final text reads as natural Korean prose, regardless
of what the voice profile claims.

## Track classification

Track is determined from content + invocation context, not from file path
alone. Path patterns are advisory.

| Track | Characteristics | Genre passed |
|---|---|---|
| Long-form non-fiction | Chapter headings, narrative beats, central metaphor | `book_essay` (proposed new genre — separate discussion) |
| Report / proposal | Structured sections, citations, executive summary | `report` |
| Blog / SNS / short-form | Conversational, single topic | `blog` |
| Research / data analysis | Source verification is the point | (skip — humanize-korean inappropriate) |
| Email / memo | Short, transactional | (skip — overkill) |
| Fiction | Dialog, scene structure, deliberate voice | **HARD BLOCK** |

## Hard blocks (caller-side convention)

The adapter rejects calls outright for caller-defined sensitive paths:

- Fiction manuscripts (any path matching the configured fiction glob)
- Legal-process documents (court filings, retrial materials, etc.)
- Third-party manuscripts (`received-from-others` glob)

Hard-block paths are configured per-installation in `author-context.yaml`,
not hard-coded. This is a caller convention, not a humanize-korean
requirement.

When a hard block fires, the adapter returns:

```text
This file matches a hard-block rule (<reason>). humanize-korean will not run.
Suggested alternatives: direct manual revision, or voice-style skill alone.
```

## Author voice profile injection

See `author-context-schema.proposal.yaml` for the full schema. The adapter
passes exactly four fields into the humanize-korean call:

1. `voice_anchors` — short declarative phrases describing intentional traits
   (advisory only; cannot disable a pattern, per §3 free-text prohibition
   reading)
2. `disabled_pattern_ids` — pattern IDs the author has explicitly opted out
   of (validator enforces §4 forbidden list)
3. `threshold_relaxations` — numeric multipliers on specific pattern
   thresholds (capped at 2.0)
4. `do_not_keywords` — exact phrases extending humanize-korean's standard
   Do-NOT list

**No free-text mandate field is passed through.** This is the maintainer's
constraint and the adapter enforces it: the schema rejects any string field
that isn't part of the structured fields above.

## Post-pass filtering

After humanize-korean returns findings, the adapter filters against the
voice profile:

- Findings whose pattern ID is in `disabled_pattern_ids` → suppressed,
  reported as "preserved by voice profile (`<pattern_id>`, N occurrences)"
- Findings whose threshold was relaxed and now sits below the relaxed
  threshold → suppressed, reported as "below relaxed threshold"
- Findings that touch a phrase in `do_not_keywords` → suppressed, reported
  as "preserved by Do-NOT keyword"
- All other findings → passed through unchanged

The post-pass **never adds** findings. It only suppresses, and it reports
every suppression so the user can audit what was protected. Suppressions
are also written to a structured telemetry log to support the §6 regression
gate.

## Result format

```text
1. Quality grade and severity-weighted score (from humanize-korean)
2. Real recommendations (post-pass survivors only)
3. Before → after pairs (one per surviving finding)
4. Preserved-by-voice-profile section
   - "<pattern_id>: N occurrences preserved (reason: <voice_anchor>)"
5. Author decisions (accept / reject)
```

## Failure modes (regression checklist)

- Adapter ran on a hard-blocked path → fix: tighten glob
- Author's central metaphor got rewritten → fix: ensure exact phrase in
  `do_not_keywords` with `kind: metaphor`
- Change rate exceeded 30% on a long manuscript → fix: voice profile likely
  not loaded; verify `author_context` was passed
- Author's first-person signature was flattened → fix: add to
  `do_not_keywords` with `kind: signature_phrase`
- Naturalness reviewer's verdict aligns suspiciously with voice anchors →
  contract violation: voice profile leaked into reviewer layer (§5)
- D-1..D-6 was disabled in `disabled_pattern_ids` → schema validator should
  have rejected. Bug in validator. Patch the validator before any further
  runs.

## What this adapter does NOT do

- Disable patterns at the genre level (v1.2 §3 forbids; per-author opt-in
  via `disabled_pattern_ids` is the only supported mechanism)
- Accept free-text mandates ("treat `~할 것이다` as forbidden") — only
  pattern IDs and numeric thresholds are accepted
- Auto-discover sidecar config files near the manuscript (v1.2 §2)
- Pass voice profile into the naturalness-reviewer layer (v1.2 §5)
- Override A-8, C-5, or D-1..D-6 disable (v1.2 §4)

## Version

- Reference v0.1 (sanitized): 2026-04-25
- Aligned with: `references/ai-tell-taxonomy.md` v1.1 + 권한 위계 절
  (commit `bfcf676`)
