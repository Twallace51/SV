"""Tests for LoginDialog."""

# region - imports

import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QLineEdit
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
        assert dialog.title_label.text() == f"{PROJECT_NAME} - Versión: {VERSION}\nIniciar Sesión"

    def test_fixed_size(self, dialog):
        assert dialog.width() == 500
        assert dialog.height() == 160

    def test_password_echo_mode_default(self, dialog):
        assert dialog.password_edit.echoMode() == QLineEdit.Password

    def test_logged_in_username_initially_empty(self, dialog):
        assert dialog.logged_in_username == ""

    def test_has_quit_button(self, dialog):
        assert dialog.quit_btn.text() == "Salir"

    def test_has_training_mode_button(self, dialog):
        assert dialog.training_mode_btn.text() == "Modo Entrenamiento"

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
        assert dialog.username_edit.text() == "trainee"
        assert dialog.password_edit.text() == "trainee"

class TestPasswordToggle:
    def test_toggle_show(self, dialog):
        dialog.toggle_password_visibility(True)
        assert dialog.password_edit.echoMode() == QLineEdit.Normal
        assert dialog.password_toggle_btn.text() == "Ocultar"

    def test_toggle_hide(self, dialog):
        dialog.toggle_password_visibility(True)
        dialog.toggle_password_visibility(False)
        assert dialog.password_edit.echoMode() == QLineEdit.Password
        assert dialog.password_toggle_btn.text() == "Mostrar"

class TestHandleLogin:
    @pytest.mark.parametrize("username,password", [
        ("admin", "admin"),
        ("user", "user"),
        ("trainee", "trainee"),
    ])
    def test_valid_credentials_set_username(self, dialog, username, password):
        dialog.username_edit.setText(username)
        dialog.password_edit.setText(password)
        # Intercept accept so the dialog doesn't actually close during the test
        accepted = []
        original_accept = dialog.accept
        dialog.accept = lambda: accepted.append(True) or original_accept()
        dialog.handle_login()
        assert dialog.logged_in_username == username

    def test_invalid_credentials_clear_password(self, qapp, monkeypatch):
        # Suppress the QMessageBox warning during the test
        monkeypatch.setattr(
            "main.QMessageBox.warning",
            lambda *args, **kwargs: None,
        )
        dlg = LoginDialog()
        dlg.username_edit.setText("admin")
        dlg.password_edit.setText("wrong")
        dlg.handle_login()
        assert dlg.password_edit.text() == ""
        assert dlg.logged_in_username == ""
        dlg.close()

    def test_invalid_trainee_credentials_show_password_reminder(self, dialog, monkeypatch):
        warning_calls = []
        monkeypatch.setattr(
            "dialogs.login.QMessageBox.warning",
            lambda *args, **kwargs: warning_calls.append((args, kwargs)),
        )

        dialog.username_edit.setText("trainee")
        dialog.password_edit.setText("wrong")
        dialog.handle_login()

        assert len(warning_calls) == 1
        args, _ = warning_calls[0]
        assert args[1] == "Error de acceso"
        assert "trainee" in args[2]
        assert dialog.password_edit.text() == ""

    def test_username_stripped_of_whitespace(self, dialog, monkeypatch):
        monkeypatch.setattr(
            "dialogs.login.QMessageBox.warning",
            lambda *args, **kwargs: None,
        )
        dialog.username_edit.setText("  admin  ")
        dialog.password_edit.setText("admin")
        accepted = []
        original_accept = dialog.accept
        dialog.accept = lambda: accepted.append(True) or original_accept()
        dialog.handle_login()
        assert dialog.logged_in_username == "admin"

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
