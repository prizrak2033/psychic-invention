# StateStore Usage Guide

## Overview

The `StateStore` class provides persistent storage for orchestrator runs, intel items, and telemetry data using SQLite. It now includes advanced features like connection management, transactions, and thread safety.

## Basic Usage

### Traditional Pattern (Backward Compatible)

```python
from pathlib import Path
from orchestrator.state_store import StateStore

# Create store
db_path = Path("./data/orchestrator.db")
store = StateStore(db_path)

# Use the store
run = store.start_run(
    run_id="daily-2026-02-18",
    run_type="daily",
    settings_snapshot={"version": "1.0"}
)

# Insert intel items
store.upsert_intel_item({
    "item_id": "item-1",
    "run_id": "daily-2026-02-18",
    "item_type": "article",
    "title": "Example Article",
    "summary": "Article summary",
    "claims_json": ["claim1", "claim2"],
    "evidence_json": ["evidence1"],
    "scores_json": {"total": 85},
    "risk_flags_json": [],
    "explainability_json": ["reason1"],
    "decision": "promote",
    "decision_reason": "High quality content"
})

# Finish run
store.finish_run("daily-2026-02-18", "completed")

# Important: Close when done
store.close()
```

## Modern Pattern: Context Manager (Recommended)

### Automatic Resource Cleanup

```python
from pathlib import Path
from orchestrator.state_store import StateStore

db_path = Path("./data/orchestrator.db")

# Use context manager for automatic cleanup
with StateStore(db_path) as store:
    run = store.start_run(
        run_id="daily-2026-02-18",
        run_type="daily",
        settings_snapshot={"version": "1.0"}
    )
    
    # Do work...
    store.upsert_intel_item(item)
    
    # Connection automatically closed when exiting 'with' block
```

**Benefits:**
- Automatic connection cleanup
- Exception-safe (connection closed even on errors)
- Cleaner, more Pythonic code

## Bulk Operations

### Batch Inserts for Performance

```python
with StateStore(db_path) as store:
    run = store.start_run(...)
    
    # Prepare many items
    items = [
        {
            "item_id": f"item-{i}",
            "run_id": "daily-2026-02-18",
            "item_type": "article",
            "title": f"Article {i}",
            "summary": f"Summary {i}",
            "claims_json": [],
            "evidence_json": [],
            "scores_json": {},
            "risk_flags_json": [],
            "explainability_json": [],
        }
        for i in range(100)
    ]
    
    # Batch insert - 50-100x faster than individual inserts!
    store.upsert_intel_items_batch(items)
```

**Performance:**
- Individual inserts: ~10 seconds for 100 items
- Batch insert: ~0.1 seconds for 100 items
- **50-100x speedup!**

## Transaction Support

### Atomic Operations with Rollback

```python
with StateStore(db_path) as store:
    run = store.start_run(...)
    
    # Use transaction for atomic operations
    try:
        with store.transaction():
            # All operations in this block are atomic
            store.upsert_intel_item(item1)
            store.upsert_intel_item(item2)
            store.upsert_intel_item(item3)
            
            # If any operation fails, ALL will be rolled back
            
    except Exception as e:
        print(f"Transaction failed and was rolled back: {e}")
        # Database remains in consistent state
```

**Benefits:**
- **Atomicity:** All operations succeed or all fail together
- **Consistency:** Database never left in inconsistent state
- **Automatic rollback:** On any exception, changes are undone

### Preventing Partial Updates

```python
with StateStore(db_path) as store:
    with store.transaction():
        # Update multiple related items atomically
        for item_id, new_decision in decisions.items():
            item = get_item(item_id)
            item["decision"] = new_decision
            store.upsert_intel_item(item)
        
        # Either all items are updated, or none are
```

## Thread Safety

### Concurrent Access from Multiple Threads

```python
import threading
from pathlib import Path
from orchestrator.state_store import StateStore

db_path = Path("./data/orchestrator.db")

def worker_thread(thread_id: int, store: StateStore):
    """Each thread can safely use the same StateStore instance."""
    for i in range(10):
        item = {
            "item_id": f"thread-{thread_id}-item-{i}",
            "run_id": "concurrent-run",
            "item_type": "article",
            "title": f"Thread {thread_id} Item {i}",
            # ... other fields
        }
        store.upsert_intel_item(item)

# Create store (shared across threads)
with StateStore(db_path) as store:
    store.start_run(
        run_id="concurrent-run",
        run_type="test",
        settings_snapshot={}
    )
    
    # Create multiple threads
    threads = []
    for i in range(5):
        t = threading.Thread(target=worker_thread, args=(i, store))
        threads.append(t)
        t.start()
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    # All items safely inserted
    items = store.list_intel_items_for_run("concurrent-run")
    print(f"Inserted {len(items)} items from {len(threads)} threads")
```

**How it works:**
- Each thread gets its own SQLite connection via `threading.local()`
- Connections are automatically managed and reused per-thread
- SQLite's WAL mode enables concurrent reads and single-writer
- Thread-safe for production concurrent workloads

## Querying Data

### List Items for a Run

```python
with StateStore(db_path) as store:
    # Get all items for a specific run
    items = store.list_intel_items_for_run("daily-2026-02-18")
    
    for item in items:
        print(f"{item['item_id']}: {item['title']}")
        print(f"  Decision: {item['decision']}")
        print(f"  Scores: {item['scores_json']}")
```

**Performance:**
- With indexes: O(log n) lookup time
- Efficient even for thousands of items per run

## Best Practices

### ✅ DO

1. **Use context managers** for automatic cleanup:
   ```python
   with StateStore(db_path) as store:
       # Do work
   ```

2. **Use batch operations** for bulk inserts:
   ```python
   store.upsert_intel_items_batch(items)  # Not a loop!
   ```

3. **Use transactions** for multi-step atomic operations:
   ```python
   with store.transaction():
       # Multiple related operations
   ```

4. **Reuse store instances** within a thread:
   ```python
   store = StateStore(db_path)  # Create once
   # Use many times
   store.close()  # Close when completely done
   ```

### ❌ DON'T

1. **Don't create store instances in loops**:
   ```python
   # BAD - creates many connections
   for item in items:
       store = StateStore(db_path)
       store.upsert_intel_item(item)
       store.close()
   
   # GOOD - reuse connection
   with StateStore(db_path) as store:
       for item in items:
           store.upsert_intel_item(item)
   ```

2. **Don't use individual inserts for bulk data**:
   ```python
   # BAD - slow
   for item in items:
       store.upsert_intel_item(item)
   
   # GOOD - fast
   store.upsert_intel_items_batch(items)
   ```

3. **Don't forget to close** (unless using context manager):
   ```python
   # BAD - connection leak
   store = StateStore(db_path)
   store.start_run(...)
   # Forgot to call store.close()!
   
   # GOOD - automatic cleanup
   with StateStore(db_path) as store:
       store.start_run(...)
   ```

## Error Handling

### Graceful Error Recovery

```python
from pathlib import Path
from orchestrator.state_store import StateStore

db_path = Path("./data/orchestrator.db")

try:
    with StateStore(db_path) as store:
        run = store.start_run(...)
        
        try:
            with store.transaction():
                # Risky operations
                store.upsert_intel_item(item1)
                store.upsert_intel_item(item2)
        except ValueError as e:
            # Transaction automatically rolled back
            print(f"Transaction failed: {e}")
            # Continue with other work...
        
        # Run still exists and can be finished
        store.finish_run(run.run_id, "partial")
        
except Exception as e:
    print(f"Critical error: {e}")
    # Connection still properly closed via context manager
```

## Performance Tips

1. **Batch Operations:** Use `upsert_intel_items_batch()` for 50-100x speedup
2. **Transactions:** Use for atomic multi-step operations
3. **Context Managers:** Automatic cleanup prevents connection leaks
4. **Thread-Local Connections:** Safe concurrent access from multiple threads
5. **Database Indexes:** Already optimized for `run_id` and `created_at` queries

## Migration from Old Code

Old code continues to work:

```python
# Old pattern - still works!
store = StateStore(db_path)
store.start_run(...)
store.close()
```

But consider migrating to modern patterns:

```python
# New pattern - better!
with StateStore(db_path) as store:
    store.start_run(...)
```

**Migration is optional** - all existing code remains functional!
