"""
tests/conftest.py — Shared pytest fixtures for Auracelle Charlie.

Adds the repo root to sys.path so tests can import packages without
installing the project as a package.
"""
import sys
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
