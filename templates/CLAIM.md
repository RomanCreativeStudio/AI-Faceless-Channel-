# Claim Template

One copy per discrete claim made in a content item's script. Store under
`content/<pillar>/<content-id>/claims/<claim-id>.md`. Every factual
statement in `templates/SCRIPT.md` should trace back to a claim here.

| Field | Value |
|---|---|
| Claim ID | `<content-id>-c<n>` |
| Content ID | `<matches CONTENT_ITEM.md>` |
| Exact claim | `<the specific, checkable statement>` |
| Supporting sources | `<RESEARCH.md entries backing this claim — required for FACT; "N/A" otherwise, see guide>` |
| Derived from | `<claim IDs this one is built on — required for INFERENCE/SPECULATION; "N/A" for FACT/ASSUMPTION>` |
| Evidence | `<summary of the evidence itself>` |
| Confidence level | `HIGH` \| `MEDIUM` \| `LOW` \| `N/A` (`ASSUMPTION` only — a stipulated premise isn't held with some confidence, it's chosen) |
| Classification | `FACT` \| `INFERENCE` \| `SPECULATION` \| `ASSUMPTION` |
| Contradictory evidence | `<any conflicting evidence found; "none found" if applicable>` |
| Fact-check status | `UNVERIFIED` \| `VERIFIED` \| `DISPUTED` \| `FALSE` \| `NOT_APPLICABLE` |

## Classification guide

- `FACT` — established and sourced. Cite `Supporting sources`; leave
  `Derived from` as `N/A`.
- `ASSUMPTION` — a deliberately introduced hypothetical premise. Used
  almost exclusively by `what-if` content items to model "what changed";
  never used to describe a real historical/technical fact. Not sourced —
  `Supporting sources` is `N/A`; `Derived from` is `N/A` (it's a stipulated
  premise, not derived from anything). `Fact-check status` is
  `NOT_APPLICABLE` — an assumption is neither true nor false, it's chosen.
- `INFERENCE` — logically follows from established facts/assumptions but
  is not itself directly sourced. Cite the `FACT`/`ASSUMPTION` claim IDs it
  follows from in `Derived from`; `Supporting sources` is normally `N/A`
  unless a source directly corroborates the inference too.
- `SPECULATION` — plausible but not confidently establishable even within
  the hypothetical. Cite what it's speculating from in `Derived from`.
  `Fact-check status` is normally `NOT_APPLICABLE` unless the speculation
  itself later becomes checkable.

## Atomicity rule

Each `CLAIM.md` file must contain exactly one atomic claim with exactly
one classification. This is the deterministic, mechanically-checkable
test (no NLP required) for whether a claim needs to be split:

1. **One sentence.** `Exact claim` is a single sentence (one terminal
   period, abbreviations aside).
2. **No causal/inferential connectors inside the sentence.** If
   `Exact claim` contains " because ", " therefore ", " which means ",
   " so that ", or a semicolon joining two independently-checkable
   assertions, it is fusing a fact to a conclusion drawn from it — split
   it into two claims and link them with `Derived from` instead of
   writing the reasoning inline.
3. **One classification fits without qualification.** If you cannot
   assign `FACT`/`ASSUMPTION`/`INFERENCE`/`SPECULATION` without saying
   "well, half of it is X and half is Y," the claim is compound and must
   be split.

Splitting is mandatory, not stylistic — a compound claim makes fact-check
verdicts ambiguous (which half passed?) and is the kind of thing this
rule exists to make impossible to miss, by hand today and by a linter
later.

Claims are **immutable once created**: correcting a claim's wording or
classification is never an in-place edit. Create a new claim ID, set the
old claim's `Fact-check status` note (in `Evidence` or a new trailing
line) to point at the superseding claim ID, and record why in the content
item's Notes/history log. This keeps the audit trail intact and is what
makes rule "an agent may never silently change a claim's classification"
(see `agents/researcher/CONTRACT.md`) enforceable: a classification
change is always a new, visible claim, never a silent overwrite.

`what-if` content items must classify every claim as one of the four
KNOWN FACT / ASSUMPTION / INFERENCE / SPECULATION categories defined in
`CONSTITUTION.md` rule 4 and `SYSTEM.md`; `FACT` here corresponds to
KNOWN FACT. Non-`what-if` content items should not need `ASSUMPTION` or
`SPECULATION` — if they do, reconsider whether the claim belongs in the
script at all.

Note the two different "state" concepts in this system: a claim's
`Fact-check status` here is per-claim; `CONTENT_ITEM.md`'s "Fact-check
state" is the whole item's review-stage progress (whether a fact-checker
pass has happened at all). They move independently — don't conflate them.
