"""Score modifiers for adjusting trend scores."""

from typing import Dict, Any


class ScoreModifier:
    """Modify scores based on various factors."""

    def __init__(self):
        self.modifiers = {}

    def add_modifier(self, name: str, value: float) -> None:
        """Add a score modifier."""
        self.modifiers[name] = value

    def apply_modifiers(self, base_score: float) -> float:
        """Apply all modifiers to a base score."""
        modified_score = base_score
        
        for modifier_value in self.modifiers.values():
            modified_score *= (1.0 + modifier_value)
        
        return modified_score
