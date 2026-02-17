"""Tests for scoring module."""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scoring.trend_score import TrendScorer
from scoring.modifiers import ScoreModifier


def test_trend_scorer_initialization():
    """Test TrendScorer initialization."""
    scorer = TrendScorer()
    assert scorer.base_score == 0.0


def test_calculate_score():
    """Test score calculation."""
    scorer = TrendScorer()
    trend_data = {
        "engagement": 10.0,
        "velocity": 5.0
    }
    score = scorer.calculate_score(trend_data)
    assert score >= 0.0
    assert score <= 100.0


def test_score_modifier():
    """Test score modifier."""
    modifier = ScoreModifier()
    modifier.add_modifier("boost", 0.1)
    
    base_score = 50.0
    modified_score = modifier.apply_modifiers(base_score)
    assert abs(modified_score - 55.0) < 0.001


if __name__ == "__main__":
    test_trend_scorer_initialization()
    test_calculate_score()
    test_score_modifier()
    print("All scoring tests passed!")
