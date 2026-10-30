from pathlib import Path

import pytest

from agent_eval_kit.cases import CHECK_TYPES, Check, load_suites
from agent_eval_kit.checks import CHECKERS, CheckResult, run_check

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "cases"


def check(check_type, expected, output, **params):
    return run_check(Check(type=check_type, params=params), expected, output)


@pytest.mark.parametrize(
    ("check_type", "expected", "output", "params", "passed", "reason_part"),
    [
        ("exact", "42", "42", {}, True, ""),
        ("exact", "olá", " Olá ", {"normalize": True}, True, ""),
        ("json_fields", {"status": "ok"}, '{"status":"ok","n":3}', {}, True, ""),
        ("json_fields", {"status": "ok"}, "não é json", {}, False, "invalid JSON"),
        ("json_fields", {"status": "ok", "n": 3}, '{"status":"ok"}', {}, False, "'n'"),
        ("contains", ["refund", "order #A-1001"], "We will refund you.", {}, False, "'order #A-1001'"),
        ("numeric_range", {"min": 10, "max": 20}, "10", {}, True, ""),
        ("numeric_range", {"min": 10, "max": 20}, "nenhum", {}, False, "no number found"),
    ],
    ids=[
        "exact",
        "exact-normalized",
        "json-correct",
        "json-invalid",
        "json-missing-field",
        "contains-missing-piece",
        "range-on-the-bound",
        "range-no-number",
    ],
)
def test_story_scenarios(check_type, expected, output, params, passed, reason_part):
    result = check(check_type, expected, output, **params)

    assert isinstance(result, CheckResult)
    assert result.passed is passed
    assert result.reason
    assert reason_part in result.reason


def test_registry_is_the_list_of_check_types():
    assert tuple(CHECKERS) == CHECK_TYPES == ("exact", "json_fields", "contains", "numeric_range")
    assert CHECKERS["exact"].options == ("normalize",)
    assert CHECKERS["contains"].options == ("ignore_case",)
    assert CHECKERS["json_fields"].options == CHECKERS["numeric_range"].options == ()


@pytest.mark.parametrize(
    ("expected", "output", "params", "passed"),
    [
        ("Paris", "Paris", {}, True),
        ("Paris", "paris", {}, False),
        ("Paris", "Paris\n", {}, False),
        ("Paris", " PARIS \n", {"normalize": True}, True),
        ("New York", "new   york", {"normalize": True}, True),
        ("New York", "NewYork", {"normalize": True}, False),
        ("Brasília", "Brasília", {"normalize": True}, True),
        ("Straße", "STRASSE", {"normalize": True}, True),
        ("Paris", "Paris.", {"normalize": True}, False),
    ],
)
def test_exact(expected, output, params, passed):
    assert check("exact", expected, output, **params).passed is passed


def test_exact_reason_shows_both_texts_and_where_they_differ():
    reason = check("exact", "Paris", "Paris\n").reason

    assert "'Paris'" in reason
    assert "'Paris\\n'" in reason
    assert "character 6" in reason


def test_exact_reason_truncates_a_long_output():
    reason = check("exact", "short", "x" * 500).reason

    assert len(reason) < 200
    assert "character 1" in reason


@pytest.mark.parametrize(
    ("expected", "output", "passed"),
    [
        ({"items.count": 3}, '{"items": {"count": 3}}', True),
        ({"a.b.c": "deep"}, '{"a": {"b": {"c": "deep"}}}', True),
        ({"n": 3}, '{"n": 3.0}', True),
        ({"n": 3}, '{"n": "3"}', False),
        ({"flag": True}, '{"flag": 1}', False),
        ({"n": 1}, '{"n": true}', False),
        ({"n": 0}, '{"n": false}', False),
        ({"tags": ["a", "b"]}, '{"tags": ["a", "b"]}', True),
        ({"tags": [1]}, '{"tags": [true]}', False),
        ({"tags": ["a", "b"]}, '{"tags": ["b", "a"]}', False),
        ({"meta": {"x": 1}}, '{"meta": {"x": 1, "y": 2}}', False),
        ({"note": None}, '{"note": null}', True),
        ({"note": None}, "{}", False),
        ({"status": "ok"}, ' \n {"status": "ok", "extra": [1, 2]} \n', True),
    ],
)
def test_json_fields(expected, output, passed):
    assert check("json_fields", expected, output).passed is passed


@pytest.mark.parametrize(
    ("output", "reason_part"),
    [
        ('```json\n{"status": "ok"}\n```', "Markdown code fence"),
        ('[{"status": "ok"}]', "a JSON object, got a list"),
        ('"ok"', "a JSON object, got a string"),
        ('{"status": NaN}', "invalid JSON"),
        ('{"status": "error", "status": "ok"}', "duplicate key 'status'"),
        ('{"status": "ok"', "invalid JSON"),
        ("", "invalid JSON"),
        ("[" * 100_000, "invalid JSON"),
    ],
)
def test_json_fields_rejects_what_is_not_one_json_object(output, reason_part):
    result = check("json_fields", {"status": "ok"}, output)

    assert result.passed is False
    assert reason_part in result.reason


def test_json_fields_reason_lists_every_failing_field():
    result = check(
        "json_fields",
        {"status": "ok", "n": 3, "a.b": 1, "x.y": 2},
        '{"status": "error", "a": 5, "x": {}}',
    )

    assert result.passed is False
    assert "field 'status': expected 'ok', got 'error'" in result.reason
    assert "field 'n' is missing" in result.reason
    assert "field 'a.b' is missing: 'a' is not an object" in result.reason
    assert "field 'x.y' is missing" in result.reason


def test_reasons_cut_long_values():
    big = '{"meta": {"list": [' + ", ".join(["1"] * 500) + "]}}"

    assert len(check("json_fields", {"meta": {"list": []}}, big).reason) < 200
    assert len(check("numeric_range", {"min": 0, "max": 1}, "9" * 500).reason) < 200


@pytest.mark.parametrize(
    ("expected", "output", "params", "passed"),
    [
        ("refund", "We will refund you.", {}, True),
        (["refund", "#A-1001"], "Refund for #A-1001 issued.", {}, False),
        (["refund", "#A-1001"], "Refund for #A-1001 issued.", {"ignore_case": True}, True),
        (["STRASSE"], "straße", {"ignore_case": True}, True),
        (["refund", "order"], "refund", {}, False),
    ],
)
def test_contains(expected, output, params, passed):
    assert check("contains", expected, output, **params).passed is passed


def test_contains_reason_lists_every_missing_piece():
    reason = check("contains", ["alpha", "beta", "gamma"], "only beta here").reason

    assert "'alpha'" in reason
    assert "'gamma'" in reason
    assert "'beta'" not in reason


@pytest.mark.parametrize(
    ("output", "passed"),
    [
        ("20", True),
        ("9.99", False),
        ("20.01", False),
        ("The total is 18.", True),
        ("12.50 + 2.25 + 3.25 = 18", True),
        ("A 2 kg parcel costs about 12 dollars", True),
        ("It costs 15, maybe 25", False),
        ("-15", False),
        ("Order A-15 costs 12", True),
        ("about 1,000 or 15", True),
        ("$12.5", True),
    ],
)
def test_numeric_range_uses_the_last_number(output, passed):
    assert check("numeric_range", {"min": 10, "max": 20}, output).passed is passed


@pytest.mark.parametrize(
    ("output", "value"),
    [
        ("-5", -5),
        ("x = -2.5", -2.5),
        ("Order A-15", 15),
        ("1,000", 1000),
        ("about 1,234,567 units", 1234567),
        ("+3", 3),
    ],
)
def test_numeric_range_reads_signs_decimals_and_thousands(output, value):
    assert check("numeric_range", {"min": value, "max": value}, output).passed is True


def test_numeric_range_reason_names_the_number_and_the_range():
    result = check("numeric_range", {"min": 10, "max": 20}, "first 15, then 25.5")

    assert result.passed is False
    assert "25.5" in result.reason
    assert "[10, 20]" in result.reason
    assert "last of 2 numbers" in result.reason


def test_numeric_range_ignores_digits_glued_to_a_word():
    assert check("numeric_range", {"min": 0, "max": 100}, "version v2 of A1001").reason == "no number found"


@pytest.mark.parametrize("check_type", CHECK_TYPES)
@pytest.mark.parametrize("output", ["", " ", "\x00", "```", "{", "-", ",", "." * 1000, "🙂" * 10])
def test_no_checker_raises_on_odd_output(check_type, output):
    expected = {
        "exact": "x",
        "json_fields": {"a.b": 1},
        "contains": ["x"],
        "numeric_range": {"min": 0, "max": 1},
    }[check_type]

    result = check(check_type, expected, output)

    assert result.passed is False
    assert result.reason


def test_run_check_rejects_an_unknown_type_or_option_and_a_non_string_output():
    with pytest.raises(ValueError, match="fuzzy"):
        check("fuzzy", "x", "x")
    with pytest.raises(ValueError, match="normalise"):
        check("exact", "x", "x", normalise=True)
    with pytest.raises(ValueError, match="true or false"):
        check("exact", "x", "x", normalize="yes")
    with pytest.raises(TypeError):
        check("exact", "42", 42)


def test_example_suites_pass_with_correct_answers():
    answers = {
        "capital-fr": "paris",
        "capital-jp": " Tokyo\n",
        "capital-br": "Brasília",
        "total-three-items": "12.50 + 2.25 + 3.25 = 18",
        "shipping-estimate": "About 12 dollars.",
        "triage-refund": '{"category": "billing", "priority": "high"}',
        "triage-password": '{"category": "account", "priority": "low"}',
    }
    cases = [case for suite in load_suites(EXAMPLES) for case in suite.cases]

    assert sorted(case.id for case in cases) == sorted(answers)
    for case in cases:
        result = run_check(case.check, case.expected, answers[case.id])
        assert result.passed, (case.id, result.reason)
