# Contract: Production QA

Governs the automated, structural readiness check that runs after every
other production agent — the last automated gate before human review.
Phase 7D MVP — `src/`/`tests/` exist.

Subordinate to `CONSTITUTION.md` and to `templates/PRODUCTION_QA.md`.

## Purpose

Inspect the assembled output (content, voice, assets, timeline,
captions, thumbnail) and determine whether it is **structurally** ready
for human review. This is never a creative/editorial judgment, never a
substitute for `templates/VIDEO_QA.md`'s human checklist, and never an
approval. It must not publish and must not grant final approval.

## Preconditions

- `CONTENT_ITEM.md status == APPROVED` (checked independently).
- `PRODUCTION.md Production status` in `{METADATA, HUMAN_REVIEW}` —
  `METADATA` is set by `agents/thumbnail/`; `HUMAN_REVIEW` is this
  agent's own successful terminal state (only ever reached on `PASS`),
  accepted for the standard re-run reason.

Anything else — a missing precondition, or an artifact entirely absent
(no timeline/captions/thumbnail/voice at all) — is `BLOCKED`, not
`REVISION_REQUIRED`: there is nothing to check yet.

## Checks (per area)

**Content:** status `APPROVED`; `SCRIPT.md` exists and its hash matches
`PRODUCTION.md`'s stored one; every scene's claim references resolve to
a `claims/*.md` file with a valid `Classification` (What If? distinctions
intact — enforced by `agents/researcher/src.loader.load_claims` already
raising on an invalid/missing classification, reused directly).

**Voice:** `voice/voice-01.md` exists; its `Script content hash` matches
the current script; its `Generated audio` `Reference` is populated;
`Generation status` is `GENERATED`.

**Assets:** every scene has a corresponding `assets/asset-<n>.md`; every
one has a recognized `Historical authenticity classification`; a
`Source` is recorded; a `GENERATED`-strategy asset's `Generation/
retrieval status` is `GENERATED` (its placeholder artifact genuinely
exists); a `HUMAN_PROVIDED`-strategy asset has a real, non-"unknown"
`Source` or is `REVIEW_REQUIRED`. **A `RETRIEVED`-strategy asset can
never pass this MVP's own check** — see "Known limitation: RETRIEVED
strategy" below.

**Timeline:** every scene has a positive duration; no overlaps
(`Start`/`End` reconstructed and verified row-by-row); `Total duration`
equals the sum of scene durations; every scene has a narration, visual,
and captions reference recorded.

**Captions:** `captions/captions-01.md` exists and its hash matches
current narration; every caption chunk's `Start ≤ End`; every caption
chunk's text is a verbatim substring of its scene's narration (the same
integrity property `agents/captions/CONTRACT.md` guarantees, re-verified
independently here rather than trusted blindly).

**Thumbnail:** `thumbnail/thumbnail-01.md` exists and its hash matches
current inputs; `Title concept` is non-empty; if any asset is
`GENERATED_RECONSTRUCTION`, the thumbnail's `Authenticity considerations`
explicitly says so; if the content pillar is `what-if`, the title concept
is hedged (matches `agents/thumbnail/`'s own hedging rule, re-verified).

**Output:** `timeline/timeline-01.md`'s `Video reference` and `Output
hash` are populated; `Playable` is a recognized value (`YES`/`NO`/
`UNVERIFIED` — `NO` is expected and not itself a failure this phase, see
`agents/assembler/CONTRACT.md`'s "Actual video artifact status");
`PRODUCTION.md`'s `Title / description` has a non-empty `Working title`.

## Known limitation: `RETRIEVED` strategy can never fully pass this phase

No real retrieval integration exists (`agents/assets/CONTRACT.md`'s
`LocalTestAssetRetrievalProvider` always returns
`RETRIEVAL_NOT_IMPLEMENTED`, and `Generation/retrieval status` for a
`RETRIEVED`-strategy asset can only ever legitimately be `NOT_STARTED`
this phase — never falsely `RETRIEVED`). This agent's Assets check
therefore correctly reports `REVISION_REQUIRED` for any production
containing an all-`FACT` scene (which defaults to `RETRIEVED`), honestly
reflecting that real sourcing hasn't happened yet — **this is working as
intended, not a bug to route around.** A production reaching `PASS` this
phase is necessarily one whose scenes are all hypothetical/generated or
non-representational (`GENERATED`/`NOT_APPLICABLE`), or use
`HUMAN_PROVIDED` with real, stated provenance. Once a real retrieval
provider exists (a later phase), all-`FACT` productions can reach `PASS`
too.

## Verdict states

`PASS` (every check passed — a claim about structural readiness, never
about creative quality, and never an approval), `REVISION_REQUIRED`
(artifacts exist but one or more checks failed), `BLOCKED` (a
precondition wasn't met, or a required artifact is entirely absent — no
checks could run), `SYSTEM_ERROR` (the check process itself failed
unexpectedly — wrapped and reported, never silently swallowed).

## Allowed actions

- Read everything: `CONTENT_ITEM.md`, `PRODUCTION.md`, `SCRIPT.md`,
  every scene, every claim, `voice/voice-01.md`, every
  `assets/asset-<n>.md`, `timeline/timeline-01.md`,
  `captions/captions-01.md`, `thumbnail/thumbnail-01.md`
- Create `qa/production-qa-<n>.md`
- On `PASS` only, advance `PRODUCTION.md`'s `Production status` from
  `METADATA` to `HUMAN_REVIEW` and set its `Production QA state` section

## Forbidden actions

Never writes to `CONTENT_ITEM.md`, a claim, `SCRIPT.md`, any
`scenes/scene-<n>.md`/`voice/voice-<n>.md`/`assets/asset-<n>.md`/
`timeline/timeline-<n>.md`/`captions/captions-<n>.md`/
`thumbnail/thumbnail-<n>.md` field, or `templates/VIDEO_QA.md`. Never
sets `PRODUCTION.md`'s `Human review state` (human-only, per that
section's own text — "never an agent"). Never sets `Production status`
to `APPROVED` or `READY_TO_PUBLISH` under any condition — `HUMAN_REVIEW`
is the highest state this agent may ever set. Never publishes.

## Handoff

On `PASS`, `qa/production-qa-<n>.md`'s `Verdict` is `PASS` and
`PRODUCTION.md`'s `Production status` advances to `HUMAN_REVIEW` — the
production is now reported ready for human review, never automatically
approved, scheduled, uploaded, or published. On any other verdict,
`Production status` is left untouched.
