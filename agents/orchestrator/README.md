# Unified Automated Review Orchestrator — MVP implementation

Implements [`CONTRACT.md`](./CONTRACT.md). The final piece of Phase 6: a
thin coordination layer that runs `agents/researcher/`, `agents/safety/`,
and `agents/originality/` in order and aggregates their results. It makes
no safety/factual/originality judgment itself — see CONTRACT.md's
"Important distinction."

## Running it

```
python3 -m agents.orchestrator.src content/what-if/wi-20260902-black-death-modern-medicine
```

Prints a JSON result covering all three stages. Dry run by default. Add
`--apply` to let each invoked stage write through its own existing path
(the orchestrator itself never writes anything):

```
python3 -m agents.orchestrator.src <content-item-dir> --apply
```

## Running the tests

```
python3 -m unittest discover -s agents/orchestrator/tests -t .
```

## Module map

| Module | Responsibility |
|---|---|
| `models.py` | `OverallResult`, `StageOutcome`, `OrchestratorResult` — the aggregate result shape |
| `stages.py` | `StageAdapter` + the three concrete adapters wiring each agent's own `run_*`/loader/hashing functions |
| `freshness.py` | Idempotency check: is a stage's latest attempt already a valid, unstale `PASS`? |
| `pipeline.py` | `run_automated_review()` — the one entry point |
| `__main__.py` | CLI wrapper |

There is **no `mutate.py`** in this package and no field whitelist of its
own — see CONTRACT.md's "What the orchestrator must NOT do." Every write
under `apply=True` happens inside an invoked agent's own, already-tested
write path.

## How a run works

1. For each stage in order (`FACT_CHECK`, `SAFETY_REVIEW`,
   `ORIGINALITY_REVIEW`):
   a. Check `freshness.find_fresh_pass()` — if the stage's latest attempt
      is already `PASS` and its stored content hash still matches, reuse
      it (`reused_existing_pass=True`) without invoking the stage at all.
   b. Otherwise, call that stage's real `run_*(root, apply)`.
   c. If the call raises, or the stage reports `aborted=True` (nothing
      loadable), record a system error and stop.
   d. If the stage is `blocked` by its own multi-pass gating, look up the
      *actual* last-recorded verdict (never trust an unwritten,
      freshly-recomputed one) so the reported state matches what's really
      on disk.
   e. If the stage didn't cleanly `PASS`, stop — later stages are marked
      `skipped`, never attempted.
2. Derive one `overall_result` from the first blocking stage (or `PASS`
   if none blocked) — see CONTRACT.md's derivation table.

## Relationship to `agents/researcher`, `agents/safety`, `agents/originality`

This package imports each agent's real pipeline entry point directly
(`run_fact_check`, `run_safety_review`, `run_originality_review`) plus
each agent's own hashing function and the shared generic pieces from
`agents/researcher/src` (`loader.load_reviews`, `models.ReviewVerdict`).
It contains no evidence, signal, or originality-scoring logic of its
own — every judgment is the underlying agent's. Removing the orchestrator
changes nothing about how the three agents work; each remains fully
independently usable, exactly as documented in `agents/README.md`.

## Known limitations

- **No true parallelism / no partial-pipeline resume beyond the
  freshness check.** Each run walks the three stages in order from
  `FACT_CHECK`; the freshness check is what makes a second run over an
  already-passed stage cheap and non-duplicating, but the orchestrator
  doesn't persist any state of its own between runs (its result is
  computed fresh every call from the agents' own recorded state).
- **Freshness checking re-reads and re-hashes each stage's bundle** even
  when it turns out to be reused — cheap for local file I/O at this
  scale, but a known inefficiency, not a bug, if this ever needs to run
  on very large content sets.
- **`stage_overrides`** (an optional `pipeline.run_automated_review`
  parameter) exists solely so tests can simulate a reviewer crash or a
  synthetic verdict without touching any agent's real code. It is never
  used in normal operation and is documented here so its presence in the
  code isn't mistaken for a hook meant for production use.
- **No orchestrator-level authority beyond coordination** — by design,
  not an oversight: it cannot advance `status` to `HUMAN_REVIEW`, cannot
  set `Owner approval state`, and cannot publish. Reaching
  `AUTOMATED_REVIEW_COMPLETE` only means the three automated stages
  passed; a human still drives everything from `HUMAN_REVIEW` onward,
  per `CONSTITUTION.md`.
- Editorial review and production QA stages (see `SYSTEM.md`'s pipeline
  diagram) have no agent yet, so the orchestrator only ever coordinates
  the three stages that exist.
