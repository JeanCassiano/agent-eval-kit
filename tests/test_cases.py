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
    assert "duplicate id, in this file" in str(error)


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
        ('{id: " a", input: x, expected: x, check: {type: exact}}', "id"),
        ("{id: 7, input: x, expected: x, check: {type: exact}}", "id"),
        ("{id: a, input: null, expected: x, check: {type: exact}}", "input"),
        ("{id: a, input: x, expected: x, check: {type: exact}, tags: [smoke, 1]}", "tags"),
        ("{id: a, input: x, expected: 3, check: {type: exact}}", "expected"),
        ("{id: a, input: x, expected: {}, check: {type: json_fields}}", "expected"),
        ("{id: a, input: x, expected: [status], check: {type: json_fields}}", "expected"),
        ("{id: a, input: x, expected: {min: 5, max: 1}, check: {type: numeric_range}}", "expected"),
        ("{id: a, input: x, expected: {min: true, max: 3}, check: {type: numeric_range}}", "expected"),
        ("{id: a, input: x, expected: {min: .nan, max: 3}, check: {type: numeric_range}}", "expected"),
        ("{id: a, input: x, expected: {min: 1}, check: {type: numeric_range}}", "expected"),
        ("{id: a, input: x, expected: {min: 1, max: 2, step: 1}, check: {type: numeric_range}}", "expected"),
        ("{id: a, input: x, expected: [ok, 3], check: {type: contains}}", "expected"),
        ('{id: a, input: x, expected: "", check: {type: contains}}', "expected"),
        ("{id: a, input: x, expected: {1: ok}, check: {type: json_fields}}", "expected"),
        ('{id: a, input: x, expected: {"a..b": ok}, check: {type: json_fields}}', "expected"),
        ('{id: a, input: x, expected: {".a": ok}, check: {type: json_fields}}', "expected"),
        ("{id: a, input: x, expected: x, check: {type: exact, normalise: true}}", "check.normalise"),
        ('{id: a, input: x, expected: x, check: {type: exact, normalize: "yes"}}', "check.normalize"),
        ("{id: a, input: x, expected: x, check: {type: contains, normalize: true}}", "check.normalize"),
        ("{id: a, input: x, expected: {min: 1, max: 9}, check: {type: numeric_range, n: 1}}", "check.n"),
    ],
)
def test_invalid_case_fields(tmp_path, case, field):
    error = load_error(write(tmp_path, "toy.yaml", HEADER + f"  - {case}\n"))

    assert error.field == field


@pytest.mark.parametrize(
    ("header", "field"),
    [
        ('name: toy\nversion: "1"\nsynthetic: true\ncases: []\n', "cases"),
        ("name: toy\nversion: true\nsynthetic: true\ncases: []\n", "version"),
        ('name: ""\nversion: "1"\nsynthetic: true\ncases: []\n', "name"),
        ('name: toy\nversion: "1"\nsynthetic: true\nowner: me\ncases: []\n', "owner"),
    ],
)
def test_invalid_suite_fields(tmp_path, header, field):
    error = load_error(write(tmp_path, "toy.yaml", header))

    assert error.field == field


def test_check_option_errors_say_what_is_accepted(tmp_path):
    case = "  - {id: a, input: x, expected: x, check: {type: exact, norm: true}}\n"
    unknown = load_error(write(tmp_path, "a.yaml", HEADER + case))
    no_options = load_error(
        write(
            tmp_path,
            "b.yaml",
            HEADER + "  - {id: a, input: x, expected: {n: 1}, check: {type: json_fields, strict: true}}\n",
        )
    )

    assert "accepted: normalize" in str(unknown)
    assert "`json_fields` takes no options" in str(no_options)


def test_valid_shapes_of_expected_per_check_type(tmp_path):
    cases = """\
  - {id: a, input: x, expected: "Paris", check: {type: exact}}
  - {id: b, input: x, expected: {status: ok, items.count: 3}, check: {type: json_fields}}
  - {id: c, input: x, expected: refund, check: {type: contains}}
  - {id: d, input: x, expected: [refund, order], check: {type: contains}}
  - {id: e, input: x, expected: {min: 2.5, max: 2.5}, check: {type: numeric_range}}
"""
    [suite] = load_suites(write(tmp_path, "toy.yaml", HEADER + cases))

    assert len(suite.cases) == 5


def test_repeated_yaml_key_is_an_error_not_a_silent_overwrite(tmp_path):
    path = write(
        tmp_path, "toy.yaml", HEADER + "  - {id: a, id: b, input: x, expected: x, check: {type: exact}}\n"
    )

    error = load_error(path)

    assert "duplicate key 'id'" in str(error)
    assert "line 5" in str(error)


def test_unreadable_file_is_a_format_error(tmp_path):
    path = tmp_path / "toy.yaml"
    path.write_bytes(b"name: \xff\xfe\n")

    error = load_error(path)

    assert "cannot read the file" in str(error)
    assert error.__suppress_context__


def test_folder_is_recursive_and_skips_hidden_paths(tmp_path):
    (tmp_path / "nested").mkdir()
    (tmp_path / ".hidden").mkdir()
    write(
        tmp_path / "nested",
        "deep.YAML",
        HEADER + "  - {id: deep, input: x, expected: x, check: {type: exact}}\n",
    )
    write(tmp_path / ".hidden", "skip.yaml", "not: a suite\n")
    write(tmp_path, ".skip.yaml", "not: a suite\n")

    [suite] = load_suites(tmp_path)

    assert [case.id for case in suite.cases] == ["deep"]


def test_check_params_are_read_only(tmp_path):
    [suite] = load_suites(write(tmp_path, "toy.yaml", THREE_CASES))

    with pytest.raises(TypeError):
        suite.cases[0].check.params["normalize"] = False


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


def test_anchors_and_merge_keys_still_load(tmp_path):
    cases = """\
  - &base {id: a, input: &prompt "Say hi", expected: "hi", check: {type: exact}}
  - {<<: *base, id: b, expected: "hello"}
  - {<<: [*base], id: c, input: *prompt}
"""
    [suite] = load_suites(write(tmp_path, "toy.yaml", HEADER + cases))

    assert [(case.id, case.input, case.expected) for case in suite.cases] == [
        ("a", "Say hi", "hi"),
        ("b", "Say hi", "hello"),
        ("c", "Say hi", "hi"),
    ]


def test_unhashable_yaml_key_is_a_format_error(tmp_path):
    path = write(
        tmp_path,
        "toy.yaml",
        HEADER + "  - {id: a, input: {? [x, y] : 1}, expected: x, check: {type: exact}}\n",
    )

    error = load_error(path)

    assert "unhashable key" in str(error)
