# Contract: Originality Reviewer

Specification for the third agent in the roadmap, independent of
`agents/researcher/` and `agents/safety/`. It governs the
**ORIGINALITY_REVIEW** pipeline stage only.

This contract is subordinate to `CONSTITUTION.md` and to
`templates/CLAIM.md` (Atomicity rule, claim immutability) and
`templates/REVIEW.md` (Multi-pass resolution). Where anything below could
be read as conflicting with those, they win. This document does not
restate the Constitution — see `CONSTITUTION.md` directly.

## Core principle

**This is not a plagiarism lawyer.** The Originality Reviewer evaluates
editorial originality and similarity *risk* — it never claims to make a
definitive legal determination about plagiarism or copyright, and it
never claims "100% original." It distinguishes:

- similar topic ≠ copied content
- common knowledge ≠ copying
- shared historical facts ≠ derivative storytelling
- similar format ≠ plagiarism

A similarity signal generally produces `REVIEW_REQUIRED`, handing the
judgment to a human — not an automatic legal conclusion. See "What this
reviewer must never claim," below.

## Purpose

Evaluate whether a content item's `SCRIPT.md` (title, hook, premise,
narrative approach) provides sufficiently distinct editorial value, and
flag duplication/derivative-content risk — against the rest of the
channel's content, and, if supplied, external reference material. It is
**not** a fact-check (that's `agents/researcher/`) and **not** a safety/
policy check (that's `agents/safety/`). A finding outside originality and
similarity risk is out of scope.

## Inputs

- `CONTENT_ITEM.md` (title, pillar, premise — read-only except the one
  field named in Allowed actions)
- `SCRIPT.md` (hook, premise, narrative beats, conclusion — read-only)
- `claims/*.md` (used only to count distinct cited sources for Source
  dependence — read-only)
- `research/*.md` (used only to compare script prose against recorded
  evidence for Source dependence — read-only)
- **Existing channel content metadata**: a structured summary (content
  ID, title, premise, hook) per other content item, either supplied
  explicitly (`channel_index`, e.g. by a caller/test) or auto-discovered
  by scanning sibling `content/<pillar>/*/CONTENT_ITEM.md` +
  `SCRIPT.md` files when not supplied. Never a live internet search.
- **Optional comparison/reference material**: zero or more local text
  files supplied by the caller (`reference_paths`) — e.g. a competing
  video's transcript a human wants checked. Never fetched automatically;
  never assumed to represent the whole internet.
- `templates/REVIEW.md` (the schema contract to produce against)

## Outputs

- One new `reviews/originality_reviewer-<n>.md` (verdict `PASS` /
  `REVISION_REQUIRED` / `REJECT`, per `templates/REVIEW.md`, role
  `ORIGINALITY_REVIEWER`)
- `CONTENT_ITEM.md`: updates `Originality state` only
- An appended entry in `CONTENT_ITEM.md`'s Notes/history log

## Allowed actions

- Read `CONTENT_ITEM.md`, `SCRIPT.md`, `claims/*.md`, `research/*.md`
- Read supplied channel metadata and reference material
- Create `REVIEW.md` entries with role `ORIGINALITY_REVIEWER`
- Update `CONTENT_ITEM.md`'s `Originality state` field only
- Append (never edit or delete) entries in `CONTENT_ITEM.md`'s
  Notes/history log
- Flag similarity, dependence, and ambiguity for human attention

## Forbidden actions — protected fields

The Originality Reviewer must **never** modify:

- a claim's `Classification` or `Exact claim` — or anything else in
  `claims/*.md`; this reviewer only reads claims, it writes none
- `research/*.md` evidence records
- `Owner approval state`
- the content item's top-level `status` field or `Publication state`
- `Research state`, `Fact-check state`, or `Safety state` (those belong
  to the other two agents)
- any other reviewer's role in `REVIEW.md`
- `SCRIPT.md` or `CONTENT_ITEM.md` prose — it never rewrites content to
  hide or resolve a similarity finding

It must also never:

- Publish anything, anywhere, under any condition
- Approve its own disputed work (a `REJECT` is terminal until a human
  reopens it, exactly as for the other two reviewers)
- **Delete or hide similarity evidence.** A detected overlap is recorded
  in full, never trimmed to look more favorable.
- **Claim "100% original," or claim comprehensive internet-wide
  plagiarism/originality detection.** If no reference material was
  supplied, `EXTERNAL_SIMILARITY_RISK` says exactly that — it never
  implies a broader search happened.
- Override `CONSTITUTION.md` or any human-approval field

## Originality dimensions (signal model)

Eight named signals, each evaluated independently and given a risk
level. A signal firing does not automatically mean `REJECT` — see
Verdict derivation. **No signal in this reviewer ever escalates to
`REJECT`** — see "Core principle": a definitive
plagiarism/duplication judgment is a human call, not this system's.

| Signal | What it looks for |
|---|---|
| `INTERNAL_DUPLICATION` | Substantial repeat of an existing channel topic, thesis, or hook |
| `CONCEPT_DISTINCTIVENESS` | Whether the premise has an identifiable thesis/angle at all |
| `FRAMING_DISTINCTIVENESS` | Whether the narrative approach is more than a generic chronological summary |
| `SCRIPT_DISTINCTIVENESS` | Suspiciously generic/derivative stock phrasing, where detectable |
| `SOURCE_DEPENDENCE` | Over-reliance on a single source, or restating evidence without synthesis |
| `TEMPLATE_REPETITION` | Structure/phrasing excessively formulaic *compared with other channel content* |
| `TITLE_HOOK_DISTINCTIVENESS` | Whether the hook adds anything beyond restating the title |
| `EXTERNAL_SIMILARITY_RISK` | Overlap with supplied reference material, if any was supplied |

### Risk levels

Same vocabulary as `agents/safety/CONTRACT.md` (defined independently in
this agent's own `models.py` — see `README.md` "Relationship to
agents/researcher and agents/safety" for why):

- `NOT_APPLICABLE` — out of scope for this item (e.g. no reference
  material supplied for `EXTERNAL_SIMILARITY_RISK`, or no other channel
  content exists yet to compare `INTERNAL_DUPLICATION`/`TEMPLATE_REPETITION`
  against).
- `LOW_RISK` — evaluated, no risk indicators found by this MVP's
  deterministic checks. Not a certification of originality.
- `REVIEW_REQUIRED` — an indicator was found this system cannot reliably
  resolve alone; a human must judge it.
- `HIGH_RISK` — a strong, clear structural/lexical overlap or dependence
  indicator was found.

## Verdict derivation

1. Structural failure (`SCRIPT.md` cites a claim ID with no file, or a
   claim's `Classification` is invalid) → `REJECT` — this is a data
   integrity failure, not an originality judgment, so it's handled
   identically to the other two agents.
2. No `SCRIPT.md`/`CONTENT_ITEM.md` to review → abort, no `REVIEW.md`
   written.
3. Any signal at `HIGH_RISK` → `REVISION_REQUIRED`. Never `REJECT` — see
   Core principle.
4. Any signal at `REVIEW_REQUIRED` → verdict at least `REVISION_REQUIRED`
   and `escalate_to_human = true`.
5. All signals `LOW_RISK`/`NOT_APPLICABLE` → `PASS`.

## Human escalation

Escalates to a human whenever:

- Substantial similarity is detected (`INTERNAL_DUPLICATION` or
  `EXTERNAL_SIMILARITY_RISK` above `LOW_RISK`).
- Source dependence appears excessive (`SOURCE_DEPENDENCE` above
  `LOW_RISK`).
- The system cannot confidently distinguish common knowledge from
  derivative material — this MVP's structural checks are conservative
  about this by design: shared historical/technical facts alone never
  trigger a signal (see "Important distinctions" in `README.md`), but
  when the checks can't tell, the result is `REVIEW_REQUIRED`, not a
  guess.
- External similarity evidence is incomplete or was supplied but is
  ambiguous.
- Any signal reaches `HIGH_RISK`.

Escalation is recorded via `escalate_to_human = true` and named
explicitly in `Reasons` — never silently folded into a `PASS`.

## What this reviewer must never claim

- A definitive legal determination of plagiarism, copyright infringement,
  or originality.
- "100% original," or any claim of certainty about originality.
- That it performed comprehensive, internet-wide similarity detection —
  it only ever compares against explicitly supplied channel metadata and
  explicitly supplied reference material. When neither is supplied, it
  says so plainly rather than reporting a clean pass by omission.

## Failure conditions

Same shape as `agents/researcher/CONTRACT.md` and `agents/safety/CONTRACT.md`:
- `SCRIPT.md` does not exist → cannot review, no `REVIEW.md` written.
- `SCRIPT.md` cites a claim ID with no corresponding `claims/*.md` file
  → `REJECT`.

## Exact handoff to the next pipeline stage

On `PASS`: sets `Originality state = PASS`, appends a Notes/history log
entry citing the `REVIEW.md` file, and stops. It does **not** change
`status` to `EDITORIAL_REVIEW`/whatever follows — that transition is
human/owner-approval-gated, identically to the other two agents. On
`REVISION_REQUIRED` or `REJECT`, it documents required changes/reasons
and stops.

## Relationship to agents/researcher and agents/safety

Independent, sibling stages. The Originality Reviewer reuses only
`agents/researcher/src`'s generic, role-agnostic infrastructure (markdown
table/section parsing, `ReviewVerdict`/`ReviewRecord`/`ContentItem`/
`Classification` models, `load_claims`/`load_research`/`load_reviews`,
`Multi-pass resolution` gating functions, the failure-condition
exceptions, `append_notes_log`) — never `agents/researcher`'s fact-check
domain logic, and never anything from `agents/safety` at all (they are
siblings, not dependents of each other). Each of the three agents works
with the others entirely absent. See `agents/README.md`'s shared
interface convention.

## Implementation notes (Phase 6 continuation)

The MVP (`agents/originality/src/`) implements every signal with
deterministic, structural/lexical checks (word-set overlap, stock-phrase
lists, source counts) — no semantic embeddings, no NLP model, no external
API. This is a hard limitation, not a hidden one — see
`agents/originality/README.md`'s "Known limitations." `signals.py`
exposes one pure function per signal, each taking the same
`OriginalityBundle`; a future semantic-similarity implementation can
replace or augment individual signal functions without touching
`review.py`'s verdict derivation, `pipeline.py`'s orchestration, or any
other signal.
