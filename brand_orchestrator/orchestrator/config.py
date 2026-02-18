"""Configuration management for the orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import os


class TrustTier(str, Enum):
    A = "A"  # high trust (official statements, major wires, reputable outlets)
    B = "B"  # generally reliable, may be more interpretive
    C = "C"  # low trust (social posts, screenshots, anonymous claims)


@dataclass(frozen=True)
class BrandProfile:
    """
    Brand constraints for a Socialist-in-character political stream.
    This profile is enforced by gates and used in scoring relevance.
    """

    brand_name: str = "Brand Orchestrator"
    promise: str = (
        "Analyze politics, economics, and internet culture through a socialist lens, "
        "focusing on material reality and power."
    )

    # Pillars (kept as tags for Phase 1; expanded later)
    pillars: tuple[str, ...] = (
        "material_analysis",
        "institutional_critique",
        "internet_culture_and_ideology",
        "geopolitical_power_structures",
    )

    # Hard constraints / safety posture
    forbidden_tactics: tuple[str, ...] = (
        "harassment",
        "doxxing",
        "pile_on_private_individuals",
        "speculative_accusations_without_evidence",
    )

    # "Always cover" triggers (Phase 1 uses as positive relevance signals)
    always_cover_triggers: tuple[str, ...] = (
        "major_labor_action",
        "supreme_court_ruling",
        "budget_legislation",
        "war_escalation",
        "corporate_exploitation_scandal",
        "platform_censorship_shift",
    )


@dataclass(frozen=True)
class ScoreWeights:
    """
    TrendScore weights (Socialist character bias: relevance elevated, virality reduced).
    Max component bounds are enforced in scoring functions, not here.
    """
    impact: int = 25
    timeliness: int = 20
    virality: int = 15
    relevance: int = 25
    confidence: int = 10


@dataclass(frozen=True)
class GateThresholds:
    """
    Gates decide promotion vs monitor vs block.
    """
    must_cover_score: int = 75
    optional_score: int = 60
    watch_score: int = 45

    # Confidence gates
    min_confidence_promote: int = 6   # out of 10
    min_confidence_monitor: int = 3   # out of 10


@dataclass(frozen=True)
class AppConfig:
    db_path: Path
    artifacts_dir: Path
    log_level: str = "INFO"
    brand: BrandProfile = field(default_factory=BrandProfile)
    weights: ScoreWeights = field(default_factory=ScoreWeights)
    thresholds: GateThresholds = field(default_factory=GateThresholds)

    # Source policy for Phase 1
    allowed_domains_tier_a: tuple[str, ...] = (
        "reuters.com",
        "apnews.com",
        "bbc.co.uk",
        "bbc.com",
        "theguardian.com",
        "cnn.com",
        "nytimes.com",
        "washingtonpost.com",
        "wsj.com",
        "economist.com",
        "gov",
        "gc.ca",
        "canada.ca",
        "whitehouse.gov",
        "supremecourt.gov",
    )
    
    # Cache for as_dict() conversion to avoid repeated tuple->list conversions.
    # Since AppConfig is frozen/immutable, the dict representation never changes,
    # so we can safely cache the result. Set via object.__setattr__() in as_dict().
    _dict_cache: dict[str, Any] | None = field(default=None, init=False, repr=False, compare=False)


def load_config() -> AppConfig:
    """
    Loads environment variables and builds an AppConfig.
    """
    load_dotenv()

    db_path = Path(os.getenv("BRAND_ORCH_DB_PATH", "./data/brand_orchestrator.sqlite")).resolve()
    artifacts_dir = Path(os.getenv("BRAND_ORCH_ARTIFACTS_DIR", "./artifacts")).resolve()
    log_level = os.getenv("BRAND_ORCH_LOG_LEVEL", "INFO").strip().upper()

    # Ensure folders exist (db file created later)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (Path("./data").resolve()).mkdir(parents=True, exist_ok=True)

    return AppConfig(
        db_path=db_path,
        artifacts_dir=artifacts_dir,
        log_level=log_level,
    )


def as_dict(cfg: AppConfig) -> dict[str, Any]:
    """
    For run settings snapshots (stored in DB).
    Keep stable keys so diffs are meaningful.
    Uses caching to avoid repeated tuple->list conversions.
    """
    # Return cached version if available (AppConfig is frozen/immutable)
    if cfg._dict_cache is not None:
        return cfg._dict_cache
    
    result = {
        "db_path": str(cfg.db_path),
        "artifacts_dir": str(cfg.artifacts_dir),
        "log_level": cfg.log_level,
        "brand": {
            "brand_name": cfg.brand.brand_name,
            "promise": cfg.brand.promise,
            "pillars": list(cfg.brand.pillars),
            "forbidden_tactics": list(cfg.brand.forbidden_tactics),
            "always_cover_triggers": list(cfg.brand.always_cover_triggers),
        },
        "weights": {
            "impact": cfg.weights.impact,
            "timeliness": cfg.weights.timeliness,
            "virality": cfg.weights.virality,
            "relevance": cfg.weights.relevance,
            "confidence": cfg.weights.confidence,
        },
        "thresholds": {
            "must_cover_score": cfg.thresholds.must_cover_score,
            "optional_score": cfg.thresholds.optional_score,
            "watch_score": cfg.thresholds.watch_score,
            "min_confidence_promote": cfg.thresholds.min_confidence_promote,
            "min_confidence_monitor": cfg.thresholds.min_confidence_monitor,
        },
        "source_policy": {
            "allowed_domains_tier_a": list(cfg.allowed_domains_tier_a),
        },
    }
    
    # Cache the result since AppConfig is frozen (immutable).
    # Use object.__setattr__() to bypass frozen dataclass restriction - this is
    # the standard pattern for lazy initialization in frozen dataclasses.
    object.__setattr__(cfg, '_dict_cache', result)
    return result
