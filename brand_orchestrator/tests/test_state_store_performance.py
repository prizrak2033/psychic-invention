"""Tests for state_store performance improvements."""

import json
import tempfile
from pathlib import Path

from orchestrator.state_store import StateStore


def test_batch_upsert():
    """Test batch upsert operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = StateStore(db_path)
        
        # Start a run
        run_record = store.start_run(
            run_id="test-run-1",
            run_type="daily",
            settings_snapshot={"test": "config"}
        )
        
        # Create test items
        items = [
            {
                "item_id": f"item-{i}",
                "run_id": "test-run-1",
                "item_type": "article",
                "title": f"Test Article {i}",
                "summary": f"Summary {i}",
                "claims_json": [f"claim-{i}"],
                "evidence_json": [f"evidence-{i}"],
                "scores_json": {"total": i * 10},
                "risk_flags_json": [],
                "explainability_json": [f"explanation-{i}"],
                "decision": "promote" if i % 2 == 0 else "monitor",
                "decision_reason": f"Reason {i}",
            }
            for i in range(10)
        ]
        
        # Test batch upsert
        store.upsert_intel_items_batch(items)
        
        # Verify all items were inserted
        retrieved_items = store.list_intel_items_for_run("test-run-1")
        assert len(retrieved_items) == 10
        
        # Verify data integrity
        for i, item in enumerate(retrieved_items):
            assert item["item_id"] == f"item-{i}"
            assert item["title"] == f"Test Article {i}"
            assert item["claims_json"] == [f"claim-{i}"]
            assert item["scores_json"] == {"total": i * 10}
            assert item["decision"] == ("promote" if i % 2 == 0 else "monitor")
        
        store.close()


def test_batch_upsert_empty_list():
    """Test batch upsert with empty list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = StateStore(db_path)
        
        # Should handle empty list gracefully
        store.upsert_intel_items_batch([])
        
        store.close()


def test_database_indexes():
    """Test that database indexes are created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = StateStore(db_path)
        
        # Query SQLite to check if indexes exist
        cursor = store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = [row[0] for row in cursor.fetchall()]
        
        assert "idx_intel_items_run_id" in indexes
        assert "idx_intel_items_created_at" in indexes
        
        store.close()


def test_list_intel_items_json_parsing():
    """Test that JSON parsing doesn't cause repeated lookups."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = StateStore(db_path)
        
        # Start a run
        store.start_run(
            run_id="test-run-2",
            run_type="daily",
            settings_snapshot={"test": "config"}
        )
        
        # Insert a single item
        item = {
            "item_id": "item-1",
            "run_id": "test-run-2",
            "item_type": "article",
            "title": "Test Article",
            "summary": "Summary",
            "claims_json": ["claim-1", "claim-2"],
            "evidence_json": ["evidence-1"],
            "scores_json": {"total": 85, "impact": 25},
            "risk_flags_json": ["flag-1"],
            "explainability_json": ["reason-1", "reason-2"],
            "decision": "promote",
            "decision_reason": "High impact",
        }
        store.upsert_intel_item(item)
        
        # Retrieve items
        retrieved_items = store.list_intel_items_for_run("test-run-2")
        assert len(retrieved_items) == 1
        
        # Verify all JSON fields are properly parsed
        retrieved = retrieved_items[0]
        assert retrieved["claims_json"] == ["claim-1", "claim-2"]
        assert retrieved["evidence_json"] == ["evidence-1"]
        assert retrieved["scores_json"] == {"total": 85, "impact": 25}
        assert retrieved["risk_flags_json"] == ["flag-1"]
        assert retrieved["explainability_json"] == ["reason-1", "reason-2"]
        
        store.close()


def test_batch_update_existing_items():
    """Test that batch upsert updates existing items correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = StateStore(db_path)
        
        # Start a run
        store.start_run(
            run_id="test-run-3",
            run_type="daily",
            settings_snapshot={"test": "config"}
        )
        
        # Insert initial items
        initial_items = [
            {
                "item_id": f"item-{i}",
                "run_id": "test-run-3",
                "item_type": "article",
                "title": f"Original Title {i}",
                "summary": f"Original Summary {i}",
                "claims_json": [],
                "evidence_json": [],
                "scores_json": {},
                "risk_flags_json": [],
                "explainability_json": [],
            }
            for i in range(5)
        ]
        store.upsert_intel_items_batch(initial_items)
        
        # Update items with same IDs
        updated_items = [
            {
                "item_id": f"item-{i}",
                "run_id": "test-run-3",
                "item_type": "article",
                "title": f"Updated Title {i}",
                "summary": f"Updated Summary {i}",
                "claims_json": [f"new-claim-{i}"],
                "evidence_json": [f"new-evidence-{i}"],
                "scores_json": {"total": i * 20},
                "risk_flags_json": [f"flag-{i}"],
                "explainability_json": [f"new-explanation-{i}"],
                "decision": "block",
                "decision_reason": f"Updated reason {i}",
            }
            for i in range(5)
        ]
        store.upsert_intel_items_batch(updated_items)
        
        # Verify only 5 items exist (updated, not duplicated)
        retrieved_items = store.list_intel_items_for_run("test-run-3")
        assert len(retrieved_items) == 5
        
        # Verify data was updated
        for i, item in enumerate(retrieved_items):
            assert item["title"] == f"Updated Title {i}"
            assert item["summary"] == f"Updated Summary {i}"
            assert item["claims_json"] == [f"new-claim-{i}"]
            assert item["decision"] == "block"
        
        store.close()
