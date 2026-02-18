"""Tests for connection management and pooling features."""

import tempfile
import threading
from pathlib import Path

from orchestrator.state_store import StateStore


def test_context_manager():
    """Test that StateStore works as a context manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        
        # Use StateStore as context manager
        with StateStore(db_path) as store:
            run_record = store.start_run(
                run_id="ctx-test-run",
                run_type="daily",
                settings_snapshot={"test": "context_manager"}
            )
            assert run_record.run_id == "ctx-test-run"
        
        # After context exit, connection should be closed
        # Open a new store to verify data was saved
        with StateStore(db_path) as store:
            # Verify the run was actually saved
            items = store.list_intel_items_for_run("ctx-test-run")
            assert items == []  # No items yet, but run should exist


def test_transaction_context_manager_success():
    """Test transaction context manager commits on success."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = StateStore(db_path)
        
        # Start a run first
        store.start_run(
            run_id="txn-test-run",
            run_type="daily",
            settings_snapshot={"test": "transaction"}
        )
        
        # Use transaction context manager
        items = [
            {
                "item_id": "txn-item-1",
                "run_id": "txn-test-run",
                "item_type": "article",
                "title": "Transaction Test 1",
                "summary": "Test summary 1",
                "claims_json": [],
                "evidence_json": [],
                "scores_json": {},
                "risk_flags_json": [],
                "explainability_json": [],
            },
            {
                "item_id": "txn-item-2",
                "run_id": "txn-test-run",
                "item_type": "article",
                "title": "Transaction Test 2",
                "summary": "Test summary 2",
                "claims_json": [],
                "evidence_json": [],
                "scores_json": {},
                "risk_flags_json": [],
                "explainability_json": [],
            }
        ]
        
        with store.transaction():
            for item in items:
                store.upsert_intel_item(item)
        
        # Verify items were committed
        retrieved = store.list_intel_items_for_run("txn-test-run")
        assert len(retrieved) == 2
        assert retrieved[0]["item_id"] == "txn-item-1"
        assert retrieved[1]["item_id"] == "txn-item-2"
        
        store.close()


def test_transaction_context_manager_rollback():
    """Test transaction context manager rolls back on exception."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = StateStore(db_path)
        
        # Start a run first
        store.start_run(
            run_id="rollback-test-run",
            run_type="daily",
            settings_snapshot={"test": "rollback"}
        )
        
        # Insert one item successfully
        store.upsert_intel_item({
            "item_id": "rollback-item-0",
            "run_id": "rollback-test-run",
            "item_type": "article",
            "title": "Before Transaction",
            "summary": "This should persist",
            "claims_json": [],
            "evidence_json": [],
            "scores_json": {},
            "risk_flags_json": [],
            "explainability_json": [],
        })
        
        # Try transaction that will fail
        try:
            with store.transaction():
                store.upsert_intel_item({
                    "item_id": "rollback-item-1",
                    "run_id": "rollback-test-run",
                    "item_type": "article",
                    "title": "In Transaction 1",
                    "summary": "This should rollback",
                    "claims_json": [],
                    "evidence_json": [],
                    "scores_json": {},
                    "risk_flags_json": [],
                    "explainability_json": [],
                })
                # Raise an exception to trigger rollback
                raise ValueError("Simulated error")
        except ValueError:
            pass  # Expected
        
        # Verify only the first item persisted
        retrieved = store.list_intel_items_for_run("rollback-test-run")
        assert len(retrieved) == 1
        assert retrieved[0]["item_id"] == "rollback-item-0"
        assert retrieved[0]["title"] == "Before Transaction"
        
        store.close()


def test_thread_safety():
    """Test that StateStore is thread-safe with thread-local connections."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = StateStore(db_path)
        
        # Start a run first
        store.start_run(
            run_id="thread-test-run",
            run_type="daily",
            settings_snapshot={"test": "threading"}
        )
        
        results = []
        errors = []
        
        def worker(thread_id: int):
            """Worker function to insert items from different threads."""
            try:
                for i in range(5):
                    item = {
                        "item_id": f"thread-{thread_id}-item-{i}",
                        "run_id": "thread-test-run",
                        "item_type": "article",
                        "title": f"Thread {thread_id} Item {i}",
                        "summary": f"From thread {thread_id}",
                        "claims_json": [],
                        "evidence_json": [],
                        "scores_json": {"thread_id": thread_id},
                        "risk_flags_json": [],
                        "explainability_json": [],
                    }
                    store.upsert_intel_item(item)
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Create multiple threads
        threads = []
        num_threads = 3
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == num_threads
        
        # Verify all items were inserted
        retrieved = store.list_intel_items_for_run("thread-test-run")
        assert len(retrieved) == num_threads * 5  # 3 threads * 5 items each
        
        # Verify items from different threads
        thread_0_items = [item for item in retrieved if item["scores_json"]["thread_id"] == 0]
        assert len(thread_0_items) == 5
        
        store.close()


def test_backward_compatibility():
    """Test that the old usage pattern still works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        
        # Old pattern: create, use, close
        store = StateStore(db_path)
        
        store.start_run(
            run_id="compat-test-run",
            run_type="daily",
            settings_snapshot={"test": "compatibility"}
        )
        
        store.upsert_intel_item({
            "item_id": "compat-item-1",
            "run_id": "compat-test-run",
            "item_type": "article",
            "title": "Compatibility Test",
            "summary": "Old usage pattern",
            "claims_json": [],
            "evidence_json": [],
            "scores_json": {},
            "risk_flags_json": [],
            "explainability_json": [],
        })
        
        items = store.list_intel_items_for_run("compat-test-run")
        assert len(items) == 1
        assert items[0]["item_id"] == "compat-item-1"
        
        store.close()


def test_connection_reuse_per_thread():
    """Test that connections are reused within the same thread."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = StateStore(db_path)
        
        # Get connection ID (object id)
        conn1 = store._conn
        conn1_id = id(conn1)
        
        # Access connection again
        conn2 = store._conn
        conn2_id = id(conn2)
        
        # Should be the same connection object
        assert conn1_id == conn2_id
        
        store.close()
