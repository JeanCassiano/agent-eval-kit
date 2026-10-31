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
  a number from the mock names the seed. A count that the next push can change (tests passed,
  mutations run) lives only in the PR body; a permanent doc describes the check without the number.
- Never state a guarantee the code does not enforce. Grep the owner you name; if a guard covers only
  part of the claim, narrow the claim.
- **A universal claim is a claim about a population.** A sentence with *every*, *each*, *all*, *never*,
  *always*, *only* or *exactly* is true only if it holds for every member. List the members with a
  command (`grep` the call sites, the code paths, the examples the sentence cites) and write "N of N"
  in the trace. Walk the path the reader uses: a claim about a YAML suite is checked by loading one,
  not by calling the checker with a Python value. When an audit finding names one member, sweep the
  whole population before the push; the finding is an example of the class, not its list.
- **Docs written ahead of the code.** A component that does not exist yet (a gate, a target, the mock,
  a report) appears only as intent ("is meant to", "once it lands"), never in the present tense. Before
  saying a kind of claim was removed, grep the whole file for the concept, not only the sentence you
  fixed.
- **Widening a sentence re-opens its measurement.** Removing a qualifier or an exception turns a true
  statement into a claim about everything it now covers. Re-check at the new scope.
