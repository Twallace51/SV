"""Shared pytest fixtures for the test suite."""

# region - imports
import sys
import pytest
from PySide6.QtWidgets import QApplication
# endregion


@pytest.fixture(scope="session")
def qapp():
    """Provide a single QApplication instance for the entire test session."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app
