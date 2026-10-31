---
name: verification-before-completion
description: "Verification floor for every coding task in this repository before declaring work done, committing or opening a PR: `make verify` (the CI gates), the owning tests of what changed, the surface-specific checks (seed-fixed end-to-end numbers, the Docker demo, dashboard prints, a real model call) and a written trace of every claim the PR will make. Enforced inside a session by the sensors in `sensors/`."
---

# Verification Before Completion

> The verification floor. A green unit suite is not a correct metric, a correct metric is not a valid
> compose, and a valid compose is not a dashboard showing the right number. Run every step that
> applies; never silently skip one.

List what changed with `git diff --name-only --no-renames origin/main...HEAD` plus the working tree.

## Steps (run in order)

1. **While iterating, run the owning test** of what you touched (`python -m pytest <path> -q`):

   | Changed | Run |
   | --- | --- |
   | case format, loader, validation | the loader tests |
   | a checker (`exact`, `json_fields`, `contains`, `numeric_range`) | that checker's tests |
   | executor, timeouts, result persistence | the executor tests |
   | metrics (pass rate, latency, tokens, cost) | the metrics tests **and** the seed-fixed end-to-end test |
   | A×B report | the report tests |
   | mock agent or synthetic generator | their tests (same seed → identical output) |
   | model adapter (`openai_compatible`) | the adapter tests, which never touch the network |
   | `sensors/**`, `.claude/settings.json` | `python3 -m unittest tests.test_sensors` |

2. **`make verify`** — the floor: the gates CI runs (`.github/workflows/ci.yml`; the `verify` target in
   the `Makefile` lists them). It must end with exit `0`; read the pytest summary line (`N passed`)
   instead of trusting the exit alone.

3. **The surface's own checks**, when they apply:
   - a metric or a checker changed → the seed-fixed end-to-end numbers either stay the same, or the PR
     says why they moved and by how much;
   - code under `src/` changed → `make mutate MODULE=<module>`, and settle each survivor in a changed
     function: a test that kills it, or a line in the PR saying why it survives (equivalent, cosmetic,
     or out of the tool's reach). Mutation testing does not replace listing the sites of a universal
     claim (`.claude/rules/documentation.rule.md`);
   - OTel export, the collector, Prometheus, Tempo or the compose changed → `make verify VERIFY_E2E=1`:
     a run reaches the stack and the metric and the trace are queryable;
   - the Docker image or the demo path changed → `docker compose run --rm eval demo` on a clean
     `./out`, and open the report it wrote;
   - a dashboard changed → `make screenshot` and look at the print; the PR carries it;
   - the model adapter changed → one real call with a model you have access to (Ollama counts), stated
     in the PR with the model name. Never paste a key or a raw response that holds one;
   - a new env var → documented in `.env.example` and in `docs/models.md` when it concerns a model.

4. **Trace every claim before freezing it, and write the trace down.** Before drafting the body or the
   commit message, list each material claim with what carries it: the command run at this head and its
   answer, the file you opened, or the print you looked at. A recollection is not a trace. The claims
   that fail most often feel too small to check — a count, a "nenhum uso", "não muda o relatório".
   Every risk you would ask the auditor to probe ("must not break X"), probe yourself before the push
   and cite the probe in the body: the auditor is a second check, not the first.

5. **Report** the trace, which steps ran and which were skipped, with the reason for each skip. Say
   what ran here, not what CI will do.

6. **Only then** commit and open the PR **as a draft**, filling `.github/pull_request_template.md`. The
   PR leaves draft only after a passing audit (`.claude/rules/workflow.rule.md`).

## Failure handling

- Test failure → reproduce locally before touching the test. A test changed to make it pass is a
  finding, not a fix. An end-to-end number updated without a reason in the PR is the same finding.
- Compose or image failure → fix the source, never the check.
- Sensor block → read the sensor's `.md`; it states what the control is for.

## Bypass

None. `git commit --no-verify` and `git push --no-verify` are denied in `.claude/settings.json` and
blocked by `block-no-verify`.
