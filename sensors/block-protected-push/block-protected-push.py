#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))

import hook  # noqa: E402

EXPLANATION = Path(__file__).with_suffix(".md")


def protected_target(command, cwd, resolve_branch):
    for invocation, branches in hook.git_invocations_on_branch(command, cwd, resolve_branch):
        if invocation.name != "push":
            continue
        if invocation.indirect:
            return "(argumentos vindos do xargs)"
        for branch in branches:
            for target in hook.push_destinations(invocation.args, lambda: branch):
                if target is None:
                    return "(branch ilegível no repositório indicado por --git-dir/GIT_DIR)"
                if target in hook.PROTECTED_BRANCHES:
                    return target
    return None


def main():
    payload = hook.read_payload()
    command = hook.tool_input(payload).get("command") or ""
    target = protected_target(command, hook.working_directory(payload), hook.current_branch)
    if target:
        hook.block(EXPLANATION, branch=target, protected=", ".join(hook.PROTECTED_BRANCHES))


if __name__ == "__main__":
    main()
