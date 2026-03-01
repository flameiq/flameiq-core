# Contributing to FlameIQ

Thank you for considering a contribution to FlameIQ. This project aims to become global-grade infrastructure — the kind of tool that engineers at any company can trust, embed in internal CI systems, and depend on for years. That bar requires high standards, and this document explains exactly what they are.

Please read this document fully before opening a pull request. PRs that skip the process outlined here will be closed without review.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Ways to Contribute](#ways-to-contribute)
- [Before You Start](#before-you-start)
- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Contribution Workflow](#contribution-workflow)
- [Commit Message Format](#commit-message-format)
- [Branch Naming](#branch-naming)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [RFC Process for Major Changes](#rfc-process-for-major-changes)
- [Writing a Metric Provider Plugin](#writing-a-metric-provider-plugin)
- [Documentation Contributions](#documentation-contributions)
- [Pull Request Review Process](#pull-request-review-process)
- [Release Process](#release-process)
- [Getting Help](#getting-help)

---

## Code of Conduct

All contributors are expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before participating. We are committed to a welcoming, professional, and respectful community.

---

## Ways to Contribute

There are many ways to contribute to FlameIQ, from writing a single line of documentation to designing and implementing a new statistical algorithm. Every contribution is valued.

| Contribution Type | Complexity | RFC Required |
|---|---|---|
| Bug fix | Low | No |
| Documentation improvement | Low | No |
| New example or integration guide | Low | No |
| New metric provider plugin | Medium | No |
| New CLI option or flag | Medium | No |
| New language SDK | Medium | No |
| Minor performance improvement | Medium | No |
| New baseline strategy | High | Yes |
| Statistical algorithm change | High | Yes |
| New schema version | High | Yes |
| New top-level module | High | Yes |
| Backward-incompatible change | High | Yes |

---

## Before You Start

### Check for an existing issue

Before writing any code, check if an [issue already exists](https://github.com/flameiq/flameiq/issues) for your intended change. If it does, leave a comment saying you intend to work on it and wait for a maintainer to assign it to you. This prevents duplicate work.

### Open an issue if one does not exist

For bug fixes, open a bug report. For features or improvements, open a feature request and describe what you want to build. Maintainers will discuss the approach with you before any code is written. This saves everyone time.

### For major changes, start with an RFC

If your change requires an RFC (see the table above), do not write implementation code until the RFC is accepted. Open the RFC first. See the [RFC Process](#rfc-process-for-major-changes) section below.

---

## Development Environment Setup

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.10 or higher (3.12 recommended) |
| Git | 2.40 or higher |
| Make | Required for Makefile targets |
| pre-commit | `pip install pre-commit` |
| Node.js | 18+ (for documentation tooling only) |

### Step-by-step setup

**1. Fork and clone the repository**

```bash
# Fork via GitHub, then:
git clone https://github.com/YOUR_USERNAME/flameiq.git
cd flameiq
git remote add upstream https://github.com/flameiq/flameiq.git
```

**2. Create and activate a virtual environment**

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

**3. Install all dependencies**

```bash
pip install -e ".[dev,test,docs]"
```

This installs FlameIQ in editable mode with all development, testing, and documentation dependencies.

**4. Install pre-commit hooks**

```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

Pre-commit hooks are **not optional**. They enforce code style, type checking, and commit message format on every commit. If a hook fails, the commit is rejected and you must fix the issue before committing.

**5. Verify your setup**

```bash
make check
```

You should see:

```
[OK] Linting passed
[OK] Type checks passed
[OK] All tests passed
[OK] Determinism tests passed
```

If any check fails, your environment is not set up correctly. Do not submit a PR until `make check` passes cleanly.

### Dependency groups

```toml
[project.optional-dependencies]
dev   = ["ruff", "mypy", "pre-commit", "build", "twine"]
test  = ["pytest", "pytest-cov", "hypothesis", "pytest-benchmark", "pytest-xdist"]
docs  = ["mkdocs", "mkdocs-material", "mkdocstrings[python]"]
```

### Makefile targets

| Target | Description |
|---|---|
| `make install` | Install all dependencies in editable mode |
| `make test` | Run the full test suite |
| `make test-unit` | Run unit tests only |
| `make test-integration` | Run integration tests |
| `make test-statistical` | Run determinism and statistical validation tests |
| `make lint` | Run ruff linter |
| `make format` | Auto-format code with ruff |
| `make typecheck` | Run mypy type checking |
| `make check` | Run lint + typecheck + all tests |
| `make docs` | Build the documentation site locally |
| `make benchmark` | Run FlameIQ's internal self-benchmarks |
| `make clean` | Remove build artifacts and caches |

---

## Project Structure

Understanding the project structure is essential before contributing. FlameIQ follows a strict layered architecture. Dependencies flow in one direction only — from lower layers to higher layers. No circular dependencies are permitted.

```
flameiq/
├── core/               # Deterministic engine foundation — sacred ground
├── schema/             # Versioned performance specification — immutable once released
├── engine/             # Statistical & regression algorithms
├── storage/            # Baseline & historical run storage
├── providers/          # Metric ingestion plugin system
├── cli/                # Top-level CLI consumer — no business logic here
├── reporting/          # Static HTML report generation
├── analysis/           # Drift & correlation analysis (v2.0+)
├── aggregation/        # Distributed run aggregation (v3.0+)
├── contracts/          # Performance contract & budget enforcement (v3.0+)
├── sdk/                # Official language SDKs (v3.0+)
├── api/                # Local read-only API (v4.0+)
├── docs/               # Full documentation
├── specs/              # Algorithm specifications (treated as RFCs)
├── tests/              # All test suites
└── e2e/                # End-to-end CI simulation tests
```

**Module dependency rules:**

| Module | Allowed to import from |
|---|---|
| `schema/` | Nothing else in FlameIQ |
| `core/` | `schema/` only |
| `engine/` | `core/`, `schema/` |
| `storage/` | `core/`, `schema/` |
| `analysis/` | `engine/`, `storage/`, `core/`, `schema/` |
| `providers/` | `schema/` only |
| `reporting/` | `analysis/`, `engine/`, `schema/` |
| `cli/` | Any layer — top-level consumer only |

Violations of these rules will fail a CI lint check. Do not attempt to work around them.

---

## Contribution Workflow

### 1. Sync your fork

Before starting any work, sync your fork with the upstream repository:

```bash
git fetch upstream
git checkout main
git merge upstream/main
```

### 2. Create a branch

```bash
git checkout -b feat/your-feature-name
```

See [Branch Naming](#branch-naming) for the required format.

### 3. Write your code

Follow the [Code Standards](#code-standards) section precisely. Every new function needs type annotations. Every new module needs tests.

### 4. Write your tests

No PR will be merged without adequate test coverage. See [Testing Requirements](#testing-requirements) for what is expected.

### 5. Run checks locally

```bash
make check
```

This must pass completely before you push. Do not open a PR against a red CI status.

### 6. Commit your changes

```bash
git add .
git commit -m "feat(engine): add confidence interval support"
```

See [Commit Message Format](#commit-message-format).

### 7. Push and open a Pull Request

```bash
git push origin feat/your-feature-name
```

Open a PR against the `main` branch. Fill in the PR template completely. Incomplete PRs will be closed.

### 8. Respond to review feedback

Address all review comments. Push additional commits — do not force-push during the review cycle as it makes the review harder to follow.

### 9. Merge

A maintainer will squash-merge your PR once it is approved. Never self-merge, even if you have the permissions.

---

## Commit Message Format

FlameIQ uses [Conventional Commits](https://www.conventionalcommits.org/). The pre-commit hook will reject non-conforming messages.

**Format:**

```
<type>(<scope>): <short description>

[optional body]

[optional footer(s)]
```

**Types:**

| Type | Use for |
|---|---|
| `feat` | A new feature or capability |
| `fix` | A bug fix |
| `docs` | Documentation only changes |
| `refactor` | Code restructure without behavior change |
| `test` | Adding or improving tests |
| `perf` | A performance improvement |
| `chore` | Build system, dependency, or tooling changes |
| `ci` | CI configuration changes |
| `build` | Changes to the build system |

**Examples:**

```bash
feat(engine): add Mann-Whitney U test support
fix(storage): handle NaN values in baseline comparison
docs(specs): add mathematical notation for drift algorithm
test(core): add determinism validation for threshold comparator
refactor(cli): extract JSON output formatting to shared utility
perf(engine): optimize percentile calculation for large sample sets
chore(deps): upgrade pytest to 8.x
```

**Rules:**

- The short description must be lowercase and imperative: *add*, *fix*, *update* — not *Added*, *Fixed*, *Updates*
- Maximum 72 characters in the first line
- Reference the issue number in the footer: `Closes #123`

---

## Branch Naming

| Pattern | Use for |
|---|---|
| `feat/short-description` | New feature |
| `fix/short-description` | Bug fix |
| `docs/short-description` | Documentation |
| `refactor/short-description` | Refactoring |
| `test/short-description` | Test additions |
| `perf/short-description` | Performance improvement |
| `chore/short-description` | Tooling, build, CI |
| `rfc/short-description` | RFC proposal |

Use hyphens, not underscores. Keep it short and descriptive:

```bash
feat/drift-detection-slope
fix/baseline-nan-edge-case
docs/statistical-methodology-spec
rfc/schema-v2-proposal
```

---

## Code Standards

FlameIQ enforces strict code quality standards because it is designed to be infrastructure that engineers at any organization can trust and embed in critical systems.

### Linting and formatting

We use [ruff](https://github.com/astral-sh/ruff) for both linting and formatting. It runs automatically on every commit via pre-commit.

```bash
make lint      # Check for issues
make format    # Auto-fix formatting
```

### Type annotations

All public functions and class methods **must** have complete type annotations. We run mypy in strict mode. Using `Any` is strongly discouraged — if you genuinely need it, add a comment explaining why.

```python
# Correct
def compare_metrics(
    baseline: MetricSnapshot,
    current: MetricSnapshot,
    config: ThresholdConfig,
) -> ComparisonResult:
    ...

# Will fail mypy — do not do this
def compare_metrics(baseline, current, config):
    ...
```

### Docstrings

All public functions, classes, and modules must have Google-style docstrings:

```python
def detect_regression(
    baseline: float,
    current: float,
    threshold_pct: float,
) -> RegressionResult:
    """Detect whether a performance regression has occurred.

    Uses percentage-difference comparison against a configured threshold.
    This function is deterministic: same inputs always produce same output.

    Args:
        baseline: Baseline metric value from the reference run.
        current: Current metric value from the measured run.
        threshold_pct: Maximum allowed percent increase (e.g., 10.0 = 10%).

    Returns:
        RegressionResult with is_regression flag and change_percent.

    Raises:
        ValidationError: If baseline is zero or threshold is negative.
    """
```

### Architecture rules

These are enforced in CI. Violations cause build failures.

- **No business logic in `cli/`** — the CLI layer only parses arguments and calls lower modules.
- **No network calls in `core/` or `engine/`** — these modules must work fully offline.
- **No global mutable state** — all functions must be pure or explicitly document side effects.
- **No bare `print()` in library code** — use Python's `logging` module with appropriate levels.
- **No hardcoded file paths** — all paths must be configurable or constructed with `pathlib.Path`.
- **Typed exceptions only** — raise from the FlameIQ exception hierarchy in `core/errors.py`, never raise bare `Exception`.
- **No `Any` without justification** — if you must use `Any`, add a `# type: ignore[assignment]  # reason:` comment.

### Determinism requirements (core/ and engine/ only)

Code in `core/` and `engine/` is held to an additional standard:

- **No `random` module** without a fixed, documented seed
- **No `datetime.now()`** — timestamps must be passed in as arguments
- **Explicit floating-point precision** — document rounding strategy for every calculation
- All functions must pass determinism tests: given the same inputs, they must produce the same output across 100 consecutive runs

---

## Testing Requirements

### Test categories and locations

| Category | Location | Description |
|---|---|---|
| Unit | `tests/unit/` | Test individual functions in isolation. No I/O. Fast. |
| Integration | `tests/integration/` | Test module interactions. May use tmp filesystem. |
| Statistical | `tests/statistical_validation/` | Validate algorithm correctness with known inputs/outputs. |
| Regression scenarios | `tests/regression_scenarios/` | Named scenario fixtures with expected outputs. |
| Compatibility | `tests/compatibility_tests/` | Verify schema backward compatibility. |
| End-to-end | `e2e/` | Full CI pipeline simulation. Runs in CI only. |

### Coverage requirements

| Module | Minimum Coverage |
|---|---|
| `core/` | 95% |
| `schema/` | 100% (all validation paths) |
| `engine/` | 90% |
| `storage/` | 85% |
| `analysis/` | 85% |
| `providers/` | 80% per provider |
| `cli/` | 75% |

PRs that reduce coverage below these thresholds will not be merged.

### Writing a statistical test

Statistical tests must use fixed, documented inputs and verify both the decision and the supporting statistics:

```python
def test_mann_whitney_detects_clear_regression() -> None:
    """Verify that a clearly slower distribution is detected as a regression.

    Uses hand-crafted distributions where current is ~40% slower.
    Expected: regression=True, p_value < 0.05, large effect size.
    """
    baseline_samples = [100, 102, 98, 101, 99, 103, 100, 101]
    current_samples  = [140, 142, 138, 145, 141, 143, 139, 144]

    result = mann_whitney_compare(
        baseline=baseline_samples,
        current=current_samples,
        confidence=0.95,
    )

    assert result.is_regression is True
    assert result.p_value < 0.05
    assert result.effect_size > 0.8  # Large effect (Cohen's d convention)
```

### Writing a determinism test

Any function in `core/` or `engine/` that you modify must have a determinism test:

```python
def test_comparator_is_deterministic() -> None:
    """The comparator must return identical results across repeated calls."""
    fixture = load_fixture("regression_scenario_01.json")

    results = [compare_metrics(fixture) for _ in range(100)]

    first = results[0]
    assert all(r == first for r in results[1:]), (
        "Comparator produced non-deterministic output"
    )
```

---

## RFC Process for Major Changes

Major changes to FlameIQ require a formal Request For Comments process before any implementation begins.

### When is an RFC required?

- Any change to a statistical algorithm
- Any new schema version
- Any new top-level module introduction
- Any change to baseline strategies
- Any change to exit codes or output format
- Any backward-incompatible change of any kind

### RFC lifecycle

1. **Draft** — create `docs/rfcs/XXXX-short-title.md` from the template on a branch named `rfc/short-title`
2. **Discussion** — open a GitHub Discussion linking to the RFC. Minimum 7-day comment period.
3. **Revised** — update the RFC based on community feedback
4. **Vote** — maintainer team votes: simple majority for minor RFCs, two-thirds for major changes
5. **Accepted / Rejected** — decision recorded in the RFC document
6. **Implemented** — RFC merged to `docs/rfcs/`. Implementation PR references the RFC number.
7. **Final** — specification file added to `specs/` with full mathematical documentation

### RFC template

```markdown
# RFC-XXXX: [Short Title]

## Status
Draft

## Motivation
Why is this change needed? What problem does it solve?

## Proposed Change
Detailed technical description.

## Mathematical Specification (if applicable)
Full notation. All variables defined. Edge cases documented.

## Backward Compatibility
How are existing users affected? What is the migration path?

## Alternatives Considered
What else was evaluated and why was it rejected?

## Test Plan
How will correctness be verified?
```

---

## Writing a Metric Provider Plugin

Providers are one of the most impactful contributions you can make. They allow FlameIQ to ingest benchmark output from any language or framework.

### The MetricProvider interface

```python
from abc import ABC, abstractmethod
from flameiq.schema.v1 import FlameIQSnapshot

class MetricProvider(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier, e.g. 'pytest-benchmark'"""
        ...

    @abstractmethod
    def collect(self, source: str) -> dict:
        """Read raw benchmark data from source path."""
        ...

    @abstractmethod
    def validate(self, raw: dict) -> bool:
        """Return True if raw data can be processed by this provider."""
        ...

    @abstractmethod
    def normalize(self, raw: dict) -> FlameIQSnapshot:
        """Transform raw data into FlameIQSnapshot."""
        ...
```

### Provider requirements

- Must be stateless
- Must be deterministic — same input, same output
- Must include unit tests with at least three fixture files: a valid input, an invalid input, and an edge-case input
- Must include documentation in `docs/providers/your-provider.md`
- Must be registered in `providers/registry.py`

---

## Documentation Contributions

Documentation lives in `docs/` and is built with MkDocs. To run the docs site locally:

```bash
make docs
# Opens at http://localhost:8000
```

Algorithm specifications live in `specs/` and are treated with the same rigor as code. If you find an error in a specification, open an issue or PR. Changes to specs for existing stable algorithms require an RFC.

---

## Pull Request Review Process

### What reviewers check

- Does the code follow the architecture rules?
- Are type annotations complete?
- Does `make check` pass?
- Are the tests adequate for the change?
- Are docstrings present and correct?
- For statistical changes: is the math documented and correct?
- For schema changes: is backward compatibility maintained?

### Review timeline

Maintainers aim to provide an initial review response within **5 business days**. Complex RFCs may take longer.

### What makes a PR easy to review

- Small, focused changes. One PR per concern.
- A clear description of what changed and why.
- Tests that demonstrate the intended behavior.
- No unrelated formatting changes mixed in.

---

## Release Process

FlameIQ uses [Semantic Versioning](https://semver.org/). Releases are managed by the core maintainer team.

- **PATCH** (1.0.x) — bug fixes and documentation updates
- **MINOR** (1.x.0) — new backward-compatible features
- **MAJOR** (x.0.0) — breaking changes (rare, require RFC)

Contributors are not expected to manage releases. Your job is to get the code into `main` — maintainers handle the rest.

---

## Getting Help

If you are stuck, have questions about the codebase, or are unsure whether your contribution is in scope:

- **GitHub Discussions** — best place for questions about the project and design decisions
- **GitHub Issues** — for bug reports and concrete feature requests
- Issues labelled [`help wanted`](https://github.com/flameiq/flameiq/labels/help%20wanted) are explicitly looking for community contributors
- Issues labelled [`good first issue`](https://github.com/flameiq/flameiq/labels/good%20first%20issue) are scoped specifically for new contributors

---

*Thank you for contributing to FlameIQ. Every contribution, no matter its size, helps build something the global engineering community can rely on.*
