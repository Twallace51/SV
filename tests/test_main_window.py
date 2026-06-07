"""Tests for MainWindow."""

import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QLabel

sys.path.insert(0, str(Path(__file__).parent.parent))
from main import MainWindow
from __init__ import __version__


@pytest.fixture
def window(qapp):
    win = MainWindow("testuser")
    yield win
    win.close()


class TestMainWindowInit:
    def test_window_title_contains_version(self, window):
        assert __version__ in window.windowTitle()

    def test_window_title_contains_username(self, window):
        assert "testuser" in window.windowTitle()

    def test_default_size(self, window):
        assert window.width() == 800
        assert window.height() == 600

    def test_central_widget_is_label(self, window):
        central = window.centralWidget()
        assert isinstance(central, QLabel)
        assert central.text() == "Welcome!"


class TestMainWindowMenuBar:
    def test_menu_bar_exists(self, window):
        assert window.menuBar() is not None

    def test_file_menu_present(self, window):
        titles = [a.text() for a in window.menuBar().actions()]
        assert any("File" in t for t in titles)

    def test_edit_menu_present(self, window):
        titles = [a.text() for a in window.menuBar().actions()]
        assert any("Edit" in t for t in titles)

    def test_navigation_menu_present(self, window):
        titles = [a.text() for a in window.menuBar().actions()]
        assert any("Navigation" in t for t in titles)

    def test_help_menu_present(self, window):
        titles = [a.text() for a in window.menuBar().actions()]
        assert any("Help" in t for t in titles)

    def test_file_menu_has_new_action(self, window):
        action_texts = [a.text() for a in window.file_menu.actions() if not a.isSeparator()]
        assert any("New" in t for t in action_texts)

    def test_file_menu_has_open_action(self, window):
        action_texts = [a.text() for a in window.file_menu.actions() if not a.isSeparator()]
        assert any("Open" in t for t in action_texts)

    def test_file_menu_does_not_have_exit_action(self, window):
        action_texts = [a.text() for a in window.file_menu.actions() if not a.isSeparator()]
        assert all("Exit" not in t for t in action_texts)

    def test_navigation_menu_has_logout_action(self, window):
        action_texts = [a.text() for a in window.navigation_menu.actions() if not a.isSeparator()]
        assert any("Logout" in t for t in action_texts)

    def test_navigation_menu_has_exit_action(self, window):
        action_texts = [a.text() for a in window.navigation_menu.actions() if not a.isSeparator()]
        assert any("Exit" in t for t in action_texts)


class TestMainWindowTitleUpdate:
    def test_title_reflects_constructor_username(self, qapp):
        win = MainWindow("alice")
        try:
            assert "alice" in win.windowTitle()
        finally:
            win.close()

    def test_different_usernames_produce_different_titles(self, qapp):
        win1 = MainWindow("alice")
        win2 = MainWindow("bob")
        try:
            assert win1.windowTitle() != win2.windowTitle()
        finally:
            win1.close()
            win2.close()
