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
| `cases[].check.*` | no | per checker | Checker options, such as `normalize`. |
| `cases[].tags` | no | list of strings | Free labels to group and filter cases. |

Any other suite or case field is rejected, so a typo like `expect:` fails loudly instead of being
ignored. A key repeated in the same mapping is rejected too, instead of the last value silently winning.
Options inside `check` are not validated by the loader.

YAML reads some unquoted words as booleans (`yes`, `no`, `on`, `off`) and some numbers differently than
written. Quote any string that could be read that way, such as `expected: "NO"`.

## Check types and the shape of `expected`

| `check.type` | `expected` | Example |
| --- | --- | --- |
| `exact` | a string | `expected: "Paris"` |
| `json_fields` | a mapping of field path to value; nested paths use dots | `expected: {status: ok, items.count: 3}` |
| `contains` | a non-empty string, or a list of non-empty strings that must all appear | `expected: [refund, "order #A-1001"]` |
| `numeric_range` | `{min, max}`, finite numbers, both inclusive, `min <= max` | `expected: {min: 10, max: 20}` |

The loader checks the shape of `expected` for the declared type. Each checker's options and its pass rule
are defined by the checker itself.

## Errors

Every validation error is a `CaseFormatError`. Its message names the file, the case id and the field
when they are known, and the error carries them as `path`, `case_id` and `field`:

```text
examples/cases/toy.yaml: case 'greet': field 'expected': required
examples/cases/toy.yaml: case 'greet': field 'check.type': unknown type 'fuzzy'; accepted: exact, json_fields, contains, numeric_range
examples/cases/toy.yaml: invalid YAML at line 6, column 4: expected <block end>, but found '<block mapping start>'
```

Malformed YAML is reported with its line and column, never as a raw parser traceback. A file that
cannot be read (no permission, not UTF-8) is a `CaseFormatError` too.

## Why it looks like this

- **YAML, not Python.** Reviewing a case should not require reading code, and a diff of a YAML suite
  reads like a diff of test data.
- **`expected` and `check` are separate.** `expected` is the reference answer and `check` says how to
  compare against it. The same reference can be checked strictly (`exact`) or loosely (`contains`), and
  a simulated agent can build a passing answer from `expected` alone.
- **`synthetic: true` is mandatory.** The project only uses synthetic data. Making every suite declare
  it turns that rule into a check the loader enforces instead of a convention.
- **Ids are unique across files.** Run results are meant to be keyed by case id and compared case by
  case between two runs. A duplicated id would silently merge two cases.
- **Unknown fields and repeated keys are errors.** A misspelled optional field would otherwise be
  dropped without notice, and a run would measure something other than what the author wrote.
- **Safe loading only.** Suites are data. The loader extends PyYAML's `SafeLoader`, which never builds
  arbitrary Python objects from them.
