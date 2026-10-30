from pathlib import Path
from textwrap import dedent

import pytest

from agent_eval_kit.cases import CHECK_TYPES, CaseFormatError, load_suites

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "cases"

HEADER = """\
name: toy
version: "1"
synthetic: true
cases:
"""

THREE_CASES = (
    HEADER
    + """\
  - id: greet
    input: "Say hi"
    expected: "hi"
    check: {type: exact, normalize: true}
    tags: [smoke]
  - id: order
    input: "Return the order as JSON"
    expected: {status: ok, items.count: 3}
    check: {type: json_fields}
  - id: total
    input: "How much is it?"
    expected: {min: 10, max: 20}
    check: {type: numeric_range}
"""
)


def write(directory: Path, name: str, content: str) -> Path:
    path = directory / name
    path.write_text(dedent(content), encoding="utf-8")
    return path


def load_error(path: Path) -> CaseFormatError:
    with pytest.raises(CaseFormatError) as raised:
        load_suites(path)
    return raised.value


def test_valid_file_loads_typed_cases(tmp_path):
    [suite] = load_suites(write(tmp_path, "toy.yaml", THREE_CASES))

    assert (suite.name, suite.version) == ("toy", "1")
    assert [case.id for case in suite.cases] == ["greet", "order", "total"]
    greet = suite.cases[0]
    assert greet.input == "Say hi"
    assert greet.expected == "hi"
    assert greet.check.type == "exact"
    assert greet.check.params == {"normalize": True}
    assert greet.tags == ("smoke",)
    assert suite.cases[1].tags == ()


def test_missing_field_names_file_case_and_field(tmp_path):
    path = write(tmp_path, "toy.yaml", HEADER + '  - {id: greet, input: "Say hi", check: {type: exact}}\n')

    error = load_error(path)

    assert (error.path, error.case_id, error.field) == (path, "greet", "expected")
    assert str(path) in str(error)
    assert "greet" in str(error)
    assert "expected" in str(error)


def test_duplicate_id_in_one_file(tmp_path):
    case = '  - {id: greet, input: "Say hi", expected: "hi", check: {type: exact}}\n'

    error = load_error(write(tmp_path, "toy.yaml", HEADER + case + case))

    assert error.case_id == "greet"
    assert "duplicate" in str(error)


def test_unknown_check_type_lists_accepted_types(tmp_path):
    case = '  - {id: greet, input: "x", expected: "x", check: {type: fuzzy}}\n'
    path = write(tmp_path, "toy.yaml", HEADER + case)

    error = load_error(path)

    assert error.field == "check.type"
    assert "fuzzy" in str(error)
    for check_type in CHECK_TYPES:
        assert check_type in str(error)


def test_malformed_yaml_reports_the_line_without_a_raw_traceback(tmp_path):
    path = write(tmp_path, "toy.yaml", HEADER + "  - id: greet\n   input: broken\n")

    error = load_error(path)

    assert "line 6" in str(error)
    assert error.__cause__ is None
    assert error.__suppress_context__


def test_folder_loads_every_file(tmp_path):
    write(tmp_path, "a.yaml", HEADER + '  - {id: one, input: "x", expected: "x", check: {type: exact}}\n')
    write(tmp_path, "b.yml", HEADER + '  - {id: two, input: "x", expected: "x", check: {type: contains}}\n')
    write(tmp_path, "notes.txt", "not a suite")

    suites = load_suites(tmp_path)

    assert [case.id for suite in suites for case in suite.cases] == ["one", "two"]


def test_duplicate_id_across_files_names_both(tmp_path):
    case = '  - {id: same, input: "x", expected: "x", check: {type: exact}}\n'
    first = write(tmp_path, "a.yaml", HEADER + case)
    second = write(tmp_path, "b.yaml", HEADER + case)

    error = load_error(tmp_path)

    assert error.path == second
    assert str(first) in str(error)


@pytest.mark.parametrize("synthetic", ["", "synthetic: false\n", 'synthetic: "yes"\n'])
def test_suite_must_be_declared_synthetic(tmp_path, synthetic):
    case = "  - {id: a, input: x, expected: x, check: {type: exact}}\n"
    content = 'name: toy\nversion: "1"\n' + synthetic + "cases:\n" + case

    error = load_error(write(tmp_path, "toy.yaml", content))

    assert error.field == "synthetic"


@pytest.mark.parametrize(
    ("case", "field"),
    [
        ("{id: a, input: x, expected: x, check: {type: exact}, expect: x}", "expect"),
        ('{id: "", input: x, expected: x, check: {type: exact}}', "id"),
        ("{id: a, input: x, expected: x, check: exact}", "check"),
        ("{id: a, input: x, expected: x, check: {type: exact}, tags: smoke}", "tags"),
        ("{id: a, input: x, expected: x, check: {type: json_fields}}", "expected"),
        ("{id: a, input: x, expected: {min: 5, max: 1}, check: {type: numeric_range}}", "expected"),
        ("{id: a, input: x, expected: [ok, 3], check: {type: contains}}", "expected"),
    ],
)
def test_invalid_case_fields(tmp_path, case, field):
    error = load_error(write(tmp_path, "toy.yaml", HEADER + f"  - {case}\n"))

    assert error.field == field


def test_empty_folder_is_an_error(tmp_path):
    error = load_error(tmp_path)

    assert "no case files" in str(error)


def test_missing_path_is_an_error(tmp_path):
    error = load_error(tmp_path / "nope.yaml")

    assert "not found" in str(error)


def test_examples_load_and_use_three_check_types():
    suites = load_suites(EXAMPLES)

    assert len(suites) == 3
    assert len({case.check.type for suite in suites for case in suite.cases}) == 3
