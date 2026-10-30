# agent-eval-kit

Evaluate AI agents the way you test code: describe cases in YAML, run each one N times, check the
answers with deterministic rules and compare two versions with numbers — pass rate, latency, tokens and
cost — instead of a gut feeling. Runs export OpenTelemetry metrics and traces, and a local Docker stack
shows them in Grafana.

> **Work in progress.** The repository is being bootstrapped; the commands below grow as features land.

> **Synthetic data only.** Every test case, example and generated suite in this repository is
> synthetic. No real user, customer or production data is used anywhere.

## Quickstart

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/), which installs the right Python
version by itself.

```bash
make install   # Python + dependencies
make test      # test suite
make lint      # style and formatting
```

`make help` lists every target.

## Writing cases

Cases are YAML files; see [docs/case-format.md](docs/case-format.md) for the format and how each checker
decides pass or fail, and the suites in [examples/cases/](examples/cases/).

## License

[MIT](LICENSE)
