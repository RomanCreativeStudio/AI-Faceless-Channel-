# Claim Template

One copy per discrete claim made in a content item's script. Store under
`content/<pillar>/<content-id>/claims/<claim-id>.md`. Every factual
statement in `templates/SCRIPT.md` should trace back to a claim here.

| Field | Value |
|---|---|
| Claim ID | `<content-id>-c<n>` |
| Content ID | `<matches CONTENT_ITEM.md>` |
| Exact claim | `<the specific, checkable statement>` |
| Supporting sources | `<RESEARCH.md entries backing this claim>` |
| Evidence | `<summary of the evidence itself>` |
| Confidence level | `HIGH` \| `MEDIUM` \| `LOW` |
| Classification | `FACT` \| `INFERENCE` \| `SPECULATION` \| `ASSUMPTION` |
| Contradictory evidence | `<any conflicting evidence found; "none found" if applicable>` |
| Fact-check status | `UNVERIFIED` \| `VERIFIED` \| `DISPUTED` \| `FALSE` |

## Classification guide

- `FACT` — established and sourced.
- `INFERENCE` — logically follows from established facts/assumptions but
  is not itself directly sourced.
- `SPECULATION` — plausible but not confidently establishable.
- `ASSUMPTION` — a deliberately introduced hypothetical premise. Used
  almost exclusively by `what-if` content items to model "what changed";
  never used to describe a real historical/technical fact.

`what-if` content items must classify every claim as one of the four
KNOWN FACT / ASSUMPTION / INFERENCE / SPECULATION categories defined in
`CONSTITUTION.md` rule 4 and `SYSTEM.md`; `FACT` here corresponds to
KNOWN FACT. Non-`what-if` content items should not need `ASSUMPTION` or
`SPECULATION` — if they do, reconsider whether the claim belongs in the
script at all.
