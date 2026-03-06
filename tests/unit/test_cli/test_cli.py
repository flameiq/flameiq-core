"""Unit tests for the FlameIQ CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from flameiq.cli.main import cli

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def valid_metrics_file(tmp_path: Path) -> Path:
    data = {
        "schema_version": 1,
        "metadata": {"commit": "abc1234", "branch": "main"},
        "metrics": {
            "latency": {"mean": 100.0, "p50": 95.0, "p95": 120.0, "p99": 200.0},
            "throughput": 5000.0,
            "memory_mb": 256.0,
        },
    }
    p = tmp_path / "metrics.json"
    p.write_text(json.dumps(data))
    return p


@pytest.fixture()
def baseline_metrics_file(tmp_path: Path) -> Path:
    data = {
        "schema_version": 1,
        "metadata": {"commit": "base000", "branch": "main"},
        "metrics": {
            "latency": {"mean": 100.0, "p50": 95.0, "p95": 120.0, "p99": 200.0},
            "throughput": 5000.0,
            "memory_mb": 256.0,
        },
    }
    p = tmp_path / "baseline.json"
    p.write_text(json.dumps(data))
    return p


@pytest.fixture()
def regressed_metrics_file(tmp_path: Path) -> Path:
    data = {
        "schema_version": 1,
        "metadata": {"commit": "bad0001", "branch": "main"},
        "metrics": {
            "latency": {"mean": 200.0, "p50": 190.0, "p95": 300.0, "p99": 500.0},
            "throughput": 5000.0,
            "memory_mb": 256.0,
        },
    }
    p = tmp_path / "regressed.json"
    p.write_text(json.dumps(data))
    return p


# ── flameiq --version ─────────────────────────────────────────────────────────


def test_version(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "flameiq" in result.output.lower()


# ── flameiq init ──────────────────────────────────────────────────────────────


def test_init_creates_config(runner: CliRunner, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        assert Path("flameiq.yaml").exists()
        assert Path(".flameiq").exists()


def test_init_existing_config_no_force(runner: CliRunner, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("flameiq.yaml").write_text("existing: true")
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        # Should warn, not overwrite
        assert "already exists" in result.output
        assert Path("flameiq.yaml").read_text() == "existing: true"


def test_init_existing_config_with_force(runner: CliRunner, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("flameiq.yaml").write_text("existing: true")
        result = runner.invoke(cli, ["init", "--force"])
        assert result.exit_code == 0
        assert "existing: true" not in Path("flameiq.yaml").read_text()


def test_init_updates_gitignore(runner: CliRunner, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path(".gitignore").write_text("*.pyc\n")
        runner.invoke(cli, ["init"])
        assert ".flameiq" in Path(".gitignore").read_text()


def test_init_skips_gitignore_if_already_present(runner: CliRunner, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path(".gitignore").write_text("*.pyc\n.flameiq/\n")
        runner.invoke(cli, ["init"])
        # Should not duplicate the entry
        assert Path(".gitignore").read_text().count(".flameiq") == 1


# ── flameiq run ───────────────────────────────────────────────────────────────


def test_run_valid_metrics(runner: CliRunner, valid_metrics_file: Path, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["run", "--metrics", str(valid_metrics_file)])
        assert result.exit_code == 0
        assert "Snapshot loaded" in result.output


def test_run_outputs_json(runner: CliRunner, valid_metrics_file: Path, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["run", "--metrics", str(valid_metrics_file), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "ok"
        assert "metrics" in data


def test_run_writes_output_file(
    runner: CliRunner, valid_metrics_file: Path, tmp_path: Path
) -> None:
    out = tmp_path / "snapshot.json"
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli, ["run", "--metrics", str(valid_metrics_file), "--output", str(out)]
        )
        assert result.exit_code == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert "metrics" in data


def test_run_invalid_file_exits_3(runner: CliRunner, tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not valid json {{")
    result = runner.invoke(cli, ["run", "--metrics", str(bad)])
    assert result.exit_code == 3


# ── flameiq validate ──────────────────────────────────────────────────────────


def test_validate_valid_file(runner: CliRunner, valid_metrics_file: Path, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["validate", str(valid_metrics_file)])
        assert result.exit_code == 0
        assert "Valid" in result.output


def test_validate_outputs_json(runner: CliRunner, valid_metrics_file: Path, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["validate", str(valid_metrics_file), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["valid"] is True


def test_validate_invalid_file_exits_3(runner: CliRunner, tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    result = runner.invoke(cli, ["validate", str(bad)])
    assert result.exit_code == 3


def test_validate_list_providers(
    runner: CliRunner, valid_metrics_file: Path, tmp_path: Path
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["validate", str(valid_metrics_file), "--list-providers"])
        assert result.exit_code == 0
        assert "json" in result.output


# ── flameiq baseline ──────────────────────────────────────────────────────────


def test_baseline_set(runner: CliRunner, valid_metrics_file: Path, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["baseline", "set", "--metrics", str(valid_metrics_file)])
        assert result.exit_code == 0
        assert "Baseline set" in result.output


def test_baseline_set_with_tag(runner: CliRunner, valid_metrics_file: Path, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            ["baseline", "set", "--metrics", str(valid_metrics_file), "--tag", "v1.0.0"],
        )
        assert result.exit_code == 0
        assert "v1.0.0" in result.output


def test_baseline_show(runner: CliRunner, valid_metrics_file: Path, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli, ["baseline", "set", "--metrics", str(valid_metrics_file)])
        result = runner.invoke(cli, ["baseline", "show"])
        assert result.exit_code == 0
        assert "latency" in result.output


def test_baseline_show_no_baseline(runner: CliRunner, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["baseline", "show"])
        assert result.exit_code == 2


def test_baseline_clear(runner: CliRunner, valid_metrics_file: Path, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli, ["baseline", "set", "--metrics", str(valid_metrics_file)])
        result = runner.invoke(cli, ["baseline", "clear"], input="y\n")
        assert result.exit_code == 0
        assert "cleared" in result.output


def test_baseline_promote_hint(runner: CliRunner, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["baseline", "promote"])
        assert result.exit_code == 0
        assert "baseline set" in result.output


# ── flameiq compare ───────────────────────────────────────────────────────────


def test_compare_pass(
    runner: CliRunner,
    valid_metrics_file: Path,
    baseline_metrics_file: Path,
    tmp_path: Path,
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli, ["baseline", "set", "--metrics", str(baseline_metrics_file)])
        result = runner.invoke(
            cli, ["compare", "--metrics", str(valid_metrics_file), "--no-fail-on-regression"]
        )
        assert result.exit_code == 0
        assert "PASS" in result.output


def test_compare_regression_exits_1(
    runner: CliRunner,
    regressed_metrics_file: Path,
    baseline_metrics_file: Path,
    tmp_path: Path,
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli, ["baseline", "set", "--metrics", str(baseline_metrics_file)])
        result = runner.invoke(cli, ["compare", "--metrics", str(regressed_metrics_file)])
        assert result.exit_code == 1
        assert "REGRESSION" in result.output


def test_compare_outputs_json(
    runner: CliRunner,
    valid_metrics_file: Path,
    baseline_metrics_file: Path,
    tmp_path: Path,
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli, ["baseline", "set", "--metrics", str(baseline_metrics_file)])
        result = runner.invoke(
            cli,
            ["compare", "--metrics", str(valid_metrics_file), "--json", "--no-fail-on-regression"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "status" in data
        assert "diffs" in data


def test_compare_no_baseline_exits_2(
    runner: CliRunner, valid_metrics_file: Path, tmp_path: Path
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["compare", "--metrics", str(valid_metrics_file)])
        assert result.exit_code == 2


def test_compare_threshold_override(
    runner: CliRunner,
    regressed_metrics_file: Path,
    baseline_metrics_file: Path,
    tmp_path: Path,
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli, ["baseline", "set", "--metrics", str(baseline_metrics_file)])
        # Very loose threshold — regression should not fire
        result = runner.invoke(
            cli,
            [
                "compare",
                "--metrics",
                str(regressed_metrics_file),
                "--threshold",
                "latency.p95=999%",
                "--no-fail-on-regression",
            ],
        )
        assert result.exit_code == 0


def test_compare_invalid_threshold_format(
    runner: CliRunner,
    valid_metrics_file: Path,
    baseline_metrics_file: Path,
    tmp_path: Path,
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli, ["baseline", "set", "--metrics", str(baseline_metrics_file)])
        result = runner.invoke(
            cli,
            ["compare", "--metrics", str(valid_metrics_file), "--threshold", "badformat"],
        )
        assert result.exit_code == 2


# ── flameiq report ────────────────────────────────────────────────────────────


def test_report_generates_html(
    runner: CliRunner,
    valid_metrics_file: Path,
    baseline_metrics_file: Path,
    tmp_path: Path,
) -> None:
    out = tmp_path / "report.html"
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli, ["baseline", "set", "--metrics", str(baseline_metrics_file)])
        result = runner.invoke(
            cli,
            ["report", "--metrics", str(valid_metrics_file), "--output", str(out)],
        )
        assert result.exit_code == 0
        assert out.exists()
        assert "<html" in out.read_text().lower()


def test_report_no_baseline_exits_2(
    runner: CliRunner, valid_metrics_file: Path, tmp_path: Path
) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["report", "--metrics", str(valid_metrics_file)])
        assert result.exit_code == 2


# ── verbose flag ──────────────────────────────────────────────────────────────


def test_verbose_flag_accepted(runner: CliRunner, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["--verbose", "init"])
        assert result.exit_code == 0
