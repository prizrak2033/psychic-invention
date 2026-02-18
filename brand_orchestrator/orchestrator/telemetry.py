"""Telemetry and monitoring for orchestrator."""

from typing import Dict, Any
import time


class Telemetry:
    """Telemetry collection and reporting."""

    # Maximum number of metrics to store before cleanup
    MAX_METRICS = 10000

    def __init__(self):
        self.metrics = {}

    def record_metric(self, name: str, value: Any) -> None:
        """Record a metric."""
        # Prevent unbounded growth by removing oldest metrics
        if len(self.metrics) >= self.MAX_METRICS:
            # Remove oldest metric by timestamp
            oldest_key = min(self.metrics, key=lambda k: self.metrics[k]["timestamp"])
            del self.metrics[oldest_key]
        
        self.metrics[name] = {
            "value": value,
            "timestamp": time.time()
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get all recorded metrics."""
        return self.metrics

    def clear_metrics(self) -> None:
        """Clear all metrics."""
        self.metrics = {}
