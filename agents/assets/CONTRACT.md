# Contract: Assets

Governs turning a scene's finalized visual requirement into a structured,
provenance-honest `templates/ASSET.md` record — an asset *strategy*
(generated/retrieved/human-provided), a deterministic test artifact for
that strategy, and an explicit, never-ambiguous authenticity
classification. Phase 7C-2 MVP — `src/`/`tests/` exist.

Subordinate to `CONSTITUTION.md` and to `templates/ASSET.md` (the schema
it produces against). Where anything below conflicts with that, it wins.

## Purpose

For each scene in a production, determine what asset it needs, how that
asset will be acquired (`GENERATED` / `RETRIEVED` / `HUMAN_PROVIDED`),
produce a deterministic placeholder artifact (or, for `RETRIEVED`, a
structured requirement — no real retrieval integration exists this
phase), and record honest provenance and an explicit `Historical
authenticity classification`. This agent does **not** perform video
assembly, real image/video/audio generation, real external retrieval, or
publishing.

```
SCENE → VISUAL REQUIREMENT → ASSET STRATEGY (GENERATED | RETRIEVED |
HUMAN_PROVIDED) → PROVENANCE → AUTHENTICITY → ASSET QA → READY FOR ASSEMBLY
```

## Relationship to `agents/visual_planner/` — resolving a real ownership question

`agents/visual_planner/CONTRACT.md` already gives Visual Planner
authority to create `assets/asset-<n>.md` (a Phase 7B decision made
before this agent existed). This agent does not change Visual Planner's
code or contract (out of this phase's stated scope), so it is designed to
coexist with that fact rather than conflict with it:

- For a scene where Visual Planner already created `assets/asset-<n>.md`
  (any scene whose claims are all `FACT`, or which cites any
  non-`FACT` claim — see Visual Planner's Visual Safety Rule), this agent
  treats that file as an **intentionally incomplete skeleton**: real
  content for `Provenance`/`Generation/retrieval status`/`Verification
  status` doesn't exist yet, `Historical authenticity classification` is
  the one field Visual Planner already decided authoritatively. This
  agent **reads and preserves that classification verbatim** — it never
  recomputes or overrides it — then performs one full rewrite of the file
  to complete every other field. This is the same "placeholder →
  populated by the next agent with real content" pattern already
  established between `agents/producer/` and `agents/visual_planner/`
  for `PRODUCTION.md`'s rollup sections (see `agents/README.md`'s "The
  production lifecycle"), not a new precedent.
- For a scene Visual Planner left with **no** asset record at all
  (`Visual type = ON_SCREEN_TEXT_GRAPHIC`, no claim references — Visual
  Planner's own contract calls this "produced directly at assembly, no
  discrete asset record"), this agent still creates one: assembly needs
  *something* to place in the scene, and per this phase's task
  description "modern infographic → `NOT_APPLICABLE`" is one of the
  explicit classification cases this agent must prove out. This agent's
  own authenticity classification (below) independently reproduces
  Visual Planner's identical no-claims → `NOT_APPLICABLE` rule, so the
  outcome is consistent either way this agent reaches a scene.
- Once **this** agent has written its own `Scene/visual content hash` to
  an `assets/asset-<n>.md` file, that file is this agent's own history
  from then on — re-running never overwrites it except through the same
  hash-match/stale logic every other agent in this repo uses (see
  "Re-running / staleness").

## Preconditions

- `CONTENT_ITEM.md`'s `status` must be `APPROVED` — checked
  independently of `PRODUCTION.md` (the same defense-in-depth pattern
  `agents/visual_planner/` and `agents/voice/` both already use).
- `PRODUCTION.md` must exist with `Production status` equal to either
  `ASSET_COLLECTION` (the state `agents/visual_planner/` sets once every
  scene has a finalized visual plan — reliably reachable, unlike the
  gaps found in earlier phases, since Visual Planner's own contract
  already owns setting it) or `ASSEMBLY` (this agent's own successful
  terminal state — accepted for the same reason `agents/voice/` accepts
  its own terminal state: so re-running after a prior success can still
  reach the already-up-to-date/staleness check instead of always
  blocking on this precondition).
- The current `SCRIPT.md`'s content hash (`agents/producer/src/hashing.py`,
  reused directly) must match `PRODUCTION.md`'s stored `Script content
  hash` — otherwise the whole production plan is stale relative to the
  script, and this agent refuses to build assets against outdated scenes.
- Every scene's `Source / claim references` must resolve to an actual
  `claims/*.md` file. A scene citing a claim with no corresponding file
  blocks the entire run (structural failure) rather than silently
  skipping that one asset.

## Schema changes (documented per this phase's task requirement)

Four additive, backward-compatible changes to `templates/ASSET.md` —
none renames or removes an existing field, so the Phase 7A golden
`assets/asset-01.md`–`asset-03.md` fixture remains valid as-is:

1. **`Scene/visual content hash`** (identity table) — needed for
   staleness detection (task requirement: "If the scene or visual
   requirement changes, the existing asset requirement/artifact must
   become STALE"); mirrors the identical, already-established pattern in
   `templates/PRODUCTION.md`/`REVIEW.md`/`VOICE.md`.
2. **`Generated vs. retrieved` gains a third value, `HUMAN_PROVIDED`** —
   the field name is kept (not renamed to "Acquisition strategy") so the
   golden fixture's existing `GENERATED`/`RETRIEVED` values need no
   change; the field's meaning was already "how this asset is acquired,"
   which `HUMAN_PROVIDED` fits without redefinition.
3. **New `## Generation/retrieval status` section** — `templates/ASSET.md`
   had no field distinguishing "an artifact actually exists" from "a
   classification/provenance skeleton exists" until this phase; mirrors
   `templates/SCENE.md`'s field of the identical name and vocabulary,
   extended with `HUMAN_PROVIDED`. Explicitly documented: `RETRIEVED` may
   only be set once a real retrieval has happened — since no retrieval
   integration exists this phase, a `RETRIEVED`-strategy asset's status
   stays `NOT_STARTED`, never falsely claiming retrieval occurred.
4. **`Verification status` gains a fifth value, `REVIEW_REQUIRED`** —
   needed for the task's explicit rule: "Human-provided unknown-origin
   image: MUST NOT automatically become authentic. Require provenance or
   flag `REVIEW_REQUIRED`." Distinct from `DISPUTED` (an active
   conflict) and `NOT_STARTED` (nothing checked yet).

No other template was touched. `related claims` was deliberately **not**
added as a new field — an asset's claims are already reachable
transitively via `Intended scene` → that scene's `Source / claim
references`, the same link `templates/ASSET.md` already relied on;
adding a redundant field would just be a second place for the same fact
to go stale.

## Inputs

- `CONTENT_ITEM.md` (`status` — read-only)
- `PRODUCTION.md` (`Production status`, `Script content hash` — read-only
  except as listed below)
- `SCRIPT.md` (for its current content hash only — read-only)
- `scenes/scene-<n>.md` (`Visual type`, `Visual description`, `Source /
  claim references`, `Narration text` — read-only)
- `claims/*.md` (`Classification` only, to derive authenticity — read-only)
- Any pre-existing `assets/asset-<n>.md` (for its `Historical
  authenticity classification` only, when created by
  `agents/visual_planner/` — read, then superseded per "Relationship to
  `agents/visual_planner/`" above)

## Outputs

- `assets/asset-<n>.md` (one per scene)

## Asset strategies

Every asset is assigned exactly one of three strategies. There is no
default; every asset states its strategy explicitly.

- **`GENERATED`** — produced by `agents/assets/src/provider.py`'s
  `GeneratedAssetProvider` interface. This phase's only implementation,
  `LocalTestGeneratedAssetProvider`, is deterministic (same visual
  description always produces the same artifact content), makes no
  network calls, and writes a plain-text placeholder artifact
  (`assets/asset-<n>.generated.txt`) permanently labeled `TEST /
  PLACEHOLDER GENERATED ASSET — this is NOT an actual image, video, or
  audio file`. A real image/video/audio generation integration is a
  future second `GeneratedAssetProvider` implementation; nothing in
  `pipeline.py` needs to change to add one.
- **`RETRIEVED`** — handled by `agents/assets/src/provider.py`'s
  `AssetRetrievalProvider` interface. This phase's only implementation,
  `LocalTestAssetRetrievalProvider`, never contacts any external service
  and never fabricates a source, URL, or organization name — it returns
  a structured `RETRIEVAL_NOT_IMPLEMENTED` result naming what a human or
  a future retrieval integration would need to source. `Source` stays
  `"not yet sourced"`; `Generation/retrieval status` stays `NOT_STARTED`.
- **`HUMAN_PROVIDED`** — never the deterministic default for any scene;
  a caller must explicitly select it per scene (`run_asset_generation`'s
  `human_provided` argument), optionally supplying a source description.
  This agent never assumes a human-provided asset is authentic, licensed,
  or provenanced merely because a human supplied it. See "Authenticity"
  below for exactly how missing provenance is handled.

The default strategy for a scene not explicitly marked `HUMAN_PROVIDED`
is derived from its authenticity classification (see below):
`AUTHENTIC_HISTORICAL_MEDIA` → `RETRIEVED` (a real historical item must
be sourced, never generated); `GENERATED_RECONSTRUCTION` or
`NOT_APPLICABLE` → `GENERATED`.

## Authenticity classification (the Visual Safety Rule, reimplemented)

Deterministic, driven only by the `Classification` of a scene's
referenced claims — identical rule to `agents/visual_planner/src/classification.py`,
reimplemented here (not imported) per this repo's established
sibling-agent boundary: production agents reuse only truly generic
infrastructure across each other (parsing, hashing, scene-field reading),
never another agent's own domain judgment, so that no agent's safety
behavior can be silently altered by changing a different agent's code.

- No claim references → `NOT_APPLICABLE` (e.g. a modern infographic or
  explanatory diagram).
- All referenced claims `FACT` → `AUTHENTIC_HISTORICAL_MEDIA` — as
  **sourcing intent only**; `Verification status` never becomes
  `VERIFIED` by this agent.
- Any referenced claim `ASSUMPTION`/`INFERENCE`/`SPECULATION` (including
  every What If? hypothetical/alternate-history depiction, and an
  imagined technology in a historical setting) → `GENERATED_RECONSTRUCTION`,
  unconditionally.

**Authenticity classification is always derived from claim data, never
from strategy or filename.** A `HUMAN_PROVIDED` asset for an all-`FACT`
scene is still classified `AUTHENTIC_HISTORICAL_MEDIA`; what changes for
an unprovenanced human-provided asset is `Verification status`, not this
field — see below. This keeps "never infer authenticity from filename
alone" (this phase's explicit rule) consistent with never inferring it
from acquisition method either.

**Human-provided provenance handling:** if a scene is marked
`HUMAN_PROVIDED` without a non-empty, non-"unknown" source description,
`Verification status` is set to `REVIEW_REQUIRED` — regardless of what
the authenticity classification says — so the asset can never be treated
as safe to use without a human confirming it first. A `HUMAN_PROVIDED`
asset with a real stated source keeps `Verification status =
NOT_STARTED` (an honest starting point, not `VERIFIED` — a human
stating a source is not the same as this agent having checked it).

## Provenance

Every asset record includes, at minimum: Asset ID, source/reference,
acquisition strategy (`Generated vs. retrieved`), `Verification status`
(carrying `REVIEW_REQUIRED` where applicable), `Generation/retrieval
status`, `Historical authenticity classification`, `Intended scene`
(originating scene), and (transitively, via that scene) related claims.
This agent never fabricates a URL, a source organization, or an
acquisition that didn't happen — `RETRIEVED` and unprovenanced
`HUMAN_PROVIDED` assets are honest about not being sourced yet.

## Asset QA (`qa.py`)

Deterministic, structural checks only — **not** a visual-quality
judgment. This agent cannot and does not claim to determine whether an
image "looks historically accurate"; that is a future, unbuilt visual QA
layer. Checked per asset: Asset ID and Scene ID are present; strategy is
one of the three valid values; authenticity classification is one of the
three valid values; `Verification status` is a recognized value;
source/reference matches what the strategy implies (never a fabricated
URL for `RETRIEVED`, never asserting `GENERATED` without an actual
artifact reference); every claim reference resolves to a real
`claims/*.md` file; a `GENERATED` asset's artifact file actually exists
and is labeled as generated; a `RETRIEVED` asset never claims
`Generation/retrieval status = RETRIEVED` (since no real retrieval
happened); a `HUMAN_PROVIDED` asset without a stated source is flagged
`REVIEW_REQUIRED`, not silently passed.

## Allowed actions

- Read `CONTENT_ITEM.md`, `PRODUCTION.md`, `SCRIPT.md`, every scene's
  `Visual type`/`Visual description`/`Source / claim references`/
  `Narration text`, every referenced claim's `Classification`, and any
  pre-existing `assets/asset-<n>.md`'s `Historical authenticity
  classification`
- Create/rewrite `assets/asset-<n>.md` (per "Relationship to
  `agents/visual_planner/`" and "Re-running / staleness" — never a
  silent overwrite of this agent's own prior, unstale work)
- Create the corresponding `assets/asset-<n>.generated.txt` artifact for
  `GENERATED`-strategy assets
- Update `PRODUCTION.md`'s `Asset references (rollup)` section, and
  advance `Production status` from `ASSET_COLLECTION` to `ASSEMBLY` once
  every scene's asset is recorded

## Forbidden actions

The Asset agent must **never**:

- Leave `Historical authenticity classification` blank, or invent a
  fourth value beyond `AUTHENTIC_HISTORICAL_MEDIA` /
  `GENERATED_RECONSTRUCTION` / `NOT_APPLICABLE`.
- Infer authenticity from a filename, a strategy, or any signal other
  than the scene's referenced claims' `Classification`.
- Fabricate a URL, archive name, or source organization for a
  `RETRIEVED` or unprovenanced `HUMAN_PROVIDED` asset.
- Mark a `RETRIEVED` asset's `Generation/retrieval status` as `RETRIEVED`
  when no real retrieval happened, or mark any placeholder artifact as
  production-ready.
- Create, delete, or modify a claim, its classification, its evidence, or
  its fact-check status. If a scene cites a claim with no corresponding
  file, this agent fails safely (blocks the run) rather than inventing
  one.
- Modify `SCRIPT.md`, `CONTENT_ITEM.md` (status, approval, or any stage
  state), any `scenes/scene-<n>.md` field, any `voice/voice-<n>.md`
  field, or any `reviews/*.md` file.
- Publish anything, anywhere, under any condition.

## Re-running / staleness

If `assets/asset-<n>.md` already carries a `Scene/visual content hash`
written by this agent: a matching hash means it's already up to date
(no-op); a mismatched hash means the scene's narration, claim
references, or visual type/description changed since — the existing
asset is `STALE`. This agent refuses to silently regenerate it, leaving
the existing record and artifact untouched, the same conservative
pattern `agents/producer/CONTRACT.md`'s and `agents/voice/CONTRACT.md`'s
own "Re-running" sections use. **Known limitation, documented rather
than worked around:** this MVP does not implement versioned supersession
(`asset-01` attempt 1 → attempt 2) the way `templates/CLAIM.md` does for
claims — the existing production-versioning mechanism (`PRODUCTION.md`'s
own `Production ID` suffix scheme) has no defined convention for a
*per-asset* attempt history either, and inventing one here, unprompted,
would be new conflicting history semantics rather than a documented gap;
regenerating after a scene change is a decision this MVP surfaces to a
human/operator, not automates.

## Handoff

On completion, every scene has an `assets/asset-<n>.md` record with an
explicit strategy, honest provenance, and an unambiguous authenticity
classification, and `PRODUCTION.md`'s `Production status` advances to
`ASSEMBLY` — the next, still unbuilt stage (Phase 7D) where a real
renderer would assemble scenes, voice, and assets into an actual video.
