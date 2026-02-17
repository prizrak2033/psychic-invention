"""Score modifiers for adjusting trend scores."""

from __future__ import annotations

from dataclasses import dataclass

from .trend_score import ScoreBreakdown, clamp


@dataclass(frozen=True)
class ModifierResult:
    adjusted: ScoreBreakdown
    notes: list[str]


def apply_modifiers(
    base: ScoreBreakdown,
    *,
    single_source_only: bool = False,
    brigading_suspected: bool = False,
    high_misinfo_risk: bool = False,
) -> ModifierResult:
    """
    Phase 1 modifiers: conservative penalties to prevent chasing unreliable virality.
    """
    notes: list[str] = []
    impact = base.impact
    timeliness = base.timeliness
    virality = base.virality
    relevance = base.relevance
    confidence = base.confidence

    if single_source_only:
        penalty = 8 if confidence <= 5 else 5
        confidence = clamp(confidence - 1, 0, 10)
        virality = clamp(virality - penalty // 2, 0, 20)
        notes.append(f"Penalty: single-source item (reduced confidence and virality by ~{penalty}).")

    if brigading_suspected:
        virality = clamp(virality - 10, 0, 20)
        notes.append("Penalty: suspected brigading/coordinated spread (virality reduced).")

    if high_misinfo_risk:
        confidence = clamp(confidence - 3, 0, 10)
        notes.append("Penalty: high misinfo risk (confidence reduced; requires stricter gating).")

    return ModifierResult(
        adjusted=ScoreBreakdown(
            impact=impact,
            timeliness=timeliness,
            virality=virality,
            relevance=relevance,
            confidence=confidence,
        ),
        notes=notes,
    )
