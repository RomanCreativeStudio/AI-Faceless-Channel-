"""Originality Reviewer MVP — implements agents/originality/CONTRACT.md.

Stdlib only, no dependencies. Reuses agents/researcher/src's generic,
role-agnostic infrastructure (parsing, ReviewVerdict/ReviewRecord/
ContentItem/Classification models, load_claims/load_research/
load_reviews, multi-pass gating, append_notes_log) — never Researcher's
fact-check domain logic, and nothing from agents/safety at all (siblings,
not dependents). See README.md "Relationship to agents/researcher and
agents/safety".
"""
