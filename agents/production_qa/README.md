# Production QA

Implements [`CONTRACT.md`](./CONTRACT.md). Phase 7D MVP — `src/`/
`tests/` exist and are stdlib-only.

## Responsibility

Inspects the assembled output (content, voice, assets, timeline,
captions, thumbnail) and determines whether it is **structurally** ready
for human review — never a creative/editorial judgment, never a
substitute for `templates/VIDEO_QA.md`'s human checklist, and never an
approval. Cannot publish, cannot grant final approval.

## Verdict states

`PASS` (every check passed — a claim about structural readiness only),
`REVISION_REQUIRED` (artifacts exist but a check failed),
`BLOCKED` (a precondition or a whole required artifact is missing, or an
upstream input is stale — nothing could be meaningfully checked),
`SYSTEM_ERROR` (the check process itself failed unexpectedly, caught and
reported rather than crashing the caller).

**Staleness is always `BLOCKED`, never a soft check** — a QA pass
evaluated against an outdated script, voice track, or asset can't be
trusted at all, so `pipeline.py` gates on it before running any checks,
the same way `agents/assembler/`'s, `agents/captions/`'s, and
`agents/thumbnail/`'s own preconditions already do.

## Known limitation: `RETRIEVED` strategy can never fully pass this phase

No real retrieval integration exists — `agents/assets/`'s
`LocalTestAssetRetrievalProvider` always returns
`RETRIEVAL_NOT_IMPLEMENTED`, so a `RETRIEVED`-strategy asset's
`Generation/retrieval status` can only legitimately be `NOT_STARTED`
this phase. This agent's Assets check therefore correctly reports
`REVISION_REQUIRED` for any production containing an all-`FACT` scene
(which defaults to `RETRIEVED`) — **this is intentional, not a bug.** A
production reaching `PASS` this phase is one whose scenes are all
hypothetical/generated/non-representational, or `HUMAN_PROVIDED` with
real stated provenance. See `agents/production_qa/tests/builders.py`'s
`build_passing_item` for a concrete example.

## Checks (by area)

Content, Voice, Assets, Timeline, Captions, Thumbnail, Output — see
`CONTRACT.md`'s "Checks (per area)" for the full list. Every check
**re-verifies** what an earlier agent already claimed rather than
trusting it blindly (e.g. caption text is independently re-checked
against narration, not assumed faithful because `agents/captions/` says
so).

## Write boundary

`mutate.py`'s whitelist: `qa/production-qa-<n>.md` only, plus
`PRODUCTION.md`'s `Production QA state` section and (only on `PASS`)
`Production status` — hard-coded to allow setting it to `HUMAN_REVIEW`
only, never `APPROVED` or `READY_TO_PUBLISH`. Never touches `Human
review state` (human-only, per that section's own text).

## Relationship to other agents

Reuses `agents/producer/src.hashing`, `agents/assets/src.hashing`, and
`agents/assets/src.scene_reader.load_scene_visual_records` directly.
Reads every other production agent's output but never their domain
logic. Runs after `agents/thumbnail/` (`Production status = METADATA`)
and, on `PASS`, hands off to human review (`Production status =
HUMAN_REVIEW`) — the final automated stage in this phase.

## Running it

```
python3 -m agents.production_qa.src <content-item-dir> [--apply]
```

```
python3 -m unittest discover -s agents/production_qa/tests -t .
```

## Known limitations

- See "Known limitation: RETRIEVED strategy" above.
- No versioned supersession — one `production-qa-01` attempt per
  production.
- Structural checks only — no visual-quality, pronunciation, or
  historical-accuracy evaluation exists or is claimed.
