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
