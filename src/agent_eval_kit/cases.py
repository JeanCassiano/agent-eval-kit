"""Test case suites: the YAML format, its loader and its validation (see docs/case-format.md)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

CHECK_TYPES = ("exact", "json_fields", "contains", "numeric_range")
SUITE_SUFFIXES = (".yaml", ".yml")

_CASE_FIELDS = ("id", "input", "expected", "check", "tags")
_REQUIRED_CASE_FIELDS = ("id", "input", "expected", "check")


class CaseFormatError(ValueError):
    def __init__(self, path: Path, message: str, *, case_id: str | None = None, field: str | None = None):
        self.path = path
        self.case_id = case_id
        self.field = field
        where = str(path)
        if case_id is not None:
            where += f": case '{case_id}'"
        if field is not None:
            where += f": field '{field}'"
        super().__init__(f"{where}: {message}")


@dataclass(frozen=True)
class Check:
    type: str
    params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Case:
    id: str
    input: Any
    expected: Any
    check: Check
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Suite:
    name: str
    version: str
    path: Path
    cases: tuple[Case, ...]


def load_suites(path: str | Path) -> list[Suite]:
    """Load one suite file, or every `*.yaml`/`*.yml` under a folder, with case ids unique across all."""
    path = Path(path)
    if path.is_dir():
        files = sorted(p for p in path.rglob("*") if p.is_file() and p.suffix in SUITE_SUFFIXES)
        if not files:
            raise CaseFormatError(path, f"no case files ({', '.join(SUITE_SUFFIXES)}) in this folder")
    elif path.is_file():
        files = [path]
    else:
        raise CaseFormatError(path, "not found")

    suites = []
    seen: dict[str, Path] = {}
    for file in files:
        suite = _load_file(file)
        for case in suite.cases:
            if case.id in seen:
                raise CaseFormatError(
                    file, f"duplicate id, already used in {seen[case.id]}", case_id=case.id, field="id"
                )
            seen[case.id] = file
        suites.append(suite)
    return suites


def _load_file(path: Path) -> Suite:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise CaseFormatError(path, _describe_yaml_error(error)) from None

    if not isinstance(data, dict):
        raise CaseFormatError(path, "a suite must be a mapping with name, version, synthetic and cases")
    for key in ("name", "version"):
        if not isinstance(data.get(key), str | int | float) or isinstance(data.get(key), bool):
            raise CaseFormatError(path, "required, must be a string or a number", field=key)
    if data.get("synthetic") is not True:
        raise CaseFormatError(
            path, "must be `true`: suites hold synthetic data only, never real data", field="synthetic"
        )
    unknown = set(data) - {"name", "version", "synthetic", "cases"}
    if unknown:
        raise CaseFormatError(path, "unknown field", field=sorted(unknown)[0])

    raw_cases = data.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise CaseFormatError(path, "required, must be a non-empty list", field="cases")

    cases: list[Case] = []
    for index, raw in enumerate(raw_cases):
        case = _parse_case(path, index, raw)
        if any(existing.id == case.id for existing in cases):
            raise CaseFormatError(path, "duplicate id in this file", case_id=case.id, field="id")
        cases.append(case)
    return Suite(name=str(data["name"]), version=str(data["version"]), path=path, cases=tuple(cases))


def _parse_case(path: Path, index: int, raw: Any) -> Case:
    if not isinstance(raw, dict):
        raise CaseFormatError(path, f"case #{index + 1} must be a mapping")
    case_id = raw.get("id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise CaseFormatError(path, f"case #{index + 1}: required, must be a non-empty string", field="id")

    def fail(field: str, message: str) -> CaseFormatError:
        return CaseFormatError(path, message, case_id=case_id, field=field)

    for key in _REQUIRED_CASE_FIELDS:
        if key not in raw:
            raise fail(key, "required")
    unknown = set(raw) - set(_CASE_FIELDS)
    if unknown:
        raise fail(sorted(unknown)[0], f"unknown field; a case accepts {', '.join(_CASE_FIELDS)}")

    raw_check = raw["check"]
    if not isinstance(raw_check, dict):
        raise fail("check", "must be a mapping with a `type` and its options")
    check_type = raw_check.get("type")
    if check_type not in CHECK_TYPES:
        raise fail("check.type", f"unknown type {check_type!r}; accepted: {', '.join(CHECK_TYPES)}")
    check = Check(
        type=check_type,
        params=MappingProxyType({key: value for key, value in raw_check.items() if key != "type"}),
    )

    problem = _expected_problem(check_type, raw["expected"])
    if problem:
        raise fail("expected", problem)

    tags = raw.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise fail("tags", "must be a list of strings")

    return Case(id=case_id, input=raw["input"], expected=raw["expected"], check=check, tags=tuple(tags))


def _expected_problem(check_type: str, expected: Any) -> str | None:
    if check_type == "exact" and not isinstance(expected, str):
        return "for `exact`, must be a string"
    if check_type == "json_fields" and not (isinstance(expected, dict) and expected):
        return "for `json_fields`, must be a non-empty mapping of field path to value"
    if check_type == "contains":
        parts = [expected] if isinstance(expected, str) else expected
        if not isinstance(parts, list) or not parts or not all(isinstance(p, str) for p in parts):
            return "for `contains`, must be a string or a non-empty list of strings"
    if check_type == "numeric_range":
        if not isinstance(expected, dict) or set(expected) != {"min", "max"}:
            return "for `numeric_range`, must be a mapping with `min` and `max`"
        low, high = expected["min"], expected["max"]
        if not all(isinstance(v, int | float) and not isinstance(v, bool) for v in (low, high)):
            return "for `numeric_range`, `min` and `max` must be numbers"
        if low > high:
            return "for `numeric_range`, `min` must not exceed `max`"
    return None


def _describe_yaml_error(error: yaml.YAMLError) -> str:
    mark = getattr(error, "problem_mark", None)
    problem = getattr(error, "problem", None) or "malformed YAML"
    if mark is None:
        return f"invalid YAML: {problem}"
    return f"invalid YAML at line {mark.line + 1}, column {mark.column + 1}: {problem}"
