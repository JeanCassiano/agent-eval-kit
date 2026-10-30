---
paths:
  - "src/**"
  - "deploy/**"
  - "scripts/**"
  - "tests/**"
  - "sensors/**"
  - "Makefile"
---

# Code Comments

Applies to every comment in code and config: Python, the compose and the collector, Prometheus and
Grafana configs, shell and the Makefile. The bar itself is in CLAUDE.md,
"Code comments"; this rule is the catalog that applies it. A comment is a **signpost** — the non-obvious
*why* behind the line — never a **memoir** of the change that produced it. Git owns provenance, the
test owns behavior.

## Write to the bar, don't only clean to it

New or edited code starts at **zero** added comment lines. Roughly one comment line per 30 added code
lines is already a smell that says re-run the keep-bar on each one; `require-comment-budget` advises at
that ratio after every `Edit`/`Write` of a `.yml`, `.yaml`, `.tf`, `.sh` or `.py` file under `src/`,
`deploy/`, `scripts/`, `tests/` or `sensors/`, and also when an added comment looks Portuguese. It never
blocks; the Makefile is not scanned. Before finishing an edit, re-read every comment you added — each one clears the bar or is
deleted in that same edit.

## The noise catalog

None of these clears the bar:

| Shape | Example |
| --- | --- |
| Step narration | `# 1. render the env` · `# then restart the stack` |
| Section banner | `# ---- helpers ----` · `# Panels` |
| Restating the next line | `# load the cases` above `cases = load_cases(path)` |
| Trailing echo | `retries=$((retries + 1))  # increment retries` |
| Declaration narration | `# defaults to 30` on `--days 30` |
| Memoir | `# moved here from runner.py` · `# no longer uses numpy` · `# was 3 repeats before` |
| Tracking token | `# PR #41` · `# item 13` · a ticket id |
| A query re-told in prose | a block above a PromQL query describing each function |

## What survives

- **A non-obvious why**, in one clause: a workaround for a tool ("the provider omits `usage`
  when streaming"), an ordering constraint, a value that looks wrong but is not.
- **A pointer** to where the related thing lives (a script, a rule, a doc section), when the reader
  would not find it otherwise.
- **Directives**: `# noqa`, `# shellcheck disable=…` (with its reason), `# type: ignore`. They change a
  tool's behavior, so they are not prose.
- `TODO` naming open work.

## Language

Comments are in **English**, always, even though commit messages, PR bodies, Makefile help and the
`.md` messages of the sensors are Portuguese. Grafana panel titles and descriptions inside the
dashboard JSON are UI text, not comments; they are in English like the README.

## Coherence

Every comment you write or keep must be true of the code it sits on, now. A comment next to changed
code that still describes the old behavior is a lie the next reader trusts: fix it or delete it. When a
comment claims a behavior the code contradicts, suspect the code first and surface it.

## Scope

| Surface | Applies? |
| --- | --- |
| `src/`, `deploy/`, `scripts/`, `sensors/`, `Makefile` | Yes, in full. |
| `tests/` | Yes, but a test name or a scenario description is legitimate. |
| `docs/`, `*.md`, `.claude/**` | No — `.claude/rules/documentation.rule.md` covers documents. |
