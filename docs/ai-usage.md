# AI usage log

How AI tools were used to build this project, story by story. Each entry answers the same five
questions, so the reader can tell what was delegated from what was decided and verified by me.

## Template

```markdown
## AE-N — <story title>

- **Tools:** which assistants or models, and for what.
- **Delegated:** what the AI produced.
- **Decided by me:** the choices I made, and the ones I overrode.
- **Where the AI was wrong:** concrete examples, and how each one was caught.
- **How I validated:** commands run, tests, manual checks.
```

## AE-7 — Repository structure, environment and basic CI

> Draft written by the AI. Review it — especially "Decided by me" — before closing the story.

- **Tools:** Claude Code (Claude Opus).
- **Delegated:** scaffolding of `pyproject.toml`, `Makefile`, the CI workflow, the README skeleton and
  this log; copying the development harness (skills, rules and Claude Code hooks in `sensors/`) from
  another repository of mine and adapting it to this project.
- **Decided by me:** uv as the environment manager and Python 3.12; ruff for lint and formatting;
  `main` as the trunk with every change through a draft PR and a cold-context audit; English for the
  README and `docs/`, Portuguese for commits and PRs.
- **Where the AI was wrong:** the first `make lint` failed with 45 issues, all in the hook code copied
  from the other repository. Instead of reformatting it, it was excluded from ruff so both copies stay
  diffable.
- **How I validated:** `make install && make test` in a fresh clone; `make lint` passing, and failing
  with exit ≠ 0 on a file with an unused import; the workflow checked with actionlint.
