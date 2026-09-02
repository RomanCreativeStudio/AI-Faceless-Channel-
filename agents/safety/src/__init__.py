"""Safety Reviewer MVP — implements agents/safety/CONTRACT.md.

Stdlib only, no dependencies. Reuses agents/researcher/src's generic,
role-agnostic infrastructure (parsing, ReviewVerdict/ReviewRecord/
ContentItem models, multi-pass gating) — never its fact-check domain
logic. See README.md "Relationship to agents/researcher".
"""
