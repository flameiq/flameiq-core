"""FlameIQ v2 Storage Engine.

Persistent local run history backed by SQLite + JSONL audit log.

Design principles:
  - All data stays local, in .flameiq/
  - SQLite for fast indexed queries (branch, commit, timestamp)
  - JSONL sidecar for human-readable audit trail
  - Named baselines as individual JSON files (explicit promotion)
  - No auto-promotion of baselines (trust through explicitness)
  - Air-gap safe: zero network calls
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from flameiq.v2.schema import MetadataV2, MetricsV2, RunV2

# ── Schema SQL ────────────────────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id       TEXT PRIMARY KEY,
    commit_sha   TEXT NOT NULL DEFAULT '',
    branch      TEXT NOT NULL DEFAULT '',
    environment TEXT NOT NULL DEFAULT 'ci',
    timestamp   TEXT NOT NULL,
    tags_json   TEXT NOT NULL DEFAULT '{}',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    full_json   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_branch    ON runs(branch);
CREATE INDEX IF NOT EXISTS idx_commit_sha ON runs(commit_sha);
CREATE INDEX IF NOT EXISTS idx_timestamp ON runs(timestamp);
"""


# ── History Entry ─────────────────────────────────────────────────────────────


@dataclass
class HistoryEntry:
    """A single run entry from history, with deserialized run object."""

    run_id: str
    commit: str
    branch: str
    environment: str
    timestamp: str
    tags: dict[str, str]
    run: RunV2

    def metric_value(self, key: str) -> float | None:
        """Get a metric value by key from the flattened metrics."""
        return self.run.metrics.flat().get(key)


# ── History Store ─────────────────────────────────────────────────────────────


class HistoryStore:
    """Local persistent run history.

    Every run is stored in SQLite and appended to runs.jsonl.

    Usage:
        store = HistoryStore(Path(".flameiq"))
        store.record(run)
        entries = store.get_last_n(30)
    """

    def __init__(self, root: Path) -> None:
        """Initialize storage at the given root directory."""
        self._dir = Path(root) / "history"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db = self._dir / "runs.db"
        self._jsonl = self._dir / "runs.jsonl"
        self._conn = self._connect()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db))
        conn.row_factory = sqlite3.Row
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        return conn

    # ── Write ─────────────────────────────────────────────────────────────────

    def record(self, run: RunV2) -> None:
        """Store a run in SQLite and append to JSONL audit log."""
        data = run.to_dict()
        self._conn.execute(
            """INSERT OR REPLACE INTO runs
               (run_id, commit_sha, branch, environment, timestamp,
                tags_json, metrics_json, full_json)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                run.run_id,
                run.metadata.commit,  # stored as commit_sha
                run.metadata.branch,
                run.metadata.environment,
                run.metadata.timestamp,
                json.dumps(run.metadata.tags),
                json.dumps(run.metrics.to_dict()),
                json.dumps(data),
            ),
        )
        self._conn.commit()
        with self._jsonl.open("a") as f:
            f.write(json.dumps(data) + "\n")

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, run_id: str) -> HistoryEntry | None:
        """Fetch a single run by its ID."""
        row = self._conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return self._row(row) if row else None

    def get_by_commit(self, commit: str) -> list[HistoryEntry]:
        """Fetch all runs for a given commit SHA."""
        rows = self._conn.execute(
            "SELECT * FROM runs WHERE commit_sha = ? ORDER BY timestamp DESC", (commit,)
        ).fetchall()
        return [self._row(r) for r in rows]

    def get_last_n(self, n: int = 30, branch: str | None = None) -> list[HistoryEntry]:
        """Returns up to n entries in chronological order (oldest first)."""
        if branch:
            rows = self._conn.execute(
                "SELECT * FROM runs WHERE branch = ? ORDER BY timestamp DESC LIMIT ?",
                (branch, n),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM runs ORDER BY timestamp DESC LIMIT ?", (n,)
            ).fetchall()
        entries = [self._row(r) for r in rows]
        entries.reverse()  # chronological order
        return entries

    def get_metric_series(
        self, metric_key: str, n: int = 50, branch: str | None = None
    ) -> list[tuple[str, str, float]]:
        """Returns list of (timestamp, commit, value) for a metric key.

        Used by drift detection and trend charts.
        """
        entries = self.get_last_n(n, branch=branch)
        return [
            (e.timestamp, e.commit, v)
            for e in entries
            if (v := e.metric_value(metric_key)) is not None
        ]

    def count(self, branch: str | None = None) -> int:
        """Count total runs, optionally filtered by branch."""
        if branch:
            row = self._conn.execute(
                "SELECT COUNT(*) as c FROM runs WHERE branch = ?", (branch,)
            ).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) as c FROM runs").fetchone()
        return int(row["c"])

    def all_metric_keys(self, n: int = 100) -> set[str]:
        """Return all metric keys seen in recent history."""
        entries = self.get_last_n(n)
        keys: set[str] = set()
        for e in entries:
            keys.update(e.run.metrics.flat().keys())
        return keys

    # ── Internal ──────────────────────────────────────────────────────────────

    def _row(self, row: sqlite3.Row) -> HistoryEntry:
        run = RunV2.from_dict(json.loads(row["full_json"]))
        return HistoryEntry(
            run_id=row["run_id"],
            commit=row["commit_sha"],
            branch=row["branch"],
            environment=row["environment"],
            timestamp=row["timestamp"],
            tags=json.loads(row["tags_json"]),
            run=run,
        )

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()


# ── Baseline Store ────────────────────────────────────────────────────────────


class BaselineStoreV2:
    """Named baseline management.

    Baselines are stored as individual JSON files.
    Explicit promotion only — no auto-promotion (trust through explicitness).

    .flameiq/baselines/<name>.json
    """

    def __init__(self, root: Path) -> None:
        """Initialize the baseline storage directory."""
        self._dir = Path(root) / "baselines"
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, run: RunV2, name: str = "main") -> Path:
        """Save a run as a named baseline."""
        path = self._dir / f"{name}.json"
        path.write_text(json.dumps(run.to_dict(), indent=2))
        return path

    def load(self, name: str = "main") -> RunV2 | None:
        """Load a baseline by name, or None if not found."""
        path = self._dir / f"{name}.json"
        if not path.exists():
            return None
        return RunV2.from_dict(json.loads(path.read_text()))

    def promote(self, source: str, target: str = "main") -> bool:
        """Explicitly promote one named baseline to another name."""
        run = self.load(source)
        if run is None:
            return False
        self.save(run, target)
        return True

    def delete(self, name: str) -> bool:
        """Delete a baseline, returning True if it existed."""
        path = self._dir / f"{name}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def list_names(self) -> list[str]:
        """List all baseline names currently stored."""
        return sorted(p.stem for p in self._dir.glob("*.json"))


# ── Rolling median baseline ───────────────────────────────────────────────────


def rolling_median_baseline(entries: list[HistoryEntry], window: int = 10) -> RunV2 | None:
    """Compute a synthetic baseline from the rolling median of recent runs.

    Useful when no explicit baseline has been set.
    """
    if not entries:
        return None
    recent = entries[-window:]

    all_keys: set[str] = set()
    for e in recent:
        all_keys.update(e.run.metrics.flat().keys())

    medians: dict[str, float] = {}
    for key in all_keys:
        vals = [v for e in recent if (v := e.metric_value(key)) is not None]
        if vals:
            medians[key] = _median(vals)

    metrics = _medians_to_metrics(medians)
    return RunV2(
        metadata=MetadataV2(
            commit="rolling_median",
            branch=entries[-1].branch if entries else "",
            environment="baseline",
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
        metrics=metrics,
    )


def _medians_to_metrics(m: dict[str, float]) -> MetricsV2:
    from flameiq.v2.schema import LatencyV2

    lat = LatencyV2(
        mean=m.get("latency.mean"),
        p50=m.get("latency.p50"),
        p95=m.get("latency.p95"),
        p99=m.get("latency.p99"),
    )
    return MetricsV2(
        latency=lat if any(v is not None for v in [lat.mean, lat.p50, lat.p95, lat.p99]) else None,
        throughput=m.get("throughput"),
        memory_mb=m.get("memory_mb"),
        cpu_percent=m.get("cpu_percent"),
        custom={k.replace("custom.", ""): v for k, v in m.items() if k.startswith("custom.")},
    )


def _median(vals: list[float]) -> float:
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0
