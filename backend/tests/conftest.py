"""Shared pytest fixtures and helpers for the backend test suite."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

# Point tests at an isolated .env so the real secrets are never required.
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-signing-sessions")

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def fixtures_dir() -> Path:
    """Return the absolute path to the ``tests/fixtures/`` directory."""
    return FIXTURES_DIR


@pytest.fixture()
def sample_txt_bytes(fixtures_dir: Path) -> bytes:
    return (fixtures_dir / "sample.txt").read_bytes()
