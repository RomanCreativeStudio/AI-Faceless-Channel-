# Research / Fact-Check Agent — MVP implementation

Implements [`CONTRACT.md`](./CONTRACT.md). Phase 5 of the roadmap: the
first agent that actually runs, scoped to **FACT_CHECK only** (structured
evidence evaluation against existing `research/`/`claims/` records — not
live web retrieval, and not RESEARCH-mode source collection). Stdlib
Python only, no dependencies.

## Running it

```
python3 -m agents.researcher.src content/what-if/wi-20260902-black-death-modern-medicine
```

Prints a JSON `FactCheckResult` to stdout. This is a **dry run** — nothing
on disk changes. Add `--apply` to actually write
`reviews/fact_checker-<n>.md` and update `CONTENT_ITEM.md`'s `Fact-check
state` field plus its Notes/history log (the only two things
`CONTRACT.md`'s Allowed actions permit):

```
python3 -m agents.researcher.src <content-item-dir> --apply
```

The real golden sample (`content/what-if/wi-20260902-black-death-modern-medicine`)
has **not** been run with `--apply` as part of this phase — it's exercised
read-only by the test suite and the dry-run example above. Actually
fact-checking it for real (and updating its documented "stops before
FACT_CHECK" status) is left for a deliberate follow-up, not a side effect
of implementing the agent.

## Running the tests

```
python3 -m unittest discover -s agents/researcher/tests -t .
```

## Module map

| Module | Responsibility |
|---|---|
| `models.py` | Dataclasses/enums mirroring `templates/*.md` fields verbatim |
| `parsing.py` | Generic `\| Field \| Value \|` table and `## Heading` section parsing |
| `loader.py` | Reads a content item directory into a `ContentBundle` |
| `atomicity.py` | `templates/CLAIM.md` Atomicity rule, checks 1-2 (mechanical) |
| `evidence.py` | Per-claim evaluation: `EvidenceSupport` -> `FactCheckStatus` |
| `factcheck.py` | Rolls per-claim evaluations into one verdict |
| `multipass.py` | `templates/REVIEW.md` Multi-pass resolution rule |
| `hashing.py` | `Reviewed content hash` (PASS staleness detection) |
| `review_writer.py` | Renders a `REVIEW.md`-formatted file |
| `mutate.py` | The *only* code that writes to an existing `CONTENT_ITEM.md`/`CLAIM.md`, field-whitelisted |
| `pipeline.py` | `run_fact_check()` — the one entry point gluing all of the above |
| `__main__.py` | CLI wrapper |

## Design decisions worth knowing about

- **Research collection vs. fact-check evaluation are separated in the
  data model, not the templates.** `EvidenceSupport` (`SUPPORTED` /
  `PARTIALLY_SUPPORTED` / `UNSUPPORTED` / `CONTRADICTED` / `UNRESOLVED`)
  is computed by `evidence.py` and surfaced in the `REVIEW.md` output; it
  is never written back onto a `CLAIM.md` file as a new field. See
  `CONTRACT.md`'s "Implementation notes (Phase 5)" for why this didn't
  need a template change.
- **No semantic/NLP claim-checking.** `evidence.py` only uses structural
  signals already present in the templates: does a cited source exist,
  does it *reciprocally* list the claim in its own `Related claims`
  field, what's its `Source reliability`, is `Contradictory evidence`
  populated, does a `Derived from` chain resolve. It does not compare
  claim text against source text for meaning. This is deliberate — a
  rule engine that doesn't understand English can still be strict, honest,
  and impossible to fool with a plausible-sounding fabrication in a way a
  keyword-matching NLP shortcut would not be.
- **Never auto-`FALSE`.** Contradicted evidence always resolves to
  `DISPUTED`, never `FALSE` — `FALSE` requires stronger judgment than
  structural signals give this MVP (see `CONTRACT.md`). A pre-existing
  `FALSE` status is also never silently cleared by re-evaluation.
- **`REJECT` vs `REVISION_REQUIRED`.** Structural/data-integrity failures
  (a script cites a claim with no file, an invalid `Classification`) are
  `REJECT`. Content-quality failures (unresolved evidence, disputes,
  atomicity violations) are `REVISION_REQUIRED`. See `CONTRACT.md`'s
  "Verdict derivation" list for the full order of checks.
- **`HUMAN_REOPEN` convention.** `templates/REVIEW.md` requires a human to
  log a reopen decision before any new attempt follows a `REJECT`, but
  doesn't specify the mechanics. This implementation's convention: a line
  in `CONTENT_ITEM.md`'s Notes/history log containing the literal text
  `HUMAN_REOPEN: <ROLE>`, e.g. `HUMAN_REOPEN: FACT_CHECKER`.

## Swapping in live retrieval (future work, not built here)

`loader.load_research()` reads local `research/*.md` files — that's the
whole "source" interface: a directory in, `dict[str, ResearchEntry]` out.
A future RESEARCH-mode implementation that retrieves sources live would
write the same `research/*.md` files (per `templates/RESEARCH.md`) via
whatever retrieval method it uses, and everything downstream (this
FACT_CHECK evaluator included) keeps working unchanged. No crawler is
built here — CONTRACT.md's RESEARCH mode (source collection) is not yet
implemented, only FACT_CHECK mode is.

## Known limitations (MVP scope)

- `INFERENCE`/`SPECULATION` claims' `Fact-check status` always resolves to
  `NOT_APPLICABLE`, even when `evidence.py` can tell their `Derived from`
  chain is broken or contradicted (that shows up as `EvidenceSupport`
  only). `CONTRACT.md` allows this ("normally `NOT_APPLICABLE` unless the
  speculation itself later becomes checkable") but a future version could
  be more precise here.
- The markdown table parser (`parsing.py`) assumes no cell value contains
  a literal `|` — true of every file in this repo today, not guaranteed
  in general.
- Atomicity rule check 3 ("one classification fits without qualification")
  isn't mechanically enforced — `templates/CLAIM.md` itself calls this a
  judgment call, not a mechanical test.
- `can_run_new_attempt`'s two-consecutive-attempt cap counts trailing
  `REVISION_REQUIRED` verdicts regardless of whether they're "the same
  underlying issue" (`CONTRACT.md`'s exact phrasing) — distinguishing
  *which* issue would need comparing `Reasons` text between attempts,
  which is out of scope for this MVP's structural-signal approach.
- Running this against the real golden sample in dry-run mode surfaced a
  genuine, previously-unnoticed Atomicity violation in `claims/c5.md`
  (two sentences). Left as-is deliberately — that's exactly what
  `REVISION_REQUIRED` is for, not something to silently patch while
  implementing the checker that found it.
