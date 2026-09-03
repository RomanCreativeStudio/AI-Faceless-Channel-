# Production QA Template

One copy per production-QA attempt, store under
`content/<pillar>/<content-id>/qa/production-qa-<n>.md`. Produced by
`agents/production_qa/` — an **automated, structural readiness check**.
Never a substitute for `templates/VIDEO_QA.md`'s human checklist/final
approval, and never itself an approval — see
`agents/production_qa/CONTRACT.md`.

| Field | Value |
|---|---|
| Production QA ID | `<content-id>-production-qa-<n>` |
| Content ID | `<matches CONTENT_ITEM.md>` |
| Production ID | `<matches PRODUCTION.md>` |
| QA date | `<YYYY-MM-DD>` |
| Verdict | `PASS` \| `REVISION_REQUIRED` \| `BLOCKED` \| `SYSTEM_ERROR` |

`PASS` means every structural check below passed — it is a claim about
readiness for human review, never a claim about creative or editorial
quality, and never an approval. `BLOCKED` means a precondition wasn't
met at all (e.g. a missing input) and no checks could run.
`SYSTEM_ERROR` means the check process itself failed unexpectedly.

## Checks

Grouped by area, one line per check:

### Content

- `<check>` — `PASS` \| `FAIL` — `<note>`

### Voice

- `<check>` — `PASS` \| `FAIL` — `<note>`

### Assets

- `<check>` — `PASS` \| `FAIL` — `<note>`

### Timeline

- `<check>` — `PASS` \| `FAIL` — `<note>`

### Captions

- `<check>` — `PASS` \| `FAIL` — `<note>`

### Thumbnail

- `<check>` — `PASS` \| `FAIL` — `<note>`

### Output

- `<check>` — `PASS` \| `FAIL` — `<note>`

## Reasons

`<itemized findings for every non-PASS check — empty if Verdict is PASS>`

## Notes

`<additional context>`
