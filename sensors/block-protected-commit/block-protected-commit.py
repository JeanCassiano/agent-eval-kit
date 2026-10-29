#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))

import hook  # noqa: E402

EXPLANATION = Path(__file__).with_suffix(".md")
UNKNOWN = "(branch ilegível no repositório indicado por --git-dir/GIT_DIR)"


def action_for(name, args):
    if name == "commit":
        return "git commit --amend" if "--amend" in args else "git commit"
    return None


def violation_for(command, cwd, resolve_branch):
    for invocation, branches in hook.git_invocations_on_branch(command, cwd, resolve_branch):
        action = action_for(invocation.name, invocation.args)
        protected = sorted(UNKNOWN if b is None else b for b in branches if b is None or b in hook.PROTECTED_BRANCHES)
        if action and protected:
            return {"branch": protected[0], "action": action}
    return None


def main():
    payload = hook.read_payload()
    command = hook.tool_input(payload).get("command") or ""
    violation = violation_for(command, hook.working_directory(payload), hook.current_branch)
    if violation:
        hook.block(EXPLANATION, protected=", ".join(hook.PROTECTED_BRANCHES), **violation)


if __name__ == "__main__":
    main()
