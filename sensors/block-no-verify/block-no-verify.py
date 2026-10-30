#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))

import hook  # noqa: E402

GATED_ACTIONS = ("commit", "push")
SHORTEST_ABBREVIATION = "--no-veri"
GLOBAL_OPTIONS_WITH_VALUE = {"-C", "--git-dir", "--work-tree", "--namespace", "--super-prefix"}
COMMIT_OPTIONS_WITH_VALUE = {
    "-m", "--message", "-F", "--file", "-C", "--reuse-message", "-c", "--reedit-message", "--fixup",
    "--squash", "--author", "--date", "--cleanup", "--trailer", "--pathspec-from-file",
}
SHORT_OPTIONS_TAKING_A_VALUE = set("mFCcSu")
EXPLANATION = Path(__file__).with_suffix(".md")


def parse_git(tokens):
    aliases, overrides_hooks_path, index = [], False, 1
    while index < len(tokens):
        token = tokens[index]
        inline = None
        if token in ("-c", "--config-env") and index + 1 < len(tokens):
            inline, index = tokens[index + 1], index + 2
        elif token.startswith("-c") and len(token) > 2:
            inline, index = token[2:], index + 1
        elif token.startswith("--config-env="):
            inline, index = token.split("=", 1)[1], index + 1
        if inline is not None:
            key, _, value = inline.partition("=")
            if key.lower() == "core.hookspath":
                overrides_hooks_path = True
            if key.lower().startswith("alias.") and value:
                aliases.append(value)
            continue
        if token in GLOBAL_OPTIONS_WITH_VALUE:
            index += 2
            continue
        if token == "--":
            break
        if token.startswith("-"):
            index += 1
            continue
        return token, tokens[index + 1 :], overrides_hooks_path, aliases
    return "", [], overrides_hooks_path, aliases


def alias_body(alias):
    return alias[1:] if alias.startswith("!") else f"git {alias}"


def is_no_verify(token):
    return len(token) >= len(SHORTEST_ABBREVIATION) and "--no-verify".startswith(token)


def skips_verification(action, args):
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--":
            return None
        if action == "commit" and token in COMMIT_OPTIONS_WITH_VALUE:
            index += 2
            continue
        if is_no_verify(token):
            return f"git {action} --no-verify"
        if action == "commit" and token.startswith("-") and not token.startswith("--") and len(token) > 1:
            for flag in token[1:]:
                if flag in SHORT_OPTIONS_TAKING_A_VALUE:
                    break
                if flag == "n":
                    return "git commit -n"
        index += 1
    return None


def config_bypass(args, depth):
    if any(a in ("-l", "--list", "--unset", "--unset-all") or a.startswith("--get") for a in args):
        return None
    positionals = [a for a in args if not a.startswith("-")]
    keys = [positional.lower() for positional in positionals[:-1]]
    if "core.hookspath" in keys:
        return "git config core.hooksPath"
    for index, key in enumerate(keys):
        if key.startswith("alias."):
            return find_bypass(alias_body(positionals[index + 1]), depth + 1)
    return None


def inspect_segment(segment, depth):
    tokens, environment = segment.tokens, segment.environment
    if not tokens or hook.basename(tokens[0]) != "git":
        return None
    action, args, overrides_hooks_path, aliases = parse_git(tokens)
    for alias in aliases:
        bypass = find_bypass(alias_body(alias), depth + 1)
        if bypass:
            return bypass
    if action == "config":
        return config_bypass(args, depth)
    if action not in GATED_ACTIONS:
        return None
    if any(n.startswith("GIT_CONFIG") and "core.hookspath" in v.lower() for n, v in environment.items()):
        return f"git {action} com core.hooksPath via GIT_CONFIG_*"
    if overrides_hooks_path:
        return f"git {action} com core.hooksPath sobrescrito"
    return skips_verification(action, args)


def find_bypass(command, depth=0):
    if depth > hook.MAX_NESTING:
        return None
    for segment in hook.command_segments(command, "."):
        bypass = inspect_segment(segment, depth)
        if bypass:
            return bypass
    return None


def main():
    command = hook.tool_input(hook.read_payload()).get("command") or ""
    bypass = find_bypass(command)
    if bypass:
        hook.block(EXPLANATION, bypass=bypass)


if __name__ == "__main__":
    main()
