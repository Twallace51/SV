"""Tests for cuentas dialogs."""

import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from __init__ import reset_active_db_path, set_active_db_path
from dialogs.cuentas import BuscarCuentaDialog


def _create_cuentas_dialog_database(path: Path):
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE alumnos ("
            "id INTEGER PRIMARY KEY, nombres TEXT, paterno TEXT, materno TEXT)"
        )
        connection.execute(
            "CREATE TABLE ctas ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "id_alumno INTEGER, debito REAL, credito REAL, "
            "aclaracion TEXT, fecha TEXT, factura TEXT)"
        )
        connection.execute(
            "INSERT INTO alumnos (id, nombres, paterno, materno) VALUES (7, 'Ana', 'Lopez', 'Rios')"
        )
        connection.execute(
            "INSERT INTO ctas (id_alumno, debito, credito, aclaracion, fecha, factura) "
            "VALUES (7, 100, 0, 'Pension enero', '2026-01-01', '')"
        )


def test_buscar_cuenta_dialog_shows_alumno_id_first_and_uses_hidden_cuenta_id(qapp, tmp_path, monkeypatch):
    database = tmp_path / "cuentas_dialog.db"
    _create_cuentas_dialog_database(database)
    set_active_db_path(database)
    try:
        calls = []

        class FakeEditCuentaDialog:
            def __init__(self, record_id, parent=None, is_admin=False):
                calls.append(("created", record_id, parent, is_admin))

            def exec(self):
                calls.append(("exec", None))
                return QDialog.Accepted

        monkeypatch.setattr("dialogs.cuentas.EditCuentaDialog", FakeEditCuentaDialog)

        dialog = BuscarCuentaDialog(is_admin=True)

        assert dialog.table.horizontalHeaderItem(0).text() == "ID Alumno"
        assert dialog.table.item(0, 0).text() == "7"
        assert dialog.table.item(0, 0).data(Qt.UserRole) == 1

        dialog._on_double_click(0, 0)

        assert calls == [("created", 1, dialog, True), ("exec", None)]
    finally:
        reset_active_db_path()
