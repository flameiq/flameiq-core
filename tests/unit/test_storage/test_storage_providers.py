"""Tests for storage and providers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flameiq.core.errors import (
    BaselineCorruptedError,
    BaselineNotFoundError,
    MetricsFileNotFoundError,
    ProviderError,
    ProviderNotFoundError,
)
from flameiq.providers.json_provider import JsonProvider
from flameiq.providers.registry import get_provider, list_providers
from flameiq.storage.baseline_store import BaselineStore
from tests.fixtures.test_fixtures import make_snapshot

pytestmark = pytest.mark.unit

# ── Valid snapshot dict ──────────────────────────────────────────────────────
VALID = {
    "schema_version": 1,
    "metadata": {"commit": "abc123", "branch": "main", "environment": "ci"},
    "metrics": {
        "latency": {"mean": 100.0, "p95": 150.0, "p99": 200.0},
        "throughput": 1000.0,
        "memory_mb": 512.0,
    },
}


# ---------------------------------------------------------------------------
# JsonProvider
# ---------------------------------------------------------------------------
@pytest.fixture
def json_file(tmp_path: Path) -> Path:
    f = tmp_path / "metrics.json"
    f.write_text(json.dumps(VALID), encoding="utf-8")
    return f


class TestJsonProvider:
    def test_name(self):
        assert JsonProvider().name == "json"

    def test_load_valid_file(self, json_file: Path):
        snap = JsonProvider().load(str(json_file))
        assert snap.schema_version == 1
        assert snap.metadata.commit == "abc123"
        assert snap.metrics.latency.p95 == 150.0

    def test_file_not_found(self):
        with pytest.raises(MetricsFileNotFoundError):
            JsonProvider().load("/nonexistent/path/metrics.json")

    def test_invalid_json(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("{ not valid json }", encoding="utf-8")
        with pytest.raises(ProviderError):
            JsonProvider().load(str(bad))

    def test_wrong_schema_version(self, tmp_path: Path):
        data = {**VALID, "schema_version": 2}
        f = tmp_path / "v2.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ProviderError):
            JsonProvider().load(str(f))

    def test_validate_missing_metrics(self):
        assert JsonProvider().validate({"schema_version": 1}) is False

    def test_validate_empty_metrics(self):
        assert JsonProvider().validate({"schema_version": 1, "metrics": {}}) is False

    def test_validate_valid(self):
        assert JsonProvider().validate(VALID) is True


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------
class TestProviderRegistry:
    def test_list_providers(self):
        providers = list_providers()
        assert "json" in providers
        assert "pytest-benchmark" in providers

    def test_get_known_provider(self):
        p = get_provider("json")
        assert p.name == "json"

    def test_get_unknown_provider(self):
        with pytest.raises(ProviderNotFoundError):
            get_provider("nonexistent-tool")


# ---------------------------------------------------------------------------
# BaselineStore
# ---------------------------------------------------------------------------
@pytest.fixture
def store(tmp_path: Path) -> BaselineStore:
    return BaselineStore(root=tmp_path / ".flameiq")


class TestBaselineStore:
    def test_has_baseline_false_initially(self, store: BaselineStore):
        assert store.has_baseline() is False

    def test_load_raises_when_no_baseline(self, store: BaselineStore):
        with pytest.raises(BaselineNotFoundError):
            store.load_baseline()

    def test_save_and_load_roundtrip(self, store: BaselineStore):
        snap = make_snapshot(p95=125.0, commit="test-commit")
        store.save_baseline(snap)
        loaded = store.load_baseline()
        assert loaded.metrics.latency.p95 == 125.0
        assert loaded.metadata.commit == "test-commit"

    def test_has_baseline_true_after_save(self, store: BaselineStore):
        store.save_baseline(make_snapshot())
        assert store.has_baseline() is True

    def test_history_grows_with_saves(self, store: BaselineStore):
        store.save_baseline(make_snapshot(commit="run-1"))
        store.save_baseline(make_snapshot(commit="run-2"))
        store.save_baseline(make_snapshot(commit="run-3"))
        history = store.load_history()
        assert len(history) == 3
        assert history[0].metadata.commit == "run-1"
        assert history[2].metadata.commit == "run-3"

    def test_history_empty_when_no_file(self, store: BaselineStore):
        assert store.load_history() == []

    def test_clear_removes_all(self, store: BaselineStore):
        store.save_baseline(make_snapshot())
        store.clear()
        assert not store.has_baseline()
        assert store.load_history() == []

    def test_corrupted_baseline_raises(self, store: BaselineStore):
        store._ensure_dirs()
        store.baseline_path.write_text("{ bad json }", encoding="utf-8")
        with pytest.raises(BaselineCorruptedError):
            store.load_baseline()

    def test_save_creates_dirs_automatically(self, tmp_path: Path):
        deep_store = BaselineStore(root=tmp_path / "a" / "b" / ".flameiq")
        deep_store.save_baseline(make_snapshot())
        assert deep_store.has_baseline()
