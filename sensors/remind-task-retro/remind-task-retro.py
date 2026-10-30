#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))

import hook  # noqa: E402

EXPLANATION = Path(__file__).with_suffix(".md")


def readies_pull_request(command):
    calls = hook.gh_invocations(command, ".")
    return any(call.args[:2] == ["pr", "ready"] and "--undo" not in call.args for call in calls)


def main():
    payload = hook.read_payload()
    command = hook.tool_input(payload).get("command") or ""
    if readies_pull_request(command):
        hook.advise(EXPLANATION, event=payload.get("hook_event_name") or "PostToolUse")


if __name__ == "__main__":
    main()
