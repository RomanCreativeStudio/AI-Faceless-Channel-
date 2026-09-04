# Research / Fact-Check Agent — MVP implementation

Implements [`CONTRACT.md`](./CONTRACT.md). Phase 5 of the roadmap: the
first agent that actually runs, scoped to **FACT_CHECK only** (structured
evidence evaluation against existing `research/`/`claims/` records — not
live web retrieval, and not RESEARCH-mode source collection). Phase 7F
adds a third mode, **Autonomous Revision** (`src/revision.py`) — see
below. Phase 7G adds a fourth, narrow extension of that mode, **Bounded
Research** (`src/research.py`) — see below. Stdlib Python only, no
dependencies.

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
| `research_provider.py` | Bounded Research Mode's provider `Protocol` + result dataclasses (Phase 7G) |
| `source_policy.py` | Deterministic, conservative source-reliability policy (Phase 7G) |
| `research.py` | Bounded Research Mode's engine — see below |
| `research_writer.py` | Renders one evaluated source as a `RESEARCH.md`-formatted file |
| `test_research_provider.py` | Deterministic local/test `ResearchProvider`, no network |
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

## Swapping in live retrieval (future work, partially built in Phase 7G)

`loader.load_research()` reads local `research/*.md` files — that's the
whole "source" interface: a directory in, `dict[str, ResearchEntry]` out.
Phase 7G's `research_provider.py` now defines exactly that swap point for
one narrow case (Bounded Research Mode, below): a `ResearchProvider`
Protocol (`label` + `search(query) -> ResearchProviderResult`) that a real
web-search/archive-retrieval implementation could satisfy without
changing `research.py`, `revision.py`, or any model. Only
`test_research_provider.py`'s `LocalTestResearchProvider` exists today —
deterministic, no network, results supplied per-claim by a test fixture.
CONTRACT.md's general RESEARCH mode (open-ended source collection for a
whole content item, not one claim's evidence gap) is still not
implemented — Bounded Research Mode is deliberately narrower than that.

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

## Bounded Research Mode (Phase 7G)

A fourth, narrow mode, `src/research.py` — see `CONTRACT.md`'s "Bounded
Research Mode" for the full contract. It extends Autonomous Revision
Mode's Case C only: when a `FACT` claim's evidence gap can't be closed
with anything already on disk, this module issues **exactly one** bounded
query (the claim's own exact text, verbatim — never reworded, never
broadened) to a `ResearchProvider`, evaluates every result against
`source_policy.py`'s deterministic, conservative reliability model, and
either produces one new, genuinely reciprocal `research/*.md` entry that
Autonomous Revision Mode's *existing, unmodified* Case A machinery then
turns into a successor claim, or escalates. **This is not general
autonomous browsing** — no retry, no rewording, no scope expansion,
exactly one query per claim, one bounded-research pass per revision
cycle.

```
FACT-CHECK RESULT (REVISION_REQUIRED)
  -> REVISION DIAGNOSIS       (revision.diagnose_claim, unchanged)
  -> EXISTING-EVIDENCE REPAIR (Case A, unchanged — tried first, always wins if it applies)
  -> BOUNDED RESEARCH         (research.run_bounded_research — only reached on Case C)
  -> NEW RESEARCH RECORD      (research/<n>-<slug>.md, written for every evaluated source)
  -> RE-DIAGNOSIS             (the new entry either makes the claim Case A-eligible, or it doesn't)
  -> PASS / REVISION_REQUIRED / ESCALATE
```

**Source reliability is deterministic and conservative, never a
per-domain authority list.** `source_policy.py` caps a source's
reliability using only structural signals — is retrieval independently
verified, is a publisher recorded, is a publication date recorded, what
does the provider itself claim — and can only ever cap a provider's claim
*down*, never up. A source is never `HIGH` merely because a provider
returned it labeled that way.

**Full auditability, not just the winners.** `run_bounded_research`
writes one `research/*.md` entry per evaluated source, accepted *or*
rejected — every rejected entry records why (`Rejection reason`), and a
rejected entry's `Related claims` field, even though it names the claim
it was evaluated for, is never treated as valid Case A reciprocal
evidence by a later run (`revision.py`'s `_find_reciprocal_uncited_source`
excludes anything this engine itself marked `REJECTED`).

**Verdicts**: `SUPPORTED` (hands off to Case A's existing
`create_successor_claim`, unchanged) / `CONTRADICTED` (a contradicting
source was found — never automatically rewrites, escalates like Case B) /
`CONFLICT` (accepted sources both support *and* contradict — an explicit
conflict, never silently resolved by picking one) / `INSUFFICIENT`
(nothing usable found — escalates, exactly like Case C already did).

```
python3 -c "from agents.researcher.src.research import run_bounded_research; \
            from agents.researcher.src.loader import load_bundle; \
            from pathlib import Path; \
            b = load_bundle(Path('<content-item-dir>')); \
            print(run_bounded_research(Path('<content-item-dir>'), b.claims['<short-id>'], reason='manual test', apply=False))"
```

Or, more commonly, invoked automatically by
`run_fact_check_with_autonomous_revision`/`run_autonomous_revision`
whenever a claim diagnoses as Case C — including through
`agents/full_pipeline/`, which calls that function unmodified (see
`agents/full_pipeline/README.md`).

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
- **Bounded Research Mode (Phase 7G) only ever runs for Case C**
  (`INSUFFICIENT_EVIDENCE`) — a Case B (`CONTRADICTED`) claim never
  triggers a provider search, even though "search for a tie-breaking
  source" might sound plausible; doing so would be exactly the
  silent-pick-a-side behavior `CONFLICT` handling exists to refuse.
- No real research provider exists yet — `LocalTestResearchProvider` is
  permanently a deterministic test double (no network, no real
  retrieval). A real provider is a distinct, deliberate follow-up, not a
  side effect of building the abstraction it plugs into.
- `MAX_ACCEPTED_SOURCES_PER_CLAIM` is enforced by rank (highest
  reliability kept, ties broken by evaluation order) — a source demoted
  purely for exceeding this limit is otherwise indistinguishable from one
  that failed reliability/actionability in its own `Rejection reason`
  text, though the reason string does name the limit specifically.
- `research_writer.py` always renders `Source type` as `OTHER` — nothing
  in `ProviderSourceResult` lets this MVP determine
  `PRIMARY`/`SECONDARY`/`TERTIARY`/`EXPERT_COMMENTARY` without guessing,
  and guessing here was judged worse than an honest, structurally-correct
  `OTHER`.
