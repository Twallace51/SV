"""Tests for cuentas reports."""

import sqlite3
from pathlib import Path

from __init__ import reset_active_db_path, set_active_db_path
from dialogs.reportes_cuentas import ReporteCuentasTotalDialog, ReporteCuentasAlumnosDialog


def _create_cuentas_database(path: Path):
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE ctas ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "id_alumno INTEGER, debito REAL, credito REAL, "
            "aclaracion TEXT, fecha TEXT, factura TEXT)"
        )
        connection.executemany(
            "INSERT INTO ctas (id_alumno, debito, credito, aclaracion, fecha, factura) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (1, 100, 0,   "Pension enero",  "2026-01-01", ""),
                (1, 0,   200, "Pago enero",     "2026-01-15", "F-001"),
                (2, 150, 0,   "Pension febrero","2026-02-01", ""),
                (2, 0,   150, "Pago febrero",   "2026-02-10", "F-002"),
            ],
        )


def test_cuentas_total_dialog_computes_correct_total(qapp, tmp_path):
    database = tmp_path / "cuentas_report.db"
    _create_cuentas_database(database)
    set_active_db_path(database)
    try:
        dialog = ReporteCuentasTotalDialog()

        # creditos = 200 + 150 = 350, debitos = 100 + 150 = 250, total = 100
        assert dialog._total == 100.0
        assert "+100" in dialog.total_label.text()
    finally:
        reset_active_db_path()


def test_cuentas_total_dialog_shows_negative_total(qapp, tmp_path):
    database = tmp_path / "cuentas_report_neg.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE ctas ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "id_alumno INTEGER, debito REAL, credito REAL, "
            "aclaracion TEXT, fecha TEXT, factura TEXT)"
        )
        connection.execute(
            "INSERT INTO ctas (id_alumno, debito, credito, aclaracion, fecha, factura) "
            "VALUES (1, 500, 100, 'test', '2026-01-01', '')"
        )
    set_active_db_path(database)
    try:
        dialog = ReporteCuentasTotalDialog()

        assert dialog._total == -400.0
        assert "-400" in dialog.total_label.text()
        assert "+" not in dialog.total_label.text()
    finally:
        reset_active_db_path()


def test_cuentas_total_dialog_empty_table_shows_zero(qapp, tmp_path):
    database = tmp_path / "cuentas_report_empty.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE ctas ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "id_alumno INTEGER, debito REAL, credito REAL, "
            "aclaracion TEXT, fecha TEXT, factura TEXT)"
        )
    set_active_db_path(database)
    try:
        dialog = ReporteCuentasTotalDialog()

        assert dialog._total == 0.0
        assert "+0" in dialog.total_label.text()
    finally:
        reset_active_db_path()


def _create_alumnos_cuentas_database(path: Path):
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
        connection.executemany(
            "INSERT INTO alumnos (id, nombres, paterno, materno) VALUES (?, ?, ?, ?)",
            [
                (1, "Ana",  "Lopez",  "Rios"),
                (2, "Beto", "Perez",  ""),
                (3, "Celia","Vega",   "Mora"),
            ],
        )
        connection.executemany(
            "INSERT INTO ctas (id_alumno, debito, credito, aclaracion, fecha, factura) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (1, 100, 250, "pago",    "2026-01-01", ""),   # balance +150
                (2, 300, 300, "pension", "2026-01-01", ""),   # balance 0  → excluded
                (3, 200, 50,  "pension", "2026-01-01", ""),   # balance -150
            ],
        )


def test_cuentas_alumnos_report_excludes_zero_balances(qapp, tmp_path):
    database = tmp_path / "cuentas_alumnos.db"
    _create_alumnos_cuentas_database(database)
    set_active_db_path(database)
    try:
        dialog = ReporteCuentasAlumnosDialog()

        ids = [row[0] for row in dialog._rows]
        assert 2 not in ids           # zero balance excluded
        assert 1 in ids
        assert 3 in ids
    finally:
        reset_active_db_path()


def test_cuentas_alumnos_report_correct_balances(qapp, tmp_path):
    database = tmp_path / "cuentas_alumnos_bal.db"
    _create_alumnos_cuentas_database(database)
    set_active_db_path(database)
    try:
        dialog = ReporteCuentasAlumnosDialog()

        by_id = {row[0]: row[2] for row in dialog._rows}
        assert by_id[1] == 150.0
        assert by_id[3] == -150.0
    finally:
        reset_active_db_path()


def test_cuentas_alumnos_report_sorted_by_nombre(qapp, tmp_path):
    database = tmp_path / "cuentas_alumnos_sort.db"
    _create_alumnos_cuentas_database(database)
    set_active_db_path(database)
    try:
        dialog = ReporteCuentasAlumnosDialog()

        nombres = [row[1] for row in dialog._rows]
        assert nombres == sorted(nombres, key=str.lower)
    finally:
        reset_active_db_path()


def test_cuentas_alumnos_report_html_contains_names_and_balances(qapp, tmp_path):
    database = tmp_path / "cuentas_alumnos_html.db"
    _create_alumnos_cuentas_database(database)
    set_active_db_path(database)
    try:
        dialog = ReporteCuentasAlumnosDialog()
        html = dialog._build_html()

        assert "Ana Lopez Rios" in html
        assert "+150" in html
        assert "Celia Vega Mora" in html
        assert "-150" in html
        assert "Beto" not in html
    finally:
        reset_active_db_path()


def test_cuentas_alumnos_action_in_main_window(qapp):
    from windows.main_window import MainWindow
    win = MainWindow("testuser")
    try:
        action_texts = [
            action.text().replace("&", "")
            for action in win.cuentas_reportes_menu.actions()
        ]
        assert "Alumnos" in action_texts
    finally:
        win.close()
