#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))

import hook  # noqa: E402

AUDIT_LINE = re.compile(r"^\s*audit: (pass|fail) ([0-9a-f]{40})\b", re.MULTILINE)
GH_OPTIONS_WITH_VALUE = {"-R", "--repo"}
EXPLANATION = Path(__file__).with_suffix(".md")


def ready_requests(command, cwd):
    return [(selector, directory) for selector, directory, _ in ready_calls(command, cwd)]


def ready_calls(command, cwd):
    requests = []
    for call in hook.gh_invocations(command, cwd):
        args = call.args
        if args[:2] != ["pr", "ready"]:
            continue
        rest = args[2:]
        if "--undo" in rest:
            continue
        selector, repo, index = [], [], 0
        while index < len(rest):
            token = rest[index]
            if token in GH_OPTIONS_WITH_VALUE and index + 1 < len(rest):
                repo = ["-R", rest[index + 1]]
                index += 1
            elif token.startswith("--repo="):
                repo = ["-R", token.split("=", 1)[1]]
            elif not token.startswith("-") and not selector:
                selector = [token]
            index += 1
        requests.append((selector + repo, call.directory, call.indirect))
    return requests


def audit_status(head, bodies):
    status = None
    for body in bodies:
        for verdict, sha in AUDIT_LINE.findall(body or ""):
            if head.lower() == sha:
                status = verdict
    return status


def read_pull_request(selector, directory, run_gh):
    code, output = run_gh(["gh", "pr", "view", *selector, "--json", "headRefOid,comments"], directory)
    if code != 0 and "headRefOid" in output:
        code, output = run_gh(["gh", "pr", "view", *selector, "--json", "commits,comments"], directory)
    if code != 0:
        raise ValueError((output or "").strip() or "saída vazia")
    data = json.loads(output)
    head = data.get("headRefOid") or data["commits"][-1]["oid"]
    return head, [comment.get("body", "") for comment in data.get("comments") or []]


def decide(command, cwd, run_gh):
    for selector, directory, indirect in ready_calls(command, cwd):
        pr = selector[0] if selector and not selector[0].startswith("-") else "(branch atual)"
        if indirect:
            reason = "Os argumentos do `gh pr ready` vêm do xargs, então o sensor não sabe qual PR é. Rode `gh pr ready <n>` direto."
            return {"pr": pr, "head": "desconhecido", "reason": reason}
        try:
            head, bodies = read_pull_request(selector, directory, run_gh)
        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as error:
            return {"pr": pr, "head": "desconhecido", "reason": f"Não consegui ler o PR com o gh: {error}"}
        status = audit_status(head, bodies)
        if status != "pass":
            reason = (
                "O último veredito para este head é `audit: fail`."
                if status == "fail"
                else "O PR não tem `audit: pass` para este head."
            )
            return {"pr": pr, "head": head, "reason": reason}
    return None


def main():
    payload = hook.read_payload()
    command = hook.tool_input(payload).get("command") or ""
    refusal = decide(command, hook.working_directory(payload), hook.run)
    if refusal:
        hook.block(EXPLANATION, **refusal)


if __name__ == "__main__":
    main()
