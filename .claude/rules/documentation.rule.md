---
paths:
  - "docs/**"
  - "README.md"
  - "CLAUDE.md"
  - ".claude/rules/**"
  - ".claude/skills/**"
  - ".claude/agents/**"
  - "sensors/**/*.md"
---

# Documentation

Applies to every document of the repository — `docs/`, `README.md`, `CLAUDE.md`, the rules, skills and
agents, and the sensors' messages — and to PR bodies. `README.md` and `docs/` are in English: the
repository is a public portfolio. PR bodies, commit messages and sensor messages are in Portuguese.
Agent-facing files follow the language they were written in.

## Permanent owners stand alone

A rule, a skill, `CLAUDE.md` or a `docs/` page must still read correctly once the plan, the PR and the
conversation that produced it are gone. It keeps the behavior, scope, constraints, decisions, known
limits and verification of what it governs. It never needs a plan file, a task list or a personal note
to be understood, and it never links to one.

When a change settles a contract, update its permanent owner in the same diff.

## Codify the recurring correction

The second time you fix the same drift (2+ files or 2+ sessions), capture it in the same session, in
the one owner that the ladder in `.claude/rules/guidance.rule.md` picks — never two. Per-user memory is
not a target: it never reaches the next agent.

## Write the doc against the final code

Re-read every line you touched against the final diff before closing.

- Cite the symbol or the config name, not the line number: `metrics.percentile`, `check.type`.
- A published count is a measurement: re-run the command or the query at the final head and paste its
  answer, never a recollection. A number measured with a real model names the model and the date;
  a number from the mock names the seed.
- Never state a guarantee the code does not enforce. Grep the owner you name; if a guard covers only
  part of the claim, narrow the claim.
- **Widening a sentence re-opens its measurement.** Removing a qualifier or an exception turns a true
  statement into a claim about everything it now covers. Re-check at the new scope.
