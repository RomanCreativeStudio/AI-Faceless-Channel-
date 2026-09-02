# Agents

Contracts (and, for two agents so far, MVP implementations) for the
automated review pipeline — what each is allowed and forbidden to do, and
how it hands off to the next stage.

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

## Not yet specified

Script drafting, originality review, editorial review, production QA,
and publication remain fully human-driven until a contract is written and
approved here — see `STATE.md` for what's next.

## The pipeline sequence, and the shared interface shape

```
RESEARCH / FACT_CHECK → SAFETY_REVIEW → ORIGINALITY_REVIEW →
EDITORIAL_REVIEW → PRODUCTION_QA
```

No orchestrator exists yet that runs this sequence automatically — each
agent is invoked independently today (its own CLI, its own tests). This
is deliberate: `researcher/` and `safety/` are each fully usable on their
own, with no dependency on the other having run. When an orchestrator is
eventually built, it can drive this sequence because every stage's entry
point already shares one result shape:

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

Both existing agents' entry points — `agents.researcher.src.pipeline
.run_fact_check(root, apply)` and `agents.safety.src.pipeline
.run_safety_review(root, apply)` — return a dataclass with this shape and
share the same `dry-run by default, --apply is opt-in` behavior. A future
orchestrator can call each stage's entry point in sequence, stopping (and
surfacing `escalate_to_human`) whenever a stage doesn't return `PASS`,
without needing to know anything about that stage's internals.

## Shared vs. independent code

`safety/` reuses `researcher/src`'s generic, role-agnostic infrastructure
(markdown table/section parsing, the `ReviewVerdict`/`ReviewRecord`/
`ContentItem` models, the `Multi-pass resolution` gating functions, and
the two failure-condition exception types) — never its fact-check domain
logic (`evidence.py`, `factcheck.py`, `atomicity.py`, or its own field
whitelist/hashing). Each agent has its own `mutate.py` with its own
hard-coded field whitelist, its own `hashing.py`, and its own signal/
evidence evaluation. Neither agent requires the other to run first or to
exist at all.
