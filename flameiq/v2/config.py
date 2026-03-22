"""FlameIQ v2 Configuration.

Loads and validates flameiq.yaml for v2 features.
Fully backward compatible with v1 config files.

New v2 keys:
  version: 2
  history:
    backend: sqlite | jsonl
    max_runs: 500
  drift:
    enabled: true
    threshold_percent: 5.0
    min_runs: 5
    window: 30
  budgets:
    latency.p95: 200
    memory_mb: 1024
  statistics:
    enabled: true
    confidence: 0.95
    noise_tolerance: 0.5
  correlation:
    enabled: true
    change_threshold: 5.0
"""

from __future__ import annotations

import contextlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml

    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


# ── Sub-configs ───────────────────────────────────────────────────────────────


@dataclass
class HistoryConfig:
    """Configuration for run history storage."""

    backend: str = "sqlite"  # "sqlite" | "jsonl"
    max_runs: int = 500
    flameiq_dir: str = ".flameiq"


@dataclass
class DriftConfig:
    """Configuration for performance drift detection."""

    enabled: bool = True
    threshold_percent: float = 5.0
    min_runs: int = 5
    window: int = 30


@dataclass
class StatisticsConfig:
    """Configuration for statistical analysis in comparisons."""

    enabled: bool = False
    confidence: float = 0.95
    noise_tolerance: float = 0.5  # % band to absorb noise


@dataclass
class CorrelationConfig:
    """Configuration for correlation analysis between metrics."""

    enabled: bool = True
    change_threshold: float = 5.0  # min % change to consider correlated


@dataclass
class BaselineConfigV2:
    """Configuration for baseline selection in comparisons."""

    strategy: str = "rolling_median"  # rolling_median | last_successful | tagged_release
    window: int = 10
    name: str = "main"  # named baseline to use


@dataclass
class ConfigV2:
    """Complete FlameIQ v2 project configuration."""

    schema_version: int = 2
    provider: str = "json"

    # Threshold: metric_path -> max allowed % change
    thresholds: dict[str, float] = field(
        default_factory=lambda: {
            "latency.mean": 10.0,
            "latency.p95": 10.0,
            "latency.p99": 15.0,
            "throughput": -5.0,
            "memory_mb": 8.0,
            "cpu_percent": 10.0,
        }
    )

    # Budget: metric_path -> absolute ceiling value
    budgets: dict[str, float] = field(default_factory=dict)

    history: HistoryConfig = field(default_factory=HistoryConfig)
    drift: DriftConfig = field(default_factory=DriftConfig)
    statistics: StatisticsConfig = field(default_factory=StatisticsConfig)
    correlation: CorrelationConfig = field(default_factory=CorrelationConfig)
    baseline: BaselineConfigV2 = field(default_factory=BaselineConfigV2)

    output_dir: str = ".flameiq"
    report_path: str = ".flameiq/report.html"

    @property
    def flameiq_dir(self) -> Path:
        """Get the FlameIQ output directory as a Path."""
        return Path(self.output_dir)


def load_config_v2(path: str | Path | None = None) -> ConfigV2:
    """Load FlameIQ v2 configuration from YAML.

    Falls back to safe defaults if file not found.

    Args:
        path: Path to flameiq.yaml. Defaults to ./flameiq.yaml.

    Returns:
        ConfigV2 instance.
    """
    cfg = ConfigV2()

    if not _HAS_YAML:
        return cfg

    config_path = Path(path) if path else Path("flameiq.yaml")
    if not config_path.exists():
        return cfg

    try:
        with config_path.open(encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
    except Exception:
        return cfg  # Degraded gracefully

    if "provider" in data:
        cfg.provider = str(data["provider"])

    if "output_dir" in data:
        cfg.output_dir = str(data["output_dir"])
        cfg.report_path = str(Path(cfg.output_dir) / "report.html")

    if "report_path" in data:
        cfg.report_path = str(data["report_path"])

    # ── Thresholds
    if "thresholds" in data:
        raw = data["thresholds"]
        if isinstance(raw, dict):
            parsed: dict[str, float] = {}
            for k, v in raw.items():
                with contextlib.suppress(ValueError, TypeError):
                    fv = float(str(v).strip().rstrip("%"))
                    if math.isfinite(fv):
                        parsed[k] = fv
            cfg.thresholds = parsed

    # ── Budgets
    if "budgets" in data:
        raw = data["budgets"]
        if isinstance(raw, dict):
            for k, v in raw.items():
                with contextlib.suppress(ValueError, TypeError):
                    fv = float(str(v).strip())
                    if math.isfinite(fv) and fv > 0:
                        cfg.budgets[k] = fv

    # ── History
    if "history" in data:
        h = data["history"]
        if isinstance(h, dict):
            if "backend" in h and h["backend"] in ("sqlite", "jsonl"):
                cfg.history.backend = h["backend"]
            if "max_runs" in h:
                with contextlib.suppress(ValueError, TypeError):
                    cfg.history.max_runs = max(10, int(h["max_runs"]))

    # ── Drift
    if "drift" in data:
        d = data["drift"]
        if isinstance(d, dict):
            cfg.drift.enabled = bool(d.get("enabled", True))
            if "threshold_percent" in d:
                with contextlib.suppress(ValueError, TypeError):
                    cfg.drift.threshold_percent = float(d["threshold_percent"])
            if "min_runs" in d:
                with contextlib.suppress(ValueError, TypeError):
                    cfg.drift.min_runs = max(3, int(d["min_runs"]))
            if "window" in d:
                with contextlib.suppress(ValueError, TypeError):
                    cfg.drift.window = max(5, int(d["window"]))

    # ── Statistics
    if "statistics" in data:
        s = data["statistics"]
        if isinstance(s, dict):
            cfg.statistics.enabled = bool(s.get("enabled", False))
            if "confidence" in s:
                with contextlib.suppress(ValueError, TypeError):
                    c = float(s["confidence"])
                    if 0 < c < 1:
                        cfg.statistics.confidence = c
            if "noise_tolerance" in s:
                with contextlib.suppress(ValueError, TypeError):
                    cfg.statistics.noise_tolerance = float(s["noise_tolerance"])

    # ── Correlation
    if "correlation" in data:
        c = data["correlation"]
        if isinstance(c, dict):
            cfg.correlation.enabled = bool(c.get("enabled", True))
            if "change_threshold" in c:
                with contextlib.suppress(ValueError, TypeError):
                    cfg.correlation.change_threshold = float(c["change_threshold"])

    # ── Baseline
    if "baseline" in data:
        b = data["baseline"]
        if isinstance(b, dict):
            if "strategy" in b:
                cfg.baseline.strategy = str(b["strategy"])
            if "window" in b:
                with contextlib.suppress(ValueError, TypeError):
                    cfg.baseline.window = max(2, int(b["window"]))
            if "name" in b:
                cfg.baseline.name = str(b["name"])

    return cfg
