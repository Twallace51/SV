"""Tests for LoginDialog."""

# region - imports

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Qt

sys.path.insert(0, str(Path(__file__).parent.parent))
from dialogs.login import LoginDialog
from __init__ import PROJECT_NAME, VERSION

# endregion

@pytest.fixture
def dialog(qapp):
    dlg = LoginDialog()
    yield dlg
    dlg.close()

class TestLoginDialogInit:
    def test_window_title(self, dialog):
        assert dialog.windowTitle() == f"{PROJECT_NAME} - Versión: {VERSION}"

    def test_title_label(self, dialog):
        assert dialog.title_label.text() == f"{PROJECT_NAME} - Versión: {VERSION}\nIniciar Session Modo:"

    def test_fixed_size(self, dialog):
        assert dialog.width() == 500
        assert dialog.height() == 190

    def test_logged_in_username_initially_empty(self, dialog):
        assert dialog.logged_in_username == ""

    def test_has_quit_button(self, dialog):
        assert dialog.quit_btn.text() == "Salir"

    def test_has_training_mode_button(self, dialog):
        assert dialog.training_mode_btn.text() == "Entrenamiento"

    def test_has_admin_mode_button(self, dialog):
        assert dialog.admin_mode_btn.text() == "Admin"

    def test_has_normal_user_mode_button(self, dialog):
        assert dialog.normal_user_mode_btn.text() == "Usuario Normal"

class TestQuitButton:
    def test_quit_button_rejects_dialog(self, dialog):
        rejected = []
        original_reject = dialog.reject
        dialog.reject = lambda: rejected.append(True) or original_reject()

        dialog.quit_btn.click()

        assert rejected == [True]


class TestTrainingModeButton:
    def test_training_mode_button_logs_in_as_trainee(self, dialog):
        accepted = []
        original_accept = dialog.accept
        dialog.accept = lambda: accepted.append(True) or original_accept()

        dialog.training_mode_btn.click()

        assert accepted == [True]
        assert dialog.logged_in_username == "trainee"


class TestNormalUserModeButton:
    def test_normal_user_mode_button_logs_in_as_user(self, dialog):
        accepted = []
        original_accept = dialog.accept
        dialog.accept = lambda: accepted.append(True) or original_accept()

        dialog.normal_user_mode_btn.click()

        assert accepted == [True]
        assert dialog.logged_in_username == "user"


class TestAdminModeButton:
    def test_admin_mode_button_logs_in_as_admin_with_valid_password(self, dialog, monkeypatch):
        monkeypatch.setattr(
            "dialogs.login.QInputDialog.getText",
            lambda *args, **kwargs: ("admin", True),
        )

        accepted = []
        original_accept = dialog.accept
        dialog.accept = lambda: accepted.append(True) or original_accept()

        dialog.admin_mode_btn.click()

        assert accepted == [True]
        assert dialog.logged_in_username == "admin"

    def test_admin_mode_button_invalid_password_shows_error(self, dialog, monkeypatch):
        monkeypatch.setattr(
            "dialogs.login.QInputDialog.getText",
            lambda *args, **kwargs: ("wrong", True),
        )

        warning_calls = []
        monkeypatch.setattr(
            "dialogs.login.QMessageBox.warning",
            lambda *args, **kwargs: warning_calls.append((args, kwargs)),
        )

        accepted = []
        original_accept = dialog.accept
        dialog.accept = lambda: accepted.append(True) or original_accept()

        dialog.admin_mode_btn.click()

        assert accepted == []
        assert dialog.logged_in_username == ""
        assert len(warning_calls) == 1

    def test_admin_mode_button_cancel_does_nothing(self, dialog, monkeypatch):
        monkeypatch.setattr(
            "dialogs.login.QInputDialog.getText",
            lambda *args, **kwargs: ("", False),
        )

        accepted = []
        original_accept = dialog.accept
        dialog.accept = lambda: accepted.append(True) or original_accept()

        dialog.admin_mode_btn.click()

        assert accepted == []
        assert dialog.logged_in_username == ""

class TestRightClickScrollShortcut:
    def test_right_btn_held_flag_set_on_press(self, dialog):
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QPointF, QPoint
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(0, 0),
            QPointF(0, 0),
            Qt.RightButton,
            Qt.RightButton,
            Qt.NoModifier,
        )
        dialog.mousePressEvent(event)
        assert dialog._right_btn_held is True

    def test_right_btn_held_flag_cleared_on_release(self, dialog):
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QPointF
        press = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(0, 0),
            QPointF(0, 0),
            Qt.RightButton,
            Qt.RightButton,
            Qt.NoModifier,
        )
        release = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(0, 0),
            QPointF(0, 0),
            Qt.RightButton,
            Qt.RightButton,
            Qt.NoModifier,
        )
        dialog.mousePressEvent(press)
        dialog.mouseReleaseEvent(release)
        assert dialog._right_btn_held is False
