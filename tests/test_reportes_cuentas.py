"""Tests for cuentas reports."""

import csv
import sqlite3
from pathlib import Path

import pytest

from __init__ import reset_active_db_path, set_active_db_path
from dialogs.reportes_cuentas import (
    ReporteCuentasTotalDialog,
    ReporteCuentasAlumnosDialog,
    ReporteCuentasDetallesDialog,
)


# ---------------------------------------------------------------------------
# Shared DB helpers
# ---------------------------------------------------------------------------

def _create_cuentas_db(path: Path):
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE ctas ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "id_alumno INTEGER, debito REAL, credito REAL, "
            "aclaracion TEXT, fecha TEXT, factura TEXT)"
        )
        conn.executemany(
            "INSERT INTO ctas (id_alumno, debito, credito, aclaracion, fecha, factura) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (1, 100, 0,   "Pension enero",   "2026-01-01", ""),
                (1, 0,   200, "Pago enero",      "2026-01-15", "F-001"),
                (2, 150, 0,   "Pension febrero", "2026-02-01", ""),
                (2, 0,   150, "Pago febrero",    "2026-02-10", "F-002"),
            ],
        )


def _create_alumnos_cuentas_db(path: Path):
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
        conn.executemany(
            "INSERT INTO alumnos (id, nombres, paterno, materno) VALUES (?, ?, ?, ?)",
            [
                (1, "Ana",   "Lopez", "Rios"),
                (2, "Beto",  "Perez", ""),
                (3, "Celia", "Vega",  "Mora"),
            ],
        )
        conn.executemany(
            "INSERT INTO ctas (id_alumno, debito, credito, aclaracion, fecha, factura) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (1, 100, 250, "pago",    "2026-01-01", ""),
                (2, 300, 300, "pension", "2026-01-01", ""),
                (3, 200, 50,  "pension", "2026-01-01", ""),
            ],
        )


# ---------------------------------------------------------------------------
# ReporteCuentasTotalDialog
# ---------------------------------------------------------------------------

class TestReporteCuentasTotal:
    def test_computes_correct_positive_total(self, qapp, tmp_path):
        db = tmp_path / "cuentas.db"
        _create_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = ReporteCuentasTotalDialog()
            # creditos = 200+150=350, debitos = 100+150=250, total = +100
            assert dlg._total == 100.0
            assert "+100" in dlg.total_label.text()
        finally:
            reset_active_db_path()

    def test_shows_negative_total(self, qapp, tmp_path):
        db = tmp_path / "neg.db"
        with sqlite3.connect(db) as conn:
            conn.execute(
                "CREATE TABLE ctas (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "id_alumno INTEGER, debito REAL, credito REAL, "
                "aclaracion TEXT, fecha TEXT, factura TEXT)"
            )
            conn.execute(
                "INSERT INTO ctas (id_alumno, debito, credito, aclaracion, fecha, factura) "
                "VALUES (1, 500, 100, 'test', '2026-01-01', '')"
            )
        set_active_db_path(db)
        try:
            dlg = ReporteCuentasTotalDialog()
            assert dlg._total == -400.0
            assert "-400" in dlg.total_label.text()
            assert "+" not in dlg.total_label.text()
        finally:
            reset_active_db_path()

    def test_empty_table_shows_zero(self, qapp, tmp_path):
        db = tmp_path / "empty.db"
        with sqlite3.connect(db) as conn:
            conn.execute(
                "CREATE TABLE ctas (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "id_alumno INTEGER, debito REAL, credito REAL, "
                "aclaracion TEXT, fecha TEXT, factura TEXT)"
            )
        set_active_db_path(db)
        try:
            dlg = ReporteCuentasTotalDialog()
            assert dlg._total == 0.0
            assert "+0" in dlg.total_label.text()
        finally:
            reset_active_db_path()


# ---------------------------------------------------------------------------
# ReporteCuentasAlumnosDialog
# ---------------------------------------------------------------------------

class TestReporteCuentasAlumnos:
    def test_excludes_zero_balances(self, qapp, tmp_path):
        db = tmp_path / "alumnos.db"
        _create_alumnos_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = ReporteCuentasAlumnosDialog()
            ids = [row[0] for row in dlg._rows]
            assert 2 not in ids
            assert 1 in ids
            assert 3 in ids
        finally:
            reset_active_db_path()

    def test_correct_balances(self, qapp, tmp_path):
        db = tmp_path / "alumnos.db"
        _create_alumnos_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = ReporteCuentasAlumnosDialog()
            by_id = {row[0]: row[2] for row in dlg._rows}
            assert by_id[1] == 150.0
            assert by_id[3] == -150.0
        finally:
            reset_active_db_path()

    def test_sorted_by_nombre(self, qapp, tmp_path):
        db = tmp_path / "alumnos.db"
        _create_alumnos_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = ReporteCuentasAlumnosDialog()
            nombres = [row[1] for row in dlg._rows]
            assert nombres == sorted(nombres, key=str.lower)
        finally:
            reset_active_db_path()

    def test_html_contains_names_and_balances(self, qapp, tmp_path):
        db = tmp_path / "alumnos.db"
        _create_alumnos_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = ReporteCuentasAlumnosDialog()
            html = dlg._build_html()
            assert "Ana Lopez Rios" in html
            assert "+150" in html
            assert "Celia Vega Mora" in html
            assert "-150" in html
            assert "Beto" not in html
        finally:
            reset_active_db_path()

    def test_markdown_format(self, qapp, tmp_path):
        db = tmp_path / "alumnos.db"
        _create_alumnos_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = ReporteCuentasAlumnosDialog()
            md = dlg._build_markdown()
            assert "# Cuentas - Balance por alumno" in md
            assert "| ID | Alumno | Balance |" in md
            assert "Ana Lopez Rios" in md
            assert "+150" in md
            assert "-150" in md
        finally:
            reset_active_db_path()

    def test_export_csv(self, qapp, tmp_path):
        db = tmp_path / "alumnos.db"
        _create_alumnos_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = ReporteCuentasAlumnosDialog()
            csv_path = tmp_path / "export.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                import csv as csv_mod
                writer = csv_mod.writer(f)
                writer.writerow(dlg._HEADERS)
                writer.writerows(dlg._rows)
            content = csv_path.read_text(encoding="utf-8-sig")
            assert "ID,Alumno,Balance" in content
            assert "Ana Lopez Rios" in content
        finally:
            reset_active_db_path()

    def test_export_excel(self, qapp, tmp_path):
        db = tmp_path / "alumnos.db"
        _create_alumnos_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = ReporteCuentasAlumnosDialog()
            xlsx_path = tmp_path / "export.xlsx"
            dlg._write_xlsx(xlsx_path, [dlg._HEADERS, *dlg._rows])
            assert xlsx_path.exists()
            assert xlsx_path.stat().st_size > 0
        finally:
            reset_active_db_path()

    def test_action_present_in_main_window(self, qapp):
        from windows.main_window import MainWindow
        win = MainWindow("testuser")
        try:
            action_texts = [
                a.text().replace("&", "") for a in win.cuentas_reportes_menu.actions()
            ]
            assert "Alumnos" in action_texts
        finally:
            win.close()


# ---------------------------------------------------------------------------
# ReporteCuentasDetallesDialog
# ---------------------------------------------------------------------------

class TestReporteCuentasDetalles:
    def test_loads_rows_for_alumno(self, qapp, tmp_path):
        db = tmp_path / "det.db"
        _create_alumnos_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = ReporteCuentasDetallesDialog(alumno_id=1)
            assert len(dlg._rows) == 1
            assert dlg._rows[0][0] == "2026-01-01"
            assert dlg._rows[0][1] == "pago"
        finally:
            reset_active_db_path()

    def test_computes_balance(self, qapp, tmp_path):
        db = tmp_path / "det.db"
        _create_alumnos_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = ReporteCuentasDetallesDialog(alumno_id=1)
            assert dlg._balance == 150.0
        finally:
            reset_active_db_path()

    def test_gets_alumno_nombre(self, qapp, tmp_path):
        db = tmp_path / "det.db"
        _create_alumnos_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = ReporteCuentasDetallesDialog(alumno_id=1)
            assert dlg._alumno_nombre == "Ana Lopez Rios"
        finally:
            reset_active_db_path()

    def test_html_contains_key_fields(self, qapp, tmp_path):
        db = tmp_path / "det.db"
        _create_alumnos_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = ReporteCuentasDetallesDialog(alumno_id=1)
            html = dlg._build_html()
            assert "Alumno ID: 1" in html
            assert "Ana Lopez Rios" in html
            assert "pago" in html
            assert "+150" in html
            assert "Balance" in html
        finally:
            reset_active_db_path()

    def test_markdown_format(self, qapp, tmp_path):
        db = tmp_path / "det.db"
        _create_alumnos_cuentas_db(db)
        set_active_db_path(db)
        try:
            dlg = ReporteCuentasDetallesDialog(alumno_id=1)
            md = dlg._build_markdown()
            assert "# Cuentas - Detalles por alumno" in md
            assert "**Alumno ID:** 1" in md
            assert "**Alumno:** Ana Lopez Rios" in md
            assert "| Fecha | Aclaración | Débito | Crédito |" in md
            assert "2026-01-01" in md
            assert "pago" in md
        finally:
            reset_active_db_path()

    def test_uses_current_alumno_id_when_no_arg(self, qapp, tmp_path, monkeypatch):
        db = tmp_path / "det.db"
        _create_alumnos_cuentas_db(db)
        set_active_db_path(db)
        try:
            import dialogs.alumnos as alumnos_dialogs
            monkeypatch.setattr(alumnos_dialogs, "current_alumno_id", 2)
            monkeypatch.setattr(alumnos_dialogs, "current_alumno_name", "Beto Perez")
            dlg = ReporteCuentasDetallesDialog()
            assert dlg._alumno_id == 2
            assert dlg._alumno_nombre == "Beto Perez"
        finally:
            reset_active_db_path()

    def test_action_present_in_main_window(self, qapp):
        from windows.main_window import MainWindow
        win = MainWindow("testuser")
        try:
            action_texts = [
                a.text().replace("&", "") for a in win.cuentas_reportes_menu.actions()
            ]
            assert "Detalles" in action_texts
        finally:
            win.close()
