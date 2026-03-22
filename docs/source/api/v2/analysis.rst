.. _api_v2_analysis:

flameiq.v2.analysis — Analysis Engine
=======================================

The v2 analysis engine provides drift detection, trend analysis,
multi-metric correlation, and performance budget monitoring.
All analysis is deterministic, rule-based, and offline-capable.

.. automodule:: flameiq.v2.analysis.engine
   :members: TrendAnalyzer, TrendReport, TrendPoint,
             DriftAnalyzer, DriftSummary, CorrelationAnalyzer,
             CorrelationReport, CorrelationFinding, BudgetMonitor, BudgetStatus
