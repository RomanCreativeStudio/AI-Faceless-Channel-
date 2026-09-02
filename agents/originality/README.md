# Originality Reviewer — MVP implementation

Implements [`CONTRACT.md`](./CONTRACT.md). Continuation of Phase 6: the
third agent, independent of `agents/researcher/` and `agents/safety/`,
scoped to **ORIGINALITY_REVIEW only**. Stdlib Python only, no
dependencies.

**Core principle, worth repeating from `CONTRACT.md`: this is not a
plagiarism lawyer.** It evaluates editorial originality and similarity
*risk*, never a legal determination, and it never claims "100%
original" or comprehensive internet-wide detection.

## Running it

```
python3 -m agents.originality.src content/what-if/wi-20260902-black-death-modern-medicine
```

Prints a JSON originality-review result. Dry run by default. Add
`--apply` to write `reviews/originality_reviewer-<n>.md` and update
`CONTENT_ITEM.md`'s `Originality state` field plus its Notes/history log
(the only two things `CONTRACT.md`'s Allowed actions permit):

```
python3 -m agents.originality.src <content-item-dir> --apply
python3 -m agents.originality.src <content-item-dir> --reference other-video-transcript.txt --apply
```

`--reference` may repeat to supply multiple comparison files (see
`EXTERNAL_SIMILARITY_RISK`). Without it, that signal reports
`NOT_APPLICABLE` and says explicitly that no internet-wide search was
performed — see "Known limitations."

By default the reviewer auto-discovers sibling channel content by
scanning the repo's `content/<pillar>/*/CONTENT_ITEM.md` files (skipping
the item being reviewed) — this is local-filesystem only, never a
network call. As with `agents/researcher/` and `agents/safety/`, the real
golden sample has **not** been run with `--apply` as part of this phase.

## Running the tests

```
python3 -m unittest discover -s agents/originality/tests -t .
```

Tests never rely on auto-discovery scanning the real repo — each test
passes an explicit `channel_index` (often `[]`) so results are fully
isolated from whatever else exists under `content/`.

## Module map

| Module | Responsibility |
|---|---|
| `models.py` | `RiskLevel`, `OriginalitySignal`, `SignalEvaluation`, `ChannelItemSummary`, `OriginalityBundle`, `OriginalityReviewResult` |
| `loader.py` | Reads a content item into an `OriginalityBundle`; `discover_channel_index()` for sibling metadata; `load_reference_texts()` for supplied comparison material |
| `signals.py` | The eight signal checks from `CONTRACT.md`, one pure function each |
| `review.py` | Rolls signal evaluations into one verdict (never `REJECT` for a content signal) |
| `hashing.py` | Originality's own `Reviewed content hash` (content item + script + cited claims + supplied reference material) |
| `review_writer.py` | Renders a `REVIEW.md`-formatted file, role `ORIGINALITY_REVIEWER` |
| `mutate.py` | The *only* code that writes to `CONTENT_ITEM.md`; whitelists exactly `{Originality state}`; has **no** claim- or research-writing function |
| `pipeline.py` | `run_originality_review()` — the one entry point |
| `__main__.py` | CLI wrapper |

## Relationship to `agents/researcher` and `agents/safety`

Reused directly from `agents/researcher/src` (generic, role-agnostic):
`parsing`, `models.ReviewVerdict`/`ReviewRecord`/`ContentItem`/
`Classification`, `loader.load_content_item`/`load_claims`/
`load_research`/`load_script`/`load_reviews`, `multipass.can_run_new_attempt`
(and what it's built from), `errors.NoLoadableContent`/`StructuralFailure`,
`mutate.append_notes_log`.

**Not** reused — each reviewer has its own: `hashing.py` (different
definition of "reviewed content" per role), `mutate.py`'s field
whitelist, and all signal/evidence evaluation logic. Nothing here imports
from `agents/safety` at all, and nothing in `agents/safety` imports from
here — they are siblings, each depending only on `agents/researcher`'s
generic base, never on each other. `RiskLevel` has the same shape as
`agents/safety/src/models.RiskLevel` but is defined independently on
purpose. Each of the three agents works with the other two entirely
absent. See `agents/README.md` for the shared interface convention.

## The eight signals — one deterministic check each

| Signal | How it's computed |
|---|---|
| `INTERNAL_DUPLICATION` | Word-set (Jaccard) overlap of title+premise, and separately of hook, against every item in `channel_index` |
| `CONCEPT_DISTINCTIVENESS` | Premise length as a floor for "a thesis could exist here" |
| `FRAMING_DISTINCTIVENESS` | Presence of analytical-framing words (why/how/impact/consequence-type) anywhere in the script body |
| `SCRIPT_DISTINCTIVENESS` | Curated stock-phrase list matched against the hook/conclusion |
| `SOURCE_DEPENDENCE` | Count of distinct real (non-`N/A`) `Supporting sources` across `FACT` claims |
| `TEMPLATE_REPETITION` | Whether this item's stock phrases (if any) also appear in ≥2 sibling items' hooks |
| `TITLE_HOOK_DISTINCTIVENESS` | Word-set overlap between the title and the hook |
| `EXTERNAL_SIMILARITY_RISK` | Word-set overlap against each supplied reference file; `NOT_APPLICABLE` if none supplied |

## Important distinctions this MVP is built to respect

- **Similar topic ≠ copied content.** `INTERNAL_DUPLICATION` uses two
  thresholds: below ~35% word overlap is `LOW_RISK` (shared subject
  matter alone), 35-60% is `REVIEW_REQUIRED` (a human should look), only
  ≥60% is `HIGH_RISK`. Two items about the same historical era with
  different angles land well under those thresholds — see
  `tests/test_signal_detection.py`'s shared-facts and similar-format
  tests.
- **No signal ever escalates to `REJECT`.** `models.REJECT_TIER_SIGNALS`
  is an empty set. `REJECT` is reserved for structural failures (a
  missing claim file, an invalid classification) exactly like the other
  two agents — never for a content-similarity finding, because that
  would itself be the kind of definitive judgment this reviewer must not
  make.

## Known limitations (MVP scope)

- All eight signals are lexical/structural (word-set overlap, stock
  phrase lists, source counts) — no semantic embeddings, no NLP model.
  `LOW_RISK`/`NOT_APPLICABLE` means "no known pattern/overlap matched
  this MVP's thresholds," not "confirmed original."
- `EXTERNAL_SIMILARITY_RISK` only ever compares against files the caller
  explicitly supplies via `--reference`/`reference_paths`. It never
  fetches anything from the internet and never implies it has. Every
  rendered `REVIEW.md` states this explicitly, not just this file.
- `channel_index` auto-discovery only reads `CONTENT_ITEM.md`/`SCRIPT.md`
  pairs already present under this repo's own `content/` tree — it has
  no memory of past channel content beyond what's currently checked in.
- Word-set Jaccard similarity is crude: it can't distinguish a genuinely
  derivative retelling from two pieces that happen to share vocabulary
  for unrelated reasons, and it can miss a close paraphrase that avoids
  shared words entirely. `signals.py`'s functions are each independent
  and take the same `OriginalityBundle`, so a future semantic-similarity
  implementation can replace or augment any one of them (most likely
  `INTERNAL_DUPLICATION` and `EXTERNAL_SIMILARITY_RISK`) without
  touching verdict derivation, orchestration, or the other signals.
- `SOURCE_DEPENDENCE` and `TEMPLATE_REPETITION` are `NOT_APPLICABLE` when
  there's insufficient basis for comparison (fewer than two `FACT`
  claims; no other channel content) rather than guessed at.
- Like the other two agents, the markdown table/section parser assumes
  no cell value contains a literal `|`.
