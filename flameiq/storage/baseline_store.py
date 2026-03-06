"""FlameIQ local baseline storage.

All storage is file-based. Zero external services required.

Layout::

    .flameiq/
    └── baselines/
        ├── current.json   ← active baseline (pretty-printed JSON)
        └── history.jsonl  ← append-only run log (one JSON object per line)

Default root: ``.flameiq/`` in the current working directory.
Override via ``BaselineStore(root=Path("/custom/path"))``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from flameiq.core.errors import (
    BaselineCorruptedError,
    BaselineNotFoundError,
    StorageError,
)

if TYPE_CHECKING:
    from flameiq.schema.v1.models import PerformanceSnapshot

logger = logging.getLogger(__name__)

_CURRENT_FILE = "current.json"
_HISTORY_FILE = "history.jsonl"


class BaselineStore:
    """Manages local baseline and run-history storage.

    Args:
        root: The ``.flameiq`` root directory.
              Defaults to ``Path(".flameiq")`` relative to ``cwd``.

    Example::

        store = BaselineStore()
        store.save_baseline(snapshot)
        baseline = store.load_baseline()
        history  = store.load_history()
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = (root or Path(".flameiq")).resolve()
        self._dir = self._root / "baselines"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def baseline_path(self) -> Path:
        """Path to the ``current.json`` baseline file."""
        return self._dir / _CURRENT_FILE

    @property
    def history_path(self) -> Path:
        """Path to the ``history.jsonl`` append-only log."""
        return self._dir / _HISTORY_FILE

    def has_baseline(self) -> bool:
        """Return ``True`` if a baseline snapshot file exists."""
        return self.baseline_path.exists()

    def load_baseline(self) -> PerformanceSnapshot:
        """Load the current baseline snapshot from disk.

        Returns:
            The stored :class:`~flameiq.schema.v1.models.PerformanceSnapshot`.

        Raises:
            :class:`~flameiq.core.errors.BaselineNotFoundError`:
                If no baseline has been set.
            :class:`~flameiq.core.errors.BaselineCorruptedError`:
                If the file cannot be parsed.
        """
        from flameiq.schema.v1.models import PerformanceSnapshot

        path = self.baseline_path
        if not path.exists():
            raise BaselineNotFoundError(str(path))

        raw = path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BaselineCorruptedError(str(path), f"JSON parse error: {exc}") from exc

        try:
            return PerformanceSnapshot.from_dict(data)
        except Exception as exc:
            raise BaselineCorruptedError(str(path), str(exc)) from exc

    def save_baseline(self, snapshot: PerformanceSnapshot) -> None:
        """Save *snapshot* as the current baseline and append to history.

        Args:
            snapshot: The snapshot to persist.

        Raises:
            :class:`~flameiq.core.errors.StorageError`: On write failure.
        """
        self._ensure_dirs()
        payload = json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False)
        try:
            self.baseline_path.write_text(payload, encoding="utf-8")
            logger.info("Baseline written → %s", self.baseline_path)
        except OSError as exc:
            raise StorageError(f"Failed to write baseline: {exc}") from exc

        self._append_history(snapshot)

    def load_history(self) -> list[PerformanceSnapshot]:
        """Load all historical snapshots from the JSONL log.

        Returns:
            List of snapshots, **oldest first**.
            Empty list if no history file exists.
        """
        from flameiq.schema.v1.models import PerformanceSnapshot

        if not self.history_path.exists():
            return []

        snapshots: list[PerformanceSnapshot] = []
        for lineno, raw_line in enumerate(
            self.history_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = raw_line.strip()
            if not line:
                continue
            try:
                snapshots.append(PerformanceSnapshot.from_dict(json.loads(line)))
            except Exception as exc:
                logger.warning("Skipping malformed history entry (line %d): %s", lineno, exc)

        return snapshots

    def clear(self) -> None:
        """Delete all stored baselines and history. **Destructive.**

        Raises:
            :class:`~flameiq.core.errors.StorageError`: On deletion failure.
        """
        try:
            if self.baseline_path.exists():
                self.baseline_path.unlink()
            if self.history_path.exists():
                self.history_path.unlink()
            logger.info("Baseline storage cleared.")
        except OSError as exc:
            raise StorageError(f"Failed to clear storage: {exc}") from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_dirs(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    def _append_history(self, snapshot: PerformanceSnapshot) -> None:
        self._ensure_dirs()
        line = json.dumps(snapshot.to_dict(), ensure_ascii=False)
        try:
            with self.history_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError as exc:
            logger.warning("Failed to append history: %s", exc)
