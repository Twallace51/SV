"""Tests for MainWindow."""

# region - imports
import runpy
import sys
import types
from pathlib import Path

import pytest
from PySide6.QtWidgets import QLabel, QDialog, QWidget

sys.path.insert(0, str(Path(__file__).parent.parent))
from windows.main_window import MainWindow
from __init__ import VERSION, DB_PATH, get_active_db_path, set_active_db_path, reset_active_db_path
# endregion

@pytest.fixture
def window(qapp):
    win = MainWindow("testuser")
    yield win
    win.close()
class TestMainWindowInit:
    def test_window_title_contains_version(self, window):
        assert VERSION in window.windowTitle()

    def test_window_title_contains_username(self, window):
        assert "testuser" in window.windowTitle()

    def test_default_size(self, window):
        assert window.width() == 800
        assert window.height() == 600

    def test_central_widget_contains_welcome_label(self, window):
        central = window.centralWidget()
        assert isinstance(central, QWidget)
        assert isinstance(window.welcome_label, QLabel)
        assert window.welcome_label.text() == "¡Bienvenido!"

    def test_current_alumno_id_defaults_to_dash(self, window):
        assert window.current_alumno_id_label.text() == "Current alumno ID:"
        assert window.current_alumno_id_value.text() == "-"

    def test_current_adulto_id_defaults_to_dash(self, window):
        assert window.current_adulto_id_label.text() == "Current adulto ID:"
        assert window.current_adulto_id_value.text() == "-"

    def test_refresh_current_alumno_id_label_uses_shared_state(self, window, monkeypatch):
        monkeypatch.setattr("windows.main_window.alumnos_dialogs.current_alumno_id", 23)
        window._refresh_current_alumno_id_label()

        assert window.current_alumno_id_value.text() == "23"

    def test_refresh_current_adulto_id_label_uses_shared_state(self, window, monkeypatch):
        monkeypatch.setattr("windows.main_window.parientes_dialogs.current_adulto_id", 41)
        window._refresh_current_adulto_id_label()

        assert window.current_adulto_id_value.text() == "41"
class TestMainWindowMenuBar:
    def test_menu_bar_exists(self, window):
        assert window.menuBar() is not None

    def test_navigation_menu_comes_before_file_menu(self, window):
        titles = [action.text().replace("&", "") for action in window.menuBar().actions()]
        assert titles.index("Navegación") < titles.index("Archivo")

    def test_file_menu_present(self, window):
        titles = [a.text() for a in window.menuBar().actions()]
        assert any("Archivo" in t for t in titles)

    def test_edit_menu_not_present(self, window):
        titles = [a.text() for a in window.menuBar().actions()]
        assert all("Editar" not in t for t in titles)

    def test_navigation_menu_present(self, window):
        titles = [a.text() for a in window.menuBar().actions()]
        assert any("Navegación" in t for t in titles)

    def test_help_menu_present(self, window):
        titles = [a.text() for a in window.menuBar().actions()]
        assert any("yuda" in t for t in titles)

    def test_file_menu_does_not_have_new_action(self, window):
        action_texts = [a.text() for a in window.file_menu.actions() if not a.isSeparator()]
        assert all("Nuevo" not in t for t in action_texts)

    def test_file_menu_does_not_have_open_action(self, window):
        action_texts = [a.text() for a in window.file_menu.actions() if not a.isSeparator()]
        assert all("Abrir" not in t for t in action_texts)

    def test_file_menu_has_backup_action(self, window):
        action_texts = [a.text() for a in window.file_menu.actions() if not a.isSeparator()]
        assert any("Backup" in t for t in action_texts)

    def test_file_menu_does_not_have_exit_action(self, window):
        action_texts = [a.text() for a in window.file_menu.actions() if not a.isSeparator()]
        assert all("Salir" not in t for t in action_texts)

    def test_navigation_menu_has_logout_action(self, window):
        action_texts = [a.text() for a in window.navigation_menu.actions() if not a.isSeparator()]
        assert any("Cerrar sesión" in t for t in action_texts)

    def test_navigation_menu_has_exit_action(self, window):
        action_texts = [a.text() for a in window.navigation_menu.actions() if not a.isSeparator()]
        assert any("Salir" in t for t in action_texts)

    def test_logout_action_reopens_login_dialog_and_updates_user(self, window, monkeypatch):
        shown = []
        hidden = []
        closed = []

        class FakeLoginDialog:
            def __init__(self, parent=None):
                self.parent = parent
                self.logged_in_username = "admin"

            def exec(self):
                return QDialog.Accepted

        monkeypatch.setattr("windows.main_window.LoginDialog", FakeLoginDialog)
        monkeypatch.setattr(window, "show", lambda: shown.append(True))
        monkeypatch.setattr(window, "hide", lambda: hidden.append(True))
        monkeypatch.setattr(window, "close", lambda: closed.append(True))

        window.logout_action.trigger()

        assert hidden == [True]
        assert shown == [True]
        assert closed == []
        assert "admin" in window.windowTitle()

    def test_logout_action_closes_window_when_relogin_cancelled(self, window, monkeypatch):
        hidden = []
        closed = []

        class FakeLoginDialog:
            def __init__(self, parent=None):
                self.parent = parent
                self.logged_in_username = ""

            def exec(self):
                return QDialog.Rejected

        monkeypatch.setattr("windows.main_window.LoginDialog", FakeLoginDialog)
        monkeypatch.setattr(window, "hide", lambda: hidden.append(True))
        monkeypatch.setattr(window, "close", lambda: closed.append(True))

        window.logout_action.trigger()

        assert hidden == [True]
        assert closed == [True]

    def test_logout_relogin_dialog_created_without_parent(self, window, monkeypatch):
        created_parents = []

        class FakeLoginDialog:
            def __init__(self, parent=None):
                created_parents.append(parent)
                self.logged_in_username = "admin"

            def exec(self):
                return QDialog.Accepted

        monkeypatch.setattr("windows.main_window.LoginDialog", FakeLoginDialog)
        monkeypatch.setattr(window, "show", lambda: None)
        monkeypatch.setattr(window, "hide", lambda: None)
        monkeypatch.setattr(window, "close", lambda: None)

        window.logout_action.trigger()

        assert created_parents == [None]
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


class TestTraineeDatabaseSession:
    def test_trainee_login_creates_and_uses_temp_database(self, qapp, tmp_path, monkeypatch):
        source_db = tmp_path / "SV.db"
        source_db.write_text("db", encoding="utf-8")
        copied_paths = {}
        active_paths = []

        def fake_copy2(src, dst):
            copied_paths["src"] = Path(src)
            copied_paths["dst"] = Path(dst)
            Path(dst).write_text("db", encoding="utf-8")
            return dst

        monkeypatch.setattr("windows.main_window.DB_PATH", source_db)
        monkeypatch.setattr("windows.main_window.shutil.copy2", fake_copy2)
        monkeypatch.setattr(
            "windows.main_window.set_active_db_path",
            lambda p: active_paths.append(Path(p)),
        )

        win = MainWindow("trainee")
        try:
            assert copied_paths["src"] == source_db
            assert copied_paths["dst"].exists()
            assert active_paths == [copied_paths["dst"]]
            assert "Modo Entrenamiento DB Temporal" in win.windowTitle()
        finally:
            win.close()

    def test_cleanup_removes_temp_database_and_restores_default(self, qapp, tmp_path):
        reset_active_db_path()
        win = MainWindow("user")
        temp_db = tmp_path / "session_temp.db"
        temp_db.write_text("db", encoding="utf-8")

        try:
            set_active_db_path(temp_db)
            win._trainee_temp_db_path = temp_db

            win._cleanup_trainee_temp_database()

            assert not temp_db.exists()
            assert get_active_db_path() == DB_PATH
        finally:
            win.close()
            reset_active_db_path()


class TestMainWindowBootstrap:
    def test_running_main_window_as_main_delegates_to_main_main(self, monkeypatch):
        called = []

        fake_main_module = types.ModuleType("main")

        def fake_main():
            called.append(True)

        fake_main_module.main = fake_main
        monkeypatch.setitem(sys.modules, "main", fake_main_module)

        main_window_path = Path(__file__).parent.parent / "windows" / "main_window.py"
        runpy.run_path(str(main_window_path), run_name="__main__")

        assert called == [True]
