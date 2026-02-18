"""Trend scoring logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


def clamp(value: int, min_val: int, max_val: int) -> int:
    """Clamp a value between min and max bounds."""
    return max(min_val, min(value, max_val))


@dataclass(frozen=True)
class ScoreBreakdown:
    """
    Breakdown of a trend score into component parts.
    Phase 1: discrete components that sum to a final score.
    """
    impact: int
    timeliness: int
    virality: int
    relevance: int
    confidence: int

    def total(self) -> int:
        """Calculate the total score from all components."""
        return self.impact + self.timeliness + self.virality + self.relevance + self.confidence


class TrendScorer:
    """Calculate trend scores for content."""

    def __init__(self):
        self.base_score = 0.0

    def calculate_score(self, trend_data: Dict[str, Any]) -> float:
        """Calculate a trend score based on input data."""
        # Use dict.get() for better performance than "if key in dict" checks
        score = self.base_score
        score += trend_data.get("engagement", 0) * 0.5
        score += trend_data.get("velocity", 0) * 0.3
        
        # Clamp score to valid range
        return min(100.0, max(0.0, score))
