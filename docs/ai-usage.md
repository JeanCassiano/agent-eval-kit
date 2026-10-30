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

## AE-8 — YAML case format, loader and validation

> Draft written by the AI. Review it before closing the story.

- **Tools:** Claude Code (Claude Opus).
- **Delegated:** the loader (`agent_eval_kit.cases`), its tests, the three example suites and
  `docs/case-format.md`.
- **Decided by me:** approved the AI's plan: PyYAML's safe loader and plain dataclasses with
  hand-written validation instead of pydantic, so each error names file, case and field. Also decided
  that the AI writes AE-9 and AE-11 too, to finish v1 faster.
- **Where the AI was wrong:** the malformed-YAML test first expected the error on line 5; the broken
  line is line 6, which is what the loader reported. The test expectation was fixed, not the loader.
  The first cold audit found edge cases the loader accepted or leaked: a repeated YAML key silently kept
  the last value, an unreadable file raised a raw exception, hidden folders were scanned, and `null`
  inputs, padded ids and NaN bounds were accepted. Each got a test that failed on the audited loader
  before the fix. The second audit then failed the fix itself: rejecting repeated keys had broken YAML
  merge keys (`<<`), which no test covered. Merge keys now have a test.
- **How I validated:** `make verify`; the error messages quoted in `docs/case-format.md` were produced
  by running the loader on those inputs; on the first commit, six mutations of the validation rules (synthetic flag,
  duplicate ids across files, unknown fields, unknown check type, `min > max`, chained traceback) each
  turned a test red.
