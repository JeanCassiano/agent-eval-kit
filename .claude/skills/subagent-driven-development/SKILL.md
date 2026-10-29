---
name: subagent-driven-development
description: "When to delegate to subagents and when to work serially in this repository: delegating multi-file exploration to keep the orchestrator's context lean, the implementer + validator loop for a planned change, parallel write work in isolated worktrees, and the cold-context audit per PR. Use when planning a delegation, dispatching implementation or review, or deciding whether a task is worth splitting."
---

# Subagent-Driven Development

> When to spawn subagents, and when to just do the work. Every cold start costs context and wall-clock
> time — choose deliberately. The parent owns scope, synthesis, integration and delivery; a worker owns
> one bounded result.

## Authorization

- **Read-only exploration** is the parent's call: delegating a survey keeps its reads out of the
  orchestrator.
- **The PR's cold-context audit** is part of every delivery and needs no further authorization: a
  fresh `pr-auditor` audits the head and returns its verdict file; the parent publishes it
  (`adversarial-pr-verification`).
- **Write work, and any worker that pushes, comments or opens a PR,** needs the user's authorization
  for that delegation. A worker never infers permission for external side effects from being delegated
  to. Nobody but the user merges.

## The implementer + validator loop

The default shape for a change with an approved plan:

1. **Implementer** — one worker, in its own worktree and branch, writes the tests first, then the code,
   runs `make verify` and returns its report. It does not commit, push or open the PR unless the brief
   says so.
2. **Validator** — a separate worker with **no inherited implementation context** runs `make verify`
   itself and reviews the diff against the plan and the rules. It never edits the branch.
3. **Parent** — reads both reports and the actual diff, sends the findings back to the implementer for
   a new round, and stops after at most three rounds, reporting what is still open.
4. Then the delivery flow of `.claude/rules/workflow.rule.md`: draft PR → `pr-auditor` → verdict
   comment → `gh pr ready`.

## Fan-out triggers

- More than three independent read-only investigations are needed before an implementation choice.
- Any multi-file exploration beyond a one- or two-file lookup — delegate the reads, keep the summary.
- Independent changes that can land as separate PRs, each in its own worktree.

## Serial triggers

- A single-file change, or work under three tool calls.
- Sequential dependencies: step B's input is step A's output.
- Shared state: `deploy/docker-compose.yml`, the dashboard JSON, `.claude/settings.json`, the
  `Makefile`, `pyproject.toml` and the seed-fixed end-to-end numbers. One owner keeps them.

## Brief before dispatch

Every brief is self-contained — the worker cannot see this conversation:

- **Goal and acceptance**, observable.
- **Starting points** — exact paths, or the symbols to grep.
- **What you already know**, so the worker does not re-derive it.
- **Boundaries** — worktree path and branch, owned paths, read-only or write, prohibited side effects
  (commit, push, PR, the main checkout).
- **Test budget** — search existing test bodies first; extend the nearest owner when setup and action
  match; no count quota.
- **Expected return** — its shape and length, and what it must include: changed files, checks run with
  results, checks not run and why, inferences labeled as such.

## Keep parallel branches independent

- One worktree per worker; never switch or clean another session's checkout. Map branch to worktree
  with `git worktree list`.
- Keep author and reviewer disjoint per PR: a finding goes back to that PR's author.
- Freeze a base while it serves open PRs; moving it invalidates the audited heads.

## Require a reviewable handoff

Review the actual diff and the owning assertions, not a success summary. A worker's green `make verify`
is evidence for its own tree only: run it again on the integrated revision.

## Cost discipline

- A broad "be very thorough" survey can take longer than the targeted reads by hand. Scope the question.
- **Wait or cancel — never both.** Reading the same files yourself while a worker does wastes its budget.
- Continue an existing worker when its context still applies instead of spawning a new one.
- At most three workers per turn unless there is a genuine parallel-work reason.

## Anti-patterns

- Spawning for trivially fast work.
- Delegating synthesis — the parent decides; workers gather.
- Fan-out for theater.
- Editing a PR you audited — it destroys the independence you attested.
