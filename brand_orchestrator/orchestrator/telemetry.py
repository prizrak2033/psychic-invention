"""Telemetry and monitoring for orchestrator."""

from typing import Dict, Any
import time


class Telemetry:
    """Telemetry collection and reporting."""

    def __init__(self):
        self.metrics = {}

    def record_metric(self, name: str, value: Any) -> None:
        """Record a metric."""
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
