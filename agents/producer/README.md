# Producer

Implements [`CONTRACT.md`](./CONTRACT.md) — **not implemented yet.** This
is a Phase 7 contract-only deliverable; there is no `src/` here. The next
roadmap task (Phase 7 Implementation) builds the Producer + Visual
Planner MVP against this contract.

## Responsibility

Turns an `APPROVED` content item's `SCRIPT.md` into a structured
`PRODUCTION.md` + `scenes/scene-<n>.md` set (`templates/PRODUCTION.md`,
`templates/SCENE.md`) — narration decomposed into scenes with estimated
timing and carried-forward claim references. Generates no media itself.

## Relationship to other agents

Runs only after `agents/orchestrator/`'s automated review layer and full
human approval (`CONTENT_ITEM.md` `status = APPROVED`) — see CONTRACT.md
"Preconditions". Hands off to `agents/voice/` (narration → audio) and
`agents/visual-planner/` (scenes → finalized visual requirements), which
each own later `templates/PRODUCTION.md` sections the Producer only
initializes.

See `content/what-if/wi-20260902-black-death-modern-medicine/PRODUCTION.md`
for a golden fixture showing the target shape of this agent's output
(hand-built for schema validation this phase, not agent-generated).
