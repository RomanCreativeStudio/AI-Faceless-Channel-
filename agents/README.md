# Agents

Contracts and MVP implementations for the automated review pipeline —
what each is allowed and forbidden to do, and how it hands off to the
next stage.

Every agent contract here is subordinate to `CONSTITUTION.md`. Where
anything in an agent contract could be read as conflicting with
`CONSTITUTION.md`, the constitution wins — a contract is never grounds to
override it. No agent has publishing authority, ever, at any stage.

## Agents specified so far

- [`researcher/`](./researcher/) — Research / Fact-Check Agent:
  populates `RESEARCH.md`/`CLAIM.md` during `RESEARCH`, verifies claims
  during `FACT_CHECK`. FACT_CHECK mode has a working MVP
  (`researcher/src/`, `researcher/README.md`).
- [`safety/`](./safety/) — Safety Reviewer: evaluates `SCRIPT.md` for
  safety/policy risk during `SAFETY_REVIEW`. Has a working MVP
  (`safety/src/`, `safety/README.md`).
- [`originality/`](./originality/) — Originality Reviewer: evaluates
  editorial originality and similarity *risk* during
  `ORIGINALITY_REVIEW` — never a plagiarism/legal determination, never
  "100% original." Has a working MVP (`originality/src/`,
  `originality/README.md`).
- [`orchestrator/`](./orchestrator/) — Unified Automated Review
  Orchestrator: runs the three agents above in order and aggregates
  their results. Makes **no** review judgment of its own — see
  `orchestrator/CONTRACT.md`'s "Important distinction." Has a working
  MVP (`orchestrator/src/`, `orchestrator/README.md`).

Three more have **contracts only, no implementation yet** — Phase 7's
foundation for the production stack, which starts once a content item
reaches `status = APPROVED` and is a separate lifecycle from everything
above (see `templates/PRODUCTION.md`):

- [`producer/`](./producer/) — turns an approved script into
  `PRODUCTION.md` + `scenes/*.md`. Never writes to `CONTENT_ITEM.md`,
  changes a claim, or bypasses human approval.
- [`voice/`](./voice/) — narration → voiceover audio, provider-agnostic
  (no vendor named anywhere in the contract). Never alters narration
  meaning or inserts unsupported claims.
- [`visual-planner/`](./visual-planner/) — finalizes each scene's visual
  requirement and creates `assets/*.md` records. Never presents generated
  media as authentic, never invents historical evidence.

## Not yet specified

Editorial review and production QA remain fully human-driven until a
contract is written and approved here (the orchestrator's pipeline stops
before them). Publication remains human-gated permanently, by
`CONSTITUTION.md` rule 2, regardless of what gets automated upstream of
it — see `STATE.md` for what's next.

## The pipeline sequence, and the shared interface shape

```
RESEARCH / FACT_CHECK → SAFETY_REVIEW → ORIGINALITY_REVIEW →
EDITORIAL_REVIEW → PRODUCTION_QA
```

`agents/orchestrator/` now runs the first three stages
(`FACT_CHECK → SAFETY_REVIEW → ORIGINALITY_REVIEW`) in order, stopping at
the first stage that doesn't cleanly `PASS` — see
`orchestrator/CONTRACT.md`. `EDITORIAL_REVIEW` and `PRODUCTION_QA` have
no agent yet, so the orchestrator's pipeline currently ends at
`ORIGINALITY_REVIEW`; a clean run reaches `AUTOMATED_REVIEW_COMPLETE`,
which hands off to the still fully human-driven `HUMAN_REVIEW` stage (the
orchestrator never touches `status`, so nothing actually advances
automatically).

Each of the four agents remains independently usable — the orchestrator
existing doesn't create any new dependency between `researcher/`,
`safety/`, and `originality/`, and each still has its own CLI and test
suite. This works because every review-stage entry point shares one
result shape:

| Field | Meaning |
|---|---|
| `verdict` | `PASS` / `REVISION_REQUIRED` / `REJECT` (`ReviewVerdict`) |
| `reasons` | Human-readable findings, one per line |
| `required_changes` | What would need to change for a future `PASS` |
| `escalate_to_human` | `True` whenever a human must decide — never silently folded into `PASS` |
| `content_hash` | For staleness detection (`templates/REVIEW.md` Multi-pass resolution rule 4) |
| `aborted` / `abort_reason` | Nothing loadable — no `REVIEW.md` was written |
| `blocked` / `blocked_reason` | Multi-pass gating refused a new attempt (REJECT-terminal or two-consecutive-`REVISION_REQUIRED`) |
| `review_path` | Where the `REVIEW.md` was written, if `apply=True` and not blocked |

All three review agents' entry points — `agents.researcher.src.pipeline
.run_fact_check(root, apply)`, `agents.safety.src.pipeline
.run_safety_review(root, apply)`, and `agents.originality.src.pipeline
.run_originality_review(root, apply, ...)` — return a dataclass with this
shape and share the same `dry-run by default, --apply is opt-in`
behavior. `agents.orchestrator.src.pipeline.run_automated_review(root,
apply, ...)` calls each of those directly, in order, and aggregates their
results into one `OrchestratorResult` (same core fields, plus
`stages_executed`/`stages_skipped`/`first_blocking_stage` — see
`orchestrator/CONTRACT.md`'s Result model) — it doesn't need to know
anything about any stage's internals to do this.

## Shared vs. independent code

`safety/` and `originality/` each reuse `researcher/src`'s generic,
role-agnostic infrastructure (markdown table/section parsing, the
`ReviewVerdict`/`ReviewRecord`/`ContentItem`/`Classification` models, the
`Multi-pass resolution` gating functions, and the two failure-condition
exception types) — never `researcher/`'s fact-check domain logic
(`evidence.py`, `factcheck.py`, `atomicity.py`, or its own field
whitelist/hashing). `safety/` and `originality/` do **not** import from
each other — they are siblings, each depending only on `researcher/`'s
generic base. Each review agent has its own `mutate.py` with its own
hard-coded field whitelist, its own `hashing.py`, and its own
signal/evidence evaluation. `orchestrator/` imports each of the three
agents' real `run_*` pipeline functions directly (never reimplementing
their logic) plus the same generic pieces from `researcher/src`; it has
**no `mutate.py` of its own** — every write under `--apply` happens
inside the invoked agent's own existing path. No agent requires any other
to run first or to exist at all.

## The production lifecycle (Phase 7 — schema only)

```
PRODUCTION_PLANNING → VOICE → VISUAL_PLANNING → ASSET_COLLECTION →
ASSEMBLY → CAPTIONS → THUMBNAIL → METADATA → PRODUCTION_QA →
HUMAN_REVIEW → APPROVED → READY_TO_PUBLISH
```

Owned by `templates/PRODUCTION.md`, tracked entirely separately from the
content-review `status` above — no production agent writes to
`CONTENT_ITEM.md` at all. `producer/` → `voice/` → `visual-planner/` map
onto the first three states; the rest have neither an agent nor an
implementation yet. `READY_TO_PUBLISH` is the last state any of this may
ever reach — actual publishing is a separate, human-driven system, not
built in this phase or any so far. See
`content/what-if/wi-20260902-black-death-modern-medicine/PRODUCTION.md`
for a golden fixture demonstrating the schema against real content.
