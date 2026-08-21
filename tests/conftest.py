"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

# Add backend to Python path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
