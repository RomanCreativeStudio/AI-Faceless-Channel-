# Research Entry Template

One copy per source consulted for a content item. A content item typically
has many of these. Store under
`content/<pillar>/<content-id>/research/<n>-<short-slug>.md`.

| Field | Value |
|---|---|
| Content ID | `<matches CONTENT_ITEM.md>` |
| Source | `<name/title of the source>` |
| Source type | `PRIMARY` \| `SECONDARY` \| `TERTIARY` \| `EXPERT_COMMENTARY` \| `OTHER` |
| Source URL / reference | `<url, ISBN, archive reference, etc.>` |
| Publication date | `<YYYY-MM-DD or "unknown">` |
| Retrieved date | `<YYYY-MM-DD>` |
| Source reliability | `HIGH` \| `MEDIUM` \| `LOW` \| `UNVERIFIED` |
| Discovery status | `DISCOVERED` \| `EVALUATED` \| `ACCEPTED` \| `REJECTED` (added Phase 7G — see `agents/researcher/CONTRACT.md`'s "Bounded Research Mode"; existing entries predating Phase 7G have no value here and default to `ACCEPTED`, since their presence on disk already implies acceptance) |
| Provider result ID | `<the research provider's own identifier for this result, or "N/A" for a human-entered entry>` |
| Retrieval verified | `YES` \| `NO` \| `UNVERIFIED` — whether this environment could actually confirm the cited URL/reference was retrieved; never `YES` unless independently confirmed, never silently assumed |

## Relevant evidence

`<what this source actually says, close to verbatim or accurately paraphrased, with page/timestamp if applicable>`

## Related claims

`<list of CLAIM IDs (templates/CLAIM.md) this source supports>`

## Claim support relationship

`<SUPPORTS \| CONTRADICTS \| UNRELATED \| UNVERIFIED — this source's relationship to the specific claim research was performed for; added Phase 7G, "N/A" for entries predating it or not tied to one bounded research request>`

## Conflicting evidence

`<anything in this source that conflicts with other research entries or claims; "none found" if applicable>`

## Rejection reason

`<why this candidate was rejected, if Discovery status = REJECTED; "N/A" otherwise — added Phase 7G>`

## Researcher notes

`<caveats, context, translation issues, why this source was/wasn't trusted>`
