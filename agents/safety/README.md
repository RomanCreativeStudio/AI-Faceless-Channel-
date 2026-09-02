# Safety Reviewer — MVP implementation

Implements [`CONTRACT.md`](./CONTRACT.md). Phase 6 of the roadmap: the
second agent, independent of `agents/researcher/`, scoped to
**SAFETY_REVIEW only**. Stdlib Python only, no dependencies.

## Running it

```
python3 -m agents.safety.src content/what-if/wi-20260902-black-death-modern-medicine
```

Prints a JSON safety-review result. This is a **dry run** — nothing on
disk changes. Add `--apply` to write `reviews/safety_reviewer-<n>.md` and
update `CONTENT_ITEM.md`'s `Safety state` field plus its Notes/history
log (the only two things `CONTRACT.md`'s Allowed actions permit):

```
python3 -m agents.safety.src <content-item-dir> --apply
```

As with `agents/researcher/`, the real golden sample has **not** been run
with `--apply` as part of this phase — exercised read-only by the dry-run
example above and by tests (against disposable copies/fixtures only).

## Running the tests

```
python3 -m unittest discover -s agents/safety/tests -t .
```

## Module map

| Module | Responsibility |
|---|---|
| `models.py` | `RiskLevel`, `SafetySignal`, `SignalEvaluation`, `SafetyBundle`, `SafetyReviewResult` |
| `loader.py` | Reads a content item into a `SafetyBundle` (reuses `agents/researcher/src`'s generic loaders) |
| `signals.py` | The twelve signal checks from `CONTRACT.md` |
| `review.py` | Rolls signal evaluations into one verdict |
| `hashing.py` | Safety's own `Reviewed content hash` (title/premise + script + cited claims) |
| `review_writer.py` | Renders a `REVIEW.md`-formatted file, role `SAFETY_REVIEWER` |
| `mutate.py` | The *only* code that writes to `CONTENT_ITEM.md`; whitelists exactly `{Safety state}`; has **no** claim-writing function at all |
| `pipeline.py` | `run_safety_review()` — the one entry point |
| `__main__.py` | CLI wrapper |

## Relationship to `agents/researcher`

Reused directly (generic, role-agnostic — not fact-check domain logic):
`parsing` (table/section parsing), `models.ReviewVerdict` /
`models.ReviewRecord` / `models.ContentItem`, `models.Classification`,
`loader.load_content_item` / `load_claims` / `load_script` /
`load_reviews`, `multipass.can_run_new_attempt` (and the functions it's
built from), `errors.NoLoadableContent` / `StructuralFailure`,
`mutate.append_notes_log`.

**Not** reused, each agent has its own: `evidence.py`/`factcheck.py`/
`atomicity.py` (Researcher's fact-check domain logic — Safety has no
equivalent, it evaluates signals, not evidence), `hashing.py` (different
definition of "reviewed content" per role), `mutate.py`'s field whitelist
(`{Research state, Fact-check state}` vs. `{Safety state}` — structurally
distinct, enforced by two separate `PermissionError`-raising whitelists).

Each agent is independently runnable: `agents/safety` does not require
`agents/researcher` to have run against a content item first, and vice
versa. See `agents/README.md` for the shared result-shape convention a
future orchestrator would use to run all stages in sequence.

## Design decisions worth knowing about

- **Twelve independent signals, not one verdict.** Each of
  `DANGEROUS_INSTRUCTION` … `TITLE_THUMBNAIL_MISREPRESENTATION` is
  evaluated on its own and given a `RiskLevel`
  (`NOT_APPLICABLE`/`LOW_RISK`/`REVIEW_REQUIRED`/`HIGH_RISK`). A signal
  firing doesn't automatically mean `REJECT` — see `CONTRACT.md`'s
  "Verdict derivation": only `DANGEROUS_INSTRUCTION`/`ILLEGAL_ACTIVITY`
  at `HIGH_RISK` are severe enough to be terminal; everything else maps
  to `REVISION_REQUIRED`, and any `REVIEW_REQUIRED` always escalates to a
  human rather than resolving itself into a `PASS`.
- **No semantic/NLP understanding — pattern/structural signals only.**
  Same philosophy as `agents/researcher`'s evidence evaluation. Some
  signals are genuinely structural and reliable (`AI_DISCLOSURE` reads a
  required template field; `MISINFORMATION_RISK`'s KNOWN-FACT-labeling
  check cross-references `claims/*.md`'s `Classification` field
  directly). Others (`DANGEROUS_INSTRUCTION`, `DEFAMATION`, `PRIVACY`,
  etc.) are curated keyword/regex patterns that catch some explicit cases
  and will miss subtler ones — see "Known limitations."
- **`LOW_RISK` is not a safety certification.** It means "no known
  pattern matched by this MVP," not "a human confirmed this is safe."
  This is stated on every rendered `REVIEW.md`, not just in this file.
- **`REJECT` reserved for the two most severe signal categories.**
  Everything else that's `HIGH_RISK` is `REVISION_REQUIRED` — fixable by
  editing the content, not a terminal structural failure.

## Known limitations (MVP scope)

- Keyword/regex detection for `DANGEROUS_INSTRUCTION`, `ILLEGAL_ACTIVITY`,
  `DECEPTION`, `IMPERSONATION`, `PRIVACY`, `DEFAMATION`, `SENSITIVE_CONTENT`,
  and `COPYRIGHT_RISK` is a small, curated pattern list — not exhaustive,
  not a real content-moderation model. Absence of a match is reported as
  `LOW_RISK`/`NOT_APPLICABLE`, never claimed as a guarantee.
- `DEFAMATION` and `SENSITIVE_CONTENT` never resolve above
  `REVIEW_REQUIRED` in this MVP — determining whether an accusatory claim
  is adequately sourced, or whether tragic-subject framing is handled
  responsibly, is treated as inherently requiring human judgment rather
  than something pattern-matching should ever resolve on its own.
- `TITLE_THUMBNAIL_MISREPRESENTATION` only inspects the title text
  (`CONTENT_ITEM.md`'s `Working title`/`Final title`); there is no actual
  thumbnail image to inspect at this stage of the pipeline (none exists
  before `PRODUCTION`).
- `MISINFORMATION_RISK`'s unsupported-certainty check only looks at
  `SCRIPT.md`'s `Narrative beats` bullet lines for a small list of
  certainty words; nuanced hedging/overclaiming outside that pattern
  won't be caught.
- Like `agents/researcher`, the markdown table/section parser assumes no
  cell value contains a literal `|`.
