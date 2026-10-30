# Case format

Test cases live in YAML files, one **suite** per file. `agent_eval_kit.cases.load_suites(path)` loads a
single file or every `*.yaml` / `*.yml` file under a folder (recursively, extension in any case,
skipping hidden files and folders) and returns typed `Suite` objects. Every such file in the folder must
be a suite. Examples are in [`examples/cases/`](../examples/cases/).

```yaml
name: ticket-triage        # suite name, shown in reports
version: "1"               # suite version: bump it when cases change, so runs stay comparable
synthetic: true            # required, and must be true
cases:
  - id: triage-refund      # unique across every file loaded together
    input: "Classify this ticket ..."
    expected: {category: billing, priority: high}
    check: {type: json_fields}
    tags: [triage]         # optional
```

## Fields

| Field | Required | Type | Meaning |
| --- | --- | --- | --- |
| `name` | yes | non-empty string or number | Suite name. |
| `version` | yes | non-empty string or number | Suite version, stored as a string. Quote it: unquoted `1.10` is the number `1.1`. |
| `synthetic` | yes | `true` | Declares that the suite holds synthetic data only. |
| `cases` | yes | non-empty list | The cases. |
| `cases[].id` | yes | non-empty string, no surrounding spaces | Case id, unique across all loaded files. |
| `cases[].input` | yes | any YAML value except `null` | What the agent receives. |
| `cases[].expected` | yes | depends on `check.type` | The reference the checker compares the output against. |
| `cases[].check.type` | yes | one of the types below | Which checker decides pass or fail. |
| `cases[].check.*` | no | `true` or `false` | Checker options, such as `normalize`; see [Checkers](#checkers). |
| `cases[].tags` | no | list of strings | Free labels to group and filter cases. |

Any other suite or case field is rejected, so a typo like `expect:` fails loudly instead of being
ignored. A key repeated in the same mapping is rejected too, instead of the last value silently winning.
Anchors, aliases and merge keys (`<<: *base`) work as in any YAML file, and a key brought in by a merge
may be overridden by the mapping's own key.
Options inside `check` are checked too: each checker accepts only its own options, so `normalise: true`
is an error rather than a silently ignored typo.

YAML reads some unquoted words as booleans (`yes`, `no`, `on`, `off`) and some numbers differently than
written. Quote any string that could be read that way, such as `expected: "NO"`.

## Check types and the shape of `expected`

| `check.type` | `expected` | Example |
| --- | --- | --- |
| `exact` | a string | `expected: "Paris"` |
| `json_fields` | a mapping of field path to value; a path is names joined by dots, none empty | `expected: {status: ok, items.count: 3}` |
| `contains` | a non-empty string, or a list of non-empty strings that must all appear | `expected: [refund, "order #A-1001"]` |
| `numeric_range` | `{min, max}`, finite numbers, both inclusive, `min <= max` | `expected: {min: 10, max: 20}` |

The loader checks the shape of `expected` for the declared type.

## Checkers

`agent_eval_kit.checks.run_check(case.check, case.expected, output)` runs the checker named by
`check.type` on the agent's text output and returns a `CheckResult` with `passed` and a `reason`. The
reason is written for a person reading a failed run, and is set on a pass too. Each value, field path
and bound it quotes is cut to 60 characters. Checkers never raise on odd output (empty, binary, deeply
nested); they fail with a reason. Every option is a boolean flag, off by default.

| `check.type` | Options | Passes when |
| --- | --- | --- |
| `exact` | `normalize` | the output equals `expected`. Without `normalize` the comparison is strict, so a trailing newline fails. With it, both sides are Unicode-normalized (NFC), trimmed, their inner whitespace collapsed to one space and case folded, so `" PARIS\n"` matches `"Paris"`. Punctuation still counts. |
| `json_fields` | none | the whole output is one JSON object (surrounding whitespace allowed) and every listed field has the expected value. Other fields are ignored. |
| `contains` | `ignore_case` | every expected piece appears in the output. |
| `numeric_range` | none | the **last** number in the output is within `[min, max]`, both ends included. |

Rules a reader might otherwise relax:

- **`json_fields` is strict JSON.** An answer wrapped in a Markdown code fence fails, with a reason that
  says so, and so do `NaN`, `Infinity` and a key repeated in one object. The checker measures whether the
  agent followed the requested format, not only whether the values are right.
- **`json_fields` compares types.** `true` is not `1` and `"3"` is not `3`; `3` and `3.0` are equal.
  Nested objects and lists in `expected` must match exactly, not as a subset. A path cannot index into a
  list (`items.0` is not supported), and a key that itself contains a dot cannot be reached.
- **`numeric_range` reads the last number** because it is usually the conclusion when the agent shows its
  work: `"12.50 + 2.25 + 3.25 = 18"` reads as 18. A number glued to a word or a dot is skipped (`v2`,
  `A1001`), and so is a minus sign after a word: `"order A-15"` reads as 15, not -15. Commas only group
  thousands (`1,000`). Known limits: a decimal comma (`18,50`) reads as two numbers, and scientific
  notation (`1e3`) is not recognized.

Examples of reasons, as returned by the checkers:

| `check.type` | Output | Passed | Reason |
| --- | --- | --- | --- |
| `exact` + `normalize` | `"Paris."` | no | `expected 'Paris', got 'Paris.'; first difference at character 6 after normalizing spaces and case` |
| `json_fields` | `{"category": "billing", "priority": "low"}` | no | `field 'priority': expected 'high', got 'low'` |
| `json_fields` | `{"status": "ok"}` | no | `field 'items.count' is missing` |
| `json_fields` | a fenced JSON block | no | `invalid JSON: the output is wrapped in a Markdown code fence` |
| `contains` | `"We will refund you."` | no | `missing 1 of 2 pieces: 'order #A-1001'` |
| `numeric_range` | `"12.50 + 2.25 + 3.25 = 18"` | yes | `18 (last of 4 numbers found) is within [10, 20]` |
| `numeric_range` | `"no idea"` | no | `no number found` |

When a `json_fields` case fails on several fields, the reason lists all of them, joined by `; `.

## Errors

Every validation error is a `CaseFormatError`. Its message names the file, the case id and the field
when they are known, and the error carries them as `path`, `case_id` and `field`:

```text
examples/cases/toy.yaml: case 'greet': field 'expected': required
examples/cases/toy.yaml: case 'greet': field 'check.type': unknown type 'fuzzy'; accepted: exact, json_fields, contains, numeric_range
examples/cases/toy.yaml: case 'greet': field 'check.normalise': unknown option; accepted: normalize
examples/cases/toy.yaml: invalid YAML at line 6, column 4: expected <block end>, but found '<block mapping start>'
```

Malformed YAML is reported with its line and column, never as a raw parser traceback. A file that
cannot be read (no permission, not UTF-8) is a `CaseFormatError` too.

## Why it looks like this

- **YAML, not Python.** Reviewing a case should not require reading code, and a diff of a YAML suite
  reads like a diff of test data.
- **`expected` and `check` are separate.** `expected` is the reference answer and `check` says how to
  compare against it. The same reference can be checked strictly (`exact`) or loosely (`contains`).
- **`synthetic: true` is mandatory.** The project only uses synthetic data. Making every suite declare
  it turns that rule into a check the loader enforces instead of a convention.
- **Ids are unique across files.** Run results are meant to be keyed by case id and compared case by
  case between two runs. A duplicated id would silently merge two cases.
- **Unknown fields and repeated keys are errors.** A misspelled optional field would otherwise be
  dropped without notice, and a run would measure something other than what the author wrote.
- **Safe loading only.** Suites are data. The loader extends PyYAML's `SafeLoader`, which never builds
  arbitrary Python objects from them.
