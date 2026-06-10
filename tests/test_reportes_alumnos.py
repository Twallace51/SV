"""Tests for alumnos reports."""

import sqlite3
from pathlib import Path
from zipfile import ZipFile

from PySide6.QtGui import QTextFormat

from __init__ import reset_active_db_path, set_active_db_path
from dialogs.reportes_alumnos import (
    ReporteAlumnosBecadosDialog,
    ReporteAlumnosCumpleanosDialog,
    ReporteAlumnosPorGradoDialog,
    ReporteAlumnosRudeDialog,
)


def _create_report_database(path: Path):
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE grados (id INTEGER PRIMARY KEY, grado TEXT)")
        connection.execute(
            "CREATE TABLE alumnos ("
            "id INTEGER PRIMARY KEY, nombres TEXT, paterno TEXT, materno TEXT, "
            "cumpleanos TEXT, rude TEXT, Carnet TEXT, pension REAL, id_grado TEXT)"
        )
        connection.executemany(
            "INSERT INTO grados (id, grado) VALUES (?, ?)",
            [(1, "Primero A"), (2, "Segundo A")],
        )
        connection.executemany(
            "INSERT INTO alumnos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "Ana", "Lopez", "Rios", "2010-01-15", "R-1", "C-1", 300, "1"),
                (2, "Beto", "Perez", "", "2011-07-20", "R-2", "C-2", 320, "2"),
                (3, "Celia", "Vega", "", "2010-08-30", "R-3", "C-3", 0, "0"),
                (4, "Dario", "Soto", "", "", "R-4", "C-4", 0, None),
                (5, "Elena", "Mora", "", "2009-12-03", "R-5", "C-5", 0, "2"),
                (6, "Fabio", "Ruiz", "", "2010-02-28", "R-6", "C-6", 0, "1"),
            ],
        )


def test_report_groups_only_alumnos_with_positive_grade(qapp, tmp_path):
    database = tmp_path / "report.db"
    _create_report_database(database)
    set_active_db_path(database)
    try:
        dialog = ReporteAlumnosPorGradoDialog()

        assert list(dialog._groups) == [(1, "Primero A"), (2, "Segundo A")]
        assert [student[0] for students in dialog._groups.values() for student in students] == [1, 6, 5, 2]
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


def test_report_defaults_to_continuous_output(qapp, tmp_path):
    database = tmp_path / "report.db"
    _create_report_database(database)
    set_active_db_path(database)
    try:
        dialog = ReporteAlumnosPorGradoDialog()

        assert dialog.continuous_output_checkbox.isChecked()
        assert "page-break-before: always" not in dialog._build_html()
    finally:
        reset_active_db_path()


def test_disabling_continuous_output_adds_page_break_per_grade(qapp, tmp_path):
    database = tmp_path / "report.db"
    _create_report_database(database)
    set_active_db_path(database)
    try:
        dialog = ReporteAlumnosPorGradoDialog()

        dialog.continuous_output_checkbox.setChecked(False)

        assert dialog._build_html().count("page-break-before: always") == 1
        second_grade = dialog._document.find("Segundo A (ID 2)")
        assert not second_grade.isNull()
        assert second_grade.blockFormat().pageBreakPolicy() & (
            QTextFormat.PageBreakFlag.PageBreak_AlwaysBefore
        )
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


def test_becados_report_filters_zero_pension_with_positive_grade(qapp, tmp_path):
    database = tmp_path / "report.db"
    _create_report_database(database)
    set_active_db_path(database)
    try:
        dialog = ReporteAlumnosBecadosDialog()
        student_ids = [student[0] for students in dialog._groups.values() for student in students]

        assert student_ids == [6, 5]
        assert "Elena" in dialog.viewer.toPlainText()
        assert "Fabio" in dialog.viewer.toPlainText()
        assert "Celia" not in dialog.viewer.toPlainText()
        assert "Dario" not in dialog.viewer.toPlainText()
        assert not hasattr(dialog, "continuous_output_checkbox")
        assert dialog._DEFAULT_FILENAME == "alumnos_becados"

        report_html = dialog._build_html()
        markdown = dialog._build_markdown()
        assert "<h2>" not in report_html
        assert report_html.count("<table") == 1
        assert "## Primero A" not in markdown
        assert "## Segundo A" not in markdown
        assert markdown.count("| Grado | ID | Nombres | Paterno | Materno | Pension |") == 1
        assert "ID Grado" not in markdown
        assert "RUDE" not in markdown
        assert "Carnet" not in markdown
    finally:
        reset_active_db_path()


def test_cumpleanos_report_has_mm_dd_column_and_no_group_sections(qapp, tmp_path):
    database = tmp_path / "report.db"
    _create_report_database(database)
    set_active_db_path(database)
    try:
        dialog = ReporteAlumnosCumpleanosDialog()
        student_ids = [student[0] for students in dialog._groups.values() for student in students]

        assert student_ids == [1, 6, 2, 5]
        assert not hasattr(dialog, "continuous_output_checkbox")

        plain_text = dialog.viewer.toPlainText()
        assert "Cumpleanos" in plain_text
        assert "Cumpleanos MM-dd" in plain_text
        assert "ID Grado" not in plain_text
        assert "RUDE" not in plain_text
        assert "Carnet" not in plain_text
        assert "01-15" in plain_text
        assert "02-28" in plain_text
        assert "12-03" in plain_text
        assert "07-20" in plain_text

        report_html = dialog._build_html()
        markdown = dialog._build_markdown()
        assert "<h2>" not in report_html
        assert "| Cumpleanos MM-dd | Grado | ID | Nombres | Paterno | Materno | Cumpleanos |" in markdown
        assert "| 01-15 | Primero A | 1 | Ana | Lopez | Rios | 2010-01-15 |" in markdown
        assert markdown.index("| 02-28 |") < markdown.index("| 07-20 |") < markdown.index("| 12-03 |")
    finally:
        reset_active_db_path()


def test_rude_report_has_rude_column_without_becados_filter(qapp, tmp_path):
    database = tmp_path / "report.db"
    _create_report_database(database)
    set_active_db_path(database)
    try:
        dialog = ReporteAlumnosRudeDialog()
        student_ids = [student[0] for students in dialog._groups.values() for student in students]

        assert student_ids == [1, 6, 5, 2]
        assert not hasattr(dialog, "continuous_output_checkbox")

        plain_text = dialog.viewer.toPlainText()
        assert "RUDE" in plain_text
        assert "Pension" not in plain_text
        assert "Carnet" not in plain_text
        assert "ID Grado" not in plain_text
        assert "R-1" in plain_text
        assert "R-2" in plain_text

        report_html = dialog._build_html()
        markdown = dialog._build_markdown()
        assert "<h2>" not in report_html
        assert "| Grado | ID | Nombres | Paterno | Materno | RUDE |" in markdown
        assert "| Primero A | 1 | Ana | Lopez | Rios | R-1 |" in markdown
        assert "Pension" not in markdown
    finally:
        reset_active_db_path()
