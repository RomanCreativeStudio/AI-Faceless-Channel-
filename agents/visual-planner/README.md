# Visual Planner

Implements [`CONTRACT.md`](./CONTRACT.md) — **not implemented yet.** This
is a Phase 7 contract-only deliverable; there is no `src/` here. The next
roadmap task (Phase 7 Implementation) builds this agent (alongside the
Producer) as an MVP.

## Responsibility

Finalizes each scene's visual requirement and specifies the
corresponding `templates/ASSET.md` record — what's needed, generated vs.
retrieved, and (the critical part) whether it will be
`AUTHENTIC_HISTORICAL_MEDIA` or `GENERATED_RECONSTRUCTION`. Never
generates or retrieves the asset itself, never presents generated media
as authentic, never invents historical evidence beyond what the content
item's claims establish.

## Relationship to other agents

Runs after `agents/voice/` completes voiceover generation
(`Production status = VISUAL_PLANNING`) and hands off to the still-unbuilt
`ASSET_COLLECTION` stage — see `templates/PRODUCTION.md`'s `Production
status` sequence.
