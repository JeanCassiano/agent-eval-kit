import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

BLOCKING_EXIT_CODE = 2
PROTECTED_BRANCHES = ("develop", "main")

SHELL_EXECUTABLES = ("bash", "sh", "zsh")
HEREDOC_START = re.compile(r"(?<!<)<<-?(?!<)(?!HEREDOC_\d)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
HEREDOC_MARKER = re.compile(r"<<HEREDOC_(\d+)\b")
REDIRECTION = re.compile(r"^(\d*|&)(>>?|<<<|<)(&?)(.*)$")
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
WRAPPERS = {
    "env": {"values": {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}},
    "command": {"no_exec": {"-v", "-V"}},
    "builtin": {},
    "exec": {"values": {"-a"}},
    "time": {"values": {"-f", "--format", "-o", "--output"}},
    "nohup": {},
    "sudo": {"values": {"-u", "--user", "-g", "--group", "-h", "--host", "-p", "--prompt", "-C", "-D", "--chdir", "-r", "-t", "-U", "-T"}},
    "nice": {"values": {"-n", "--adjustment"}},
    "ionice": {"values": {"-c", "--class", "-n", "--classdata"}},
    "timeout": {"values": {"-s", "--signal", "-k", "--kill-after"}, "positionals": 1},
    "stdbuf": {"values": {"-i", "--input", "-o", "--output", "-e", "--error"}},
    "xargs": {
        "values": {"-I", "-n", "--max-args", "-L", "--max-lines", "-P", "--max-procs", "-s", "--max-chars", "-d", "--delimiter", "-E", "-a", "--arg-file"},
        "indirect": True,
    },
    "unbuffer": {},
    "chronic": {},
    "flock": {"values": {"-w", "--wait", "--timeout", "-E", "--conflict-exit-code"}, "positionals": 1, "command_flag": True},
    "watch": {"values": {"-n", "--interval"}},
    "coproc": {},
}
SHELL_KEYWORDS = {"if", "then", "elif", "else", "fi", "do", "done", "while", "until", "esac", "{", "}", "!", "function"}
GIT_OPTIONS_WITH_VALUE = {"-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--super-prefix"}
GH_GLOBAL_OPTIONS_WITH_VALUE = {"-R", "--repo", "--hostname"}
CREATE_FLAGS = {
    "checkout": ("-b", "-B", "--orphan"),
    "switch": ("-c", "-C", "--create", "--force-create", "--orphan"),
}
BRANCH_RENAME_OR_COPY_FLAGS = {"-m", "-M", "--move", "-c", "-C", "--copy"}
BRANCH_PASSTHROUGH_FLAGS = {"-f", "--force", "-t", "--track", "--no-track", "-q", "--quiet"}
MAX_NESTING = 8
PUSH_OPTIONS_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
EVERY_BRANCH_FLAGS = {"--all", "--branches", "--mirror"}
RELEASE_TAG = re.compile(r"^(refs/tags/)?v\d+\.\d+\.\d+$")


def read_payload(stream=None):
    try:
        payload = json.loads((stream or sys.stdin).read() or "{}")
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def tool_input(payload):
    value = payload.get("tool_input")
    return value if isinstance(value, dict) else {}


def working_directory(payload):
    return payload.get("cwd") or os.getcwd()


def render(explanation, placeholders):
    try:
        text = Path(explanation).read_text(encoding="utf-8")
    except OSError:
        return (
            "Bloqueado por um sensor do repositório, mas a explicação dele não pôde ser lida.\n"
            f"Arquivo ausente ou ilegível: {explanation}\n"
            "Corrija a configuração do sensor antes de seguir."
        )
    for name, value in placeholders.items():
        text = text.replace("{{" + name + "}}", str(value))
    return text


def block(explanation, **placeholders):
    print(render(explanation, placeholders), file=sys.stderr)
    sys.exit(BLOCKING_EXIT_CODE)


def advise(explanation, event="PreToolUse", **placeholders):
    output = {"hookSpecificOutput": {"hookEventName": event, "additionalContext": render(explanation, placeholders)}}
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


def git_environment():
    return {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}


def run(args, cwd):
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=git_environment(), timeout=20)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, str(error)
    return result.returncode, result.stdout if result.returncode == 0 else (result.stderr or result.stdout)


def current_branch(directory):
    code, output = run(["git", "-C", directory, "branch", "--show-current"], directory if os.path.isdir(directory) else None)
    return output.strip() if code == 0 else None


def mark_heredocs(command, bodies):
    kept, pending, body = [], [], []
    for line in command.split("\n"):
        if pending:
            index, delimiter = pending[0]
            if line.strip() == delimiter:
                bodies[index] = "\n".join(body)
                body = []
                pending.pop(0)
            else:
                body.append(line)
            continue

        def replace(match):
            bodies.append("")
            pending.append((len(bodies) - 1, match.group(2)))
            return f"<<HEREDOC_{len(bodies) - 1}"

        kept.append(HEREDOC_START.sub(replace, line))
    if pending:
        bodies[pending[0][0]] = "\n".join(body)
    return "\n".join(kept)


def _parse(text, index=0, closer=None):
    items, current, quote, connector = [], "", "", None

    def flush():
        nonlocal current, connector
        if current.strip():
            items.append((connector, current.strip()))
            connector = None
        current = ""

    while index < len(text):
        char = text[index]
        if quote:
            current += char
            if char == "\\" and quote == '"' and index + 1 < len(text):
                current += text[index + 1]
                index += 1
            elif char == quote:
                quote = ""
        elif char in "'\"":
            quote = char
            current += char
        elif char == "\\" and index + 1 < len(text):
            current += text[index : index + 2]
            index += 1
        elif closer is not None and char == closer:
            flush()
            return items, index + 1
        elif char in "(`":
            flush()
            group, index = _parse(text, index + 1, ")" if char == "(" else "`")
            items.append((connector, group))
            connector = None
            continue
        elif text.startswith(("&&", "||"), index):
            flush()
            connector = text[index : index + 2]
            index += 1
        elif char == "|":
            flush()
            connector = "|"
            if text.startswith("|&", index):
                index += 1
        elif char == "&" and not text.startswith("&>", index) and not (index and text[index - 1] in "<>"):
            flush()
            connector = "&"
        elif char in ";\n)":
            flush()
            connector = ";"
        else:
            current += char
        index += 1
    flush()
    return items, index


def quoted_substitutions(raw):
    found, quote, index = [], "", 0
    while index < len(raw):
        char = raw[index]
        if quote == "'":
            quote = "" if char == "'" else quote
        elif char == "\\":
            index += 1
        elif quote == '"' and raw.startswith("$(", index):
            depth, end = 1, index + 2
            while end < len(raw) and depth:
                depth += {"(": 1, ")": -1}.get(raw[end], 0)
                end += 1
            found.append(raw[index + 2 : end - 1])
            index = end
            continue
        elif quote == '"' and char == "`":
            end = raw.find("`", index + 1)
            end = len(raw) if end == -1 else end
            found.append(raw[index + 1 : end])
            index = end
        elif char in "'\"":
            quote = "" if quote == char else (quote or char)
        index += 1
    return found


def _tokens_with_quoting(segment):
    tokens, current, started, quoted, quote, index = [], "", False, False, "", 0
    while index < len(segment):
        char = segment[index]
        if quote:
            if char == quote:
                quote = ""
            elif char == "\\" and quote == '"' and index + 1 < len(segment) and segment[index + 1] in '"\\$`':
                current += segment[index + 1]
                index += 1
            else:
                current += char
        elif char in "'\"":
            quote, started, quoted = char, True, True
        elif char == "\\" and index + 1 < len(segment):
            if segment[index + 1] != "\n":
                current += segment[index + 1]
                started = True
            index += 1
        elif char.isspace():
            if started:
                tokens.append((current, quoted))
            current, started, quoted = "", False, False
        else:
            current += char
            started = True
        index += 1
    if started:
        tokens.append((current, quoted))
    return tokens


def shell_tokens(segment):
    kept, skip_next = [], False
    for token, quoted in _tokens_with_quoting(segment):
        if skip_next:
            skip_next = False
            continue
        if not quoted and token.startswith("<<HEREDOC_"):
            continue
        redirect = None if quoted else REDIRECTION.match(token)
        if redirect:
            skip_next = not redirect.group(4)
            continue
        kept.append(token)
    return kept


def is_assignment(token):
    return bool(ASSIGNMENT.match(token))


def basename(token):
    return token.rsplit("/", 1)[-1]


def unwrap(tokens):
    environment, indirect, index = {}, False, 0
    while index < len(tokens):
        token = tokens[index]
        if is_assignment(token):
            name, value = token.split("=", 1)
            environment[name] = value
            index += 1
            continue
        if token in SHELL_KEYWORDS:
            index += 2 if token == "function" else 1
            continue
        wrapper = WRAPPERS.get(basename(token))
        if wrapper is None:
            break
        indirect = indirect or wrapper.get("indirect", False)
        index += 1
        while index < len(tokens) and tokens[index].startswith("-") and len(tokens[index]) > 1:
            flag = tokens[index]
            if flag in wrapper.get("no_exec", ()):
                return [], environment, indirect
            index += 2 if flag in wrapper.get("values", ()) else 1
            if flag == "--":
                break
        index += wrapper.get("positionals", 0)
        if wrapper.get("command_flag") and index < len(tokens) and tokens[index] in ("-c", "--command"):
            return ["sh", "-c", tokens[index + 1] if index + 1 < len(tokens) else ""], environment, indirect
    return tokens[index:], environment, indirect


def nested_command(tokens):
    executable = basename(tokens[0]) if tokens else ""
    if executable in SHELL_EXECUTABLES:
        for position, token in enumerate(tokens[1:], start=1):
            if token.startswith("-") and not token.startswith("--") and "c" in token:
                return tokens[position + 1] if position + 1 < len(tokens) else ""
        return None
    if executable == "eval":
        return " ".join(tokens[1:])
    return None


def compose_directory(base, path):
    return os.path.normpath(path if os.path.isabs(path) else os.path.join(base, path))


@dataclass
class Segment:
    tokens: list
    directory: str
    environment: dict
    heredocs: list
    connector: str
    indirect: bool


def command_segments(command, directory):
    bodies = []
    yield from _walk_text(mark_heredocs(command, bodies), bodies, directory, 0, None, {})


def _walk_text(text, bodies, directory, depth, connector, exported):
    if depth > MAX_NESTING:
        return
    yield from _walk(_parse(text)[0], bodies, directory, depth, connector, dict(exported))


def _walk(items, bodies, directory, depth, inherited, exported):
    for position, (connector, node) in enumerate(items):
        if connector is None and position == 0:
            connector = inherited
        if isinstance(node, list):
            yield from _walk(node, bodies, directory, depth + 1, connector, dict(exported))
            continue
        for inner in quoted_substitutions(node):
            yield from _walk_text(inner, bodies, directory, depth + 1, connector, exported)
        tokens, own, indirect = unwrap(shell_tokens(node))
        environment = {**exported, **own}
        heredocs = [bodies[int(number)] for number in HEREDOC_MARKER.findall(node)]
        nested = nested_command(tokens)
        if nested is not None:
            yield from _walk_text(mark_heredocs(nested, bodies), bodies, directory, depth + 1, connector, environment)
            continue
        if tokens and basename(tokens[0]) in SHELL_EXECUTABLES and heredocs:
            for body in heredocs:
                yield from _walk_text(mark_heredocs(body, bodies), bodies, directory, depth + 1, connector, environment)
            continue
        yield Segment(tokens, directory, environment, heredocs, connector, indirect)
        if tokens[:1] == ["cd"] and len(tokens) > 1 and not tokens[1].startswith("-"):
            directory = compose_directory(directory, tokens[1])
        elif not tokens:
            exported.update(own)
        elif tokens[0] == "export":
            exported.update(dict(token.split("=", 1) for token in tokens[1:] if is_assignment(token)))
        elif tokens[0] == "unset":
            for name in tokens[1:]:
                exported.pop(name, None)


@dataclass
class GitInvocation:
    name: str
    args: list
    directory: str
    tokens: list
    heredocs: list
    environment: dict
    indirect: bool
    git_dir: str = None

    @property
    def location(self):
        return self.git_dir or self.directory


@dataclass
class GhInvocation:
    args: list
    directory: str
    indirect: bool


def parse_git(segment):
    tokens, directory = segment.tokens, segment.directory
    if not tokens or basename(tokens[0]) != "git":
        return None
    git_dir, index = segment.environment.get("GIT_DIR"), 1
    while index < len(tokens):
        token = tokens[index]
        if token == "-C" and index + 1 < len(tokens):
            directory = compose_directory(directory, tokens[index + 1])
            index += 1
        elif token.startswith("-C") and len(token) > 2:
            directory = compose_directory(directory, token[2:])
        elif token == "--git-dir" and index + 1 < len(tokens):
            git_dir = tokens[index + 1]
            index += 1
        elif token.startswith("--git-dir="):
            git_dir = token.split("=", 1)[1]
        elif token in GIT_OPTIONS_WITH_VALUE:
            index += 1
        elif not token.startswith("-"):
            return GitInvocation(
                token,
                tokens[index + 1 :],
                directory,
                tokens,
                segment.heredocs,
                segment.environment,
                segment.indirect,
                compose_directory(directory, git_dir) if git_dir else None,
            )
        index += 1
    return None


def git_invocations(command, directory):
    for segment in command_segments(command, directory):
        invocation = parse_git(segment)
        if invocation:
            yield invocation


def gh_invocations(command, directory):
    for segment in command_segments(command, directory):
        if not segment.tokens or basename(segment.tokens[0]) != "gh":
            continue
        rest, moved = list(segment.tokens[1:]), []
        while rest and rest[0].startswith("-"):
            flag = rest.pop(0)
            moved.append(flag)
            if flag in GH_GLOBAL_OPTIONS_WITH_VALUE and rest:
                moved.append(rest.pop(0))
        yield GhInvocation(rest + moved, segment.directory, segment.indirect)


def value_after(args, flags):
    for index, token in enumerate(args):
        if token == "--":
            return None
        if token in flags:
            return args[index + 1] if index + 1 < len(args) else None
        for flag in flags:
            if flag.startswith("--") and token.startswith(flag + "="):
                return token.split("=", 1)[1]
            if not flag.startswith("--") and token.startswith(flag) and len(token) > len(flag):
                return token[len(flag) :]
    return None


def created_branch(name, args):
    if name in CREATE_FLAGS:
        return value_after(args, CREATE_FLAGS[name])
    if name == "worktree" and args[:1] == ["add"]:
        explicit = value_after(args[1:], ("-b", "-B"))
        if explicit or "--detach" in args or "-d" in args:
            return explicit
        positionals = [token for token in args[1:] if not token.startswith("-")]
        return basename(positionals[0].rstrip("/")) if len(positionals) == 1 else None
    if name == "branch":
        positionals = [token for token in args if not token.startswith("-")]
        if any(token in BRANCH_RENAME_OR_COPY_FLAGS for token in args):
            return positionals[-1] if positionals else None
        if any(token.startswith("-") and token not in BRANCH_PASSTHROUGH_FLAGS for token in args):
            return None
        return positionals[0] if positionals else None
    return None


def switched_branch(invocation):
    name, args = invocation.name, invocation.args
    if name not in CREATE_FLAGS:
        return None
    created = value_after(args, CREATE_FLAGS[name])
    if created:
        return created
    if "--detach" in args or (name == "switch" and "-d" in args):
        return ""
    if "--" in args:
        return None
    positionals = [token for token in args if not token.startswith("-")]
    if len(positionals) != 1 or positionals[0] == "-":
        return None
    target = positionals[0]
    if name == "checkout" and os.path.exists(os.path.join(invocation.directory, target)):
        return None
    return target


def git_invocations_on_branch(command, directory, resolve_branch):
    switches = {}
    for segment in command_segments(command, directory):
        if segment.connector != "&&":
            for state in switches.values():
                state[2] = False
        invocation = parse_git(segment)
        if not invocation:
            continue
        location = invocation.location
        if location in switches:
            target, prior, chained = switches[location]
            branches = {target} if chained else prior | {target}
        else:
            branch = resolve_branch(location)
            branches = {"" if branch is None and not invocation.git_dir else branch}
        yield invocation, branches
        target = switched_branch(invocation)
        if target is not None:
            switches[location] = [target, branches, True]


def split_push_args(args):
    flags, positionals, index = [], [], 0
    while index < len(args):
        token = args[index]
        if token in PUSH_OPTIONS_WITH_VALUE:
            index += 2
            continue
        (flags if token.startswith("-") else positionals).append(token)
        index += 1
    return flags, positionals


def push_destination(refspec, current_branch):
    target = refspec.lstrip("+").split(":", 1)[-1]
    if target.startswith("refs/heads/"):
        target = target[len("refs/heads/") :]
    return current_branch() if target in ("HEAD", "@") else target


def push_destinations(args, current_branch):
    flags, positionals = split_push_args(args)
    if EVERY_BRANCH_FLAGS & set(flags):
        return list(PROTECTED_BRANCHES)
    refspecs = positionals[1:]
    if not refspecs:
        return [] if "--tags" in flags else [current_branch()]
    return [push_destination(refspec, current_branch) for refspec in refspecs]
