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
| Package date | 2026-09-05 |
| Current `CONTENT_ITEM.md` status | `SCRIPT` (unchanged — this system has never set `APPROVED`) |
| Overall content-review status | **BLOCKED — human Safety review required** (see "Safety" below) |

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

## 3. Originality

**Not reached.** `agents/orchestrator/`'s `run_automated_review` runs
`FACT_CHECK → SAFETY_REVIEW → ORIGINALITY_REVIEW` and correctly stops at
the first blocking stage. Safety is currently `REVISION_REQUIRED`
(human-gated, see above), so `ORIGINALITY_REVIEW` has not run. Its
outcome is genuinely unknown until Safety clears.

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

**HUMAN APPROVAL REQUIRED.**

Two separate, sequential decisions remain, in order:

1. A human must review this episode's tone and framing of real
   historical mass-casualty content (Section 2 above) and decide whether
   `SAFETY_REVIEW` may be recorded as cleared. This system cannot and
   will not make this decision.
2. Only after content review reaches a genuine `PASS` (Fact Check +
   Safety + Originality), the human owner may consider setting
   `CONTENT_ITEM.md`'s `status = APPROVED`. This system has not done so
   and will not do so on its own authority.

The episode is **not** published and **not** approved.
