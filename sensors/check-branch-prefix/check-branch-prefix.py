#!/usr/bin/env python3
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))

import hook  # noqa: E402

CONVENTIONAL_BRANCH = re.compile(r"^(feat|fix|refactor|chore|docs|test|perf|build|ci|style|revert)/[a-z0-9]+(-[a-z0-9]+)*$")
RELEASE_BRANCH = re.compile(r"^release/(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
LONG_LIVED = ("develop", "main")
EXPLANATION = Path(__file__).with_suffix(".md")


def created_branches(command):
    branches = []
    for invocation in hook.git_invocations(command, "."):
        branch = hook.created_branch(invocation.name, invocation.args)
        if branch:
            branches.append(branch)
    return branches


def is_conventional(name):
    return name in LONG_LIVED or bool(CONVENTIONAL_BRANCH.match(name) or RELEASE_BRANCH.match(name))


def main():
    command = hook.tool_input(hook.read_payload()).get("command") or ""
    for branch in created_branches(command):
        if not is_conventional(branch):
            hook.block(EXPLANATION, received=branch)


if __name__ == "__main__":
    main()
