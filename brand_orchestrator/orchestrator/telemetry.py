"""Telemetry and monitoring for orchestrator."""

from collections import OrderedDict
from typing import Dict, Any
import time


class Telemetry:
    """Telemetry collection and reporting."""

    # Maximum number of metrics to store before cleanup
    MAX_METRICS = 10000

    def __init__(self):
        # Use OrderedDict to maintain insertion order for efficient cleanup
        self.metrics: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    def record_metric(self, name: str, value: Any) -> None:
        """Record a metric."""
        # Remove oldest metric if at capacity and recording a new metric
        if name not in self.metrics and len(self.metrics) >= self.MAX_METRICS:
            # OrderedDict maintains insertion order, so first item is oldest
            self.metrics.popitem(last=False)  # O(1) removal of oldest
        
        # If updating existing metric, move it to end (most recent)
        if name in self.metrics:
            self.metrics.move_to_end(name)
        
        self.metrics[name] = {
            "value": value,
            "timestamp": time.time()
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get all recorded metrics."""
        return dict(self.metrics)

    def clear_metrics(self) -> None:
        """Clear all metrics."""
        self.metrics = OrderedDict()
