# Assets

Implements [`CONTRACT.md`](./CONTRACT.md). Phase 7C-2 MVP — `src/`/
`tests/` exist and are stdlib-only, matching the shape of the other
agents in this repo.

## Responsibility

For each scene in a production, determines an asset strategy
(`GENERATED` / `RETRIEVED` / `HUMAN_PROVIDED`), produces a deterministic
placeholder artifact (or, for `RETRIEVED`, a structured requirement — no
real retrieval integration exists this phase), and records honest
provenance plus an explicit, never-ambiguous `Historical authenticity
classification`. Does not perform video assembly, real image/video/audio
generation, real external retrieval, or publishing.

```
SCENE → VISUAL REQUIREMENT → ASSET STRATEGY (GENERATED | RETRIEVED |
HUMAN_PROVIDED) → PROVENANCE → AUTHENTICITY → ASSET QA → READY FOR ASSEMBLY
```

## Real providers (Phase 8)

`agents/assets/src/real_providers.py` adds the first two production-
capable providers, both second implementations of `provider.py`'s
existing `GeneratedAssetProvider`/`AssetRetrievalProvider` Protocols —
nothing in `pipeline.py` needed to change to add them.

- **`GeneratedAssetProviderReal`** — a deterministic, fully offline
  illustration renderer (`illustration.py`, Pillow-based: gradient +
  abstract geometric motif, never photorealistic). No network, no
  external model, no API key. Always burns in an "AI-GENERATED
  RECONSTRUCTION" watermark. Used for scene assets with
  `draw_caption=False` — the scene's real narration is already captioned,
  in sync, by the video renderer's own subtitle burn-in
  (`agents/assembler/`), so the illustration itself carries no
  competing/colliding caption text (a real Phase 8 bug, found and fixed —
  see STATE.md).
- **`WikimediaCommonsRetrievalProvider`** — queries Wikimedia Commons'
  public search API (no API key/authentication) for a freely-licensed
  image, downloads it, and records the real source, URL, and license text
  Wikimedia itself reports. `Licensing/provenance status` reflects only a
  structural read of that license text (public-domain/CC-BY/GFDL keyword
  matching) — never a claim of legal review; `Verification status` always
  stays `NOT_STARTED` regardless (a human still confirms it). Retries a
  429/5xx with backoff (a public, shared, rate-limited API is expected to
  need this); on any failure returns a structured `RETRIEVAL_FAILED` —
  never fabricates a source, license, or successful download.

`pipeline.py`'s prompt derivation also changed: it now prefers the
scene's own narration text over `agents/visual_planner/`'s
`visual_description`, which is a **fixed boilerplate string per
authenticity bucket**, never scene-specific — harmless when `GENERATED`
meant "write a placeholder" and `RETRIEVED` meant
`RETRIEVAL_NOT_IMPLEMENTED` regardless of the prompt, but a real defect
now that a real provider acts on it. See `pipeline.py`'s own comment.

`agents/assets/src/qa.py`'s structural check for `RETRIEVED` assets was
also corrected: it previously flagged *any* source URL on a `RETRIEVED`
asset as suspicious (true before Phase 8, when no real retrieval
existed); it now requires a source URL *and* a retrieved artifact file
specifically when `generation_status == RETRIEVED` — the genuinely
correct, expected shape of a real successful retrieval.

## Relationship to `agents/visual_planner/`

`agents/visual_planner/` already creates `assets/asset-<n>.md` skeletons
(a Phase 7B decision, unchanged this phase) with a real `Historical
authenticity classification` already decided but placeholder
provenance/status fields. This agent **preserves that classification
verbatim** and completes every other field with a full rewrite — the same
"placeholder → populated by the next agent" pattern already used between
`agents/producer/` and `agents/visual_planner/` for `PRODUCTION.md`'s
rollups. For a scene Visual Planner left with no asset record at all (no
claim references — "produced directly at assembly"), this agent creates
one from scratch, independently reaching the identical `NOT_APPLICABLE`
classification. See `CONTRACT.md`'s "Relationship to
agents/visual_planner/" for the full reasoning.

## Three asset strategies

| Strategy | What happens | Default when |
|---|---|---|
| `GENERATED` | `LocalTestGeneratedAssetProvider` writes a deterministic, permanently-labeled `TEST / PLACEHOLDER GENERATED ASSET` text artifact — never a real image/video/audio file. | Authenticity is `GENERATED_RECONSTRUCTION` or `NOT_APPLICABLE`. |
| `RETRIEVED` | `LocalTestAssetRetrievalProvider` returns a structured `RETRIEVAL_NOT_IMPLEMENTED` requirement — never a fabricated source/URL/organization. `Generation/retrieval status` stays `NOT_STARTED` (never falsely `RETRIEVED`). | Authenticity is `AUTHENTIC_HISTORICAL_MEDIA` (a real item must be sourced, never generated). |
| `HUMAN_PROVIDED` | Never a default — a caller opts a scene in explicitly (`run_asset_generation(..., human_provided={...})`), optionally with a source description. | Only when explicitly requested per scene. |

Both providers implement a small interface (`provider.py`'s
`GeneratedAssetProvider`/`AssetRetrievalProvider`); `pipeline.py` depends
only on those interfaces, so a real generation/retrieval integration is a
future second implementation, swappable via `run_asset_generation`'s
`generated_provider=`/`retrieval_provider=` arguments without touching
`pipeline.py` or `mutate.py`.

## Authenticity model (the Visual Safety Rule, reimplemented)

Deterministic, driven only by a scene's referenced claims'
`Classification` — reimplemented from `agents/visual_planner/`'s
identical rule (not imported — production agents reuse only generic
infrastructure across each other, never another agent's domain
judgment):

- No claim references → `NOT_APPLICABLE`.
- All referenced claims `FACT` → `AUTHENTIC_HISTORICAL_MEDIA` (sourcing
  intent only — `Verification status` never becomes `VERIFIED` here).
- Any `ASSUMPTION`/`INFERENCE`/`SPECULATION` claim → `GENERATED_RECONSTRUCTION`,
  unconditionally — every What If?/hypothetical/alternate-history
  depiction included.

**Authenticity is always derived from claims, never from strategy or
filename.** For an unprovenanced `HUMAN_PROVIDED` asset, what changes is
`Verification status = REVIEW_REQUIRED` — flagging that a human must
confirm it before use — not the authenticity classification itself.

## Provenance

Every asset record carries: Asset ID, source/reference, acquisition
strategy, `Verification status`, `Generation/retrieval status`,
authenticity classification, and (via `Intended scene`) its originating
scene and, transitively, related claims. No URL, source organization, or
completed acquisition is ever fabricated.

## Asset QA (`qa.py`)

Deterministic, structural checks only — **not** a visual-quality
judgment; this agent cannot and does not claim to determine whether an
image "looks historically accurate." Checks: asset/scene IDs present,
strategy and authenticity values are recognized, claim references
resolve, a `GENERATED` asset has a real artifact reference, a `RETRIEVED`
asset never claims `Generation/retrieval status = RETRIEVED` or carries a
fabricated URL, and an unprovenanced `HUMAN_PROVIDED` asset is
`REVIEW_REQUIRED`, never silently passed.

## Write boundary and staleness

`mutate.py`'s hard-coded whitelist: `assets/asset-<n>.md` and
`assets/asset-<n>.generated.txt` only, plus `PRODUCTION.md`'s `Asset
references (rollup)` section and (only once every scene's asset is
current) `Production status`. A `Scene/visual content hash` (new this
phase — see `CONTRACT.md`'s "Schema changes") records what the asset was
built against; a mismatch on re-run means the underlying scene changed —
the existing asset is `STALE` and is never silently regenerated or
overwritten. **Known limitation:** no versioned supersession
(`asset-01` attempt 1 → attempt 2) — regenerating after a scene change is
a decision this MVP surfaces to a human/operator, matching
`agents/producer/`'s and `agents/voice/`'s identical documented
limitation.

## Running it

```
python3 -m agents.assets.src <content-item-dir> [--apply]
```

Prints a JSON result (`aborted`/`blocked`/`produced`, one plan summary
per scene, `stale_filenames`/`already_up_to_date_filenames`,
`qa_passed`). Without `--apply`, nothing on disk changes. The CLI always
uses the deterministic local test providers and never opts any scene
into `HUMAN_PROVIDED` — use the Python API (`run_asset_generation`) for
that.

```
python3 -m unittest discover -s agents/assets/tests -t .
```

## Known limitations

- Placeholder assets only — no real image/video/audio generation or
  retrieval integration exists; adding one is a future `GeneratedAssetProvider`/
  `AssetRetrievalProvider` implementation, not built this phase.
- One asset per scene, keyed to the scene's order number — matches
  `agents/visual_planner/`'s identical simplification.
- No versioned supersession (see "Write boundary and staleness" above).
- QA is structural only — no visual-quality/historical-accuracy
  evaluation exists or is claimed.
