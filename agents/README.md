# Agents

Contracts for future agents — what each one is allowed and forbidden to
do, and how it hands off to the next pipeline stage. **Specification
only.** No agent code, dependencies, or automation exist yet; nothing in
this directory executes.

Every agent contract here is subordinate to `CONSTITUTION.md`. Where
anything in an agent contract could be read as conflicting with
`CONSTITUTION.md`, the constitution wins — a contract is never grounds to
override it.

## Agents specified so far

- [`researcher/CONTRACT.md`](./researcher/CONTRACT.md) — Research /
  Fact-Check Agent: populates `RESEARCH.md`/`CLAIM.md` during `RESEARCH`,
  and verifies claims during `FACT_CHECK`. First agent in the roadmap.

## Not yet specified

Script drafting, safety review, originality review, production, QA, and
publication all remain fully human-driven (or unspecified for future
agents) until a contract is written and approved here — see `STATE.md`
for what's next.
