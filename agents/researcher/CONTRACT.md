# Contract: Research / Fact-Check Agent

Specification only — no implementation exists yet. This is the contract a
future implementation must satisfy before it is allowed to run against
real content items. It governs two adjacent, clearly separated jobs
mapped to two pipeline stages: **RESEARCH** and **FACT_CHECK**.

This contract is subordinate to `CONSTITUTION.md` and the rules in
`templates/CLAIM.md` (Atomicity rule) and `templates/REVIEW.md`
(Multi-pass resolution). Where anything below could be read as
conflicting with those, they win.

## Purpose

- **RESEARCH mode:** given a content item's `CONTENT_ITEM.md` (premise,
  pillar, target audience), find real sources, record them as
  `RESEARCH.md` entries, and draft `CLAIM.md` entries from that research —
  never write `SCRIPT.md` itself.
- **FACT_CHECK mode:** given a content item whose `SCRIPT.md` exists and
  cites claim IDs, independently re-verify each cited claim against the
  linked evidence and produce a `REVIEW.md` (role `FACT_CHECKER`) verdict.

The agent never authors narrative script content and never grants final
approval of its own findings — see Forbidden actions.

## Inputs

- `CONTENT_ITEM.md` for the target content item (read-only, except the
  two fields named in Allowed actions)
- Existing `research/*.md` and `claims/*.md` files for that item, if any
- `SCRIPT.md` and its `Verified claims` table, in FACT_CHECK mode
  (read-only)
- `templates/RESEARCH.md`, `templates/CLAIM.md`, `templates/REVIEW.md`
  (schema contracts — structure, not content, to produce against)
- `CONSTITUTION.md`, `SYSTEM.md` (governing rules, read-only)
- In RESEARCH mode: real, retrievable external source material the agent
  looks up at run time — never fabricated

## Outputs

**RESEARCH mode:**
- New/updated `research/<n>-<slug>.md` files, one per source
- New `claims/<claim-id>.md` files, one per atomic claim (per the
  Atomicity rule)
- `CONTENT_ITEM.md`: updates `Research state` only
  (`NOT_STARTED`→`IN_PROGRESS`→`COMPLETE`)
- An appended entry in `CONTENT_ITEM.md`'s Notes/history log

**FACT_CHECK mode:**
- One new `reviews/fact_checker-<n>.md` (verdict `PASS` /
  `REVISION_REQUIRED` / `REJECT`, per `templates/REVIEW.md`)
- Per reviewed claim: updates to that claim's `Fact-check status`,
  `Evidence`, `Contradictory evidence`, and `Confidence level` fields only
  — never `Classification` or `Exact claim` (see Claim handling)
- `CONTENT_ITEM.md`: updates `Fact-check state` only, per
  `templates/REVIEW.md`'s Multi-pass resolution rule
- An appended entry in `CONTENT_ITEM.md`'s Notes/history log

## Allowed actions

- Create `RESEARCH.md` entries from real sources it retrieved
- Create new `CLAIM.md` files, assigning classification at creation time
  per `templates/CLAIM.md`'s Classification guide, with a justification
- Update an existing claim's `Fact-check status`, `Evidence`,
  `Contradictory evidence`, `Confidence level` fields based on findings
- Create `REVIEW.md` entries with role `FACT_CHECKER`
- Update `CONTENT_ITEM.md`'s `Research state` and `Fact-check state`
  fields only
- Append (never edit or delete) entries in `CONTENT_ITEM.md`'s
  Notes/history log
- Flag contradictions, gaps, and disputes for human attention

## Forbidden actions

The agent must **never**:

- Invent sources, URLs, quotes, statistics, or evidence
- Convert an `ASSUMPTION`, `INFERENCE`, or `SPECULATION` claim into
  `FACT` (or any other classification change on an existing claim) —
  classification is set once at claim creation and is otherwise immutable
  per the Atomicity rule; a correction creates a new claim ID, it never
  edits the old one
- Silently rewrite a claim's `Exact claim` wording to make it easier to
  verify or pass review
- Lower a quality/evidence standard to complete a task (e.g. accepting a
  `LOW`-reliability source as sufficient for `VERIFIED`, or marking
  `VERIFIED` at `LOW` confidence — see Confidence handling)
- Issue a `PASS` verdict covering a claim it has itself marked `DISPUTED`
  in this or a prior pass, without an intervening human decision recorded
  in Notes/history log
- Create a new review attempt for a role after a `REJECT` verdict without
  a human reopen decision already logged (per `templates/REVIEW.md`
  Multi-pass resolution, rule 3)
- Publish anything, anywhere, under any condition
- Set, or attempt to influence, `Owner approval state` — that field is
  human-only
- Change the content item's top-level `status` field. The agent updates
  only its two named stage-state fields; advancing `status` to the next
  pipeline stage is reserved for the human owner (or a future,
  explicitly-authorized orchestration step — not this agent)
- Modify `CONSTITUTION.md`, `SYSTEM.md`, or any `templates/*.md` file
- Delete or overwrite any existing `research/*.md`, `claims/*.md`, or
  `reviews/*.md` file — all records are append-only/immutable, corrections
  supersede rather than overwrite
- Write or edit `SCRIPT.md`, `VIDEO_QA.md`, or any review role other than
  `FACT_CHECKER`

## Required evidence/source standards

- A source must be real and independently retrievable/attributable — no
  exceptions, ever (see Forbidden actions).
- Prioritize the same tiers used in the Phase 3 golden sample: academic
  institutions, peer-reviewed/scholarly work, established museums,
  government/public-health institutions, and authoritative encyclopedic or
  historical references.
- Every `FACT` claim needs at least one `HIGH`- or `MEDIUM`-reliability
  source (per `templates/RESEARCH.md`'s `Source reliability` field). A
  `LOW`/`UNVERIFIED`-reliability source may corroborate but can never by
  itself justify `VERIFIED`.
- If no adequate source exists for a needed claim, the agent records that
  gap (Notes/history log in RESEARCH mode; `Reasons` in FACT_CHECK mode)
  instead of lowering the bar or inventing one.

## Claim handling

- New claims follow `templates/CLAIM.md` exactly, including the Atomicity
  rule (one sentence, one classification, no fused reasoning) and correct
  use of `Supporting sources` vs. `Derived from` per classification.
- Classification is assigned once, at creation, with a one-line
  justification citing the Classification guide. It is never edited
  afterward by this agent (see Forbidden actions).
- `ASSUMPTION` claims are never "fact-checked" by this agent — they stay
  `NOT_APPLICABLE`. Verifying a stipulated premise is a category error.

## Fact-check statuses

Using `templates/CLAIM.md`'s enum (`UNVERIFIED` / `VERIFIED` / `DISPUTED`
/ `FALSE` / `NOT_APPLICABLE`), the agent's transition rules:

- `UNVERIFIED → VERIFIED`: only when a `HIGH`- or `MEDIUM`-reliability
  source directly and unambiguously supports the exact claim text, with
  no unresolved contradictory evidence.
- `UNVERIFIED → DISPUTED`: when credible sources conflict. Both sides are
  recorded in `Contradictory evidence`; the agent does not pick a winner
  unless one source is definitively authoritative (e.g. the other was
  retracted) — otherwise this is a human/editorial call.
- `UNVERIFIED → FALSE`: only when authoritative evidence directly
  contradicts the claim. This always forces the fact-check verdict to at
  least `REVISION_REQUIRED` — a `FALSE` claim needs the script rewritten,
  not just relabeling.
- `ASSUMPTION`/`SPECULATION` claims stay `NOT_APPLICABLE`.

## Confidence handling

- `Confidence level` reflects source reliability plus directness of
  support: `HIGH` = direct statement in a `HIGH`-reliability source, no
  contradiction; `MEDIUM` = `MEDIUM`-reliability source, or minor
  interpretation required; `LOW` = weak/indirect support or a single
  low-reliability source.
- **`VERIFIED` requires `Confidence level` of `HIGH` or `MEDIUM`.** A
  claim the agent can only support at `LOW` confidence must remain
  `UNVERIFIED` or move to `DISPUTED` — never `VERIFIED`. The agent may not
  raise a confidence rating just to justify a `PASS`.

## How contradictions are reported

- Recorded on the specific claim's `Contradictory evidence` field, citing
  both the original and conflicting evidence with their `research/*.md`
  entries.
- Any contradiction touching a `FACT` claim a script conclusion depends on
  makes a clean `PASS` verdict unavailable for that review — the fact
  checker verdict must be `REVISION_REQUIRED` (or `REJECT` if
  unresolvable), and `Reasons` must name the specific claim ID(s) and
  describe the conflict.
- The agent never silently resolves a contradiction by discarding one
  side.

## How missing/insufficient evidence is handled

- No source found → `Fact-check status` stays `UNVERIFIED`. Never defaults
  to `VERIFIED`, never invents a source to close the gap.
- A `FACT` claim in the script with no realistically obtainable source →
  verdict `REVISION_REQUIRED`, with `Reasons` stating the evidence gap and
  recommending human/editorial reconsideration of the claim (the agent
  flags this; it does not reclassify the claim itself — see Forbidden
  actions).
- In RESEARCH mode, if the agent cannot find adequate sources for the
  premise (see Phase 3's 2–3-source bar), it reports the shortfall in
  Notes/history log and does **not** mark `Research state` as `COMPLETE`.

## How the agent records uncertainty

- Per-claim: the `Confidence level` field — never omitted or inflated to
  make a verdict look cleaner.
- Item-level: the `Notes` section of the `REVIEW.md` it produces.
- The agent may recommend edits to `SCRIPT.md`'s existing "Uncertainty
  notes" section via `Reasons`/`Required changes` in a
  `REVISION_REQUIRED` verdict — it does not edit `SCRIPT.md` itself
  (out of scope; see Forbidden actions).

## Failure conditions

The agent stops and reports rather than producing a verdict when:

- It cannot retrieve any source material at all (total retrieval
  failure).
- Multiple `HIGH`-reliability sources contradict each other
  irreconcilably.
- `SCRIPT.md` cites a claim ID with no corresponding `claims/*.md` file.
- The content pillar is `what-if` and a cited claim has no
  `Classification` or an invalid one.
- More than half of the claims under review come back `DISPUTED` or
  `FALSE` — this signals the item wasn't ready for fact-check, not that
  it needs a marginal revision.

On any failure condition the agent's only available outputs are
`REVISION_REQUIRED` or `REJECT` (never `PASS`), with the failure stated
plainly in `Reasons`; if it cannot reach even that (e.g. total retrieval
failure), it logs the failure in Notes/history log and produces no
`REVIEW.md` at all rather than guessing.

## Human escalation conditions

- Any `REJECT` verdict (always requires human review before any further
  attempt, per Multi-pass resolution).
- Any `FALSE` fact-check status (script content likely needs to change —
  an editorial call, not this agent's to make).
- Any irreconcilable contradiction between `HIGH`-reliability sources.
- Any claim the agent believes is misclassified — it flags this in
  `Reasons`/Notes, it does not reclassify.
- Two consecutive `REVISION_REQUIRED` verdicts for the `FACT_CHECKER` role
  on the same underlying issue — escalate to the human owner instead of a
  third autonomous attempt.
- Any request that would require touching `status`, production,
  publication, or another reviewer role's territory.

## Exact handoff to the next pipeline stage

- **RESEARCH → done:** agent sets `Research state = COMPLETE`, appends a
  Notes/history log entry citing the new `research/*.md` and `claims/*.md`
  files, and stops. It does **not** change `status`. The item is now
  ready for script drafting by a human or a future, separately-contracted
  script agent.
- **FACT_CHECK → done:** on `PASS`, agent sets `Fact-check state = PASS`,
  appends a Notes/history log entry citing the `REVIEW.md` file, and
  stops. It does **not** change `status` to `SAFETY_REVIEW` — that
  transition is human/owner-approval-gated. On `REVISION_REQUIRED`, it
  documents required changes and stops; a human or the agent (bounded by
  the two-consecutive-attempts escalation rule) may act on them next.

## Implementation notes (Phase 5)

The Phase 5 MVP (`agents/researcher/src/`) implements this contract. Two
design decisions made during implementation, recorded here rather than
left implicit:

- **Evidence support is separate from `Fact-check status`, but computed —
  not a new persisted `CLAIM.md` field.** Research collection (does a
  source exist?) is a different question from fact-check evaluation (does
  it actually support this exact claim?). The implementation models this
  internally as `SUPPORTED` / `PARTIALLY_SUPPORTED` / `UNSUPPORTED` /
  `CONTRADICTED` / `UNRESOLVED`, derived deterministically per claim from:
  whether cited `research/*.md`/`claims/*.md` files exist, whether a cited
  research entry's own `Related claims` field reciprocally names the
  claim (an unconfirmed one-directional citation is not enough to
  `SUPPORT`), source `Source reliability`, and whether `Contradictory
  evidence` is populated. This is compatible with the existing templates
  without a schema change — it's surfaced in the `REVIEW.md` `Reasons`
  list and the structured JSON result, not written back onto `CLAIM.md`.
  `Fact-check status` is then derived from evidence support plus
  `Confidence level` per the Fact-check statuses/Confidence handling
  sections above — evidence support is the "why," `Fact-check status` is
  the field this contract already governs.
- **`Reviewed content hash`** (`templates/REVIEW.md`, added Phase 5) is
  populated by this agent on every `REVIEW.md` it writes, making Multi-pass
  resolution rule 4 (`PASS` staleness) mechanically checkable instead of a
  manual obligation. See `agents/researcher/src/hashing.py`.

Verdict derivation used by the implementation (all deterministic, no
claim ever guessed as `FALSE` — that requires stronger judgment than this
MVP applies automatically, so `CONTRADICTED` evidence maps to `DISPUTED`,
never auto-`FALSE`):

1. Structural failure (a `SCRIPT.md`-cited claim ID has no file, or a
   claim's `Classification` is missing/invalid) → `REJECT`.
2. No research/claims loadable at all → abort, no `REVIEW.md` written.
3. More than half of reviewed claims come back `DISPUTED`, or any claim
   involves a `CONTRADICTED` conflict between two `HIGH`-reliability
   sources → `REVISION_REQUIRED`, flagged for human escalation.
4. Any claim's evidence support is `CONTRADICTED` → that claim's
   `Fact-check status` is `DISPUTED` → verdict at least `REVISION_REQUIRED`.
5. Any `FACT` claim not `VERIFIED` (still `UNVERIFIED`, including
   `UNRESOLVED` evidence support — this is the `c11` case) →
   `REVISION_REQUIRED`, gap named explicitly, no citation fabricated.
6. Otherwise → `PASS`.

## What the agent is explicitly NOT allowed to do (summary)

- Invent sources, URLs, quotes, statistics, or evidence
- Convert `ASSUMPTION`/`INFERENCE`/`SPECULATION` into `FACT`, or change
  any existing claim's classification in place
- Silently rewrite a claim to make it pass
- Lower a quality/evidence standard to complete a task
- Approve its own disputed work
- Publish anything
- Override `CONSTITUTION.md` or any human-approval field
- Silently modify pipeline `status`, or any state outside `Research
  state`/`Fact-check state`
