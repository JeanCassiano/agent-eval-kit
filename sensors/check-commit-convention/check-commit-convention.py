#!/usr/bin/env python3
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))

import hook  # noqa: E402

CONVENTIONAL_SUBJECT = re.compile(r"^(feat|fix|refactor|chore|docs|test|perf|build|ci|style|revert)(\([a-z0-9-]+\))?!?: .+")
SUBJECT_LENGTH_LIMIT = 72
VALUE_FLAGS = set("mFcCt")
EXPLANATION = Path(__file__).with_suffix(".md")


def message_sources(args):
    sources = []
    index = 0
    while index < len(args):
        token = args[index]
        following = args[index + 1] if index + 1 < len(args) else None
        if token == "--":
            break
        if token in ("--message", "--file"):
            sources.append((token[2], following))
            index += 1
        elif token.startswith(("--message=", "--file=")):
            name, value = token[2:].split("=", 1)
            sources.append((name[0], value))
        elif token.startswith("-") and not token.startswith("--"):
            for position, flag in enumerate(token[1:], start=1):
                if flag not in VALUE_FLAGS:
                    continue
                if flag in "mF":
                    attached = token[position + 1 :]
                    sources.append(("m" if flag == "m" else "f", attached or following))
                    if not attached:
                        index += 1
                break
        index += 1
    return sources


def first_line(message):
    for line in (message or "").split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return ""


def commit_subjects(command, cwd):
    subjects = []
    for invocation in hook.git_invocations(command, cwd):
        if invocation.name != "commit":
            continue
        sources = message_sources(invocation.args)
        if not sources:
            continue
        kind, value = sources[0]
        if value is None:
            continue
        if (kind == "m" and "<<" in value) or (kind == "f" and value == "-"):
            message = invocation.heredocs[0] if invocation.heredocs else ""
        elif kind == "f":
            try:
                message = Path(hook.compose_directory(invocation.directory, value)).read_text(encoding="utf-8")
            except OSError:
                continue
        else:
            message = value
        subject = first_line(message)
        if subject:
            subjects.append(subject)
    return subjects


def violation(subject):
    if not CONVENTIONAL_SUBJECT.match(subject):
        return "Não segue o formato esperado."
    if len(subject) > SUBJECT_LENGTH_LIMIT:
        return f"Tem {len(subject)} caracteres, acima dos {SUBJECT_LENGTH_LIMIT} permitidos."
    return ""


def main():
    payload = hook.read_payload()
    command = hook.tool_input(payload).get("command") or ""
    for subject in commit_subjects(command, hook.working_directory(payload)):
        problem = violation(subject)
        if problem:
            hook.block(EXPLANATION, received=subject, violation=problem)


if __name__ == "__main__":
    main()
