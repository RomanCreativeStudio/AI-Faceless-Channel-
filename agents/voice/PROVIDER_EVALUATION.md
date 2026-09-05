# Owner-Voice Provider Evaluation

A research document, not an implementation. No account was created, no
purchase made, no credential added, and the owner's private voice
sample was not uploaded to, or even mentioned by path/content to, any
external service while producing this. See
`agents/voice/src/owner_voice.py` for the existing, vendor-neutral
architecture this evaluation is choosing a provider *for* — nothing
about that architecture changes here.

**The final choice of provider is `HUMAN_OWNER_DECISION`.** This
document narrows the field and states tradeoffs; it does not pick a
winner on the owner's behalf.

Research date: 2026-09-05. Pricing, terms, and feature availability for
every vendor below change over time — treat the figures here as a
snapshot to sanity-check against the provider's own current pages
before acting, not as a permanent quote.

---

## 1. What an adapter must implement

Recap of the existing, unmodified `OwnerVoiceEngine` protocol
(`agents/voice/src/owner_voice.py`) — this is the entire surface a real
provider adapter would need to fill in:

```python
class OwnerVoiceEngine(Protocol):
    name: str
    required_credential_env_vars: list[str]

    def is_available(self) -> tuple[bool, str]:
        """Engine-specific checks beyond credentials (e.g. a required
        package is importable, a local model file exists)."""
        ...

    def synthesize(self, narration_text: str, config: OwnerVoiceConfig) -> EngineSynthesisResult:
        """Returns EngineSynthesisResult(audio_bytes, extension,
        duration_seconds, model_label) or raises."""
        ...
```

A future adapter (e.g. `agents/voice/src/engines/elevenlabs_engine.py`,
never built until the owner decides) would:

1. Declare `name` (the string an operator sets `OWNER_VOICE_ENGINE` to)
   and `required_credential_env_vars` (e.g. `["ELEVENLABS_API_KEY"]` —
   names only; this module never reads the value itself).
2. Implement `is_available()` — for a cloud vendor, typically "is the
   SDK importable" plus maybe a lightweight reachability check; for a
   local model, "is the model file present, is the required package
   importable, is a GPU available if required."
3. Implement `synthesize()` — read `config.sample_path` itself (this is
   the *only* code in the whole system that would ever touch the
   sample's contents), call the vendor's real cloning/TTS call using
   `config.voice_id`/`model_id`/`language`/`speaking_style`/
   `stability`/`consistency`/`pronunciation`, and return real audio
   bytes.
4. Call `register_owner_voice_engine(MyEngine())` once, at process
   start (e.g. in a small, new, vendor-specific module — never inside
   `owner_voice.py` itself, which stays vendor-neutral permanently).

Nothing else changes: not `pipeline.py`, not `mutate.py`, not
`templates/VOICE.md`, not `provider_selection.py`'s three existing
names (owner-voice already resolves to whatever engine is registered).

---

## 2. Sample status

```
INITIAL_SAMPLE_STATUS = TECHNICALLY_USABLE_FOR_TEST
```

The ~18-second sample already provided (mono AAC, 44.1kHz, clean —
checked with `ffprobe` in a prior session) is technically clean audio.
**Technical cleanliness is not the same claim as production-quality
voice-clone fidelity.** Whether it's *sufficient* depends entirely on
which provider is chosen (see the shortlist below — some explicitly
support clips this short for an initial test; none of the reputable
cloud vendors recommend stopping there for a voice a channel will use
repeatedly). A longer, 2–5 minute clean sample is recommended before
committing to any provider for real production use, and is close to
what several vendors themselves recommend as a *minimum*, not just an
upgrade.

---

## 3. Provider shortlist

Every factual claim below cites its source inline. Aggregator/blog
sources are marked as such; where only an aggregator could be reached
this session, that's stated rather than presented as a primary-source
fact.

### 3.1 ElevenLabs

| Field | Value |
|---|---|
| Minimum sample (stated) | ~30 seconds possible per some usage reports; **official guidance recommends 1–2 minutes**, and explicitly warns more than 3 minutes yields little benefit [[docs]](https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning/instant-voice-cloning) |
| 18s supported? | `POSSIBLE_FIT` — below the recommended range; may run, quality/consistency not guaranteed at this length |
| Recommended duration | 1–2 minutes, clean mono, ≥192kbps or high-quality capture, no reverb/background noise [[docs]](https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning/instant-voice-cloning) |
| Voice quality | Reputationally considered a leading commercial option (multiple independent reviews); **not independently verified by this evaluation** — `UNKNOWN` in absolute terms |
| Expressiveness/cadence | Same caveat — widely reported as strong, not independently tested here |
| API availability | `GOOD_FIT` — mature, documented REST API and SDKs |
| Commercial/YouTube use | `GOOD_FIT` on a paid plan — commercial license included starting at the $6/mo Starter tier; **voice cloning itself requires the Creator tier ($11–22/mo) or above** [[pricing]](https://elevenlabs.io/pricing) |
| Privacy/data | Voice data is treated as biometric data under EU/UK GDPR; default retention up to 3 years after last interaction, with user-initiated deletion available; "Zero Retention Mode" exists but is an Enterprise-tier feature [[privacy research, aggregated]](https://elevenlabs.io/privacy-policy) |
| Cost category | `$` (Starter) to `$$` (Creator/Pro) for a single narration voice at this project's scale |
| Integration complexity | `GOOD_FIT` — simple REST call, maps cleanly onto `synthesize()` |
| Major limitation | Cloning requires a $11–22/mo tier, not the cheapest commercial tier; the private sample must be uploaded to ElevenLabs' cloud |

### 3.2 PlayHT

| Field | Value |
|---|---|
| Minimum sample (stated) | 30 seconds minimum, ~1 minute recommended for usable results (aggregator sources; PlayHT's own docs page could not be reached this session — `UNKNOWN`, verify directly before adoption) |
| 18s supported? | `POSSIBLE_FIT` — below the reported 30s minimum |
| Recommended duration | ~1 minute+ (aggregator-sourced, `UNKNOWN` precision) |
| Voice quality / expressiveness | `UNKNOWN` — only aggregator reputation found, not independently verified |
| API availability | `GOOD_FIT` — official Python SDK on GitHub (`playht/pyht`) |
| Commercial/YouTube use | `UNKNOWN` — exact commercial-license terms need direct verification with PlayHT; paid tiers exist ($29–99/mo, aggregator-sourced) |
| Privacy/data | `UNKNOWN` — could not reach primary documentation this session |
| Cost category | `$$` (aggregator-sourced: ~$29–99/mo tiers) |
| Integration complexity | `GOOD_FIT` — REST API, multiple audio formats/sample rates documented (WAV/MP3/FLAC/OGG/mulaw; 8–48kHz) |
| Major limitation | This evaluation could not reach PlayHT's own docs to verify commercial terms/privacy — treat as `UNKNOWN` until confirmed directly, not assumed acceptable |

### 3.3 Resemble AI

| Field | Value |
|---|---|
| Minimum sample (stated) | "Rapid Clone" from as little as ~10 seconds; "Professional Clone" wants 10–25+ minutes for best consistency (aggregator-sourced) |
| 18s supported? | `GOOD_FIT` for an initial Rapid Clone — comfortably above the ~10s floor reported |
| Recommended duration | 10–25+ minutes for the Professional tier's consistency/expressiveness |
| Voice quality / expressiveness | `UNKNOWN` in absolute terms; some sources highlight real-time expressive delivery — not independently verified |
| API availability | `GOOD_FIT` — API-first product, including real-time speech-to-speech |
| Commercial/YouTube use | `POSSIBLE_FIT` — commercial rights require a paid Creator-or-above plan; explicitly notes a paid license is *not* a substitute for the speaker's own consent to use their identity/voice (a good philosophical match for this project's `OWNER_AUTHORIZED_VOICE` stance) |
| Privacy/data | `UNKNOWN` in detail; the explicit consent-documentation expectation above is a positive signal, not a substitute for reading their DPA/privacy policy directly |
| Cost category | `$` — pay-per-use reported around $0.0005/sec of synthesized audio plus voice-clone/seat fees (aggregator-sourced); likely the cheapest *hosted* option at this project's narration volume |
| Integration complexity | `GOOD_FIT` — API-first |
| Major limitation | Exact commercial-license and data-retention fine print needs direct verification; pay-per-use pricing needs modeling against this channel's actual expected monthly narration volume |

### 3.4 Azure AI Speech — "Personal Voice"

| Field | Value |
|---|---|
| Minimum sample (stated) | **One minute of human speech**, per Microsoft's own comparison table [[docs]](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/personal-voice-overview) |
| 18s supported? | `POOR_FIT` — below Microsoft's own stated one-minute requirement |
| Recommended duration | 1 minute minimum per Microsoft; training itself is reported as under 5 seconds of compute once the sample is in |
| Voice quality | Microsoft's own table describes Personal Voice output as "Natural" (their own comparative label, not an independent benchmark) |
| Expressiveness/cadence | `UNKNOWN` — not benchmarked here |
| API availability | `POSSIBLE_FIT` — an API exists, but "Access to the API is restricted to eligible customers and approved use cases" via an intake form [[docs]](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/personal-voice-overview) |
| Commercial/YouTube use | `POOR_FIT` for this project as described — Personal Voice's stated target scenario is "Business customers [building] an app to allow their users to create and use their own personal voice **in the app**," explicitly "restricted to limited use cases" under Microsoft's Responsible AI policy. A general commercial YouTube channel narrating its own content is a plausible-but-unconfirmed fit; approval is not guaranteed and must be requested, never assumed |
| Privacy/data | `GOOD_FIT` conceptually — the product is built around a mandatory, recorded verbal consent statement before any voice is created, which aligns unusually well with this project's own `OWNER_AUTHORIZED_VOICE` requirement |
| Cost category | `UNKNOWN` — "pricing will only be visible for service regions where the feature is available," i.e. after approval |
| Integration complexity | `POSSIBLE_FIT` — more steps than a typical cloning API (create project → record+upload consent statement → obtain a speaker profile ID → synthesize), all Microsoft-SDK-mediated |
| Major limitation | Gated behind an approval process for a "Limited Access" feature; not something this system can self-certify as usable for a general commercial channel — must be confirmed directly with Microsoft first |

### 3.5 OpenVoice V2 (MyShell/MIT) — self-hosted, open source

| Field | Value |
|---|---|
| Minimum sample (stated) | As little as 1–5 seconds of reference audio for instant cloning [[repo]](https://github.com/myshell-ai/OpenVoice) |
| 18s supported? | `GOOD_FIT` — well above the reported minimum |
| Recommended duration | Not specified in the project's own README; general voice-cloning practice (more/cleaner audio generally helps consistency) still applies |
| Voice quality / expressiveness | `UNKNOWN` in absolute terms; the project's own materials claim "granular control over voice styles" (emotion, accent, rhythm, pauses, intonation) and "better audio quality" in V2 vs. V1 — self-reported, not independently verified here |
| API availability | `POOR_FIT` as a *hosted* API — this is a self-hosted model/codebase, not a managed service; there is no vendor endpoint to call |
| Commercial/YouTube use | `GOOD_FIT` — MIT license, explicitly "free for both commercial and research use" as of April 2024 [[repo]](https://github.com/myshell-ai/OpenVoice) |
| Privacy/data | `GOOD_FIT` — the strongest privacy posture of any option here: the sample never has to leave infrastructure the owner controls at all |
| Cost category | `$` — free software; the only cost is compute (a capable GPU, locally or rented) |
| Integration complexity | `POSSIBLE_FIT` — no network call needed (fits `synthesize()` as a direct in-process/local call), but requires standing up and maintaining a local inference environment (Python/PyTorch/model weights/GPU driver stack) — meaningfully more DevOps than calling a REST endpoint |
| Major limitation | Self-hosting effort and hardware requirement; supports 6 languages natively (English, Spanish, French, Chinese, Japanese, Korean) vs. ElevenLabs'/Azure's 90+ |

**Honorable mention, explicitly not shortlisted as a primary
recommendation: Coqui XTTS-v2.** Frequently recommended online as *the*
open-source cloning model (clones from ~6 seconds of audio, 17
languages, actively maintained by the community as the `coqui-tts`
package after Coqui the company shut down in early 2024
[[GitHub discussion]](https://github.com/coqui-ai/TTS/discussions/3489)),
but its model weights are released under the **Coqui Public Model
License (CPML) 1.0.0, which explicitly permits non-commercial use
only**. For a channel that publishes commercially/monetized content,
that license makes XTTS-v2 a `POOR_FIT` as evaluated — not because of
technical capability, but because of a real, easy-to-miss legal
restriction. It remains worth keeping in mind for genuinely
non-commercial internal experimentation only, never for anything that
ships to the public channel, unless a separate commercial license is
independently obtained from whoever currently holds rights to it.

---

## 4. Comparison matrix

Deterministic rule used for every cell: `GOOD_FIT` = the requirement is
clearly met per a primary or high-confidence source; `POSSIBLE_FIT` =
met with a real caveat (paid tier required, below-recommended sample
length, approval-gated, or aggregator-only evidence); `POOR_FIT` =
not met, or conflicts with a hard project constraint (e.g. a
non-commercial license for a commercial channel); `UNKNOWN` =
insufficient verified information this session — never guessed.

| Criterion | ElevenLabs | PlayHT | Resemble AI | Azure Personal Voice | OpenVoice V2 |
|---|---|---|---|---|---|
| Voice similarity/quality | `UNKNOWN`* | `UNKNOWN`* | `UNKNOWN`* | `UNKNOWN`* | `UNKNOWN`* |
| Expressiveness/cadence | `UNKNOWN`* | `UNKNOWN`* | `UNKNOWN`* | `UNKNOWN`* | `UNKNOWN`* |
| 18-second sample supported | `POSSIBLE_FIT` | `POSSIBLE_FIT` | `GOOD_FIT` | `POOR_FIT` | `GOOD_FIT` |
| Commercial/YouTube usage rights | `GOOD_FIT` (paid) | `UNKNOWN` | `POSSIBLE_FIT` (paid) | `POOR_FIT` (gated) | `GOOD_FIT` |
| API availability | `GOOD_FIT` | `GOOD_FIT` | `GOOD_FIT` | `POSSIBLE_FIT` (gated) | `POOR_FIT` (no hosted API) |
| Reliability | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `POSSIBLE_FIT` (Azure infra) | `POSSIBLE_FIT` (self-owned) |
| Cost/pricing predictability | `POSSIBLE_FIT` | `POSSIBLE_FIT` | `GOOD_FIT` | `UNKNOWN` | `GOOD_FIT` |
| Privacy/data handling | `POSSIBLE_FIT` | `UNKNOWN` | `POSSIBLE_FIT` | `GOOD_FIT`† | `GOOD_FIT` |
| Integration w/ `OwnerVoiceEngine` | `GOOD_FIT` | `GOOD_FIT` | `GOOD_FIT` | `POSSIBLE_FIT` | `POSSIBLE_FIT` |

\* No provider's raw voice-clone quality/expressiveness was
independently tested in this evaluation — every "top-tier quality"
claim in circulation is reputational/self-reported. This must be
verified with a real (opt-in, provider-appropriate) test sample before
final selection, not assumed from marketing or aggregator reviews.

† Rated on *consent-design philosophy* (mandatory recorded verbal
consent before voice creation), not on whether Azure will actually
grant this project access to Personal Voice at all — that remains
`UNKNOWN`/gated.

---

## 5. Recommendations (non-binding — `HUMAN_OWNER_DECISION`)

1. **Best overall candidate:** ElevenLabs — most mature, best-documented
   API and cloning workflow among the cloud options, with an
   unambiguous path to commercial rights (paid tier) and a clear
   consent checkbox in its own product flow. Caveat: quality claims are
   reputational, and the 18-second sample is below its own recommended
   1–2 minute minimum.
2. **Best low-cost candidate:** Resemble AI, if a hosted service is
   preferred (pay-per-use, reported ~$0.0005/sec) — or **OpenVoice V2**
   if self-hosting is acceptable (free software; only compute cost).
3. **Best privacy/local candidate:** OpenVoice V2 — MIT-licensed
   (commercial use explicitly permitted, unlike XTTS-v2's non-commercial
   CPML), and the only option where the voice sample never has to leave
   infrastructure the owner controls.
4. **Best candidate for natural, expressive narration:** ElevenLabs,
   based on the most consistent reputational signal found across
   independent reviews — with Resemble AI a plausible second candidate
   for expressive delivery. Neither claim is independently verified
   here; a short, real comparative listening test (with a sample the
   owner explicitly authorizes for that specific test) is the only way
   to confirm this before committing.

None of the above is a final selection. All four still require the
owner to weigh cost, the privacy tradeoff of a cloud upload vs.
self-hosting, and their own tolerance for Azure's approval gate — that
weighing is `HUMAN_OWNER_DECISION`, not something this evaluation
resolves.

---

## 6. Main risks / limitations found

- **Every cloud vendor requires uploading the owner's private voice
  sample to that vendor's servers.** This is an inherent tradeoff of
  any hosted cloning API, not a defect of one particular vendor — only
  a self-hosted option (OpenVoice V2) avoids it entirely.
- **The 18-second sample is below the stated minimum/recommendation for
  most reputable options** (ElevenLabs recommends 1–2 minutes; Azure
  requires 1 minute). It comfortably clears Resemble AI's and OpenVoice
  V2's much lower floors. A longer 2–5 minute sample is recommended
  before any production commitment, independent of which provider is
  chosen.
- **Free/default tiers typically exclude commercial rights.** A paid
  tier is required before any owner-voice narration could be safely
  used on a monetized YouTube channel, regardless of vendor.
- **XTTS-v2's popularity online does not include its licensing
  restriction** — its CPML license is non-commercial only. This is an
  easy, costly mistake to make by following generic "best open source
  voice cloning" advice without checking the license.
- **Azure Personal Voice's availability for this exact use case is not
  guaranteed** — it is a Limited Access feature gated behind an intake
  form and explicitly scoped to "limited use cases"; treat it as
  `UNKNOWN`/aspirational, not a confirmed option, until Microsoft
  actually grants access for this specific purpose.
- **Voice data is classified as biometric data under EU/UK GDPR** (and
  similar regimes elsewhere) — a regulatory consideration independent
  of which vendor is chosen, relevant to consent language and data
  handling regardless of the final pick.
- **No provider's reliability (uptime/SLA) was independently verified**
  in this evaluation — check each candidate's own status page/SLA
  documentation directly before committing production narration to it.
- **All pricing above is a September 2026 snapshot**, gathered via web
  search and primary docs where reachable — re-verify current pricing
  directly with the vendor before budgeting.

---

## 7. What the owner must decide

1. Which provider to actually use — weighing cost, the cloud-upload vs.
   self-hosted privacy tradeoff, and willingness to accept an
   approval-gated option (Azure) if pursued.
2. Whether they're comfortable with their voice sample being processed
   by a third-party cloud service at all, versus preferring to keep it
   entirely on infrastructure they control.
3. Whether to record a longer (2–5 minute) clean sample before
   committing — likely worthwhile regardless of provider.
4. Creating the actual vendor account, agreeing to that vendor's terms,
   and generating API credentials themselves — this system must not and
   will not do any of that.
5. Confirming the chosen vendor's data-retention/consent terms are
   acceptable, given voice data's biometric-data classification in some
   jurisdictions.

## 8. Can a real adapter be implemented now?

**No.** Per the decisions above, none of which this system may make.
Once the owner picks a provider and supplies real, owner-obtained
credentials via the environment, a single new, small, isolated module
(e.g. `agents/voice/src/engines/<chosen>_engine.py`, implementing
exactly the `OwnerVoiceEngine` protocol recapped in Section 1 and
registered via `register_owner_voice_engine`) is the only code change
needed — `owner_voice.py` itself, `pipeline.py`, `mutate.py`, and
`templates/VOICE.md` all stay exactly as they are.
