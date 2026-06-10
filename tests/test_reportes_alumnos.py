"""Tests for alumnos reports."""

import sqlite3
from pathlib import Path
from zipfile import ZipFile

from __init__ import reset_active_db_path, set_active_db_path
from dialogs.reportes_alumnos import ReporteAlumnosPorGradoDialog


def _create_report_database(path: Path):
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE grados (id INTEGER PRIMARY KEY, grado TEXT)")
        connection.execute(
            "CREATE TABLE alumnos ("
            "id INTEGER PRIMARY KEY, nombres TEXT, paterno TEXT, materno TEXT, "
            "rude TEXT, Carnet TEXT, pension REAL, id_grado TEXT)"
        )
        connection.executemany(
            "INSERT INTO grados (id, grado) VALUES (?, ?)",
            [(1, "Primero A"), (2, "Segundo A")],
        )
        connection.executemany(
            "INSERT INTO alumnos VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "Ana", "Lopez", "Rios", "R-1", "C-1", 300, "1"),
                (2, "Beto", "Perez", "", "R-2", "C-2", 320, "2"),
                (3, "Celia", "Vega", "", "R-3", "C-3", 0, "0"),
                (4, "Dario", "Soto", "", "R-4", "C-4", 0, None),
            ],
        )


def test_report_groups_only_alumnos_with_positive_grade(qapp, tmp_path):
    database = tmp_path / "report.db"
    _create_report_database(database)
    set_active_db_path(database)
    try:
        dialog = ReporteAlumnosPorGradoDialog()

        assert list(dialog._groups) == [(1, "Primero A"), (2, "Segundo A")]
        assert [student[0] for students in dialog._groups.values() for student in students] == [1, 2]
        assert "Celia" not in dialog.viewer.toPlainText()
        assert "Dario" not in dialog.viewer.toPlainText()
    finally:
        reset_active_db_path()


def test_markdown_export_content_is_grouped(qapp, tmp_path):
    database = tmp_path / "report.db"
    _create_report_database(database)
    set_active_db_path(database)
    try:
        dialog = ReporteAlumnosPorGradoDialog()
        markdown = dialog._build_markdown()

        assert "## Primero A (ID 1)" in markdown
        assert "## Segundo A (ID 2)" in markdown
        assert "| 1 | Ana | Lopez | Rios | R-1 | C-1 | 300.0 |" in markdown
    finally:
        reset_active_db_path()


def test_excel_writer_creates_valid_xlsx_package(tmp_path):
    output = tmp_path / "report.xlsx"

    ReporteAlumnosPorGradoDialog._write_xlsx(output, [("ID Grado", "Grado"), (1, "Primero A")])

    with ZipFile(output) as workbook:
        assert workbook.testzip() is None
        assert "xl/workbook.xml" in workbook.namelist()
        sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "ID Grado" in sheet
        assert "Primero A" in sheet
