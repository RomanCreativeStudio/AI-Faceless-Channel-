# Research / Fact-Check Agent — MVP implementation

Implements [`CONTRACT.md`](./CONTRACT.md). Phase 5 of the roadmap: the
first agent that actually runs, scoped to **FACT_CHECK only** (structured
evidence evaluation against existing `research/`/`claims/` records — not
live web retrieval, and not RESEARCH-mode source collection). Phase 7F
adds a third mode, **Autonomous Revision** (`src/revision.py`) — see
below. Stdlib Python only, no dependencies.

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
| `revision.py` | Autonomous Revision Mode (Phase 7F) — see below |
| `revision_writer.py` | Renders a `REVISION.md`-formatted file |
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

## Autonomous Revision Mode (Phase 7F)

A narrow third mode, `src/revision.py`, alongside FACT_CHECK — see
`CONTRACT.md`'s "Autonomous Revision Mode" for the full contract. In one
sentence: when a `FACT_CHECKER` attempt is `REVISION_REQUIRED`, this
module looks for a `FACT` claim whose evidence gap is closeable with
*already-existing, already-recorded* research — never invented — and, if
one exists, creates a new **successor claim** (never editing the
original) citing it. Anything it can't close with real evidence
(contradicted, insufficient, or a claim that already violates the
Atomicity rule) it leaves alone and escalates.

```
python3 -m agents.researcher.src <content-item-dir> --apply   # attempt 1
python3 -c "from agents.researcher.src.revision import run_fact_check_with_autonomous_revision as r; \
            from pathlib import Path; print(r(Path('<content-item-dir>'), apply=True))"
```

Or, more commonly, invoked through `agents/full_pipeline/`, which
recognizes a FACT_CHECK-level `REVISION_REQUIRED` and calls this
automatically — see `agents/full_pipeline/README.md`.

**Three concepts this phase deliberately keeps separate** (see
`STATE.md` for the full reasoning): *automated review* (an AI evaluates
the work — FACT_CHECK mode, unchanged), *autonomous revision* (an AI is
permitted to create a controlled successor artifact — this mode, new),
and *human approval* (a human decides whether the content is actually
approved — untouched, permanently out of any agent's reach). A `PASS`
from this module never means `CONTENT_ITEM.md` is `APPROVED`.

**The one genuinely new piece of infrastructure**: `run_fact_check`
gained an optional, backward-compatible `claim_substitutions` parameter,
and `evidence.evaluate_claim`/`_evaluate_fact` gained an optional
`predecessor_short_id` parameter — both `None` by default, reproducing
prior behavior exactly. Together they let a re-fact-check pass evaluate a
successor claim in place of what it superseded (since a superseded
claim's own cited research entry still, correctly, names the
*predecessor* — research entries are immutable too) without ever editing
`SCRIPT.md`. Every substitution is disclosed in the resulting
`REVIEW.md`'s `Notes`, never silent.

`templates/REVISION.md` (new) is the only place a predecessor and its
successor are formally linked — see its own "What this record does NOT
do" for the approval boundary.

## Known limitations (MVP scope)

- Autonomous Revision Mode only ever acts on `FACT`-classified claims and
  only ever closes an evidence-*linkage* gap (a real, already-existing,
  reciprocal research entry not yet cited) — it never touches
  `ASSUMPTION`/`INFERENCE`/`SPECULATION` claims, never rewords a claim,
  and never reclassifies one. A claim needing an actual wording
  correction (not just a citation) always escalates instead — see
  `CONTRACT.md`'s "Evidence requirements".
- No in-process retry loop — `run_fact_check_with_autonomous_revision`
  performs exactly one diagnose-and-revise cycle per call; "self-review"
  across separate calls means safely re-invoking it later, once
  something has actually changed (a human edit, or a fresh, real
  research entry). See `agents/full_pipeline/CONTRACT.md`'s "Self-review
  behavior" for the identical reasoning applied one layer up.
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
