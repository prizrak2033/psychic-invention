"""Tests for telemetry module."""

import time
from orchestrator.telemetry import Telemetry


def test_telemetry_initialization():
    """Test telemetry instance initialization."""
    telemetry = Telemetry()
    assert telemetry.metrics == {}
    assert telemetry.MAX_METRICS == 10000


def test_record_metric():
    """Test recording a single metric."""
    telemetry = Telemetry()
    telemetry.record_metric("test_metric", 42)
    
    metrics = telemetry.get_metrics()
    assert "test_metric" in metrics
    assert metrics["test_metric"]["value"] == 42
    assert "timestamp" in metrics["test_metric"]


def test_record_multiple_metrics():
    """Test recording multiple metrics."""
    telemetry = Telemetry()
    telemetry.record_metric("metric1", 10)
    telemetry.record_metric("metric2", 20)
    telemetry.record_metric("metric3", 30)
    
    metrics = telemetry.get_metrics()
    assert len(metrics) == 3
    assert metrics["metric1"]["value"] == 10
    assert metrics["metric2"]["value"] == 20
    assert metrics["metric3"]["value"] == 30


def test_metric_update():
    """Test updating an existing metric."""
    telemetry = Telemetry()
    telemetry.record_metric("counter", 1)
    first_timestamp = telemetry.get_metrics()["counter"]["timestamp"]
    
    time.sleep(0.01)  # Small delay to ensure different timestamp
    telemetry.record_metric("counter", 2)
    
    metrics = telemetry.get_metrics()
    assert len(metrics) == 1
    assert metrics["counter"]["value"] == 2
    assert metrics["counter"]["timestamp"] > first_timestamp


def test_metrics_bounded_growth():
    """Test that metrics dictionary doesn't grow unbounded."""
    telemetry = Telemetry()
    # Temporarily set a smaller limit for testing
    original_max = telemetry.MAX_METRICS
    telemetry.MAX_METRICS = 100
    
    try:
        # Record more metrics than the limit
        for i in range(150):
            telemetry.record_metric(f"metric_{i}", i)
            # Small delay to ensure different timestamps
            time.sleep(0.0001)
        
        metrics = telemetry.get_metrics()
        # Should not exceed MAX_METRICS
        assert len(metrics) <= 100
        
        # Most recent metrics should be kept
        assert "metric_149" in metrics
        assert "metric_148" in metrics
        
        # Oldest metrics should be removed
        assert "metric_0" not in metrics
    finally:
        # Restore original limit
        telemetry.MAX_METRICS = original_max


def test_clear_metrics():
    """Test clearing all metrics."""
    telemetry = Telemetry()
    telemetry.record_metric("metric1", 10)
    telemetry.record_metric("metric2", 20)
    
    assert len(telemetry.get_metrics()) == 2
    
    telemetry.clear_metrics()
    
    assert len(telemetry.get_metrics()) == 0
    assert telemetry.get_metrics() == {}


def test_oldest_metric_removed_when_at_capacity():
    """Test that the oldest metric is removed when at capacity."""
    telemetry = Telemetry()
    telemetry.MAX_METRICS = 3
    
    # Add 3 metrics
    telemetry.record_metric("metric_1", 1)
    time.sleep(0.01)
    telemetry.record_metric("metric_2", 2)
    time.sleep(0.01)
    telemetry.record_metric("metric_3", 3)
    
    assert len(telemetry.get_metrics()) == 3
    
    # Add one more - should remove metric_1 (oldest)
    time.sleep(0.01)
    telemetry.record_metric("metric_4", 4)
    
    metrics = telemetry.get_metrics()
    assert len(metrics) == 3
    assert "metric_1" not in metrics
    assert "metric_2" in metrics
    assert "metric_3" in metrics
    assert "metric_4" in metrics
