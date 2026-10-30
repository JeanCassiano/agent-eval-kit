---
name: task-retro
description: End-of-task retrospective for this repository. Separates avoidable rework from necessary checks, tells a recall failure (a rule or memory already held the fix) from a new gotcha, ranks the biggest sinks, and — the point — names the exact owner to edit (a rule, CLAUDE.md, a skill, a test) or the sensor to add so the same class of waste cannot recur. Runs automatically once a PR is ready for review and on request — "retro", "/task-retro", "what should I improve", "how do we cut tokens next time". Not for non-PR, read-only or advisory work unless asked. Always the complete format, never a preview.
---

# Task Retro — where the next similar task gets cheaper

Produce an honest, non-defensive retrospective of the task that just finished. The deliverable is not
"you did badly" — it is a prioritized **change list** against the knowledge base and the harness, so the
next similar task spends fewer turns. It closes a delivery; it never substitutes for
`verification-before-completion` or `adversarial-pr-verification`, and it never gates them.

Two failure modes this skill exists to separate, because their fix differs:

- **Knew and didn't apply** — an instruction already held the fix; the gap was consulting it before a known-gotcha step. Cheapest win, no new document.
- **Didn't know** — a genuinely new gotcha. Write it down so next time it is a "knew".

## When to run

- **Automatically once the PR is ready for review** — after verification, the revision-bound audit and
  in-scope cleanup. Pending PR-time CI never delays it. `remind-task-retro` is the non-blocking backstop
  for a direct `gh pr ready`; the obligation stands when it is silenced.
- **On request**, including for a task that already ended.
- **Not automatically** for non-PR, read-only or advisory work, or for implementation that stops before
  a PR is ready.

## Completeness

Every trigger gets the full method and the full output below. There is no brief mode, teaser or "I can
give the complete version if you want"; default response concision does not override this. A progress
note mentioning one emerging lesson is not the retrospective. If an earlier response gave only a
partial one, say so and replace it with the complete retrospective right away.

## Method

### 1 · Bound the review

Name what is reviewed — the task, the PR and its head, or a time interval — and what history is
missing. A shortened transcript or a summary cannot support exact counts.

### 2 · Segment into phases

`understand → design → implement → verify → deliver`. Count tool-use turns per phase from the
transcript, and count failed or retried calls explicitly. **When the history does not hold them, omit
the numbers and say what is unknown** — never estimate a count, a token total or a saving.

### 3 · Classify every tool-use turn

- **Productive** — advanced the goal.
- **Necessary caution** — a justified safety or environment check: checking ownership before touching a shared worktree, confirming a real model call will not spend more than expected, keeping an API key out of a log or a print. **This is the job, never waste. Do not count it.**
- **Avoidable rework** — a retry of the same command, a discovery loop, or a fix for a preventable error. **Only this is waste.** A failed test that exposed a real regression is useful evidence, not waste.

### 4 · Tag each avoidable rework with a root cause

- **(a) Recall failure** — a rule, `CLAUDE.md`, a skill or a memory already documented the fix, and it was not applied. Cite the exact file, quote what it said, and show why it applied.
- **(b) New gotcha** — describe the evidence, without claiming nothing anywhere documented it.
- **(c) Harness or environment** — a harness quirk, a sensor's behavior, a concurrency flake. Preserve the failure; do not invent its cause.

### 5 · Rank the avoidable rework

By observed recurrence, turns spent and confidence. Include counts only when step 2 could measure
them. If no recurring, actionable lesson is supported, say so without creating rules.

### 6 · Map each ranked item to its owner

Walk the ladder in `.claude/rules/guidance.rule.md` — the first step that fits wins:

| Finding shape | Fix goes in |
| --- | --- |
| A mistake interceptable at one point in time, by an exit code | a **sensor** (`sensors/<name>/`), wired in `.claude/settings.json`, with its cases in `tests/test_sensors.py` |
| An executable quality defect in the repository's tooling | its owner in `scripts/` or the `Makefile`, with a failing, then restored, test in `tests/` |
| A repeatable pattern that any path matching a glob must follow | the closest **rule** in `.claude/rules/` (a new file only when none owns the topic) |
| Needed in every session — a command, the architecture map, *when* to act | **`CLAUDE.md`** |
| A repeatable multi-step procedure | a **skill** in `.claude/skills/` — or a reference inside one |
| How the library, the demo or the dashboard behaves, for humans | `docs/` or the `README.md`, in English |
| A gotcha local to one machine or account, not to the repository | a **memory file** plus its `MEMORY.md` pointer — never a repo-general lesson, which per-user memory never delivers to the next agent |

Placement rules:

- **A recall failure usually needs no new document.** The fix is "apply the existing one". Propose an edit only when it was hard to *find* — then sharpen its description line instead of duplicating it.
- **Prefer editing an existing owner** over creating one.
- **A harness finding names the sensor concretely**: which event (`PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`), what it matches, and what it does (block, rewrite, warn). Prefer a rewrite or a nudge over a block when the correct action is deterministic, and never invent an event or a command the repository does not have.
- For each change, name how to check the improvement worked. An already-fixed finding cites the fix and its owning check; it is not new work.

## Output

```
## Retro — <task> (<PR>, head <sha>)

Reviewed: <bounds>. Unknown: <missing history, or "none">.
Phases (tool-turns): understand N · design N · implement N · verify N · deliver N   ← omit when unmeasurable
Avoidable rework: ~X of ~T turns — of which Z were recall failures.

### Top waste (ranked)
| # | What | Evidence | Root | Owner and fix | How to check it |
|---|---|---|---|---|---|
| 1 | … | … | recall failure | apply `<file>` (already said "<quote>"); sharpen its description | … |
| 2 | … | … | new gotcha | rule `<file>` — <one line> | … |
| 3 | … | … | harness | sensor: PreToolUse(Bash) rewriting `<pattern>` | … |

### Change list
- [ ] <owner>: `<file>` — <one line>

Want me to make these edits now?
```

## Delivery

- **PR delivery → a PR comment.** Save the complete output under the ignored `.tmp/task-retro/<pr>/<head-sha>.md`, post that exact file with `gh pr comment <pr> --body-file <file>` and confirm the returned URL. The record outlives the session, and a comment does not move the audited head. A later push makes it historical: the new head gets its own.
- **Outside a delivery → the answer in chat**, with the same completeness.
- Close by offering to make the edits. A retro that only lists is unfinished.

The retro does not itself authorize unrelated edits, personal-memory changes, new PRs or external
messages. Apply a fix that already belongs to the authorized scope; record the rest in the change list.
Never reopen a delivered PR to add lessons or edit its audited title or body: a repo-general lesson ships
as its own small change.

## Hard rules

- **Never count necessary caution as waste.** Prudence on a shared checkout is the job.
- **Always separate "didn't know" from "knew and didn't apply".** The fixes are opposites.
- **Every ranked finding names a concrete owner.** No orphan complaints.
- **Numbers come from the transcript or not at all.**
- **Keep secrets and real customer data out** of the retro and its comment.
