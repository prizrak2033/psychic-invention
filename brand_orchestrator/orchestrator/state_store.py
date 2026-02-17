"""State storage for orchestrator."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._ensure_schema()

    def close(self) -> None:
        self._conn.close()

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
            """
        )
        self._conn.commit()

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
        self._conn.commit()
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
        self._conn.commit()

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
            (
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
                utc_now_iso(),
            ),
        )
        self._conn.commit()

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
        self._conn.commit()

    def list_intel_items_for_run(self, run_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM intel_items WHERE run_id = ? ORDER BY created_at ASC",
            (run_id,),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "item_id": r["item_id"],
                    "run_id": r["run_id"],
                    "item_type": r["item_type"],
                    "title": r["title"],
                    "summary": r["summary"],
                    "claims_json": json.loads(r["claims_json"]),
                    "evidence_json": json.loads(r["evidence_json"]),
                    "scores_json": json.loads(r["scores_json"]),
                    "risk_flags_json": json.loads(r["risk_flags_json"]),
                    "explainability_json": json.loads(r["explainability_json"]),
                    "decision": r["decision"],
                    "decision_reason": r["decision_reason"],
                    "created_at": r["created_at"],
                }
            )
        return out
