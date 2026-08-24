from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir() -> Path:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)
        (path / "test.txt").write_text("Test content")
        yield path