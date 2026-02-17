"""Gates for controlling content flow based on scores."""

from typing import Optional


class Gate:
    """Base gate class for score-based filtering."""

    def __init__(self, threshold: float):
        self.threshold = threshold

    def should_pass(self, score: float) -> bool:
        """Determine if content should pass the gate."""
        return score >= self.threshold


class QualityGate(Gate):
    """Quality gate for filtering low-quality content."""

    def __init__(self, threshold: float = 50.0):
        super().__init__(threshold)


class TrendGate(Gate):
    """Trend gate for filtering non-trending content."""

    def __init__(self, threshold: float = 70.0):
        super().__init__(threshold)
