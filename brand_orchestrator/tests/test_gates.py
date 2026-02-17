"""Tests for gates module.

Note: For proper usage, install the package in development mode:
    pip install -e .
"""

import sys
import os

# Add parent directory to path for imports (temporary solution)
# TODO: Install package with 'pip install -e .' for proper imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scoring.gates import Gate, QualityGate, TrendGate


def test_gate_initialization():
    """Test Gate initialization."""
    gate = Gate(threshold=50.0)
    assert gate.threshold == 50.0


def test_gate_should_pass():
    """Test gate passing logic."""
    gate = Gate(threshold=50.0)
    
    assert gate.should_pass(60.0) is True
    assert gate.should_pass(50.0) is True
    assert gate.should_pass(40.0) is False


def test_quality_gate():
    """Test QualityGate."""
    gate = QualityGate()
    assert gate.threshold == 50.0
    assert gate.should_pass(60.0) is True
    assert gate.should_pass(40.0) is False


def test_trend_gate():
    """Test TrendGate."""
    gate = TrendGate()
    assert gate.threshold == 70.0
    assert gate.should_pass(80.0) is True
    assert gate.should_pass(60.0) is False


if __name__ == "__main__":
    test_gate_initialization()
    test_gate_should_pass()
    test_quality_gate()
    test_trend_gate()
    print("All gates tests passed!")
