# Contract: Safety Reviewer

Specification for the second agent in the roadmap, independent of the
Research/Fact-Check Agent (`agents/researcher/`). It governs the
**SAFETY_REVIEW** pipeline stage only.

This contract is subordinate to `CONSTITUTION.md` and to
`templates/CLAIM.md` (Atomicity rule, claim immutability) and
`templates/REVIEW.md` (Multi-pass resolution). Where anything below could
be read as conflicting with those, they win. This document does not
restate the Constitution — see `CONSTITUTION.md` directly for the
governing rules (human authority, no automated publishing, sourceability,
staged progress).

## Purpose

Independently evaluate a content item's `SCRIPT.md` (and the `claims/`
it cites) for safety and policy risk before the item may proceed past
`SAFETY_REVIEW`. This is **not** a fact-check (that's
`agents/researcher/`'s job) and it is **not** a general quality/editorial
pass (that's `EDITORIAL_REVIEWER`'s job, not yet contracted). It stays
narrowly focused on:

- dangerous or harmful instructions
- illegal activity facilitation
- deceptive content
- impersonation
- realistic synthetic media concerns
- misinformation risk (specifically: hypothetical/speculative content
  mislabeled as established fact — see `CONSTITUTION.md` rule 4)
- unsupported certainty (absolute language attached to unverified,
  inferred, or speculative content)
- sensitive historical claims (real tragedies, mass-casualty events)
- privacy concerns
- defamation risk
- copyright/licensing warning signals
- AI disclosure requirements
- title/thumbnail deception
- potentially advertiser-sensitive content

It must never become a generic quality checker. A finding outside this
list (grammar, pacing, narrative quality) is out of scope even if noticed
in passing.

## Inputs

- `CONTENT_ITEM.md` (title, pillar, premise — read-only except the one
  field named in Allowed actions)
- `SCRIPT.md` (hook, premise, narrative beats, conclusion, CTA, visual
  requirements, music/SFX requirements, AI disclosure field, What If?
  fact/hypothesis separation section — read-only)
- `claims/*.md` (classification only matters here — read-only)
- `templates/REVIEW.md` (the schema contract to produce against)
- `CONSTITUTION.md` (governing rules, read-only)

The Safety Reviewer does **not** re-run fact-check evaluation and does
not read `research/*.md` — evidence quality is the Research/Fact-Check
Agent's job. It reads `claims/*.md` only for `Classification`, to check
labeling (see "Misinformation risk" in the signal model).

## Outputs

- One new `reviews/safety_reviewer-<n>.md` (verdict `PASS` /
  `REVISION_REQUIRED` / `REJECT`, per `templates/REVIEW.md`, role
  `SAFETY_REVIEWER`)
- `CONTENT_ITEM.md`: updates `Safety state` only
- An appended entry in `CONTENT_ITEM.md`'s Notes/history log

## Allowed actions

- Read `CONTENT_ITEM.md`, `SCRIPT.md`, `claims/*.md`
- Create `REVIEW.md` entries with role `SAFETY_REVIEWER`
- Update `CONTENT_ITEM.md`'s `Safety state` field only
- Append (never edit or delete) entries in `CONTENT_ITEM.md`'s
  Notes/history log
- Flag signals, ambiguity, and escalation needs for human attention

## Forbidden actions — protected fields

The Safety Reviewer must **never** modify:

- a claim's `Classification` or `Exact claim` (claim content is not
  its concern or its authority — flag a labeling mismatch, never fix it)
- `Owner approval state`
- the content item's top-level `status` field or `Publication state`
- `Research state` or `Fact-check state` (those belong to
  `agents/researcher/`)
- `research/*.md` evidence records
- any other reviewer's role in `REVIEW.md`
- `SCRIPT.md` or `CONTENT_ITEM.md` prose — it never rewrites content to
  make it pass; it only reports

It must also never:

- Publish anything, anywhere, under any condition
- Approve its own disputed work (see Multi-pass resolution — a `REJECT`
  is terminal until a human reopens it, exactly as for `FACT_CHECKER`)
- Invent a policy citation, or claim certainty about a policy requirement
  it cannot actually evaluate — see Signal model
- Override `CONSTITUTION.md` or any human-approval field
- Silently clear a previously-recorded `HIGH_RISK` signal or `FALSE`-
  equivalent finding without new evidence (mirrors the Researcher's
  sticky-`FALSE` rule)

## Signal model

Twelve named signals, each evaluated independently and given a risk
level. A signal firing does **not** automatically mean `REJECT` — see
Verdict derivation.

| Signal | What it looks for |
|---|---|
| `DANGEROUS_INSTRUCTION` | Actionable harmful how-to content (weapons, self-harm, hazardous synthesis) |
| `ILLEGAL_ACTIVITY` | Facilitating illegal acts (evasion, hacking, fraud how-tos) |
| `DECEPTION` | Instructing that fabricated content be presented as genuine |
| `IMPERSONATION` | Presenting a real, named person's likeness/voice/words without disclosure |
| `SYNTHETIC_MEDIA` | Realistic AI-generated depictions of real people/events that may need disclosure |
| `AI_DISCLOSURE` | Whether `SCRIPT.md`'s AI disclosure requirement is decided and, if required, has a stated disclosure plan |
| `MISINFORMATION_RISK` | Whether `ASSUMPTION`/`INFERENCE`/`SPECULATION` claims are ever presented as `KNOWN FACT` (labeling, not truth) |
| `PRIVACY` | Private individuals' personal data (addresses, records, contact info) |
| `DEFAMATION` | Accusatory claims about a named real person/entity not backed by a `FACT`-classified, sourced claim |
| `COPYRIGHT_RISK` | Named third-party copyrighted/trademarked material referenced without a licensing note |
| `SENSITIVE_CONTENT` | Real mass-casualty/tragedy subject matter warranting careful, non-sensationalized handling |
| `TITLE_THUMBNAIL_MISREPRESENTATION` | Title/hook framing (absolute-certainty language, missing hypothetical framing on `what-if` content) inconsistent with the content's actual certainty |

### Risk levels

- `NOT_APPLICABLE` — nothing in this content item is within this signal's
  scope (e.g. no third-party media referenced at all for
  `COPYRIGHT_RISK`).
- `LOW_RISK` — evaluated, no risk indicators found by this MVP's checks.
  **This is not a certification of safety** — see Implementation notes;
  it means "no known pattern matched," not "confirmed safe."
- `REVIEW_REQUIRED` — an indicator was found that this system cannot
  reliably resolve on its own; a human must judge it.
- `HIGH_RISK` — a strong, clear indicator was found.

## Verdict derivation

1. Any `DANGEROUS_INSTRUCTION` or `ILLEGAL_ACTIVITY` signal at
   `HIGH_RISK` → `REJECT`. These are the two signal categories severe
   enough to be terminal rather than fixable-and-retry.
2. Any other signal at `HIGH_RISK` (`DECEPTION`, `IMPERSONATION`,
   `MISINFORMATION_RISK`, `PRIVACY`, `DEFAMATION`,
   `TITLE_THUMBNAIL_MISREPRESENTATION`, `AI_DISCLOSURE`,
   `COPYRIGHT_RISK`) → `REVISION_REQUIRED` — content-fixable, not
   structurally broken.
3. Any signal at `REVIEW_REQUIRED` → verdict is at least
   `REVISION_REQUIRED` and `escalate_to_human = true`. Human escalation
   is never represented as `PASS` (see Human escalation, below).
4. All signals `LOW_RISK` or `NOT_APPLICABLE` → `PASS`.

## Human escalation

The Safety Reviewer escalates to a human whenever:

- Any signal cannot be reliably evaluated deterministically (recorded as
  `REVIEW_REQUIRED`, never guessed at as `LOW_RISK` to force a `PASS`).
- Policy interpretation is genuinely ambiguous (e.g. a claim that could
  be read either as historical commentary or as a specific accusation).
- Realistic synthetic media is present and it's unclear whether existing
  disclosure suffices.
- Serious defamation or privacy concerns exist, even if not certain.
- Any signal reaches `HIGH_RISK`.
- Evidence in `SCRIPT.md`/`claims/` is insufficient to make a reliable
  determination either way.

Escalation is recorded via `escalate_to_human = true` on the result and
named explicitly in `Reasons` — never silently folded into a `PASS`.

## Conservatism principle

Uncertainty is reported, not resolved by guessing. If a signal's evidence
is ambiguous: name the ambiguity, explain why it matters, and request
revision or escalation — never invent a citation to a platform policy or
claim certainty about a legal/policy requirement the reviewer cannot
actually verify. "I can't be sure, here's why, a human should decide" is
a correct and complete output for this reviewer; asserting confidence it
doesn't have is not.

## Failure conditions

- `SCRIPT.md` does not exist for the content item → cannot review, no
  `REVIEW.md` written (mirrors `agents/researcher/CONTRACT.md`'s "total
  retrieval failure" — log and stop).
- `SCRIPT.md` cites a claim ID with no corresponding `claims/*.md` file →
  `REJECT` (structural failure, same as the Researcher's contract).

## Exact handoff to the next pipeline stage

On `PASS`: sets `Safety state = PASS`, appends a Notes/history log entry
citing the `REVIEW.md` file, and stops. It does **not** change `status`
to `ORIGINALITY_REVIEW` — that transition is human/owner-approval-gated,
identically to how `agents/researcher/CONTRACT.md` handles `FACT_CHECK`.
On `REVISION_REQUIRED` or `REJECT`, it documents required changes/reasons
and stops.

## Relationship to the Research / Fact-Check Agent

Independent stages, independently runnable — SAFETY_REVIEW does not
require FACT_CHECK to have run first, and vice versa (though in the full
pipeline, FACT_CHECK precedes SAFETY_REVIEW — see `SYSTEM.md`'s pipeline
diagram). The Safety Reviewer reuses only `agents/researcher/src`'s
generic, role-agnostic infrastructure (markdown table/section parsing,
the `ReviewVerdict`/`ReviewRecord`/`ContentItem` models, `Multi-pass
resolution` gating functions, and the two failure-condition exception
types) — never its fact-check domain logic (`evidence.py`, `factcheck.py`,
`atomicity.py`, or its own field whitelist/hashing). See
`agents/safety/README.md`'s "Relationship to agents/researcher" for the
exact list. Each agent works with the other absent.

## Implementation notes (Phase 6)

The Phase 6 MVP (`agents/safety/src/`) implements this contract with
deterministic, pattern/structural-signal detection — no NLP, no semantic
understanding. This is a hard limitation, not a hidden one: a curated
keyword/pattern list can catch some explicit, blatant cases and will miss
subtler ones. `LOW_RISK` therefore means "no known pattern matched," not
"a human confirmed this is safe." See `agents/safety/README.md`'s "Known
limitations" for the full list and for which signals are genuinely
structural/deterministic (e.g. `AI_DISCLOSURE`, `MISINFORMATION_RISK`'s
labeling cross-check) versus pattern-based best-effort (e.g.
`DANGEROUS_INSTRUCTION`, `DEFAMATION`).
