# Project State

Last updated: 2026-09-02

## Phase

**Phase 3 — Golden Sample Validation: complete, approved.**
**Phase 4 — Agent Contracts: in progress (documentation/spec complete,
pending human sign-off before any implementation).**

Phase 1 (foundational docs/structure) and Phase 2 (content-item schema) —
complete, approved.

## Completed (Phase 4)

**Schema decisions (the two deferred questions from Phase 3's AUDIT.md):**
- `templates/CLAIM.md` — added the **Atomicity rule**: a claim's `Exact
  claim` must be one sentence, free of causal/inferential connectors
  ("because", "therefore", "which means", "so that", semicolon-joined
  assertions), and assignable exactly one classification. Claims are also
  now explicitly immutable once created — corrections supersede via a new
  claim ID, never an in-place edit, which is what makes "an agent can
  never silently change a claim's classification" actually enforceable.
- `templates/REVIEW.md` — added the **Multi-pass resolution rule**:
  review attempts are numbered sequentially per role and never
  overwritten; a role's stage state always equals the latest attempt's
  verdict; `REJECT` is terminal until a human logs a reopen decision;
  `PASS` is scoped to the exact artifacts reviewed and goes stale (and
  must be logged as such) if they change afterward; `REVISION_REQUIRED`
  is the only verdict an agent may act on autonomously, and two
  consecutive ones on the same issue escalates to a human rather than a
  third attempt.
- `templates/CONTENT_ITEM.md` — cross-referenced both rules from the
  Stage states section.

**Agent contract:**
- `agents/README.md` — index; states every agent contract is subordinate
  to `CONSTITUTION.md`.
- `agents/researcher/CONTRACT.md` — full contract for the **Research /
  Fact-Check Agent** (first agent in the roadmap), covering purpose,
  inputs/outputs, allowed/forbidden actions, source standards, claim
  handling, fact-check status transitions, confidence handling,
  contradiction reporting, missing-evidence handling, uncertainty
  recording, failure conditions, human escalation conditions, and exact
  pipeline handoff. Specification only — no implementation.

**Consistency-check fix to the Phase 3 golden sample:**
- Applying the new Atomicity rule to the existing sample found `c3` was
  itself a compound claim (semicolon + second sentence, three fused
  assertions). Split into `c3` (untreated fatality), `c10` (antibiotic
  efficacy), `c11` (20th-century antibiotic development — flagged with
  `Confidence level: MEDIUM` and `Supporting sources: N/A` since it isn't
  backed by this item's three research entries, rather than inventing a
  citation). Updated `SCRIPT.md`, `research/01-who-plague-fact-sheet.md`,
  `CONTENT_ITEM.md`'s Notes/history log, and `AUDIT.md` (Phase 4
  addendum) accordingly.

**Documentation updates:**
- `SYSTEM.md` — directory structure now includes `agents/`; added an
  "Agent contracts" section; "Current phase" updated; "out of scope"
  clarified to "no agent *implementations*" (contracts now exist).
- `STATE.md` — this file.

## Verified (Phase 4 consistency checks)

- No `Exact claim` field across all 11 sample claims trips the Atomicity
  rule's connector-word/semicolon test.
- Every claim ID cited in `SCRIPT.md`, research entries, or
  `CONTENT_ITEM.md` resolves to a real `claims/*.md` file (c1–c11).
- Pipeline status string is character-identical between `SYSTEM.md` and
  `templates/CONTENT_ITEM.md`.
- `agents/researcher/CONTRACT.md` never claims publishing authority,
  never permits touching `Owner approval state`, and never permits
  changing top-level `status` — consistent with `CONSTITUTION.md` rules 1
  and 2.
- No new URLs were introduced this phase beyond the three already
  verified in Phase 3 (WHO, Oxford, Britannica) — no invented sources.
- What If? fact/assumption/inference/speculation boundary is unchanged
  and still holds in the (now 11-claim) sample.

## Explicitly not done (by design, this phase)

- No agent code, dependencies, or automation
- No implementation of the Research / Fact-Check Agent
- No additional agent contracts (script, safety, originality, production,
  QA) — only the first agent in the roadmap was specified

## Remaining human sign-off required before agent implementation

1. Approve the two schema rules (Atomicity, Multi-pass resolution) as
   binding — they are currently applied but not yet formally approved.
2. Approve `agents/researcher/CONTRACT.md` as the authoritative contract
   an implementation must satisfy — in particular the boundary that the
   agent may update only `Research state`/`Fact-check state` and never
   the top-level `status` field, and the escalation thresholds (REJECT
   terminal, two-consecutive-REVISION_REQUIRED cap).
3. Confirm the `c11` sourcing gap (antibiotic-history claim with no
   dedicated citation) is acceptable to carry forward as `MEDIUM`
   confidence, or should be backed by a proper source before this sample
   is ever fact-checked.

## Next task

Implement (still no running code — this remains a design step) the
detailed behavioral spec / prompt design for the Research / Fact-Check
Agent based on `agents/researcher/CONTRACT.md`, OR — pending the human
owner's preference — begin drafting the next agent's contract (most
likely a Script Agent, since RESEARCH → SCRIPT is the next handoff this
roadmap hasn't specified yet). Actual code implementation of any agent
requires explicit human sign-off per `CONSTITUTION.md` rule 6 (staged
progress) and the sign-off items above.
