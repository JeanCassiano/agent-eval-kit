#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))

import hook  # noqa: E402

DIRECTORY = Path(__file__).resolve().parent
REMINDER = DIRECTORY / "remind-adversarial-verification.md"
PUSH_REMINDER = DIRECTORY / "remind-adversarial-verification-push.md"
DRAFT_WARNING = (
    "**Este `gh pr create` não tem `--draft`.** Cancele e abra em draft: o PR só sai do draft depois que a "
    "auditoria passa."
)


def pr_create_segments(command):
    for call in hook.gh_invocations(command, "."):
        if call.args[:2] == ["pr", "create"]:
            yield call.args[2:]


def creates_pull_request(command):
    return any(True for _ in pr_create_segments(command))


def is_draft(command):
    return any("--draft" in args or "-d" in args for args in pr_create_segments(command))


def pushed_branches(command, cwd, resolve_branch):
    branches = []
    for invocation, possible in hook.git_invocations_on_branch(command, cwd, resolve_branch):
        if invocation.name != "push":
            continue
        for branch in sorted(possible, key=str):
            for target in hook.push_destinations(invocation.args, lambda: branch):
                found = (target, invocation.directory)
                if target and target not in hook.PROTECTED_BRANCHES and not hook.RELEASE_TAG.match(target):
                    if found not in branches:
                        branches.append(found)
    return branches


def open_pull_request(branch, cwd, run_gh):
    code, output = run_gh(["gh", "pr", "list", "--head", branch, "--state", "open", "--json", "number"], cwd)
    if code != 0:
        return None
    try:
        found = json.loads(output)
    except ValueError:
        return None
    return found[0].get("number") if isinstance(found, list) and found else None


def main():
    payload = hook.read_payload()
    command = hook.tool_input(payload).get("command") or ""
    if creates_pull_request(command):
        hook.advise(REMINDER, draft="" if is_draft(command) else DRAFT_WARNING)
    for branch, directory in pushed_branches(command, hook.working_directory(payload), hook.current_branch):
        number = open_pull_request(branch, directory, hook.run)
        if number:
            hook.advise(PUSH_REMINDER, pr=f"#{number}", branch=branch)


if __name__ == "__main__":
    main()
