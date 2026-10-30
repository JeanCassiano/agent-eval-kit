# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

agent-eval-kit: a Python library and CLI to evaluate agents — YAML test cases, N repetitions per case,
deterministic checkers, pass rate / latency / tokens / cost, an A×B Markdown report, OpenTelemetry
export and a local Docker stack (OTel Collector, Prometheus, Tempo, Grafana) for the demo. The agent
under test is swappable: a seeded mock, or any model behind a Chat Completions-compatible API. Backlog
lives in Jira, project `AE`.

## Languages

- `README.md`, `docs/`, code, comments and dashboard text: English.
- Commit messages, PR bodies, Makefile help and sensor messages: Portuguese.
- All data is synthetic. Never add real data to cases, tests, examples or prints.

## Commands

Environment is managed by uv (Python from `.python-version`, dependencies locked in `uv.lock`).

- `make help` — list targets
- `make install` — `uv sync --locked`
- `make test` — `uv run pytest`; single test: `uv run pytest tests/test_package.py::<name>`
- `make lint` / `make format` — ruff check + format (`sensors/` and `tests/test_sensors.py` are excluded:
  they are copied from `indigotech/br-taqtile-observability` and kept diffable with it)
- `make verify` — the CI gates (`.github/workflows/ci.yml`); run it before pushing

When a new target lands (observability stack, demo), list it here.

## Code comments

- Default to no comment. Add one only when the code alone can't tell a reader what it does or why — a non-obvious constraint, a workaround for a tool's behavior, a value that looks wrong but isn't. Never restate what the code says, narrate the change, or explain the history.
- Comments are always in English.
- When editing code that already has comments, don't add new ones to match its density; translate or trim an existing one only if you're already touching it.

## Harness

- `sensors/<name>/<name>.py` are Claude Code hooks (Python stdlib), wired in `.claude/settings.json`; `<name>.md` is the Portuguese message shown when one blocks or advises, and `sensors/_shared/hook.py` holds the payload parsing and shell/git tokenizing. Exit `2` blocks with the message on stderr; advice is JSON `additionalContext` on stdout. `tests/test_sensors.py` covers each sensor and fails when a sensor is unwired, not executable or missing its `.md`.
- They enforce commit and branch conventions, block `--no-verify` and commits/pushes to `main`/`develop`, block `gh pr ready` without a passing audit for the current head, and advise on comment density and on the audit/retro steps.
- PR flow: open as draft → `pr-auditor` agent (skill `adversarial-pr-verification`) audits the head in a cold context → verdict posted as a PR comment starting with `audit: pass <sha>` or `audit: fail <sha>` → `gh pr ready`. Any push invalidates the verdict. Details in `.claude/rules/workflow.rule.md`.
- Skills in `.claude/skills/`: `verification-before-completion` (the floor), `adversarial-pr-verification`, `subagent-driven-development`, `task-retro`. Rules in `.claude/rules/` load when a file matching their `paths` is read; `workflow.rule.md` has none and always loads.
