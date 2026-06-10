"""Tests for cuentas reports."""

import sqlite3
from pathlib import Path

from __init__ import reset_active_db_path, set_active_db_path
from dialogs.reportes_cuentas import ReporteCuentasTotalDialog


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
