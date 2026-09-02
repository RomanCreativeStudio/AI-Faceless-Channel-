"""Unified Automated Review Orchestrator — implements
agents/orchestrator/CONTRACT.md.

Stdlib only, no dependencies. This is coordination code only: it invokes
agents/researcher, agents/safety, and agents/originality's existing
pipeline entry points in order and aggregates their already-structured
results. It contains no evidence/signal evaluation of its own, no
mutate.py, and no field whitelist of its own — every write that happens
under --apply is performed by the individual agent being coordinated,
through that agent's own existing, already-tested write path.
"""
