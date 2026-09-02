# Agents

Contracts (and, for three agents so far, MVP implementations) for the
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
- [`originality/`](./originality/) — Originality Reviewer: evaluates
  editorial originality and similarity *risk* during
  `ORIGINALITY_REVIEW` — never a plagiarism/legal determination, never
  "100% original." Has a working MVP (`originality/src/`,
  `originality/README.md`).

## Not yet specified

Script drafting, editorial review, production QA, and publication remain
fully human-driven until a contract is written and approved here — see
`STATE.md` for what's next.

## The pipeline sequence, and the shared interface shape

```
RESEARCH / FACT_CHECK → SAFETY_REVIEW → ORIGINALITY_REVIEW →
EDITORIAL_REVIEW → PRODUCTION_QA
```

No orchestrator exists yet that runs this sequence automatically — each
agent is invoked independently today (its own CLI, its own tests). This
is deliberate: `researcher/`, `safety/`, and `originality/` are each
fully usable on their own, with no dependency on the others having run.
When an orchestrator is eventually built, it can drive this sequence
because every stage's entry point already shares one result shape:

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

All three agents' entry points — `agents.researcher.src.pipeline
.run_fact_check(root, apply)`, `agents.safety.src.pipeline
.run_safety_review(root, apply)`, and `agents.originality.src.pipeline
.run_originality_review(root, apply, ...)` — return a dataclass with this
shape and share the same `dry-run by default, --apply is opt-in`
behavior. A future orchestrator can call each stage's entry point in
sequence, stopping (and surfacing `escalate_to_human`) whenever a stage
doesn't return `PASS`, without needing to know anything about that
stage's internals.

## Shared vs. independent code

`safety/` and `originality/` each reuse `researcher/src`'s generic,
role-agnostic infrastructure (markdown table/section parsing, the
`ReviewVerdict`/`ReviewRecord`/`ContentItem`/`Classification` models, the
`Multi-pass resolution` gating functions, and the two failure-condition
exception types) — never `researcher/`'s fact-check domain logic
(`evidence.py`, `factcheck.py`, `atomicity.py`, or its own field
whitelist/hashing). `safety/` and `originality/` do **not** import from
each other — they are siblings, each depending only on `researcher/`'s
generic base. Each agent has its own `mutate.py` with its own hard-coded
field whitelist, its own `hashing.py`, and its own signal/evidence
evaluation. No agent requires either of the other two to run first or to
exist at all.
