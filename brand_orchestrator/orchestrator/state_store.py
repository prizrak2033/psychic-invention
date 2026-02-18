"""State storage for orchestrator."""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    run_type: str
    started_at: str
    status: str
    settings_snapshot_json: dict[str, Any]


class StateStore:
    """
    Thin SQLite wrapper. Keeps schema + simple inserts/updates.
    Phase 1: focus on deterministic, auditable logging.
    
    Supports context manager pattern for automatic resource cleanup:
        with StateStore(db_path) as store:
            store.start_run(...)
    
    Thread-safe: Each thread gets its own connection.
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._lock = threading.Lock()
        # Initialize connection for the current thread
        self._get_connection()
        self._ensure_schema()

    @property
    def _conn(self) -> sqlite3.Connection:
        """Get thread-local connection, creating if needed."""
        return self._get_connection()
    
    @property
    def _in_transaction(self) -> bool:
        """Check if we're currently in a transaction."""
        return getattr(self._local, 'in_transaction', False)
    
    @_in_transaction.setter
    def _in_transaction(self, value: bool) -> None:
        """Set transaction state."""
        self._local.in_transaction = value
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a connection for the current thread."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,  # We handle thread safety manually
                timeout=30.0  # 30 second timeout for locks
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            # Disable auto-commit to allow explicit transaction control
            conn.isolation_level = None  # Auto-commit mode
            self._local.conn = conn
        return self._local.conn
    
    def _commit_if_not_in_transaction(self) -> None:
        """Commit unless we're in an explicit transaction."""
        if not self._in_transaction:
            self._conn.commit()

    def close(self) -> None:
        """Close the connection for the current thread."""
        if hasattr(self._local, 'conn') and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None
    
    def __enter__(self) -> StateStore:
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - close connection."""
        self.close()
        return None
    
    @contextmanager
    def transaction(self) -> Iterator[None]:
        """
        Explicit transaction context manager.
        
        Usage:
            with store.transaction():
                store.upsert_intel_item(item1)
                store.upsert_intel_item(item2)
                # Commits on success, rolls back on exception
        """
        conn = self._conn
        # Mark that we're in a transaction
        was_in_transaction = self._in_transaction
        self._in_transaction = True
        
        try:
            conn.execute("BEGIN")
            yield
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._in_transaction = was_in_transaction

    def _ensure_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
              run_id TEXT PRIMARY KEY,
              run_type TEXT NOT NULL,
              started_at TEXT NOT NULL,
              finished_at TEXT,
              status TEXT NOT NULL,
              settings_snapshot_json TEXT NOT NULL,
              notes TEXT
            );

            CREATE TABLE IF NOT EXISTS intel_items (
              item_id TEXT PRIMARY KEY,
              run_id TEXT NOT NULL,
              item_type TEXT NOT NULL,
              title TEXT NOT NULL,
              summary TEXT NOT NULL,
              claims_json TEXT NOT NULL,
              evidence_json TEXT NOT NULL,
              scores_json TEXT NOT NULL,
              risk_flags_json TEXT NOT NULL,
              explainability_json TEXT NOT NULL,
              decision TEXT,
              decision_reason TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY (run_id) REFERENCES runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS telemetry (
              run_id TEXT PRIMARY KEY,
              telemetry_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY (run_id) REFERENCES runs(run_id)
            );

            -- Performance indexes for foreign key lookups
            CREATE INDEX IF NOT EXISTS idx_intel_items_run_id ON intel_items(run_id);
            CREATE INDEX IF NOT EXISTS idx_intel_items_created_at ON intel_items(created_at);
            """
        )
        self._commit_if_not_in_transaction()

    def start_run(self, run_id: str, run_type: str, settings_snapshot: dict[str, Any]) -> RunRecord:
        rec = RunRecord(
            run_id=run_id,
            run_type=run_type,
            started_at=utc_now_iso(),
            status="running",
            settings_snapshot_json=settings_snapshot,
        )
        self._conn.execute(
            """
            INSERT INTO runs(run_id, run_type, started_at, status, settings_snapshot_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (rec.run_id, rec.run_type, rec.started_at, rec.status, json.dumps(rec.settings_snapshot_json)),
        )
        self._commit_if_not_in_transaction()
        return rec

    def finish_run(self, run_id: str, status: str, notes: str | None = None) -> None:
        self._conn.execute(
            """
            UPDATE runs
               SET finished_at = ?, status = ?, notes = ?
             WHERE run_id = ?
            """,
            (utc_now_iso(), status, notes, run_id),
        )
        self._commit_if_not_in_transaction()

    def _serialize_intel_item(self, item: dict[str, Any], created_at: str) -> tuple:
        """
        Serialize intel item data for database insertion.
        Extracts and serializes JSON fields to avoid code duplication.
        
        Args:
            item: Intel item dictionary
            created_at: ISO timestamp string
            
        Returns:
            Tuple of serialized values ready for SQL parameter binding
        """
        return (
            item["item_id"],
            item["run_id"],
            item["item_type"],
            item["title"],
            item["summary"],
            json.dumps(item.get("claims_json", [])),
            json.dumps(item.get("evidence_json", [])),
            json.dumps(item.get("scores_json", {})),
            json.dumps(item.get("risk_flags_json", [])),
            json.dumps(item.get("explainability_json", [])),
            item.get("decision"),
            item.get("decision_reason"),
            created_at,
        )

    def upsert_intel_item(self, item: dict[str, Any]) -> None:
        """
        Expected fields:
        item_id, run_id, item_type, title, summary,
        claims_json (list/dict), evidence_json, scores_json, risk_flags_json, explainability_json
        optional: decision, decision_reason
        """
        self._conn.execute(
            """
            INSERT INTO intel_items(
              item_id, run_id, item_type, title, summary,
              claims_json, evidence_json, scores_json, risk_flags_json, explainability_json,
              decision, decision_reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
              title=excluded.title,
              summary=excluded.summary,
              claims_json=excluded.claims_json,
              evidence_json=excluded.evidence_json,
              scores_json=excluded.scores_json,
              risk_flags_json=excluded.risk_flags_json,
              explainability_json=excluded.explainability_json,
              decision=excluded.decision,
              decision_reason=excluded.decision_reason
            """,
            self._serialize_intel_item(item, utc_now_iso()),
        )
        self._commit_if_not_in_transaction()

    def upsert_intel_items_batch(self, items: list[dict[str, Any]]) -> None:
        """
        Batch version of upsert_intel_item for better performance.
        Commits once after all items are inserted, significantly faster for bulk operations.
        
        Expected fields per item:
        item_id, run_id, item_type, title, summary,
        claims_json (list/dict), evidence_json, scores_json, risk_flags_json, explainability_json
        optional: decision, decision_reason
        """
        if not items:
            return
        
        created_at = utc_now_iso()
        for item in items:
            self._conn.execute(
                """
                INSERT INTO intel_items(
                  item_id, run_id, item_type, title, summary,
                  claims_json, evidence_json, scores_json, risk_flags_json, explainability_json,
                  decision, decision_reason, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                  title=excluded.title,
                  summary=excluded.summary,
                  claims_json=excluded.claims_json,
                  evidence_json=excluded.evidence_json,
                  scores_json=excluded.scores_json,
                  risk_flags_json=excluded.risk_flags_json,
                  explainability_json=excluded.explainability_json,
                  decision=excluded.decision,
                  decision_reason=excluded.decision_reason
                """,
                self._serialize_intel_item(item, created_at),
            )
        # Single commit for all items - much faster than individual commits
        self._commit_if_not_in_transaction()

    def write_telemetry(self, run_id: str, telemetry: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO telemetry(run_id, telemetry_json, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
              telemetry_json=excluded.telemetry_json,
              created_at=excluded.created_at
            """,
            (run_id, json.dumps(telemetry), utc_now_iso()),
        )
        self._commit_if_not_in_transaction()

    def list_intel_items_for_run(self, run_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM intel_items WHERE run_id = ? ORDER BY created_at ASC",
            (run_id,),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            # Parse all JSON fields once and reuse
            row_dict = dict(r)
            out.append(
                {
                    "item_id": row_dict["item_id"],
                    "run_id": row_dict["run_id"],
                    "item_type": row_dict["item_type"],
                    "title": row_dict["title"],
                    "summary": row_dict["summary"],
                    "claims_json": json.loads(row_dict["claims_json"]),
                    "evidence_json": json.loads(row_dict["evidence_json"]),
                    "scores_json": json.loads(row_dict["scores_json"]),
                    "risk_flags_json": json.loads(row_dict["risk_flags_json"]),
                    "explainability_json": json.loads(row_dict["explainability_json"]),
                    "decision": row_dict["decision"],
                    "decision_reason": row_dict["decision_reason"],
                    "created_at": row_dict["created_at"],
                }
            )
        return out
