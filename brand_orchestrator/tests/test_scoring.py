"""Tests for scoring module."""

from scoring.trend_score import TrendScorer, ScoreBreakdown, clamp
from scoring.modifiers import apply_modifiers, ModifierResult


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


def test_clamp_function():
    """Test clamp function."""
    assert clamp(5, 0, 10) == 5
    assert clamp(-5, 0, 10) == 0
    assert clamp(15, 0, 10) == 10


def test_score_breakdown():
    """Test ScoreBreakdown dataclass."""
    breakdown = ScoreBreakdown(
        impact=20,
        timeliness=15,
        virality=10,
        relevance=22,
        confidence=8
    )
    assert breakdown.total() == 75
    assert breakdown.impact == 20
    assert breakdown.confidence == 8


def test_apply_modifiers_no_penalties():
    """Test apply_modifiers with no penalties."""
    base = ScoreBreakdown(impact=20, timeliness=15, virality=12, relevance=22, confidence=7)
    result = apply_modifiers(base)
    assert result.adjusted == base
    assert len(result.notes) == 0


def test_apply_modifiers_single_source():
    """Test apply_modifiers with single_source_only penalty."""
    base = ScoreBreakdown(impact=20, timeliness=15, virality=12, relevance=22, confidence=4)
    result = apply_modifiers(base, single_source_only=True)
    # Low confidence (4 <= 5): penalty is 8
    assert result.adjusted.confidence == 3  # 4 - 1
    assert result.adjusted.virality == 8  # 12 - 4 (penalty 8 / 2)
    assert len(result.notes) == 1


def test_apply_modifiers_brigading():
    """Test apply_modifiers with brigading_suspected penalty."""
    base = ScoreBreakdown(impact=20, timeliness=15, virality=18, relevance=22, confidence=7)
    result = apply_modifiers(base, brigading_suspected=True)
    assert result.adjusted.virality == 8  # 18 - 10
    assert len(result.notes) == 1


def test_apply_modifiers_misinfo_risk():
    """Test apply_modifiers with high_misinfo_risk penalty."""
    base = ScoreBreakdown(impact=20, timeliness=15, virality=12, relevance=22, confidence=8)
    result = apply_modifiers(base, high_misinfo_risk=True)
    assert result.adjusted.confidence == 5  # 8 - 3
    assert len(result.notes) == 1


def test_apply_modifiers_combined():
    """Test apply_modifiers with all penalties combined."""
    base = ScoreBreakdown(impact=20, timeliness=15, virality=18, relevance=22, confidence=8)
    result = apply_modifiers(
        base,
        single_source_only=True,
        brigading_suspected=True,
        high_misinfo_risk=True
    )
    # Confidence: 8 - 1 (single) - 3 (misinfo) = 4
    # Virality: 18 - 2 (single, penalty 5/2) - 10 (brigading) = 6
    assert result.adjusted.confidence == 4
    assert result.adjusted.virality == 6
    assert len(result.notes) == 3


if __name__ == "__main__":
    test_trend_scorer_initialization()
    test_calculate_score()
    test_clamp_function()
    test_score_breakdown()
    test_apply_modifiers_no_penalties()
    test_apply_modifiers_single_source()
    test_apply_modifiers_brigading()
    test_apply_modifiers_misinfo_risk()
    test_apply_modifiers_combined()
    print("All scoring tests passed!")
