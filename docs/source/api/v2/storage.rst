.. _api_v2_storage:

flameiq.v2.storage — Persistent History
=========================================

The v2 storage engine provides SQLite-backed persistent run history
and named baseline management. All data stays local in ``.flameiq/``.

.. automodule:: flameiq.v2.storage.history
   :members: HistoryStore, HistoryEntry, BaselineStoreV2,
             rolling_median_baseline

Storage layout
--------------

.. code-block:: text

   .flameiq/
   ├── history/
   │   ├── runs.db        ← SQLite database (indexed queries)
   │   └── runs.jsonl     ← JSONL audit log (human-readable)
   └── baselines/
       ├── main.json      ← default named baseline
       ├── release-1.2.json
       └── staging.json

Design principles
-----------------

- **Local only** — all data stays in ``.flameiq/``. Zero network calls.
- **SQLite + JSONL** — fast indexed queries via SQLite; human-readable
  audit trail via JSONL sidecar.
- **Named baselines** — stored as individual JSON files. No auto-promotion.
  All baseline changes are explicit.
- **Air-gap safe** — no external dependencies at runtime.

.. warning::

   Never commit ``.flameiq/baselines/`` or ``.flameiq/history/`` to
   your repository. Baselines contain environment-specific measurements.
   Use your CI cache mechanism to persist them between runs.
