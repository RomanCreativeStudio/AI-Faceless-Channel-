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

## Autonomous Revision Mode

Phase 7F. A third, narrow mode alongside RESEARCH and FACT_CHECK —
`agents/researcher/src/revision.py`. It never authors new claim text or
invents evidence; it only creates a **successor claim** when *existing,
already-recorded* evidence closes a real evidence gap, and otherwise
escalates. Subordinate to everything above and to `templates/CLAIM.md`'s
Atomicity rule and `templates/REVIEW.md`'s Multi-pass resolution exactly
as FACT_CHECK mode is — nothing below expands this agent's authority
beyond what those already establish.

### When it runs

Only after a `FACT_CHECKER` attempt's verdict is `REVISION_REQUIRED` —
never after `PASS` (nothing to revise) and never after `REJECT` (see
"Retry limits" below). It is invoked explicitly (by
`agents/full_pipeline/` or a direct caller), never automatically
scheduled.

### The agent MAY

- Inspect its own `FACT_CHECKER` result and the evidence already on file
  in `research/*.md`.
- Identify a `FACT` claim that needs correction (an evidence *gap*, not a
  wording problem — see "Evidence requirements").
- Create a new successor claim ID via `mutate.supersede_claim` — the same
  primitive `templates/CLAIM.md`'s own supersession convention already
  documents, reused here, not reimplemented.
- Preserve the original claim unchanged (`supersede_claim` never edits
  the old claim's table — only appends a trailing note, exactly as it
  already does for ordinary human-invoked supersession).
- Mark the old claim as superseded using that established pattern.
- Cite research evidence only when it is already, truthfully recorded on
  disk — never create a new `research/*.md` entry in this mode (that is
  RESEARCH mode's job, and RESEARCH mode is out of scope this phase —
  see `SYSTEM.md`'s "Out of scope").
- Create one `revisions/revision-<n>.md` record per claim it diagnoses
  (successful or not — see `templates/REVISION.md`).
- Update the successor claim's own `Fact-check status` field in place
  after re-verifying it (the same whitelisted field
  `mutate.CLAIM_WRITABLE_FIELDS` already permits on any claim).
- Trigger a new `FACT_CHECKER` review attempt (attempt 2) that evaluates
  the successor in place of the claim it superseded — see "Hash and
  supersession behavior."
- Stop after the allowed retry limit (the *existing*
  two-consecutive-`REVISION_REQUIRED` rule — see "Retry limits").

### The agent MUST NOT

- Edit an old claim's `Exact claim` wording.
- Change an old claim's `Classification`.
- Erase, edit, or overwrite any existing `research/*.md`, `claims/*.md`,
  or `reviews/*.md` file — every one of those is append-only/immutable,
  exactly as FACT_CHECK mode already requires.
- Fabricate a citation, a source, or a research entry.
- Upgrade a claim's `Confidence level` without a genuinely new,
  already-existing, reciprocally-confirming source backing the upgrade.
- Convert a `FALSE` claim's status into `PASS`/`VERIFIED` — a sticky
  `FALSE` requires a human/editorial script rewrite, never autonomous
  revision (unchanged from FACT_CHECK mode's own rule).
- Override a human decision, `Owner approval state`, Safety's or
  Originality's verdict, or `CONTENT_ITEM.md`'s `status`.
- Mark anything `APPROVED` or `READY_TO_PUBLISH`.
- Publish anything, anywhere, under any condition.
- Delete or truncate review, claim, or revision history.
- Edit `SCRIPT.md` — a successor claim's fix only takes effect at the
  script level once a human updates `SCRIPT.md`'s `Verified claims` table
  to cite it; see "Hash and supersession behavior" for exactly what this
  means and why.

**The original claim must remain auditable forever.** Every successor is
linked to its predecessor by exactly one `revisions/revision-<n>.md`
record naming both IDs, both content hashes, and the exact evidence used
— see `templates/REVISION.md`.

### Evidence requirements

The revision engine never invents missing evidence. Every `FACT` claim
flagged by the triggering `FACT_CHECKER` attempt is diagnosed into
exactly one of three cases (`revision.diagnose_claim`):

- **Case A — existing evidence supports a correction.** A `research/*.md`
  entry already exists on disk and already, reciprocally names this
  claim in its own `Related claims` field, but the claim's own
  `Supporting sources` doesn't cite it yet. This is the one
  mechanically-checkable, no-fabrication signal this MVP acts on: the
  evidence-linkage gap is real and already true before this agent ever
  runs. A successor claim is created, gaining that citation (and a
  `Confidence level` derived deterministically from the source's own
  `Source reliability` — never guessed).
- **Case B — existing evidence contradicts the original but doesn't
  establish the replacement.** The claim's `Contradictory evidence` field
  is already populated. The agent never invents what the correct
  replacement should say — it creates a revision record documenting the
  conflict (`Revision status = ESCALATED_CONTRADICTORY_EVIDENCE`) and
  escalates.
- **Case C — evidence is insufficient.** No supporting source is
  recorded, and no existing research entry reciprocally supports the
  claim either. The agent stops and escalates
  (`ESCALATED_INSUFFICIENT_EVIDENCE`) rather than manufacture a
  plausible-sounding but unsupported claim. "I don't have enough
  evidence" always wins over an invented one.

A fourth, structural case exists alongside these: if the claim itself
already violates `templates/CLAIM.md`'s Atomicity rule, no successor is
attempted at all — fixing that would require rewording the claim, which
this engine never fabricates (`ESCALATED_ATOMICITY_VIOLATION`).

### Atomic successor creation

A successor claim's `Exact claim`, `Classification`, and `Derived from`
are always byte-identical to the predecessor's — this engine changes only
`Supporting sources` (gains the newly-linked entry) and `Confidence
level` (deterministically derived from that entry's reliability). Since
the predecessor was already atomic when this engine chose to act on it
(a non-atomic claim is routed to `ESCALATED_ATOMICITY_VIOLATION` instead,
never "fixed" by rewording), the successor is trivially atomic too — one
sentence, one classification, by construction, not by a separate check.

### Revision authority — write whitelist

Autonomous Revision Mode may write **only**:

- New successor claim files (`claims/<short-id>.md`, via
  `mutate.supersede_claim` — never overwrites an existing file).
- `revisions/revision-<n>.md` records (via `mutate.write_revision_file`
  — fails closed, `PermissionError`, on any other filename).
- A successor claim's own `Fact-check status` field, post-verification
  (via `mutate.update_claim_field` — the existing whitelist, unchanged).
- A new `reviews/fact_checker-<n>.md` attempt (via the existing,
  unmodified `run_fact_check`/`_apply_result` path).
- `CONTENT_ITEM.md`'s `Fact-check state` field and Notes/history log
  (via the existing, unmodified `run_fact_check`/`_apply_result` path —
  the same two fields FACT_CHECK mode has always been allowed to touch).

It may **never** write: `CONTENT_ITEM.md`'s `status` or `Owner approval
state`; `Safety state`; `Originality state`; `Production status`;
`Production QA state`; anything under `voice/`, `assets/`, `timeline/`,
`captions/`, `thumbnail/`; or any publishing-related field. No code path
in `revision.py` imports anything from `agents/safety/`,
`agents/originality/`, or any production agent's own `mutate.py` — this
is verified by an AST-based test, not just documented (see
`tests/test_revision_write_boundary.py`). An attempted write outside this
whitelist fails closed with `PermissionError`, exactly like every other
whitelisted writer in this codebase.

### Retry limits

**No second, competing retry system exists.** Autonomous Revision Mode
reuses `multipass.can_run_new_attempt` — the *same* function
FACT_CHECK mode already uses — to decide whether a new `FACT_CHECKER`
attempt may be created at all. The successor's re-fact-check becomes
attempt 2 in the exact same `reviews/fact_checker-<n>.md` sequence; if
that is *also* `REVISION_REQUIRED`, the existing two-consecutive rule
(`templates/REVIEW.md` Multi-pass resolution rule 5) blocks a third
attempt automatically, with no new counter anywhere in this module. A
`REJECT` verdict is never autonomously reopened — `run_autonomous_revision`
checks this explicitly and refuses before doing anything else, deferring
to `templates/REVIEW.md` Multi-pass resolution rule 3 exactly as
FACT_CHECK mode already does.

**No in-process loop exists either.** `run_fact_check_with_autonomous_revision`
performs exactly one diagnose-and-revise cycle per call (attempt 1 ->
diagnose -> create permitted successors -> attempt 2), the same
"exactly once per call" discipline `agents/full_pipeline/` already
established in Phase 7E and for the identical reason: nothing in this
codebase can meaningfully retry with unchanged inputs, so a third
in-process attempt would either no-op or burn the two-consecutive-attempts
budget for nothing.

### Hash and supersession behavior

Reuses the existing hash infrastructure — `hashing.compute_claim_hash`
(new, narrow: sha256 of one claim file's raw bytes, used only to prove a
predecessor is unchanged) and the unmodified
`hashing.compute_reviewed_content_hash` for the item-level `REVIEW.md`
hash. A successor claim always receives a new hash (different content:
at minimum, a new `Supporting sources` value). The predecessor's hash is
identical before and after — verified structurally in
`tests/test_revision_immutability.py`, not just asserted.

**`revisions/revision-<n>.md` is the only place old claim and successor
claim are formally linked** — see `templates/REVISION.md`'s "What this
record does NOT do."

**`SCRIPT.md` is a downstream artifact this engine never silently
rewrites.** A successor claim's `Exact claim` text is identical to its
predecessor's, so the *content* of what `SCRIPT.md` asserts remains true
either way — but `SCRIPT.md`'s `Verified claims` table still cites the
predecessor's claim ID after a successor is created, and this agent never
edits it to point at the successor instead (Forbidden actions). To let
the successor's fix actually register at the item level without ever
touching `SCRIPT.md`, `run_fact_check` gained one narrow, optional,
backward-compatible parameter — `claim_substitutions: dict[str, str]`
(old short_id -> new short_id) — used only by
`run_fact_check_with_autonomous_revision`'s own attempt-2 call. It
evaluates the successor in place of the predecessor for that one review
pass and **always discloses every substitution used**, at the top of the
resulting `REVIEW.md`'s `Notes` (e.g. *"AUTONOMOUS REVISION: evaluated
successor claim 'c5_rev1' in place of superseded claim 'c5'"*) — never a
silent substitution. **The attempt's own `Reviewed content hash` is still
always computed from the original, unsubstituted claim ids** (never the
successor's) — this keeps `agents/orchestrator/`'s own freshness re-check
working unmodified (it always recomputes plainly, with no knowledge of
any substitution), and is safe precisely because a superseded claim is
immutable forever, so its contribution to that hash never changes again
either. `SCRIPT.md` itself is never written; a human must still update it
to cite the successor before the fix is reflected anywhere `SCRIPT.md` is
read from directly (e.g. `agents/producer/`).
Any other downstream artifact that already exists (a scene, an asset) was
built from the *predecessor's* content, which is unchanged — nothing
about it becomes newly stale from a successor's creation alone; staleness
is, as before, entirely a function of each downstream agent's own
existing hash check against whatever `SCRIPT.md`/claims actually say at
the time it runs.

### Human escalation conditions (Autonomous Revision Mode)

In addition to every FACT_CHECK-mode condition above:

- Any claim diagnosed as Case B (contradictory evidence, no established
  replacement) or Case C (insufficient evidence).
- Any claim whose own wording already violates the Atomicity rule.
- The underlying `FACT_CHECKER` attempt was `REJECT` (never autonomously
  reopened).
- The two-consecutive-`REVISION_REQUIRED` limit is reached on attempt 2.

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
- (Autonomous Revision Mode) Edit an old claim's wording/classification,
  invent a replacement claim when evidence only contradicts (never
  establishes) one, autonomously reopen a `REJECT`, or edit `SCRIPT.md`
  — see "Autonomous Revision Mode" above for the complete list
