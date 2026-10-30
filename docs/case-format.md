# Case format

Test cases live in YAML files, one **suite** per file. `agent_eval_kit.cases.load_suites(path)` loads a
single file or every `*.yaml` / `*.yml` file under a folder (recursively) and returns typed `Suite`
objects. Examples are in [`examples/cases/`](../examples/cases/).

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
| `name` | yes | string or number | Suite name. |
| `version` | yes | string or number | Suite version, stored as a string. |
| `synthetic` | yes | `true` | Declares that the suite holds synthetic data only. |
| `cases` | yes | non-empty list | The cases. |
| `cases[].id` | yes | non-empty string | Case id, unique across all loaded files. |
| `cases[].input` | yes | any YAML value | What the agent receives. |
| `cases[].expected` | yes | depends on `check.type` | The reference the checker compares the output against. |
| `cases[].check.type` | yes | one of the types below | Which checker decides pass or fail. |
| `cases[].check.*` | no | per checker | Checker options, such as `normalize`. |
| `cases[].tags` | no | list of strings | Free labels to group and filter cases. |

Any other field is rejected, so a typo like `expect:` fails loudly instead of being ignored.

## Check types and the shape of `expected`

| `check.type` | `expected` | Example |
| --- | --- | --- |
| `exact` | a string | `expected: "Paris"` |
| `json_fields` | a mapping of field path to value; nested paths use dots | `expected: {status: ok, items.count: 3}` |
| `contains` | a string, or a list of strings that must all appear | `expected: [refund, "order #A-1001"]` |
| `numeric_range` | `{min, max}`, both inclusive | `expected: {min: 10, max: 20}` |

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

Malformed YAML is reported with its line and column, never as a raw parser traceback.

## Why it looks like this

- **YAML, not Python.** Reviewing a case should not require reading code, and a diff of a YAML suite
  reads like a diff of test data.
- **`expected` and `check` are separate.** `expected` is the reference answer and `check` says how to
  compare against it. The same reference can be checked strictly (`exact`) or loosely (`contains`), and
  the mock agent can produce a passing answer from `expected` alone.
- **`synthetic: true` is mandatory.** The project only uses synthetic data. Making every suite declare
  it turns that rule into a check the loader enforces instead of a convention.
- **Ids are unique across files.** Results are keyed by case id, and an A×B report compares runs case by
  case. A duplicated id would silently merge two cases.
- **Unknown fields are errors.** A misspelled optional field would otherwise be dropped without notice,
  and a run would measure something other than what the author wrote.
- **`safe_load` only.** Suites are data. The YAML parser never builds arbitrary Python objects from them.
