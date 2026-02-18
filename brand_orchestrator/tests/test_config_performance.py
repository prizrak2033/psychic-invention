"""Tests for config performance improvements."""

from pathlib import Path
from orchestrator.config import AppConfig, as_dict, BrandProfile, ScoreWeights, GateThresholds


def test_as_dict_caching():
    """Test that as_dict caches its result for better performance."""
    config = AppConfig(
        db_path=Path("/tmp/test.db"),
        artifacts_dir=Path("/tmp/artifacts"),
        log_level="INFO",
    )
    
    # First call should compute and cache
    result1 = as_dict(config)
    
    # Second call should return cached result
    result2 = as_dict(config)
    
    # Should be the exact same object (same id)
    assert result1 is result2
    
    # Verify content is correct
    assert result1["log_level"] == "INFO"
    assert result1["brand"]["brand_name"] == "Brand Orchestrator"
    assert "pillars" in result1["brand"]
    assert isinstance(result1["brand"]["pillars"], list)
    assert len(result1["brand"]["pillars"]) == 4


def test_as_dict_content():
    """Test that as_dict produces correct content."""
    config = AppConfig(
        db_path=Path("/tmp/test.db"),
        artifacts_dir=Path("/tmp/artifacts"),
        log_level="DEBUG",
    )
    
    result = as_dict(config)
    
    # Check all required keys exist
    assert "db_path" in result
    assert "artifacts_dir" in result
    assert "log_level" in result
    assert "brand" in result
    assert "weights" in result
    assert "thresholds" in result
    assert "source_policy" in result
    
    # Check brand content
    assert result["brand"]["brand_name"] == "Brand Orchestrator"
    assert isinstance(result["brand"]["pillars"], list)
    assert isinstance(result["brand"]["forbidden_tactics"], list)
    assert isinstance(result["brand"]["always_cover_triggers"], list)
    
    # Check weights
    assert result["weights"]["impact"] == 25
    assert result["weights"]["timeliness"] == 20
    assert result["weights"]["virality"] == 15
    assert result["weights"]["relevance"] == 25
    assert result["weights"]["confidence"] == 10
    
    # Check thresholds
    assert result["thresholds"]["must_cover_score"] == 75
    assert result["thresholds"]["optional_score"] == 60
    assert result["thresholds"]["watch_score"] == 45
    
    # Check source policy
    assert isinstance(result["source_policy"]["allowed_domains_tier_a"], list)
    assert "reuters.com" in result["source_policy"]["allowed_domains_tier_a"]


def test_different_configs_have_different_caches():
    """Test that different config instances have different caches."""
    config1 = AppConfig(
        db_path=Path("/tmp/test1.db"),
        artifacts_dir=Path("/tmp/artifacts1"),
        log_level="INFO",
    )
    
    config2 = AppConfig(
        db_path=Path("/tmp/test2.db"),
        artifacts_dir=Path("/tmp/artifacts2"),
        log_level="DEBUG",
    )
    
    result1 = as_dict(config1)
    result2 = as_dict(config2)
    
    # Should be different objects
    assert result1 is not result2
    
    # Should have different values
    assert result1["db_path"] == str(Path("/tmp/test1.db"))
    assert result2["db_path"] == str(Path("/tmp/test2.db"))
    assert result1["log_level"] == "INFO"
    assert result2["log_level"] == "DEBUG"
