"""Integration tests — full baseline-set → compare pipeline."""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003

import pytest

from flameiq.core.comparator import compare_snapshots
from flameiq.core.models import RegressionStatus
from flameiq.providers.json_provider import JsonProvider
from flameiq.reporting.html_generator import generate_report
from flameiq.storage.baseline_store import BaselineStore

pytestmark = pytest.mark.integration


def _write_metrics(path: Path, p95: float, throughput: float, commit: str) -> Path:
    data = {
        "schema_version": 1,
        "metadata": {"commit": commit, "branch": "main", "environment": "ci"},
        "metrics": {
            "latency": {"mean": p95 * 0.8, "p95": p95, "p99": p95 * 1.4},
            "throughput": throughput,
            "memory_mb": 512.0,
        },
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def store(tmp_path: Path) -> BaselineStore:
    return BaselineStore(root=tmp_path / ".flameiq")


@pytest.fixture
def baseline_file(tmp_path: Path) -> Path:
    return _write_metrics(
        tmp_path / "baseline.json", p95=120.0, throughput=1000.0, commit="base-001"
    )


@pytest.fixture
def passing_file(tmp_path: Path) -> Path:
    return _write_metrics(tmp_path / "passing.json", p95=123.0, throughput=990.0, commit="feat-001")


@pytest.fixture
def regression_file(tmp_path: Path) -> Path:
    return _write_metrics(
        tmp_path / "regression.json", p95=160.0, throughput=820.0, commit="slow-001"
    )


class TestFullPipeline:
    def test_baseline_then_pass(
        self, store: BaselineStore, baseline_file: Path, passing_file: Path
    ):
        provider = JsonProvider()
        store.save_baseline(provider.load(str(baseline_file)))
        result = compare_snapshots(store.load_baseline(), provider.load(str(passing_file)))
        assert result.status == RegressionStatus.PASS
        assert result.exit_code == 0

    def test_baseline_then_regression(
        self, store: BaselineStore, baseline_file: Path, regression_file: Path
    ):
        provider = JsonProvider()
        store.save_baseline(provider.load(str(baseline_file)))
        result = compare_snapshots(store.load_baseline(), provider.load(str(regression_file)))
        assert result.status == RegressionStatus.REGRESSION
        assert result.exit_code == 1

    def test_history_accumulates(
        self, store: BaselineStore, baseline_file: Path, passing_file: Path
    ):
        provider = JsonProvider()
        store.save_baseline(provider.load(str(baseline_file)))
        store.save_baseline(provider.load(str(passing_file)))
        assert len(store.load_history()) == 2

    def test_html_report_generated(
        self, store: BaselineStore, baseline_file: Path, passing_file: Path, tmp_path: Path
    ):
        provider = JsonProvider()
        baseline_snap = provider.load(str(baseline_file))
        current_snap = provider.load(str(passing_file))
        store.save_baseline(baseline_snap)
        result = compare_snapshots(baseline_snap, current_snap)

        out = tmp_path / "report.html"
        generate_report(result, baseline_snap, current_snap, out)

        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "FlameIQ" in content
        assert "PASS" in content

    def test_clear_then_reload_empty(self, store: BaselineStore, baseline_file: Path):
        store.save_baseline(JsonProvider().load(str(baseline_file)))
        store.clear()
        assert not store.has_baseline()

    def test_json_output_valid(
        self, store: BaselineStore, baseline_file: Path, regression_file: Path
    ):
        provider = JsonProvider()
        store.save_baseline(provider.load(str(baseline_file)))
        result = compare_snapshots(store.load_baseline(), provider.load(str(regression_file)))
        d = result.to_dict()
        assert d["status"] == "regression"
        assert d["exit_code"] == 1
        assert len(d["diffs"]) > 0
        assert all("metric_key" in diff for diff in d["diffs"])
