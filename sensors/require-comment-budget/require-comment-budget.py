#!/usr/bin/env python3
import os
import re
import sys
from collections import Counter, namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))

import hook  # noqa: E402

SCOPED_DIRECTORIES = ("src", "deploy", "scripts", "tests", "sensors")
SCOPED_SUFFIXES = (".yml", ".yaml", ".tf", ".sh", ".py")
CODE_LINES_PER_COMMENT = 30
DIRECTIVE = re.compile(
    r"^(#!|#\s*(noqa|type:|pragma|pylint:|fmt:|shellcheck\s|tflint-ignore|yaml-language-server|-\*-))"
)
PORTUGUESE = re.compile(r"[ãõçáéíóúâêôàÃÕÇÁÉÍÓÚÂÊÔÀ]")
EXPLANATION = Path(__file__).with_suffix(".md")

Counts = namedtuple("Counts", "comments code portuguese")


def applies_to(relative_path):
    parts = Path(relative_path).parts
    return len(parts) > 1 and parts[0] in SCOPED_DIRECTORIES and relative_path.endswith(SCOPED_SUFFIXES)


def count_added(before, after):
    stripped = lambda text: Counter(line.strip() for line in text.split("\n"))  # noqa: E731
    added = stripped(after) - stripped(before)
    comments = code = portuguese = 0
    for line, times in added.items():
        if not line or DIRECTIVE.match(line):
            continue
        if line.startswith(("#", "//")):
            comments += times
            portuguese += times if PORTUGUESE.search(line) else 0
        else:
            code += times
    return Counts(comments, code, portuguese)


def over_budget(counts):
    return counts.comments > max(1, counts.code // CODE_LINES_PER_COMMENT)


def edited_texts(tool_input, read_before):
    if isinstance(tool_input.get("new_string"), str):
        return tool_input.get("old_string") or "", tool_input["new_string"]
    if isinstance(tool_input.get("edits"), list):
        edits = [edit for edit in tool_input["edits"] if isinstance(edit, dict)]
        return (
            "\n".join(edit.get("old_string") or "" for edit in edits),
            "\n".join(edit.get("new_string") or "" for edit in edits),
        )
    if isinstance(tool_input.get("content"), str):
        return read_before(), tool_input["content"]
    return None


def repository_root(file_path, cwd):
    directory = os.path.dirname(file_path)
    code, output = hook.run(["git", "-C", directory, "rev-parse", "--show-toplevel"], None)
    if code == 0 and output.strip():
        return output.strip()
    return os.environ.get("CLAUDE_PROJECT_DIR") or cwd


def committed_content(root, relative_path):
    code, output = hook.run(["git", "-C", root, "show", f"HEAD:{relative_path}"], None)
    return output if code == 0 else ""


def main():
    payload = hook.read_payload()
    tool_input = hook.tool_input(payload)
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        return
    cwd = hook.working_directory(payload)
    file_path = hook.compose_directory(cwd, file_path)
    root = repository_root(file_path, cwd)
    relative_path = os.path.relpath(file_path, root)
    if not applies_to(relative_path):
        return
    texts = edited_texts(tool_input, lambda: committed_content(root, relative_path))
    if texts is None:
        return
    counts = count_added(*texts)
    if over_budget(counts) or counts.portuguese:
        hook.advise(
            EXPLANATION,
            event=payload.get("hook_event_name") or "PostToolUse",
            file=relative_path,
            comments=counts.comments,
            code=counts.code,
            allowed=max(1, counts.code // CODE_LINES_PER_COMMENT),
            portuguese=counts.portuguese,
        )


if __name__ == "__main__":
    main()
