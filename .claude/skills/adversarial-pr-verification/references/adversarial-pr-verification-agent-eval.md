# adversarial-pr-verification — this repository

What to check, per surface, on top of `make verify` (the CI gates; the `verify` target in the
`Makefile` lists them). Each item names the claim shape, the evidence that settles it and the mutation
that proves a test guards it. A surface whose files don't exist yet has no row to run.

## Fast-path gate list

`make verify`, plus every row below whose surface the diff touches.

## Case format and loader

- A validation claim ("rejeita id duplicado", "exige `synthetic: true`"): feed the loader the bad file
  and read the error; it names the file, the case id and the field. Mutation: drop the check and
  confirm a test goes red.
- A new field or check type is documented in `docs/case-format.md` and in at least one file of
  `examples/cases/`.

## Checkers

- Every checker returns pass/fail plus a readable reason. A claim about a border ("limites
  inclusivos", "normaliza maiúsculas") is checked at the border itself.
- Mutations: `<=` → `<` in `numeric_range`; drop the case normalization in `exact`; make `json_fields`
  ignore a nested path. Green is a finding.

## Metrics

- Percentile method is linear interpolation: `p95` of `1..100` is `95.05`. Re-derive any quoted number
  by hand or with a one-off script, never from the code under audit.
- Timeouts stay out of latency and count as failures; errors count as failures; empty runs and zero
  passes give "n/d", never a division by zero.
- The seed-fixed end-to-end test pins the numbers. A PR that updates them must say why; an unexplained
  change is a finding even when the new number is right.
- Mutations: sample vs population standard deviation; count a timeout as a pass; include timeouts in
  latency.

## A×B report

- "Não conclusivo" follows the documented rule; check one case just inside and one just outside it.
- Cases present in only one run are reported and left out of the comparison.
- The header carries date, labels, N, seed and the "synthetic data" mark.

## Agents: mock and model adapter

- Mock: same seed → identical results; it makes no network call; agents other than the mock never
  receive `expected`. Mutation: pass `expected` into the executor's call and confirm a test catches it.
- Model adapter: the key comes only from the env var named in `api_key_env`. A key in YAML, in a
  result file, in a span attribute, in a log line or in the report is a blocking finding — grep the
  diff and the produced artifacts for the key's prefix.
- 401/403 stop the run; 429/5xx retry as documented; a missing `usage` gives tokens "n/d".
- Adapter tests never hit the network. A claim that it "works with provider X" is a coverage gap unless
  the PR shows one real call made at this head.

## OpenTelemetry, compose and dashboard

- Export is off by default: with it off, no connection is attempted. With the collector down, the run
  finishes with one warning.
- Span hierarchy run → case → execution, with `case_id`, repetition, passed, tokens and
  `agent_version`; full input and output are not attributes by default.
- Every image in the compose has an exact tag; Grafana datasources and the dashboard are provisioned by
  file. A claim that data reaches the stack is verified only by `make verify VERIFY_E2E=1` or the demo
  at this head.
- A dashboard change carries a print from `make screenshot`; a print that does not show the claimed
  panel is a false claim.

## Synthetic data

Every suite and generated file is marked synthetic. Real data — anything from a real person, customer
or production system — in `examples/`, in tests or in a print is a blocking finding.

## The harness

`sensors/`, `.claude/`, `.github/`, the `Makefile` and `tests/test_sensors.py`.

- A sensor is done only when `.claude/settings.json` wires it; `tests/test_sensors.py` (`WiringTest`)
  fails on a wired file that is missing or not executable, a sensor directory not wired, or a missing
  `.md`.
- Mutation: invert a sensor's decision and run `python3 -m unittest tests.test_sensors`. A suite that
  stays green guards nothing.
- Pipe a sample payload into the sensor and read its exit code: `0` allow, `2` block (stderr is the
  reason), advice as JSON `additionalContext` on stdout.

## Comments

`.claude/rules/code-comments.rule.md`: default to no comment; English only; no history, no narration.
A Portuguese comment added in `src/`, `deploy/`, `scripts/`, `tests/` or `sensors/` is a finding.

## Claims in Portuguese

The PR body and the commit messages are in Portuguese. Translate each sentence into a claim and verify
it like any other: "não muda o relatório", "só o verificador X", "os testes cobrem Y", counts and
percentages.

## Publishing

Write the verdict to a file outside the repository (or under the ignored `.tmp/`) whose first line is
`audit: pass <sha>` or `audit: fail <sha>`, with the full head SHA audited. The author publishes it
with `gh pr comment <n> --body-file <file>` after re-reading the head, then runs `gh pr ready <n>`,
which `require-audit-before-ready` lets through only when the last verdict for the current head is a
pass. Read the head with `gh pr view <n> --json commits --jq '.commits[-1].oid'`.
