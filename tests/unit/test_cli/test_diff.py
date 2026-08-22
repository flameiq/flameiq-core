"""Unit tests for the flameiq diff CLI command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from flameiq.cli.main import cli


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
    p.write_text(json.dumps(data), encoding="utf-8")
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
    p.write_text(json.dumps(data), encoding="utf-8")
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
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_diff_pass(
    runner: CliRunner,
    baseline_metrics_file: Path,
    valid_metrics_file: Path,
    tmp_path: Path,
) -> None:
    """Test comparing two identical/passing metric snapshot files."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            ["diff", str(baseline_metrics_file), str(valid_metrics_file)],
        )
        assert result.exit_code == 0
        assert "PASS" in result.output
        assert "latency.mean" in result.output


def test_diff_regression_exits_1(
    runner: CliRunner,
    baseline_metrics_file: Path,
    regressed_metrics_file: Path,
    tmp_path: Path,
) -> None:
    """Test comparing against a regressed snapshot exits with code 1 by default."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            ["diff", str(baseline_metrics_file), str(regressed_metrics_file)],
        )
        assert result.exit_code == 1
        assert "REGRESSION" in result.output


def test_diff_regression_no_fail_on_regression(
    runner: CliRunner,
    baseline_metrics_file: Path,
    regressed_metrics_file: Path,
    tmp_path: Path,
) -> None:
    """Test comparing regressed snapshot with --no-fail-on-regression exits with code 0."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            [
                "diff",
                str(baseline_metrics_file),
                str(regressed_metrics_file),
                "--no-fail-on-regression",
            ],
        )
        assert result.exit_code == 0
        assert "REGRESSION" in result.output


def test_diff_outputs_json(
    runner: CliRunner,
    baseline_metrics_file: Path,
    valid_metrics_file: Path,
    tmp_path: Path,
) -> None:
    """Test JSON output format produces valid ComparisonResult payload."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            ["diff", str(baseline_metrics_file), str(valid_metrics_file), "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "pass"
        assert data["exit_code"] == 0
        assert data["baseline_commit"] == "base000"
        assert data["current_commit"] == "abc1234"
        assert "diffs" in data
        assert "counts" in data


def test_diff_threshold_override(
    runner: CliRunner,
    baseline_metrics_file: Path,
    regressed_metrics_file: Path,
    tmp_path: Path,
) -> None:
    """Test overriding threshold via CLI flag."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Override with a huge threshold to avoid regression failure
        result = runner.invoke(
            cli,
            [
                "diff",
                str(baseline_metrics_file),
                str(regressed_metrics_file),
                "--threshold",
                "latency.mean=999%",
                "--threshold",
                "latency.p50=999%",
                "--threshold",
                "latency.p95=999%",
                "--threshold",
                "latency.p99=999%",
            ],
        )
        assert result.exit_code == 0
        assert "PASS" in result.output


def test_diff_invalid_threshold_format(
    runner: CliRunner,
    baseline_metrics_file: Path,
    valid_metrics_file: Path,
    tmp_path: Path,
) -> None:
    """Test invalid threshold format exits with code 2."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            [
                "diff",
                str(baseline_metrics_file),
                str(valid_metrics_file),
                "--threshold",
                "invalid_threshold",
            ],
        )
        assert result.exit_code == 2
        assert "Invalid --threshold format" in result.output


def test_diff_invalid_file_exits_3(
    runner: CliRunner,
    baseline_metrics_file: Path,
    tmp_path: Path,
) -> None:
    """Test unparseable metrics file exits with code 3."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("invalid json {", encoding="utf-8")
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            ["diff", str(baseline_metrics_file), str(bad_file)],
        )
        assert result.exit_code == 3


def test_diff_unknown_provider_exits_2(
    runner: CliRunner,
    baseline_metrics_file: Path,
    valid_metrics_file: Path,
    tmp_path: Path,
) -> None:
    """Test unknown provider name exits with code 2."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            [
                "diff",
                str(baseline_metrics_file),
                str(valid_metrics_file),
                "--provider",
                "unknown_provider",
            ],
        )
        assert result.exit_code == 2
