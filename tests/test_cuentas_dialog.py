"""Tests for cuentas dialogs: NuevoCuentaDialog, BuscarCuentaDialog."""

import sqlite3
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from __init__ import reset_active_db_path, set_active_db_path
from dialogs import alumnos as alumnos_dialogs
from dialogs import parientes as parientes_dialogs
from dialogs.cuentas import BuscarCuentaDialog, EditCuentaDialog, NuevoCuentaDialog


# ---------------------------------------------------------------------------
# Shared DB helpers
# ---------------------------------------------------------------------------

def _create_minimal_cuentas_db(path: Path):
    """Minimal schema: no adultos, no id_adulto – for backward-compat tests."""
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE alumnos "
            "(id INTEGER PRIMARY KEY, nombres TEXT, paterno TEXT, materno TEXT)"
        )
        conn.execute(
            "CREATE TABLE ctas ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "id_alumno INTEGER, debito REAL, credito REAL, "
            "aclaracion TEXT, fecha TEXT, factura TEXT)"
        )
        conn.execute(
            "INSERT INTO alumnos (id, nombres, paterno, materno) "
            "VALUES (7, 'Ana', 'Lopez', 'Rios')"
        )
        conn.execute(
            "INSERT INTO ctas (id_alumno, debito, credito, aclaracion, fecha, factura) "
            "VALUES (7, 100, 0, 'Pension enero', '2026-01-01', '')"
        )


def _create_full_cuentas_db(path: Path):
    """Full schema: adultos table + alumnos.id_adulto + ctas.id_creditor."""
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE adultos "
            "(id INTEGER PRIMARY KEY, a_nombres TEXT, a_paterno TEXT, a_materno TEXT)"
        )
        conn.execute(
            "CREATE TABLE alumnos ("
            "id INTEGER PRIMARY KEY, nombres TEXT, paterno TEXT, materno TEXT, "
            "id_adulto INTEGER, id_creditor INTEGER)"
        )
        conn.execute(
            "CREATE TABLE ctas ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "id_alumno INTEGER, id_creditor INTEGER, debito REAL, credito REAL, "
            "aclaracion TEXT, fecha TEXT, factura TEXT)"
        )
        conn.executemany(
            "INSERT INTO adultos (id, a_nombres, a_paterno, a_materno) VALUES (?, ?, ?, ?)",
            [
                (10, "Pedro", "Lopez", "Diaz"),
                (20, "Marta", "Perez", "Rios"),
            ],
        )
        conn.executemany(
            "INSERT INTO alumnos "
            "(id, nombres, paterno, materno, id_adulto, id_creditor) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (7, "Ana",  "Lopez", "Rios",   10, 10),
                (8, "Luis", "Perez", "Mamani", 20, 20),
            ],
        )
        conn.executemany(
            "INSERT INTO ctas "
            "(id_alumno, id_creditor, debito, credito, aclaracion, fecha, factura) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (7, 10, 100, 0, "Pension enero",   "2026-01-01", ""),
                (8, 20, 150, 0, "Pension febrero", "2026-01-02", ""),
            ],
        )


def _create_nuevo_cuentas_db(path: Path):
    """DB for NuevoCuentaDialog: adultos + alumnos + ctas with id_creditor."""
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE adultos "
            "(id INTEGER PRIMARY KEY, a_nombres TEXT, a_paterno TEXT, a_materno TEXT)"
        )
        conn.execute(
            "CREATE TABLE alumnos "
            "(id INTEGER PRIMARY KEY, nombres TEXT, paterno TEXT, materno TEXT)"
        )
        conn.execute(
            "CREATE TABLE ctas ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "id_alumno INTEGER, id_creditor INTEGER, debito REAL, credito REAL, "
            "aclaracion TEXT, fecha TEXT, factura TEXT)"
        )
        conn.execute(
            "INSERT INTO adultos (id, a_nombres, a_paterno, a_materno) "
            "VALUES (5, 'Pedro', 'Gomez', 'Diaz')"
        )
        conn.execute(
            "INSERT INTO alumnos (id, nombres, paterno, materno) "
            "VALUES (3, 'Ana', 'Lopez', 'Rios')"
        )




# ---------------------------------------------------------------------------
# BuscarCuentaDialog – column headers
# ---------------------------------------------------------------------------

class TestBuscarCuentaDialogHeaders:
    def test_alumno_id_is_first_column(self, qapp, tmp_path):
        db = tmp_path / "hdr.db"
        _create_minimal_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            assert dlg.table.horizontalHeaderItem(0).text() == "ID Alumno"
        finally:
            reset_active_db_path()

    def test_alumno_name_is_second_column(self, qapp, tmp_path):
        db = tmp_path / "hdr.db"
        _create_minimal_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            assert dlg.table.horizontalHeaderItem(1).text() == "Alumno"
        finally:
            reset_active_db_path()

    def test_id_creditor_is_third_column(self, qapp, tmp_path):
        db = tmp_path / "hdr.db"
        _create_minimal_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            assert dlg.table.horizontalHeaderItem(2).text() == "ID Creditor"
        finally:
            reset_active_db_path()

    def test_creditor_name_is_fourth_column(self, qapp, tmp_path):
        db = tmp_path / "hdr.db"
        _create_minimal_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            assert dlg.table.horizontalHeaderItem(3).text() == "Creditor"
        finally:
            reset_active_db_path()

    def test_remaining_headers(self, qapp, tmp_path):
        db = tmp_path / "hdr.db"
        _create_minimal_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            expected = ["Débito", "Crédito", "Aclaración", "Fecha", "Factura"]
            actual = [dlg.table.horizontalHeaderItem(i).text() for i in range(4, 9)]
            assert actual == expected
        finally:
            reset_active_db_path()


# ---------------------------------------------------------------------------
# BuscarCuentaDialog – data loading (minimal schema)
# ---------------------------------------------------------------------------

class TestBuscarCuentaDialogMinimalSchema:
    def test_loads_alumno_id_in_first_column(self, qapp, tmp_path):
        db = tmp_path / "min.db"
        _create_minimal_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            assert dlg.table.item(0, 0).text() == "7"
        finally:
            reset_active_db_path()

    def test_cuenta_id_stored_as_user_role_on_first_cell(self, qapp, tmp_path):
        db = tmp_path / "min.db"
        _create_minimal_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            assert dlg.table.item(0, 0).data(Qt.UserRole) == 1
        finally:
            reset_active_db_path()

    def test_creditor_columns_empty_when_no_adulto_schema(self, qapp, tmp_path):
        db = tmp_path / "min.db"
        _create_minimal_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            assert dlg.table.item(0, 2).text() == ""
            assert dlg.table.item(0, 3).text() == ""
        finally:
            reset_active_db_path()


# ---------------------------------------------------------------------------
# BuscarCuentaDialog – data loading (full schema)
# ---------------------------------------------------------------------------

class TestBuscarCuentaDialogFullSchema:
    def test_loads_all_rows(self, qapp, tmp_path):
        db = tmp_path / "full.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            assert dlg.table.rowCount() == 2
        finally:
            reset_active_db_path()

    def test_id_creditor_column_shows_adult_id(self, qapp, tmp_path):
        db = tmp_path / "full.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            ids = {dlg.table.item(r, 2).text() for r in range(dlg.table.rowCount())}
            assert ids == {"10", "20"}
        finally:
            reset_active_db_path()

    def test_creditor_name_column_shows_adult_name(self, qapp, tmp_path):
        db = tmp_path / "full.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            names = {dlg.table.item(r, 3).text() for r in range(dlg.table.rowCount())}
            assert any("Pedro" in n for n in names)
            assert any("Marta" in n for n in names)
        finally:
            reset_active_db_path()


# ---------------------------------------------------------------------------
# BuscarCuentaDialog – alumno search filter
# ---------------------------------------------------------------------------

class TestBuscarCuentaAlumnoSearch:
    def test_search_by_alumno_name_filters_rows(self, qapp, tmp_path):
        db = tmp_path / "srch.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            dlg.search_edit.setText("Ana")
            assert dlg.table.rowCount() == 1
            assert dlg.table.item(0, 0).text() == "7"
        finally:
            reset_active_db_path()

    def test_search_by_alumno_id_filters_rows(self, qapp, tmp_path):
        db = tmp_path / "srch.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            dlg.search_edit.setText("8")
            assert dlg.table.rowCount() == 1
            assert dlg.table.item(0, 0).text() == "8"
        finally:
            reset_active_db_path()

    def test_empty_search_shows_all_rows(self, qapp, tmp_path):
        db = tmp_path / "srch.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            dlg.search_edit.setText("")
            assert dlg.table.rowCount() == 2
        finally:
            reset_active_db_path()


# ---------------------------------------------------------------------------
# BuscarCuentaDialog – creditor search filter
# ---------------------------------------------------------------------------

class TestBuscarCuentaCreditorSearch:
    def test_search_by_creditor_id_adulto_filters_rows(self, qapp, tmp_path):
        db = tmp_path / "cred.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            dlg.search_creditor_edit.setText("10")
            assert dlg.table.rowCount() == 1
            assert dlg.table.item(0, 0).text() == "7"
            assert dlg.table.item(0, 2).text() == "10"
        finally:
            reset_active_db_path()

    def test_search_by_creditor_name_filters_rows(self, qapp, tmp_path):
        db = tmp_path / "cred.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            dlg.search_creditor_edit.setText("marta")
            assert dlg.table.rowCount() == 1
            assert dlg.table.item(0, 0).text() == "8"
            assert "Marta" in dlg.table.item(0, 3).text()
        finally:
            reset_active_db_path()

    def test_creditor_and_alumno_search_combined(self, qapp, tmp_path):
        db = tmp_path / "cred.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            dlg.search_edit.setText("Ana")
            dlg.search_creditor_edit.setText("10")
            assert dlg.table.rowCount() == 1
            assert dlg.table.item(0, 0).text() == "7"
        finally:
            reset_active_db_path()

    def test_creditor_search_no_match_returns_empty(self, qapp, tmp_path):
        db = tmp_path / "cred.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = BuscarCuentaDialog()
            dlg.search_creditor_edit.setText("99")
            assert dlg.table.rowCount() == 0
        finally:
            reset_active_db_path()


# ---------------------------------------------------------------------------
# BuscarCuentaDialog – current value buttons
# ---------------------------------------------------------------------------

class TestBuscarCuentaCurrentButtons:
    def test_current_alumno_button_fills_search_with_id(self, qapp, tmp_path):
        db = tmp_path / "btn.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        saved_id, saved_name = alumnos_dialogs.current_alumno_id, alumnos_dialogs.current_alumno_name
        try:
            alumnos_dialogs.current_alumno_id = 8
            alumnos_dialogs.current_alumno_name = "Perez, Luis"
            dlg = BuscarCuentaDialog()
            dlg.current_alumno_btn.click()
            assert dlg.search_edit.text() == "8"
            assert dlg.table.rowCount() == 1
            assert dlg.table.item(0, 0).text() == "8"
        finally:
            alumnos_dialogs.current_alumno_id = saved_id
            alumnos_dialogs.current_alumno_name = saved_name
            reset_active_db_path()

    def test_current_alumno_button_falls_back_to_name_when_no_id(self, qapp, tmp_path):
        db = tmp_path / "btn.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        saved_id, saved_name = alumnos_dialogs.current_alumno_id, alumnos_dialogs.current_alumno_name
        try:
            alumnos_dialogs.current_alumno_id = None
            alumnos_dialogs.current_alumno_name = "Lopez"
            dlg = BuscarCuentaDialog()
            dlg.current_alumno_btn.click()
            assert dlg.search_edit.text() == "Lopez"
        finally:
            alumnos_dialogs.current_alumno_id = saved_id
            alumnos_dialogs.current_alumno_name = saved_name
            reset_active_db_path()

    def test_current_creditor_button_fills_search_with_adulto_id(self, qapp, tmp_path):
        db = tmp_path / "btn.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        saved_id, saved_name = parientes_dialogs.current_adulto_id, parientes_dialogs.current_adulto_name
        try:
            parientes_dialogs.current_adulto_id = 20
            parientes_dialogs.current_adulto_name = "Perez, Marta"
            dlg = BuscarCuentaDialog()
            dlg.current_creditor_btn.click()
            assert dlg.search_creditor_edit.text() == "20"
            assert dlg.table.rowCount() == 1
            assert dlg.table.item(0, 2).text() == "20"
        finally:
            parientes_dialogs.current_adulto_id = saved_id
            parientes_dialogs.current_adulto_name = saved_name
            reset_active_db_path()

    def test_current_creditor_button_falls_back_to_name_when_no_id(self, qapp, tmp_path):
        db = tmp_path / "btn.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        saved_id, saved_name = parientes_dialogs.current_adulto_id, parientes_dialogs.current_adulto_name
        try:
            parientes_dialogs.current_adulto_id = None
            parientes_dialogs.current_adulto_name = "Perez, Marta"
            dlg = BuscarCuentaDialog()
            dlg.current_creditor_btn.click()
            assert dlg.search_creditor_edit.text() == "Perez, Marta"
        finally:
            parientes_dialogs.current_adulto_id = saved_id
            parientes_dialogs.current_adulto_name = saved_name
            reset_active_db_path()


# ---------------------------------------------------------------------------
# BuscarCuentaDialog – double-click opens EditCuentaDialog
# ---------------------------------------------------------------------------

class TestBuscarCuentaDoubleClick:
    def test_double_click_opens_edit_dialog_with_cuenta_id(self, qapp, tmp_path, monkeypatch):
        db = tmp_path / "dbl.db"
        _create_minimal_cuentas_db(db)
        set_active_db_path(db)
        try:
            calls = []

            class FakeEdit:
                def __init__(self, record_id, parent=None, is_admin=False):
                    calls.append(("created", record_id, is_admin))

                def exec(self):
                    calls.append("exec")
                    return QDialog.Accepted

            monkeypatch.setattr("dialogs.cuentas.EditCuentaDialog", FakeEdit)
            dlg = BuscarCuentaDialog(is_admin=True)
            dlg._on_double_click(0, 0)

            assert calls[0] == ("created", 1, True)
            assert "exec" in calls
        finally:
            reset_active_db_path()

    def test_double_click_reloads_table_after_accepted(self, qapp, tmp_path, monkeypatch):
        db = tmp_path / "dbl.db"
        _create_minimal_cuentas_db(db)
        set_active_db_path(db)
        try:
            reloads = []

            class FakeEdit:
                def __init__(self, *a, **kw):
                    pass

                def exec(self):
                    return QDialog.Accepted

            monkeypatch.setattr("dialogs.cuentas.EditCuentaDialog", FakeEdit)
            dlg = BuscarCuentaDialog()
            monkeypatch.setattr(dlg, "_load", lambda *_: reloads.append(True))
            dlg._on_double_click(0, 0)

            assert reloads == [True]
        finally:
            reset_active_db_path()


# ---------------------------------------------------------------------------
# NuevoCuentaDialog – creditor name sync
# ---------------------------------------------------------------------------

class TestNuevoCuentaCreditorSync:
    def test_creditor_label_starts_as_dash(self, qapp, tmp_path):
        db = tmp_path / "nc.db"
        _create_nuevo_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = NuevoCuentaDialog()
            assert dlg.creditor.text() == "-"
        finally:
            reset_active_db_path()

    def test_creditor_label_shows_name_for_valid_id(self, qapp, tmp_path):
        db = tmp_path / "nc.db"
        _create_nuevo_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = NuevoCuentaDialog()
            dlg.id_creditor.setText("5")
            assert dlg.creditor.text() == "Pedro Gomez"
        finally:
            reset_active_db_path()

    def test_creditor_label_shows_not_found_for_missing_id(self, qapp, tmp_path):
        db = tmp_path / "nc.db"
        _create_nuevo_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = NuevoCuentaDialog()
            dlg.id_creditor.setText("99")
            assert dlg.creditor.text() == "No encontrado"
        finally:
            reset_active_db_path()

    def test_creditor_label_shows_invalid_for_non_integer(self, qapp, tmp_path):
        db = tmp_path / "nc.db"
        _create_nuevo_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = NuevoCuentaDialog()
            dlg.id_creditor.setText("abc")
            assert dlg.creditor.text() == "ID inválido"
        finally:
            reset_active_db_path()

    def test_creditor_label_resets_to_dash_when_cleared(self, qapp, tmp_path):
        db = tmp_path / "nc.db"
        _create_nuevo_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = NuevoCuentaDialog()
            dlg.id_creditor.setText("5")
            dlg.id_creditor.clear()
            assert dlg.creditor.text() == "-"
        finally:
            reset_active_db_path()


class TestCuentaCurrentIdButtons:
    def test_nuevo_current_alumno_button_autoloads_shared_alumno_id(self, qapp, tmp_path):
        db = tmp_path / "current_btns.db"
        _create_nuevo_cuentas_db(db)
        set_active_db_path(db)
        saved_id, saved_name = alumnos_dialogs.current_alumno_id, alumnos_dialogs.current_alumno_name
        try:
            alumnos_dialogs.current_alumno_id = 3
            alumnos_dialogs.current_alumno_name = "Lopez, Ana"
            dlg = NuevoCuentaDialog()

            assert dlg.current_alumno_btn.isEnabled() is True

            dlg.current_alumno_btn.click()

            assert dlg.id_alumno.text() == "3"
            assert dlg.alumno.text() == "Lopez, Ana"
        finally:
            alumnos_dialogs.current_alumno_id = saved_id
            alumnos_dialogs.current_alumno_name = saved_name
            reset_active_db_path()

    def test_nuevo_current_adulto_button_autoloads_shared_adulto_id(self, qapp, tmp_path):
        db = tmp_path / "current_btns.db"
        _create_nuevo_cuentas_db(db)
        set_active_db_path(db)
        saved_id, saved_name = parientes_dialogs.current_adulto_id, parientes_dialogs.current_adulto_name
        try:
            parientes_dialogs.current_adulto_id = 5
            parientes_dialogs.current_adulto_name = "Pedro Gomez"
            dlg = NuevoCuentaDialog()

            assert dlg.current_adulto_btn.isEnabled() is True

            dlg.current_adulto_btn.click()

            assert dlg.id_creditor.text() == "5"
            assert dlg.creditor.text() == "Pedro Gomez"
        finally:
            parientes_dialogs.current_adulto_id = saved_id
            parientes_dialogs.current_adulto_name = saved_name
            reset_active_db_path()

    def test_nuevo_current_buttons_disable_when_shared_ids_missing(self, qapp, tmp_path):
        db = tmp_path / "current_btns.db"
        _create_nuevo_cuentas_db(db)
        set_active_db_path(db)
        saved_alumno_id, saved_alumno_name = alumnos_dialogs.current_alumno_id, alumnos_dialogs.current_alumno_name
        saved_adulto_id, saved_adulto_name = parientes_dialogs.current_adulto_id, parientes_dialogs.current_adulto_name
        try:
            alumnos_dialogs.current_alumno_id = None
            alumnos_dialogs.current_alumno_name = None
            parientes_dialogs.current_adulto_id = None
            parientes_dialogs.current_adulto_name = None
            dlg = NuevoCuentaDialog()

            assert dlg.current_alumno_btn.isEnabled() is False
            assert dlg.current_adulto_btn.isEnabled() is False
        finally:
            alumnos_dialogs.current_alumno_id = saved_alumno_id
            alumnos_dialogs.current_alumno_name = saved_alumno_name
            parientes_dialogs.current_adulto_id = saved_adulto_id
            parientes_dialogs.current_adulto_name = saved_adulto_name
            reset_active_db_path()

    def test_edit_current_buttons_disable_when_shared_ids_missing(self, qapp, tmp_path):
        db = tmp_path / "edit_current_btns.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        saved_alumno_id, saved_alumno_name = alumnos_dialogs.current_alumno_id, alumnos_dialogs.current_alumno_name
        saved_adulto_id, saved_adulto_name = parientes_dialogs.current_adulto_id, parientes_dialogs.current_adulto_name
        try:
            alumnos_dialogs.current_alumno_id = None
            alumnos_dialogs.current_alumno_name = None
            parientes_dialogs.current_adulto_id = None
            parientes_dialogs.current_adulto_name = None
            dlg = EditCuentaDialog(1)

            assert dlg.current_alumno_btn.isEnabled() is False
            assert dlg.current_adulto_btn.isEnabled() is False
        finally:
            alumnos_dialogs.current_alumno_id = saved_alumno_id
            alumnos_dialogs.current_alumno_name = saved_alumno_name
            parientes_dialogs.current_adulto_id = saved_adulto_id
            parientes_dialogs.current_adulto_name = saved_adulto_name
            reset_active_db_path()


class TestCuentaAmountFieldInterlocks:
    def test_nuevo_debito_disables_creditor_field_and_current_adulto_button(self, qapp, tmp_path):
        db = tmp_path / "interlocks_nuevo.db"
        _create_nuevo_cuentas_db(db)
        set_active_db_path(db)
        saved_adulto_id, saved_adulto_name = parientes_dialogs.current_adulto_id, parientes_dialogs.current_adulto_name
        try:
            parientes_dialogs.current_adulto_id = 5
            parientes_dialogs.current_adulto_name = "Pedro Gomez"
            dlg = NuevoCuentaDialog()

            assert dlg.id_creditor.isEnabled() is True
            assert dlg.current_adulto_btn.isEnabled() is True

            dlg.debito.setValue(100)

            assert dlg.id_creditor.isEnabled() is False
            assert dlg.current_adulto_btn.isEnabled() is False
        finally:
            parientes_dialogs.current_adulto_id = saved_adulto_id
            parientes_dialogs.current_adulto_name = saved_adulto_name
            reset_active_db_path()

    def test_nuevo_creditor_id_disables_debito_when_debito_is_zero(self, qapp, tmp_path):
        db = tmp_path / "interlocks_nuevo.db"
        _create_nuevo_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = NuevoCuentaDialog()
            dlg.id_creditor.setText("5")

            assert dlg.debito.isEnabled() is False
        finally:
            reset_active_db_path()

    def test_edit_creditor_id_disables_debito_when_debito_is_zero(self, qapp, tmp_path):
        db = tmp_path / "interlocks_edit.db"
        _create_full_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = EditCuentaDialog(1)
            dlg.debito.setValue(0)
            dlg.id_creditor.setText("20")

            assert dlg.debito.isEnabled() is False
        finally:
            reset_active_db_path()


# ---------------------------------------------------------------------------
# NuevoCuentaDialog – save persists id_creditor
# ---------------------------------------------------------------------------

class TestNuevoCuentaSaveCreditor:
    def test_save_persists_id_creditor_when_provided(self, qapp, tmp_path, monkeypatch):
        db = tmp_path / "nc_save.db"
        _create_nuevo_cuentas_db(db)
        set_active_db_path(db)
        try:
            monkeypatch.setattr("dialogs.cuentas.QMessageBox.warning", lambda *a, **kw: None)
            dlg = NuevoCuentaDialog()
            dlg.id_alumno.setText("3")
            dlg.debito.setValue(200)
            dlg.id_creditor.setText("5")
            dlg._save()

            with sqlite3.connect(db) as conn:
                row = conn.execute(
                    "SELECT id_alumno, id_creditor, debito FROM ctas"
                ).fetchone()
            assert row == (3, 5, 200.0)
        finally:
            reset_active_db_path()

    def test_save_persists_null_id_creditor_when_empty(self, qapp, tmp_path, monkeypatch):
        db = tmp_path / "nc_null.db"
        _create_nuevo_cuentas_db(db)
        set_active_db_path(db)
        try:
            monkeypatch.setattr("dialogs.cuentas.QMessageBox.warning", lambda *a, **kw: None)
            dlg = NuevoCuentaDialog()
            dlg.id_alumno.setText("3")
            dlg.debito.setValue(100)
            dlg._save()

            with sqlite3.connect(db) as conn:
                row = conn.execute("SELECT id_creditor FROM ctas").fetchone()
            assert row[0] is None
        finally:
            reset_active_db_path()

    def test_save_rejects_nonexistent_creditor_id(self, qapp, tmp_path, monkeypatch):
        db = tmp_path / "nc_bad.db"
        _create_nuevo_cuentas_db(db)
        set_active_db_path(db)
        try:
            warnings = []
            monkeypatch.setattr(
                "dialogs.cuentas.QMessageBox.warning",
                lambda *a, **kw: warnings.append(a),
            )
            dlg = NuevoCuentaDialog()
            dlg.id_alumno.setText("3")
            dlg.debito.setValue(100)
            dlg.id_creditor.setText("99")
            dlg._save()

            with sqlite3.connect(db) as conn:
                count = conn.execute("SELECT COUNT(*) FROM ctas").fetchone()[0]
            assert count == 0
            assert warnings
        finally:
            reset_active_db_path()

    def test_save_rejects_non_integer_creditor_id(self, qapp, tmp_path, monkeypatch):
        db = tmp_path / "nc_nan.db"
        _create_nuevo_cuentas_db(db)
        set_active_db_path(db)
        try:
            warnings = []
            monkeypatch.setattr(
                "dialogs.cuentas.QMessageBox.warning",
                lambda *a, **kw: warnings.append(a),
            )
            dlg = NuevoCuentaDialog()
            dlg.id_alumno.setText("3")
            dlg.debito.setValue(100)
            dlg.id_creditor.setText("abc")
            dlg._save()

            with sqlite3.connect(db) as conn:
                count = conn.execute("SELECT COUNT(*) FROM ctas").fetchone()[0]
            assert count == 0
            assert warnings
        finally:
            reset_active_db_path()
