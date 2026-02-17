"""State storage for orchestrator."""

from typing import Any, Optional


class StateStore:
    """State storage and management."""

    def __init__(self):
        self.state = {}

    def set(self, key: str, value: Any) -> None:
        """Set a state value."""
        self.state[key] = value

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get a state value."""
        return self.state.get(key, default)

    def clear(self) -> None:
        """Clear all state."""
        self.state = {}
