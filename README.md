<div align="center">

<img src="https://raw.githubusercontent.com/flameiq/flameiq/main/assets/flameiq-logo.png" alt="FlameIQ Logo" width="120" height="120" />

# FlameIQ

**Deterministic, CI-native performance regression and evolution engine.**

Make performance a first-class, enforceable engineering signal.

[![CI](https://github.com/flameiq/flameiq/actions/workflows/ci.yml/badge.svg)](https://github.com/flameiq/flameiq/actions)
[![PyPI version](https://badge.fury.io/py/flameiq.svg)](https://pypi.org/project/flameiq/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Installation](#installation) · [Quick Start](#quick-start) · [Documentation](#documentation) · [Contributing](#contributing) · [Roadmap](#roadmap)

</div>

---

## Why FlameIQ Exists

Performance regressions are **subtle**, **cumulative**, and **expensive**. A 2–5% slowdown per PR compounds silently over months until a system that once handled 10,000 requests per second struggles with 6,000 — and no single commit is obviously to blame.

Most teams have benchmarks. Very few have **enforcement**.

FlameIQ closes that gap. It is the performance equivalent of a unit test suite: a deterministic, CI-native engine that makes performance regressions **fail builds**, **track evolution**, and **enforce budgets** — without requiring any SaaS platform, cloud account, or vendor dependency.

```
p95 latency increased 18.4%   [threshold: 10%]
throughput decreased 6.1%     [threshold: 5%]

Status: REGRESSION
Exit code: 1
```

---

## Design Principles

FlameIQ is built on eight non-negotiable engineering principles:

| Principle | What It Means |
|---|---|
| **Deterministic** | Same inputs always produce identical outputs. Floating-point precision is explicit. No randomness in core logic. |
| **CI-Native** | Designed for automation first. CLI exit codes, structured JSON output, and CI-friendly interfaces are the primary concern. |
| **Language-Agnostic** | FlameIQ does not care what language your benchmark is written in. It consumes structured JSON via a plugin interface. |
| **Offline-First** | No network calls by default. No telemetry unless explicitly opted in. Fully air-gap deployable. |
| **Vendor-Neutral** | No lock-in to any cloud provider, CI system, or hosted service. Works with any infrastructure. |
| **Statistically Grounded** | All regression detection algorithms are mathematically documented and reproducible. |
| **Extensible** | Plugin-driven metric ingestion. Stable SDK interface. Every layer is independently testable. |
| **Auditable** | All comparison algorithms are documented in `/specs`. Engineers can verify the math independently. |

> **FlameIQ is infrastructure — not a dashboard.**

---

## Installation

```bash
pip install flameiq
```

No account required. No API keys. No external services. Works fully offline.

**Requirements:** Python 3.10 or higher.

---

## Quick Start

### 1. Initialize FlameIQ in your project

```bash
flameiq init
```

This creates a `.flameiq/` directory and a `flameiq.yaml` configuration file.

### 2. Run your benchmarks and collect metrics

FlameIQ consumes structured JSON output from any benchmarking tool:

```json
{
  "schema_version": 1,
  "metadata": {
    "commit": "abc123",
    "timestamp": "2026-01-01T10:00:00Z",
    "environment": "ci"
  },
  "metrics": {
    "latency": {
      "mean": 120.5,
      "p50": 110.0,
      "p95": 180.0,
      "p99": 240.0
    },
    "throughput": 950.2,
    "memory_mb": 512.0
  }
}
```

### 3. Set your baseline

```bash
flameiq baseline set --strategy rolling_median
```

### 4. Compare on every PR

```bash
flameiq run --metrics benchmark_output.json
flameiq compare --fail-on-regression
```

If a regression is detected, the exit code is `1` — failing your CI pipeline.

---

## CI Integration

Add FlameIQ to any CI pipeline in minutes.

### GitHub Actions

```yaml
name: Performance Regression Check

on: [pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install flameiq
          pip install -r requirements.txt

      - name: Run benchmarks
        run: python benchmarks/run.py > metrics.json

      - name: Check for regressions
        run: |
          flameiq run --metrics metrics.json
          flameiq compare --fail-on-regression

      - name: Upload FlameIQ report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: flameiq-report
          path: .flameiq/report.html
```

### GitLab CI

```yaml
benchmark:
  stage: test
  script:
    - pip install flameiq
    - python benchmarks/run.py > metrics.json
    - flameiq run --metrics metrics.json
    - flameiq compare --fail-on-regression
  artifacts:
    when: always
    paths:
      - .flameiq/report.html
```

### Any CI System

```bash
# The pattern is always the same:
# 1. Run your benchmarks and output JSON
# 2. Run flameiq compare
# 3. Non-zero exit code = regression = CI failure

python run_benchmarks.py > metrics.json
flameiq run --metrics metrics.json && flameiq compare --fail-on-regression
```

---

## Configuration

FlameIQ is configured via `flameiq.yaml` in your project root.

```yaml
# flameiq.yaml

schema_version: 1

# Regression thresholds — how much change is allowed before a failure
thresholds:
  latency.p95:   10%     # Max 10% increase allowed
  latency.p99:   15%     # Max 15% increase allowed
  throughput:    -5%     # Max 5% decrease allowed
  memory_mb:      8%     # Max 8% increase allowed

# Baseline management strategy
baseline:
  strategy: rolling_median    # Options: rolling_median | last_successful | tagged_release
  warmup_runs: 3              # Runs to discard before measurement

# Optional statistical mode for higher confidence detection
statistics:
  enabled: true
  confidence: 0.95            # 95% confidence level

# Noise tolerance
noise_tolerance:
  minimum_samples: 5          # Minimum runs required for comparison

# Which metric provider to use
provider: json                # Options: json | pytest-benchmark | custom
```

---

## Plugin System

FlameIQ does not lock you into a specific benchmarking framework. Use the provider interface to ingest metrics from any tool.

### Built-in Providers

| Provider | Description | Install |
|---|---|---|
| `json` | Generic JSON file adapter | Built-in |
| `pytest-benchmark` | pytest-benchmark output adapter | Built-in |
| `go` | Go benchmark output adapter | `pip install flameiq-go` |
| `node` | Node.js benchmark adapter | `pip install flameiq-node` |
| `rust` | Rust criterion adapter | `pip install flameiq-rust` |

### Writing a Custom Provider

```python
from flameiq.providers.base import MetricProvider
from flameiq.schema.v1 import FlameIQSnapshot, Metric

class MyBenchmarkProvider(MetricProvider):

    @property
    def name(self) -> str:
        return "my-benchmark"

    def collect(self, source: str) -> dict:
        # Read your benchmark output
        with open(source) as f:
            return json.load(f)

    def validate(self, raw: dict) -> bool:
        # Confirm the data has what you need
        return "results" in raw

    def normalize(self, raw: dict) -> FlameIQSnapshot:
        # Transform into FlameIQ schema
        return FlameIQSnapshot(
            schema_version=1,
            metrics={
                "latency": Metric(
                    mean=raw["results"]["avg_ms"],
                    p95=raw["results"]["p95_ms"],
                )
            }
        )
```

Use it:

```bash
flameiq run --metrics output.json --provider my-benchmark
```

---

## CLI Reference

```
flameiq <command> [options]

Commands:
  init                    Initialize FlameIQ in the current project
  run                     Collect and validate a metrics snapshot
  compare                 Compare current run against baseline
  baseline set            Set or update the baseline snapshot
  baseline promote        Promote current run to baseline
  report                  Generate a static HTML report
  validate                Validate a metrics file against the schema
  export                  Export run history to a portable archive

Global Options:
  --config PATH           Path to flameiq.yaml (default: ./flameiq.yaml)
  --json                  Output results as JSON
  --verbose               Enable verbose logging
  --help                  Show help
```

### Exit Codes

| Code | Meaning |
|---|---|
| `0` | Pass — no regression detected |
| `1` | Regression detected — thresholds exceeded |
| `2` | Configuration error |
| `3` | Invalid or malformed metrics input |

These exit codes are stable and guaranteed across versions. CI pipelines depend on them.

---

## Performance Schema

FlameIQ defines a versioned, open performance data schema. Any tool that outputs schema-compliant JSON can be used directly with FlameIQ.

```json
{
  "schema_version": 1,
  "metadata": {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "commit": "abc123def456",
    "branch": "feature/new-endpoint",
    "timestamp": "2026-01-01T10:00:00Z",
    "environment": "ci",
    "tags": {}
  },
  "metrics": {
    "latency": {
      "mean":   120.5,
      "p50":    110.0,
      "p95":    180.0,
      "p99":    240.0
    },
    "throughput":  950.2,
    "memory_mb":   512.0,
    "cpu_percent":  73.4
  }
}
```

The schema specification lives in [`specs/performance-schema.md`](specs/performance-schema.md). Schema versions are immutable once released. Backward compatibility is guaranteed within major versions.

---

## Statistical Methodology

FlameIQ's regression detection is mathematically transparent. All algorithms are documented with full notation in [`/specs`](specs/).

**Supported detection modes:**

- **Percent-difference thresholds** — simple, predictable, fast
- **Median-based comparison** — noise-resistant baseline strategy
- **Mann–Whitney U test** — non-parametric, distribution-free statistical comparison
- **Confidence intervals** — quantify uncertainty in measurements
- **Variance comparison** — detect instability, not just mean shift
- **Drift slope detection** — catch gradual degradation across many runs *(v2.0)*

If you find a flaw in the math, [open an issue](https://github.com/flameiq/flameiq/issues). Statistical integrity is taken seriously.

---

## Repository Structure

```
flameiq-core/
├── core/               # Deterministic engine — metric comparison & threshold logic
├── schema/             # Versioned performance specification
├── engine/             # Statistical regression algorithms
├── storage/            # Baseline & historical run storage
├── providers/          # Metric ingestion plugin system
├── cli/                # Command-line interface layer
├── reporting/          # Static HTML report generator
├── analysis/           # Drift & correlation analysis (v2.0+)
├── aggregation/        # Distributed run aggregation (v3.0+)
├── contracts/          # Performance contract & budget enforcement (v3.0+)
├── sdk/                # Official language SDKs (v3.0+)
├── api/                # Local read-only API server (v4.0+)
├── docs/               # Full documentation
├── specs/              # Algorithm specifications
├── tests/              # Unit, integration & statistical tests
└── e2e/                # End-to-end CI simulation tests
```

Architectural rule: dependencies flow strictly downward. `core/` has no dependencies on any other FlameIQ module. The CLI is the top-level consumer only. No circular dependencies are permitted.

---

## Roadmap

FlameIQ evolves in five capability epochs:

| Version | Focus | Timeline |
|---|---|---|
| **v1.0** | Deterministic Regression Enforcement | 0–6 months |
| **v2.0** | Performance Evolution Intelligence | 6–12 months |
| **v3.0** | Infrastructure-Grade Scalability | 12–18 months |
| **v4.0** | Ecosystem & Standardization | 18–30 months |
| **v5.0** | Deterministic Intelligence | 30–48 months |

See the full [version roadmap](docs/version-roadmap/) for detailed feature specifications per release.

---

## Security

FlameIQ takes security seriously.

- **No network calls by default.** FlameIQ never phones home.
- **No telemetry unless explicitly enabled.** Opt-in only.
- **Air-gap compatible.** Fully functional with zero internet access.
- **No credentials.** FlameIQ requires no API keys, tokens, or accounts in its OSS form.

To report a security vulnerability, please read [`SECURITY.md`](SECURITY.md) and follow the responsible disclosure process. Do **not** open a public issue for security vulnerabilities.

---

## Contributing

FlameIQ welcomes contributions of all kinds:

- Bug fixes and regression test cases
- New metric provider plugins
- Statistical algorithm improvements
- Language SDK implementations
- Documentation and specification improvements
- Translations

Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request. It covers environment setup, code standards, the RFC process for major changes, and everything you need to get started.

**Looking for somewhere to start?** Check issues labelled [`good first issue`](https://github.com/flameiq/flameiq/labels/good%20first%20issue).

---

## Governance

FlameIQ is a community-driven project with transparent decision-making. See [`GOVERNANCE.md`](GOVERNANCE.md) for maintainer responsibilities, the voting process, and conflict resolution.

Major changes to algorithms, schema versions, or module architecture require a formal [RFC process](RFC_PROCESS.md).

---

## License

FlameIQ is released under the [Apache License 2.0](LICENSE).

---

## Acknowledgements

FlameIQ stands on the shoulders of decades of work in statistical process control, performance engineering, and the open-source CI tooling ecosystem. It was designed to complement — not replace — the benchmarking tools your team already uses.

---

<div align="center">

**Performance is not an optimization step. It is an engineering discipline.**

*FlameIQ exists to make that discipline enforceable, observable, and deterministic.*

</div>