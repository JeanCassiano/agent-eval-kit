# Development Workflow

How work moves from a branch to `main` in this repository. The commands are in `CLAUDE.md`; the
verification floor is skill `verification-before-completion` (`make verify`).

## Before changing anything

1. `git rev-parse --abbrev-ref HEAD && git status -sb`. Unrelated work in the tree means isolate first,
   in a separate worktree; never `checkout`, `reset --hard`, `clean` or `stash` over changes that are
   not yours.
2. **Check the existing pattern** — grep for a sibling that already does what you are about to do.
3. **Plan first** for a change that spans several files: get the plan approved before writing code.
4. **Test first** — search the existing test bodies, pick the owner, and make it fail before the change.

## Branches

- `main` is the trunk and the default branch. Every change reaches it through a PR; nobody commits or
  pushes to it directly (`block-protected-commit`, `block-protected-push`). The sensors protect
  `develop` too, though this repository does not use it.
- A task branch starts from `origin/main` and carries the prefix of its commit type
  (`check-branch-prefix`): `feat/`, `fix/`, `refactor/`, `chore/`, `docs/`, `test/`, `ci/`, `build/`,
  `perf/`, `style/`, `revert/`. The sensor also accepts `release/X.Y.Z` and `chore/back-merge-vX-Y-Z`
  for releases.
- Commits follow Conventional Commits with the subject in Portuguese, at most 72 characters
  (`check-commit-convention`). Stage explicit paths, never `git add -A`.
- Agents never bypass a hook: `--no-verify` is denied in `.claude/settings.json` and blocked by
  `block-no-verify`.

## Delivering a change

1. `make verify` green, and the surface checks of `verification-before-completion` (the seed-fixed numbers for a metric,
   `VERIFY_E2E=1` for the stack, a print for a dashboard).
2. Push the branch and open the PR **as a draft** (`gh pr create --draft`), filling
   `.github/pull_request_template.md`.
3. Audit it in a **cold context**: dispatch the `pr-auditor` agent (skill
   `adversarial-pr-verification`) with the PR number and the head SHA. It must not be the context that
   wrote the change.
4. Publish the verdict as a PR comment whose first line is `audit: pass <sha>` or `audit: fail <sha>`
   (`gh pr comment <n> --body-file <file>`), after re-reading the PR's `headRefOid`.
5. On a fail: fix, push, rewrite the body against the new head, and go back to step 3. Any push
   invalidates the previous verdict.
6. On a pass and with CI green: `gh pr ready <n>`. `require-audit-before-ready` blocks it unless the
   last verdict for the current head is a pass; `remind-task-retro` then suggests skill `task-retro`.
7. The user merges. Never merge a PR yourself.

## Verifying a fix

Re-derive ground truth from the running system, not from the assertion. Reproduce the bug first —
with a seed-fixed run or the demo (`make demo`) — then fix and watch it pass the same way. Never report "fixed" from a passing test or the diff alone;
report the behavior you observed and how.

## The command that exits 0 and measures something else

Before a count or a "none found" becomes a verdict, confirm what the command ran over: an emptiness
needs a control value you know exists, a count needs the number of things inspected.

- `2>/dev/null` on a probe whose emptiness you will interpret makes a failed command and a true
  negative identical. Let stderr through.
- A filter that keeps only the success lines drops the error line, and the pipe's exit code is the
  filter's. Read `${PIPESTATUS[0]}` or run it unfiltered.
- The shell cwd persists across tool calls: use absolute paths or `git -C <path>`.
- A real model call answers for that model on that day; name both.

## Implementation style

- Prefer editing an existing file over creating one.
- Implement, don't suggest — make the change unless options were requested.
- No placeholder code.
- Minimal comments — `.claude/rules/code-comments.rule.md`.
- Delegate multi-file exploration to a subagent and keep the summary (skill
  `subagent-driven-development`).
