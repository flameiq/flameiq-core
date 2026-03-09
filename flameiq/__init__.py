"""FlameIQ — Deterministic, CI-native performance regression engine.

Make performance a first-class, enforceable engineering signal.
No SaaS. No accounts. No network. Fully offline. Fully deterministic.

Quickstart::

    from flameiq.schema.v1.models import PerformanceSnapshot, Metrics, LatencyMetrics
    from flameiq.core.comparator import compare_snapshots
    from flameiq.storage.baseline_store import BaselineStore

    # Build a snapshot
    snapshot = PerformanceSnapshot.from_dict({
        "schema_version": 1,
        "metadata": {"commit": "abc123", "environment": "ci"},
        "metrics": {"latency": {"mean": 120.0, "p95": 180.0}}
    })

    # Store it as baseline
    store = BaselineStore()
    store.save_baseline(snapshot)

    # Compare later runs
    result = compare_snapshots(store.load_baseline(), new_snapshot)
    print(result.status)   # RegressionStatus.PASS or .REGRESSION

"""

__version__ = "2.0.0-dev"
__author__ = "FlameIQ Core Team"
__license__ = "Apache-2.0"
__url__ = "https://github.com/flameiq/flameiq-core"

__all__ = ["__version__", "__author__", "__license__", "__url__"]
