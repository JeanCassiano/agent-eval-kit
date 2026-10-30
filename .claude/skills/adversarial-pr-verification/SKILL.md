---
name: adversarial-pr-verification
description: "Adversarially verify a PR of this repository — open or merged — or a local commit range with no PR. Re-derive ground truth (`make verify` and the gates the change touches) instead of trusting the description, trace every claim to actual code, mutate the code to prove the tests guard it, and report findings with a verified / false / coverage-gap taxonomy against a pinned head SHA. Start as soon as a draft PR exists and again after every push that moves its head, without waiting for CI. Use when asked to verify, audit, double-check or QA a PR, a branch or a range of commits, or before `gh pr ready`."
context: fork
agent: pr-auditor
---

# Adversarial PR Verification

> An auditor's process, not a reviewer's. The PR body is a set of **claims to be disproven**, not a
> description to be summarized. Default to disbelief: a claim is unverified until you have re-derived
> it from the code, or from a command you ran yourself.

What this repository checks beyond the generic process — case format, checkers, metrics, the A×B
report, the mock and the model adapter, OpenTelemetry, the compose and the dashboard, synthetic data,
comments and Portuguese claims — is in
[references/adversarial-pr-verification-agent-eval.md](references/adversarial-pr-verification-agent-eval.md).
Read it before step 2.

List the changed paths with the path a rename left included:
`git diff --name-only --no-renames <base>...HEAD`, or for a PR
`gh api 'repos/{owner}/{repo}/pulls/<n>/files' --paginate --jq '.[] | .filename, (.previous_filename // empty)'`.
`gh pr view <n> --json files` drops that path and stops at 100 files.

## When to run

- **As soon as a draft PR exists**, without waiting for CI: audit and CI are independent gates against
  the same head.
- **Again on every push that moves the head.** A verdict names one SHA; any later push invalidates it,
  and the author rewrites the body against the new head before the re-audit starts.
- Before relying on a merged change you did not write, and after a subagent reports a batch of work done.
- `remind-adversarial-verification` nudges at `gh pr create` and at a push to a branch with an open PR.
  It never blocks. `require-audit-before-ready` does block `gh pr ready` until a passing verdict names
  the current head.

## Independence

The audit always runs in a cold context: a fresh `pr-auditor` subagent that receives only the PR or the
range, its head and this skill, or a separate session — never the context that wrote the change. The
fast path and the prose-only path below make it lighter, not optional. When no fresh context can be
started, the PR waits; the author's own review does not stand in for it.

The auditor keeps the branch read-only, writes its verdict to a file outside the repository (or under
the ignored `.tmp/`) and returns the path. The author publishes it (see "Deliver a verdict").

## Without a pull request

| PR flow | Local flow |
| --- | --- |
| `gh pr view <n> --json body` | The commit messages: `git log --format='%B' <base>..HEAD` |
| `gh api 'repos/{owner}/{repo}/pulls/<n>/files' --paginate` | `git diff --name-only --no-renames <base>...HEAD` |
| Verdict in a PR comment | A verdict file, or the report in the conversation |

Without a PR, CI does not run — its share of the ground truth is yours — and nothing pins the commit:
record `git rev-parse HEAD` in the report.

## Mindset

1. **Trust nothing in the PR body.** "testes ✅", "p95 = 95,05", "não muda o relatório" are claims.
2. **Ground truth beats CI.** Re-run the checks locally. CI can be stale, skipped or bypassed.
3. **Trace every claim to a line of code.** Open the file, confirm the change exists and actually
   causes what is claimed. Confirm every helper, checker, panel or variable the diff references exists.
4. **Tests must be real and non-vacuous.** A test that asserts nothing, or only re-asserts its own
   fixture, is not coverage. Read the assertions.
5. **Honesty is itself a finding.** A PR that says "parcial" and is telling the truth passes that
   check; one that quietly drops scope fails it.

## Steps

### Small-PR fast path

A PR qualifies when it changes at most **eight** files for one focused claim and touches no metric
calculation, no API-key handling in the model adapter and no OTel attribute that could carry input or
output. The fast path shortens orchestration, not evidence:

1. Read the body, the diff, the changed files and the owning test in one pass; write the complete claim checklist before any gate.
2. Declare the bounded gate list up front — `make verify` plus what the reference names for the touched surface.
3. Return the taxonomy right after the last planned gate.

### Prose-only path

A PR qualifies when every changed file is Markdown guidance — a skill, a rule, `CLAUDE.md`, `README.md`,
`docs/`, a sensor's `.md` message — or a test file alone. A change to what a sensor, a script, the
Makefile, a workflow or `.claude/settings.json` **does** takes the full path however small: a wrong
sensor disarms a gate in silence.

1. Every relative link and every path in the changed files resolves.
2. Read each changed document against the code it describes: a command it names exists and does what
   it says; a claimed guarantee is enforced where the text says it is.
3. What was removed had another owner. A deleted passage that was the only place a rule lived is a
   finding. Grep the concept, not the wording.

### 1 · Extract the claims

```bash
gh pr view <n> --json number,title,state,mergedAt,headRefName,additions,deletions,body
gh pr view <n> --json commits   # the head is .commits[-1].oid; older gh has no headRefOid field
```

Turn the body into a checklist: every "faz X", every "✅", every "+ teste", every count, every print and
every "parcial/bloqueado". The body is in Portuguese; a claim in Portuguese is still a claim.

### 2 · Re-derive ground truth

Run `make verify` yourself at the audited head, then the surface-specific gates of the reference. You
are auditing, not fixing. A command exiting `0` in the background does not mean the tests passed: read
the pass/fail line (`Ran N tests` / `OK`).

### 3 · Trace each claim to the code

For every checklist line, open the diff (`git show <commit> -- <file>`) and the current file on the
base. Confirm the change exists, does what is claimed, and that every referenced symbol exists. For
"added a test", read the assertions and compare with the nearest existing test: if setup and action
match, the assertion should have expanded that owner instead.

### 4 · Comment and test-quality gates

Review the **diff**, not only the final tree. Comments (`.claude/rules/code-comments.rule.md`):

- **Noise** — step narration, section banners, restating the next line. More than one comment line per
  30 added code lines is already a lot (`require-comment-budget` advises at that ratio).
- **Language** — every added comment is in English.
- **Keep-bar** — an added comment says something the code and the tests do not. History ("movido de",
  "antes era") and tracking tokens (PR numbers, ticket ids) never survive.
- **The lie check** — every comment on touched code is still true after the change.

Tests: non-vacuous, no duplicate of an existing input-to-outcome pair, no assertion left for behavior
the diff removed, no real external service and no wall-clock dependence.

### 5 · Mutation testing

Reading assertions tells you a test exists. Inverting the behavior tells you it *guards*. For every
claim, change the code so the claim becomes false and check that a test goes red:

| Claim shape | The mutation |
| --- | --- |
| "`numeric_range` is inclusive" | change `<=` to `<` |
| "timeouts count as failures" | count a timeout as a pass |
| "the mock is deterministic" | seed it from the clock |
| "the panel filters by `agent_version`" | drop the filter from the panel query |
| "the sensor blocks X" | invert the sensor's decision |

**A mutation that leaves every test green is a finding.** Report the count both ways — "N mutations; M
turned a test red; the other N−M are the findings". Mutate in a disposable copy (see below).

### 6 · Does any rule still describe the code?

For every `.claude/rules/` file, `CLAUDE.md` section, skill or README section that matches a changed
path, ask whether the change made it misdescribe what it governs. A rule that quietly became wrong is a
finding.

### 7 · Classify and report

| Class | Meaning |
| --- | --- |
| **Verified** | Re-derived from code or from a command you ran. Cite the evidence. |
| **False claim** | The claim contradicts the code or a failing command. Cite the command and its output. A contradiction measured on a stand-in (a mock, a fixture without git) is a coverage gap until it reproduces on the real thing. |
| **Coverage gap** | The claim is true but its evidence is insufficient, or you could neither confirm nor disprove it. |
| **Inconsistency** | The change drifts from a rule or from how a sibling solves the same thing. |
| **Process note** | A bypassed floor, stale CI, merge-order risk. |
| **Pre-existing** | Not introduced here — prove it with `git show <commit>~1`. |

An unresolved false claim or blocking finding fails the audit. **Report a finding as its class, with
every instance**: enumerate the whole class (the term, the pattern, the symbol), and list the PR body as
an instance whenever it states the defect. End with a one-line bottom line: did you try to break it and
fail, or did something not hold up?

## Working without endangering the tree

- **Audit the exact head in a clean, dedicated worktree.** Never switch another session's checkout.
- **Keep the audited branch read-only.** Findings go to the author for a new revision.
- **Mutate in a disposable copy.** Never revert with git: `git checkout -- <path>` silently discards
  unstaged work. Copy every file you mutate to a scratch directory outside the repository and restore
  by copying back.
- Finish by proving you left nothing behind: `git status --short` matches what you saw at the start.

## Deliver a verdict, or you did not audit

Run to completion and return the taxonomy **before** the PR is marked ready. Out of room: report what
you verified and what you did not reach.

**Publishing.** The verdict file's **first line** is exactly `audit: pass <sha>` or `audit: fail <sha>`,
with the full 40-character head SHA the audit ran against (`require-audit-before-ready` rejects a
shortened SHA). Read the PR's head adjacent to the publish call, not earlier in the turn. Write the
verdict in Portuguese: it is read by humans on the PR. Publish with:

```bash
gh pr view <n> --json commits --jq '.commits[-1].oid'   # must equal the audited SHA
gh pr comment <n> --body-file <verdict-file>
```

Then, on a pass, `gh pr ready <n>` in a separate call: `require-audit-before-ready` re-reads the PR
before the command runs, so a chained `gh pr comment … && gh pr ready` is blocked. It lets the ready
through only when the last verdict for the current head is a pass. Never push an audit-only change to the
branch — it creates a new head and invalidates the verdict.

## Anti-patterns

- Summarizing the PR body back as if it were verification.
- Reporting "tests pass" from a run you never read to completion.
- Trusting a green CI badge instead of re-running locally.
- Flagging a pre-existing issue as a regression without checking `<commit>~1`.
- A flat findings list with no taxonomy — the taxonomy is the value.
- Reporting one instance of a defect that has siblings.
- Reporting that tests exist without mutating anything.
- Reverting a mutation with git instead of restoring the copy you took.
- Relabeling an old verdict for a new head.
