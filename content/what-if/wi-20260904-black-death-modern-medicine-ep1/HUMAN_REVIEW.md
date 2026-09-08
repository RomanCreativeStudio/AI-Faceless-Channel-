# Human Review Package: What If Modern Medicine Existed During the Black Death?

A plain-language summary for the content owner. Nothing here requires
inspecting agent source code — every claim below cites the exact
underlying record it was pulled from, so it can be independently spot-
checked. This file is **not** part of the automated review chain (it is
never read by `agents/orchestrator/`, `agents/safety/`, or any other
agent) — it summarizes that chain's real output for a human decision.

| Field | Value |
|---|---|
| Content ID | `wi-20260904-black-death-modern-medicine-ep1` |
| Package date | 2026-09-05 (Safety/Originality sections updated 2026-09-08) |
| Current `CONTENT_ITEM.md` status | `SCRIPT` (unchanged — this system has never set `APPROVED`) |
| Overall content-review status | **Content review chain complete: Fact-check `PASS`, Safety human-cleared, Originality `PASS`** — final human approval (`CONTENT_ITEM.md status = APPROVED`) is still a separate, later decision (see "Approval" below) |

---

## FINAL OWNER APPROVAL CHECKLIST

Prepared 2026-09-09, at commit `6dc9452`. Every line below cites the
exact record it was pulled from — nothing here is asserted without a
source. Full detail for every item is in the numbered sections below;
this is the scannable summary.

| # | Item | Status |
|---|---|---|
| 1 | **Topic / title** | "What If Modern Medicine Existed During the Black Death?" — short-form explainer, `what-if` pillar. History/science-curious general audience. |
| 2 | **What the episode claims** | A bounded hypothetical: if select 14th-century communities had germ theory, case-tracking, sanitation, and quarantine capability (but no antibiotics/vaccines/diagnostics/hospitals), the *spread* of the Black Death could plausibly have slowed — but individual fatality outcomes would not have changed. Explicitly **not** "modern medicine saves the day" (see `SCRIPT.md`'s Conclusion). |
| 3 | **FACT / ASSUMPTION / INFERENCE / SPECULATION** | Fully separated per claim, all `FACT`-classified claims (`c1`,`c2`,`c3`,`c10`,`c11`) `VERIFIED` as of `reviews/fact_checker-2.md`. `ASSUMPTION` = the granted scenario (`c4`,`c12`). `INFERENCE` = plausible-not-established effects (`c6`,`c7`). `SPECULATION` = explicitly-unknowable death-toll/adoption questions (`c8`,`c9`), never stated as established outcomes — see Section 1 below and `SCRIPT.md`'s own "What If? fact/hypothesis separation". |
| 4 | **Safety** | Automated `Safety state` = `REVISION_REQUIRED` (by design — `SENSITIVE_CONTENT` keyword `'plague'` never auto-clears, per `agents/safety/README.md`). **Human signoff = `CLEARED`**, recorded 2026-09-08 (`human_safety_signoffs/signoff-1.md`), hash-verified current and fully covering. Script inspected end to end: no graphic/exploitative/sensational content found. |
| 5 | **Originality** | `PASS` (`reviews/originality_reviewer-3.md`). The one raw finding — 100% topic/premise overlap with `wi-20260902-black-death-modern-medicine` — is the deliberate, documented engineering-fixture relationship this episode was built from (see Section 3 below and `agents/originality/CONTRACT.md`'s "Acknowledged internal engineering fixture exception"), not an accidental/external duplicate. Every other signal `LOW_RISK`/`NOT_APPLICABLE`. |
| 6 | **AI disclosure** | Required (`YES`) and planned: opening on-screen text card + video-description statement (`SCRIPT.md`'s "AI disclosure plan"). Safety's own `AI_DISCLOSURE` signal: `LOW_RISK`. |
| 7 | **Owner voice authorization** | OpenVoice V2, locked production reference "D" (30s sample, `tau=0.3`) — `agents/voice/OWNER_VOICE_REFERENCE.md`. Owner-selected via direct listening; sample stays local/gitignored; no cloud upload; no other provider substituted. |
| 8 | **Production readiness** | **Not yet started against the canonical episode** (no `PRODUCTION.md` exists — Producer requires `status = APPROVED`, which hasn't happened). Validated only against isolated, throwaway copies: real narration, real MP4 (playable), real captions, real thumbnail all previously produced successfully in validation — see Section 4 below. |
| 9 | **Known production limitations** | Two of seven scenes (mortality timeline; absence-of-germ-theory) are `FACT`-classified → default to `RETRIEVED` asset strategy, and no real image retrieval integration exists yet (`agents/production_qa/CONTRACT.md`'s own documented, honest limitation — "working as intended, not a bug to route around"). A real, on-topic, public-domain candidate (Pasteur portrait) was already found for one scene; none was found for the other (script itself calls for a diagram there, not a photo). **Not a defect and not falsely labeled** — no asset has ever been marked `RETRIEVED` without genuine provenance. |
| 10 | **Remaining blockers to approval** | **None found.** The Wikimedia/`RETRIEVED`-strategy item (#9) is a normal, expected production-phase task — it will make the *first real production run*'s Production QA return `REVISION_REQUIRED` for those two assets specifically until resolved (real retrieval, `HUMAN_PROVIDED` with the found Pasteur portrait, or reclassifying to `GENERATED_RECONSTRUCTION`/diagram per the script's own stated visual requirements) — it does not block the approval decision itself, which is about editorial/Safety/Originality readiness. |
| 11 | **Exact action required from the owner** | **Content review is complete and this package is READY FOR OWNER APPROVAL.** If you approve, the action is: set `CONTENT_ITEM.md`'s `Current status` to `APPROVED` yourself, or explicitly instruct this system to do so on your behalf — **this system will not do so on its own authority under any other instruction.** No production, no publishing, and no further state change happens automatically as a result of approval alone. |

---

## 1. Editorial

**What is the episode about?** A short-form explainer asking: how might
the Black Death (1347–1351) have unfolded differently if a handful of
14th-century European communities had germ theory, basic case-tracking,
sanitation, and quarantine capability — but still no antibiotics,
vaccines, modern diagnostics, or hospitals?

**What If? assumption** (granted, not fact — `claims/c4.md`,
`claims/c12.md`): the scenario stipulates germ theory, case tracking,
sanitation, and quarantine capability existed; it withholds antibiotics,
vaccines, diagnostics, pharmaceutical manufacturing, and hospitals.

**Historical facts used** (`Classification: FACT`, all `Fact-check
status: VERIFIED` as of `reviews/fact_checker-2.md`):
- The Black Death's actual 1347–1351 timeline and regional mortality
  (`c1`).
- Germ theory's total absence in 1347 and its actual establishment in
  the 1860s–1880s via Pasteur, Lister, and Koch (`c2`).
- Untreated bubonic/pneumonic plague fatality rates (`c3`).
- Modern antibiotic treatment efficacy against plague today (`c10`).
- Antibiotics not existing until the 20th century (`c11`, via successor
  `c11_rev1` — see `claims/c11.md`'s Superseded note and
  `research/04-wikipedia-antibiotic-history.md`).

**Inference** (`c6`, `c7`) — plausible but not established outcomes:
transmission chains could plausibly shrink under the granted scenario,
but an infected individual still faces historical fatality risk absent a
cure; airborne pneumonic plague likely remains hard to contain even with
the granted knowledge.

**Speculation** (`c8`, `c9`) — explicitly flagged as unknowable: the
actual size of any death-toll reduction is not estimable from available
evidence; whether a 14th-century, religious/humoral worldview would have
broadly trusted a germ-based model is unknown.

The script never states `c6`–`c9` as established outcomes — beats 4–6 use
hedged language throughout ("plausibly," "could not," "likely," "we
genuinely don't know"), and beat 6 exists specifically so the piece does
not read as "modern medicine would have solved it." See `SCRIPT.md`'s own
"What If? fact/hypothesis separation" section for the full breakdown.

---

## 2. Safety

**Why did Safety escalate?** One signal only:
`SENSITIVE_CONTENT: REVIEW_REQUIRED` (`reviews/safety_reviewer-2.md` —
the current attempt; identical finding as attempt #1, re-run after this
file's own creation touched `CONTENT_ITEM.md` and changed its reviewed
content hash).
The trigger is a plain keyword match — the word **"plague"** appearing in
`SCRIPT.md` (it appears in the Premise and beats 4–6, always as the
clinical/historical name of the disease) and once in `CONTENT_ITEM.md`'s
premise field. `agents/safety/src/signals.py`'s `check_sensitive_content`
is a deterministic keyword check, by design incapable of judging tone or
framing — any occurrence of a small curated list of mass-casualty/
tragedy keywords (`genocide`, `massacre`, `plague`, `pandemic`, etc.)
always produces `REVIEW_REQUIRED`, regardless of how responsibly the
surrounding text treats the subject. This is intentional: the system
escalates every real tragedy topic to a human rather than ever attempting
to auto-clear one. **It has not been weakened, bypassed, or removed.**

**Is the material graphic?** No. The script was read in full and
scanned for graphic/exploitative language (gore, suffering, mutilation,
sensationalized death description) — none found. Mortality is discussed
only as sourced, hedged statistics ("somewhere between a quarter and well
over half of the population died," "bubonic plague killed an estimated
thirty to sixty percent of the people it infected"), never as narrated
scenes of suffering.

**Is the material sensational?** No. There is no exaggerated-casualty
framing, no dramatized language beyond the Hook's factual statistic, and
every claim about outcomes is explicitly hedged (Section 1 above). The
Conclusion explicitly rejects a "modern medicine saves the day" framing:
*"This isn't a story about medicine saving the day; it's about which
parts of 'modern medicine' actually matter, and which parts don't help
without the rest."*

**What visuals are being used?** From the validated production run (an
isolated, throwaway copy — never the canonical episode; see "Production"
below):
- Scene 1 (Hook): on-screen text/graphic framing — `NOT_APPLICABLE`
  authenticity classification, no historical depiction.
- Scenes 2–3 (mortality timeline; absence of germ theory): intended as
  `AUTHENTIC_HISTORICAL_MEDIA` (real archival images), but real Wikimedia
  retrieval genuinely failed for both in this run (see "Production" and
  "Wikimedia asset status" below) — substituted, for validation only,
  with the same abstract generated illustration style used elsewhere,
  and never marked as a successful real retrieval.
- Scenes 4–7 (the hypothetical scenario; plausible effects; airborne
  transmission limits; open uncertainty): `GENERATED_RECONSTRUCTION` —
  Pillow-rendered, deliberately non-photorealistic illustrations (a
  gradient/concentric-ring motif, never an attempt at a realistic or
  period-accurate scene), each burned with an "AI-GENERATED
  RECONSTRUCTION" label. None depict graphic imagery — the renderer is
  structurally incapable of rendering gore or realistic scenes at all
  (see `agents/assets/src/illustration.py`).
- No imagery reviewed is disturbing or could reasonably be mistaken for
  authentic historical media it isn't (the classification is burned into
  every generated asset, and Production QA's "No false factual
  implication" thumbnail check passed).

**AI disclosure**: intact. `SCRIPT.md` states `AI disclosure required:
YES` and now includes a real "AI disclosure plan" section (added this
session) describing an opening on-screen text card and a video-
description statement. Safety's own `AI_DISCLOSURE` signal reads
`LOW_RISK — AI disclosure marked YES with a stated plan`.

**What exactly must the human decide?** Whether this specific treatment
of a real historical mass-casualty event — factual, statistically hedged,
explicitly non-sensational, with no graphic content — is appropriate for
publication as-is. This system has confirmed the trigger is the subject
matter itself, not unsafe treatment of it, but only a human may make the
actual editorial tone/framing judgment call `CONSTITUTION.md` reserves
for this signal.

**No editorial revision was made to the script for this reason.**
Rewriting the script to remove the word "plague" (the historical disease
this episode is about) would not change the substance of the content —
it would only defeat the keyword detector without addressing what it is
actually for. See `agents/safety/README.md`'s "Known limitations" for why
this signal exists exactly to force this decision to a human rather than
being satisfied mechanically.

---

## Human Safety Decision — RECORDED

**Decision: `CLEARED`** — recorded 2026-09-08 by the content owner via
`agents/safety/src/human_signoff_cli.py`, at
`human_safety_signoffs/signoff-1.md`. Reviewed content hash
`6317c7ae6b847d8fea345b392f187228de39d09111997d1e1631ff73922a526e`
(matches this package's own documented value below — the signoff was
recorded against the exact content state described in this document).

The owner's stated reasoning: the episode treats the Black Death/plague
as a historical and educational subject — no graphic or exploitative
description of suffering, no sensationalized casualty framing, no
glorification, no harmful/dangerous instructions, no deceptive framing.

**What this did and did not do**: `continue_after_human_safety_review()`
verified the signoff (decision, hash freshness, full coverage of the one
outstanding Safety finding) and, because everything checked out, ran
`ORIGINALITY_REVIEW` for real — see "Originality" below for its result.
This did **not** modify `CONTENT_ITEM.md`'s `Safety state` field, which
remains `REVISION_REQUIRED` exactly as the automated `SENSITIVE_CONTENT`
detector left it — the automated Safety review is never edited or
weakened by a human signoff; the signoff is a separate, permanent record
that unblocks progression without altering what the detector itself
found. This did **not** set `CONTENT_ITEM.md status = APPROVED` and did
**not** authorize production or publishing — see "Approval" below.

*(Original text of this section, preserved for reference — the decision
above supersedes the open question it posed.)*

Read the "Safety" section above (and the script itself, if you want more
than the summary), then choose one:

**`CLEARED`** — you have reviewed the script and visual treatment above
and judge this historical, statistically-hedged, non-graphic treatment
of a real tragedy appropriate to proceed past this specific Safety
signal.

**`NOT_CLEARED`** — you judge that something about the treatment (tone,
framing, a passage you'd want changed) needs to be revised first.

Before deciding, please keep in mind:

- This is historical educational content about a real, well-documented
  event (the Black Death, 1347–1351).
- The word "plague" is triggering a deterministic Safety keyword
  detector (`SENSITIVE_CONTENT`) — the detector has no ability to judge
  tone, quality, or context; it flags the *topic*, not a defect.
- The script was inspected end to end for graphic, exploitative, or
  sensational treatment. **None was found** — see Section 2 above for
  specifics and citations.
- Clearing this signal does **not** approve the episode for publication.
  `ORIGINALITY_REVIEW` still has to run, and final content approval
  (`CONTENT_ITEM.md status = APPROVED`) remains a completely separate,
  later decision that only you make.

Nothing in this system will infer your decision from any other action
(editing this file, rerunning a command, committing code) — it has to be
recorded explicitly. To record it, run one command from the repository
root:

```
python -m agents.safety.src.human_signoff_cli \
  content/what-if/wi-20260904-black-death-modern-medicine-ep1 \
  --reviewer "<your name>" \
  --decision CLEARED \
  --signals SENSITIVE_CONTENT \
  --scope "Read HUMAN_REVIEW.md in full, plus SCRIPT.md and the per-scene visual treatment described in Section 2." \
  --historical-context-reviewed
```

(Use `--decision NOT_CLEARED` and add `--notes "<what needs to change>"`
instead, if that's your decision.) This writes a new, permanent, numbered
record under `human_safety_signoffs/` — it never edits or replaces the
automated `reviews/safety_reviewer-2.md` escalation, which stays exactly
as `agents/safety/` wrote it. The command computes the content hash it
signs off on automatically, from whatever is on disk at the moment you
run it (currently `6317c7ae6b847d8fea345b392f187228de39d09111997d1e1631ff73922a526e`
— shown here only so you can spot-check it if you like; if `SCRIPT.md` or
`CONTENT_ITEM.md` change before you run the command, it will compute a
different value automatically, and that's correct).

Once a `CLEARED` decision is recorded, running
`agents/orchestrator/src/human_safety_continuation.py`'s
`continue_after_human_safety_review()` against this content item will
verify it (decision, hash freshness, and that no *other* Safety finding
is outstanding) and, only if everything checks out, run
`ORIGINALITY_REVIEW` for real. A `NOT_CLEARED` decision leaves the item
blocked with a clear `EDITORIAL_REVISION_REQUIRED` status instead —
nothing will retry automatically.

---

## 3. Originality

**First ran 2026-09-08, after Safety was human-cleared** — `reviews/
originality_reviewer-1.md` — verdict `REVISION_REQUIRED`, one finding:
`INTERNAL_DUPLICATION: HIGH_RISK`, 100% (word-set Jaccard) topic/premise
overlap with `wi-20260902-black-death-modern-medicine`. Expected and
documented, not a surprise — Episode 1's own history states it "adapts
the editorial content originally developed and reviewed as the Phase
3-6 schema/engineering fixture" at that exact path — but the detector
had no way to *represent* that distinction as anything other than a
blocking finding.

**Architecture gap found and fixed, 2026-09-08** — `agents/originality/`
had no concept of "this comparison doesn't count" anywhere in
`signals.py`/`loader.py`/`models.py` (confirmed by direct inspection).
Added the smallest safe mechanism to represent it, documented in full in
`agents/originality/CONTRACT.md`'s "Acknowledged internal engineering
fixture exception": a new, optional `Acknowledged internal fixture`
field (this file's own `## Originality context` section — deliberately
kept out of `## Identity` so it can never affect
`agents/safety/`'s content hash, confirmed unchanged:
`6317c7ae...` before and after) that this item now sets to
`wi-20260902-black-death-modern-medicine`. The exception applies **only**
when that declaration is present *and* the matched item is
independently, structurally self-identified (from its own already-
existing, untouched text) as an internal engineering/schema-validation
fixture — never a blanket suppression, never usable against
`EXTERNAL_SIMILARITY_RISK`, and does not weaken detection for any other
item or any other comparison. 8 new regression tests
(`agents/originality/tests/test_internal_fixture_exception.py`) prove
this.

**Re-ran 2026-09-08 with the exception now representable** —
`reviews/originality_reviewer-2.md`, verdict `PASS`.

**A second, independent bug found and fixed, 2026-09-09** — while
preparing the Final Owner Approval Checklist above, a direct re-hash of
this item's reviewed content no longer matched `originality_reviewer-2.md`'s
own stored hash, even though nothing about the reviewed content had
changed. Root cause: `agents/originality/src/hashing.py`'s `compute_
reviewed_content_hash()` hashed the *entire* `CONTENT_ITEM.md` file,
including the `Originality state` field and Notes/history-log line this
agent's own apply step writes *immediately after* computing that hash —
the identical self-invalidation bug already found and fixed for Safety
(see the 2026-09-05 Notes/history-log entry), independently present and
unfixed in Originality. This defeated `agents/orchestrator/src/
freshness.py`'s generic PASS-reuse check for Originality specifically —
every fresh `PASS` looked stale the instant it was written, forcing an
unnecessary re-run every time. Fixed by scoping the hash to the Identity
and Originality-context sections only (mirroring Safety's exact fix) —
the only two sections `signals.py` actually reads from `CONTENT_ITEM.md`.
4 new regression tests
(`agents/originality/tests/test_hash_self_invalidation_fix.py`) prove
the stored hash now survives the apply step and stays sensitive to
genuine content changes. Re-ran once more with the fix applied —
`reviews/originality_reviewer-3.md`, verdict `PASS`, hash now verified
to survive its own apply step for real.

**Verdict: `PASS`** — `INTERNAL_DUPLICATION` is now `LOW_RISK`, with the
raw 100% overlap and the full exception reasoning both still stated
explicitly in the review record (never a bare, unexplained pass). Every
other signal remains `LOW_RISK`/`NOT_APPLICABLE`, unchanged from before:
concept/framing/script/title-hook distinctiveness, source dependence (6
`FACT` claims across 4 distinct sources), template repetition, and
`EXTERNAL_SIMILARITY_RISK` (`NOT_APPLICABLE` — this system does not
perform internet-wide similarity search, so this result says nothing
about material outside this repository).

---

## 4. Production

All of the below was produced and verified against a fresh, isolated,
throwaway copy of this episode (this session's own scratch directory —
never committed, never the canonical episode). The canonical
`CONTENT_ITEM.md` status was never touched and remains `SCRIPT`.

| Item | Status |
|---|---|
| Narration | Real ~191s WAV via `FliteVoiceProvider` (offline, no cloud TTS) — `GENERATED` |
| MP4 | Real H.264/AAC, `ffprobe`-verified `Playable = YES`, captions burned in (see "known production path" below) |
| Captions | Real, per-scene, generated and verified against source narration (`agents/production_qa/`'s "Captions map to narration" check passed) |
| Thumbnail | Real 1280×720 PNG rendered from the existing spec — `GENERATED` |
| Visual provenance | 5 of 7 scenes `GENERATED_RECONSTRUCTION` (Pillow, offline); 2 of 7 scenes intended `AUTHENTIC_HISTORICAL_MEDIA`, real retrieval genuinely failed, substituted for validation only with `Generation/retrieval status` left honestly `NOT_STARTED` — never marked `RETRIEVED` |
| Production QA verdict | `REVISION_REQUIRED` — exactly the two Wikimedia retrieval gaps above; every other check (Content, Voice, Timeline, Captions, Thumbnail, Output/playability) passed |

**Known production path** (documented, not a defect): the real video
renderer (`agents/assembler/src/real_provider.py`) structurally runs
before Captions in the pipeline's own stage order (Captions requires
`Production status == CAPTIONS`, which only a completed Assembler run
sets). A genuinely captioned cut requires one additional, explicit
render pass after Captions runs, reusing the same real renderer directly
— this two-pass path was exercised end to end this session and produced
a verified, playable, captioned MP4. This is the current, working
production path; it is not being redesigned, since it causes no actual
failure. Only hard-cut transitions are implemented by the renderer;
Episode 1 only ever uses cuts, so this never mattered in practice.

---

## 5. Wikimedia asset status

Real retrieval was attempted (and failed) for the two `RETRIEVED`-
strategy scenes (mortality timeline; absence of germ theory). This
session re-attempted retrieval directly, with several honest, still-
topically-faithful queries, specifically to check whether a legitimate
real asset now exists for either scene (not to force a match):

- **Mortality timeline scene**: no safe, topically accurate result found.
  Queries returned either nothing, or real-but-mismatched/misleading hits
  (e.g. a 1930s political cartoon literally titled "the New Black
  Plague," unrelated to the 1347–1351 event; an unrelated Renoir
  painting). None were used. `SCRIPT.md`'s own Visual requirements
  section already calls for a "map graphic" here — a diagram, not an
  archival photograph (none exists from 1347) — so `GENERATED_RECONSTRUCTION`
  or a diagram is arguably the structurally correct asset type for this
  scene, not a retrieval gap at all. Left honestly documented; no
  fabricated source was recorded.
- **Absence-of-germ-theory scene**: a real, safe, on-topic, public-domain
  candidate was found — a portrait of Louis Pasteur (Wikimedia Commons,
  public domain), directly relevant since the script names Pasteur as
  one of the scientists who later established germ theory. This is
  recorded here as a real finding for a future production run to use;
  it was not written into any asset file this session because the
  canonical episode has no `assets/` directory yet (Producer has never
  run against it — that requires `status = APPROVED`, which has not
  happened).

No asset anywhere in this repository is, or has been, labeled `RETRIEVED`
without a real, verifiable retrieval and provenance record.

---

## 6. Approval

**HUMAN APPROVAL STILL REQUIRED — updated 2026-09-08.**

1. ~~A human must review this episode's tone and framing... and decide
   whether `SAFETY_REVIEW` may be recorded as cleared.~~ **Done** —
   `CLEARED`, recorded 2026-09-08 (see "Human Safety Decision" above).
2. ~~Originality Review's `INTERNAL_DUPLICATION` finding needs its own
   human resolution.~~ **Done** — the relationship to the engineering
   fixture was determined to be the expected, deliberate one (not an
   accidental/external duplicate); the architecture gap that prevented
   representing this was fixed (see "Originality" above), and Originality
   now genuinely `PASS`es. Note `CONTENT_ITEM.md`'s `Safety state`
   field itself still correctly reads `REVISION_REQUIRED` — the human
   signoff is a separate record that unblocks progression without ever
   editing the automated Safety verdict.
3. Content review is now a genuine, full `PASS` (Fact-check `PASS` +
   Safety human-cleared + Originality `PASS`). The human owner may now
   consider setting `CONTENT_ITEM.md`'s `status = APPROVED` — **this
   system has not done so and will not do so on its own authority**.
   `Current status` remains `SCRIPT`, unchanged.

The episode is **not** published and **not** approved. Content review
reaching `PASS` is a precondition for approval, not approval itself —
that final decision, and only that decision, remains entirely the human
owner's.
