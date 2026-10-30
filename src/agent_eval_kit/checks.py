"""Deterministic checkers: each one decides whether an agent's output matches a case's `expected`."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent_eval_kit.cases import Check


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    reason: str


@dataclass(frozen=True)
class Checker:
    run: Callable[..., CheckResult]
    options: tuple[str, ...] = ()
    """Boolean flags the checker accepts in `check`, all off by default."""


CHECKERS: dict[str, Checker] = {}


def _register(name: str, *options: str) -> Callable[[Callable[..., CheckResult]], Callable[..., CheckResult]]:
    def add(run: Callable[..., CheckResult]) -> Callable[..., CheckResult]:
        CHECKERS[name] = Checker(run=run, options=options)
        return run

    return add


def run_check(check: Check, expected: Any, output: str) -> CheckResult:
    """Run the checker named by `check.type` on `output`, with the options in `check.params`."""
    checker = CHECKERS.get(check.type)
    if checker is None:
        raise ValueError(f"unknown check type {check.type!r}; accepted: {', '.join(CHECKERS)}")
    problem = option_problem(check.type, check.params)
    if problem:
        raise ValueError(f"check type {check.type!r}, option {problem[0]!r}: {problem[1]}")
    if not isinstance(output, str):
        raise TypeError(f"output must be a string, got {type(output).__name__}")
    return checker.run(expected, output, **{name: check.params.get(name, False) for name in checker.options})


def option_problem(check_type: str, params: Mapping[str, Any]) -> tuple[str, str] | None:
    """The first option in `params` that the checker does not accept, as `(option, message)`."""
    accepted = CHECKERS[check_type].options
    for key, value in params.items():
        if key not in accepted:
            hint = f"accepted: {', '.join(accepted)}" if accepted else f"`{check_type}` takes no options"
            return key, f"unknown option; {hint}"
        if not isinstance(value, bool):
            return key, "must be true or false"
    return None


_SHOWN_CHARS = 60


def _shorten(text: str) -> str:
    return text if len(text) <= _SHOWN_CHARS else text[:_SHOWN_CHARS] + "…"


def _show(value: Any) -> str:
    return _shorten(repr(value))


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFC", unicodedata.normalize("NFC", " ".join(text.split())).casefold())


@_register("exact", "normalize")
def _exact(expected: str, output: str, *, normalize: bool) -> CheckResult:
    left, right = (_normalize(expected), _normalize(output)) if normalize else (expected, output)
    how = " after normalizing spaces and case" if normalize else ""
    if left == right:
        return CheckResult(True, f"output equals the expected text{how}")
    differ = next(
        (i for i, (a, b) in enumerate(zip(left, right, strict=False)) if a != b), min(len(left), len(right))
    )
    where = f"first difference at character {differ + 1}{how}"
    return CheckResult(False, f"expected {_show(expected)}, got {_show(output)}; {where}")


class _StrictJSONError(ValueError):
    pass


def _reject_constant(name: str) -> Any:
    raise _StrictJSONError(f"{name} is not valid JSON")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document = {}
    for key, value in pairs:
        if key in document:
            raise _StrictJSONError(f"duplicate key {key!r}")
        document[key] = value
    return document


_MISSING = object()


@_register("json_fields")
def _json_fields(expected: Mapping[str, Any], output: str) -> CheckResult:
    try:
        document = json.loads(output, parse_constant=_reject_constant, object_pairs_hook=_unique_object)
    except json.JSONDecodeError as error:
        if output.lstrip().startswith("```"):
            return CheckResult(False, "invalid JSON: the output is wrapped in a Markdown code fence")
        return CheckResult(False, f"invalid JSON: {error.msg} at line {error.lineno}, column {error.colno}")
    except _StrictJSONError as error:
        return CheckResult(False, f"invalid JSON: {error}")
    except RecursionError:
        return CheckResult(False, "invalid JSON: nested too deeply")
    except ValueError:
        return CheckResult(False, "invalid JSON: a number has too many digits to read")
    if not isinstance(document, dict):
        return CheckResult(False, f"expected a JSON object, got {_json_kind(document)}")

    problems = []
    for path, want in expected.items():
        got, problem = _lookup(document, path)
        if problem:
            problems.append(problem)
        elif not _same_value(want, got):
            problems.append(f"field {_show(path)}: expected {_show(want)}, got {_show(got)}")
    if problems:
        return CheckResult(False, "; ".join(problems))
    return CheckResult(True, f"all {_count(len(expected), 'field')} match")


def _lookup(document: dict, path: str) -> tuple[Any, str | None]:
    node: Any = document
    walked: list[str] = []
    for segment in path.split("."):
        if not isinstance(node, dict):
            return _MISSING, f"field {_show(path)} is missing: {_show('.'.join(walked))} is not an object"
        if segment not in node:
            return _MISSING, f"field {_show(path)} is missing"
        node = node[segment]
        walked.append(segment)
    return node, None


def _same_value(want: Any, got: Any) -> bool:
    """Equality that keeps JSON's types apart: `true` is not `1` and `"3"` is not `3`, but `3` is `3.0`."""
    if isinstance(want, bool) or isinstance(got, bool):
        return isinstance(want, bool) and isinstance(got, bool) and want == got
    if isinstance(want, int | float) and isinstance(got, int | float):
        return want == got
    if isinstance(want, dict) and isinstance(got, dict):
        return want.keys() == got.keys() and all(_same_value(want[key], got[key]) for key in want)
    if isinstance(want, list) and isinstance(got, list):
        return len(want) == len(got) and all(_same_value(w, g) for w, g in zip(want, got, strict=True))
    return type(want) is type(got) and want == got


def _json_kind(value: Any) -> str:
    kinds = {list: "a list", str: "a string", bool: "a boolean", type(None): "null"}
    return kinds.get(type(value), "a number")


@_register("contains", "ignore_case")
def _contains(expected: str | list[str], output: str, *, ignore_case: bool) -> CheckResult:
    pieces = [expected] if isinstance(expected, str) else list(expected)
    haystack = output.casefold() if ignore_case else output
    missing = [piece for piece in pieces if (piece.casefold() if ignore_case else piece) not in haystack]
    how = ", ignoring case" if ignore_case else ""
    if missing:
        listed = ", ".join(map(_show, missing))
        return CheckResult(False, f"missing {len(missing)} of {_count(len(pieces), 'piece')}{how}: {listed}")
    return CheckResult(True, f"found all {_count(len(pieces), 'expected piece')}{how}")


# Digits glued to a word or a dot are not a number (`v2`, `A1001`), nor is a sign after one: `A-15` reads
# as 15. Commas only group thousands (`1,000`); a decimal comma such as `18,50` reads as two numbers.
_NUMBER = re.compile(r"(?<![\w.])[-+]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?")


@_register("numeric_range")
def _numeric_range(expected: Mapping[str, float], output: str) -> CheckResult:
    low, high = expected["min"], expected["max"]
    found = _NUMBER.findall(output)
    if not found:
        return CheckResult(False, "no number found")
    token = found[-1]
    value = float(token.replace(",", ""))
    which = f" (last of {len(found)} numbers found)" if len(found) > 1 else ""
    inside = low <= value <= high
    verdict = "within" if inside else "outside"
    bounds = f"[{_shorten(str(low))}, {_shorten(str(high))}]"
    return CheckResult(inside, f"{_shorten(token)}{which} is {verdict} {bounds}")
