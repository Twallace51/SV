"""Reports for alumnos."""

import csv
import html
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from PySide6.QtGui import QTextDocument, QTextFormat
from PySide6.QtPrintSupport import QPrintPreviewDialog, QPrinter
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from __init__ import get_active_db_path


class ReporteAlumnosPorGradoDialog(QDialog):
    """Display and export enrolled alumnos grouped by grade."""

    _HEADERS = ("ID", "Nombres", "Paterno", "Materno", "RUDE", "Carnet", "Pension")
    _WINDOW_TITLE = "Alumnos - Reporte por grados"
    _REPORT_TITLE = "Alumnos inscritos por grado"
    _EMPTY_MESSAGE = "No hay alumnos inscritos actualmente."
    _PREVIEW_TITLE = "Vista previa - Alumnos por grados"
    _DEFAULT_FILENAME = "alumnos_por_grado"
    _EXTRA_FILTER = ""
    _SHOW_PAGINATION_TOGGLE = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self._WINDOW_TITLE)
        self.resize(900, 620)
        self._groups = self._load_groups()

        layout = QVBoxLayout(self)
        if self._SHOW_PAGINATION_TOGGLE:
            self.continuous_output_checkbox = QCheckBox("Salida continua", self)
            self.continuous_output_checkbox.setChecked(True)
            self.continuous_output_checkbox.setToolTip(
                "Desactive para comenzar cada grado en una página nueva"
            )
            self.continuous_output_checkbox.toggled.connect(self._refresh_document)
            layout.addWidget(self.continuous_output_checkbox)

        self._document = QTextDocument(self)
        self._refresh_document()

        self.viewer = QTextBrowser(self)
        self.viewer.setDocument(self._document)
        layout.addWidget(self.viewer)

        actions = QHBoxLayout()
        preview_button = QPushButton("Vista previa", self)
        preview_button.clicked.connect(self._print_preview)
        actions.addWidget(preview_button)

        print_button = QPushButton("Imprimir directo", self)
        print_button.clicked.connect(self._print_direct)
        actions.addWidget(print_button)

        csv_button = QPushButton("Exportar CSV", self)
        csv_button.clicked.connect(self._export_csv)
        actions.addWidget(csv_button)

        excel_button = QPushButton("Exportar Excel", self)
        excel_button.clicked.connect(self._export_excel)
        actions.addWidget(excel_button)

        markdown_button = QPushButton("Exportar Markdown", self)
        markdown_button.clicked.connect(self._export_markdown)
        actions.addWidget(markdown_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=self)
        close_buttons.rejected.connect(self.reject)
        layout.addWidget(close_buttons)

    @classmethod
    def _load_groups(cls):
        groups = defaultdict(list)
        query = (
            "SELECT CAST(TRIM(CAST(a.id_grado AS TEXT)) AS INTEGER), "
            "COALESCE(g.grado, 'Grado ' || TRIM(CAST(a.id_grado AS TEXT))), "
            "a.id, a.nombres, a.paterno, a.materno, a.rude, a.Carnet, a.pension "
            "FROM alumnos a "
            "LEFT JOIN grados g ON g.id = CAST(TRIM(CAST(a.id_grado AS TEXT)) AS INTEGER) "
            "WHERE a.id_grado IS NOT NULL "
            "AND TRIM(CAST(a.id_grado AS TEXT)) <> '' "
            "AND LOWER(TRIM(CAST(a.id_grado AS TEXT))) NOT IN ('null', 'none') "
            "AND CAST(TRIM(CAST(a.id_grado AS TEXT)) AS INTEGER) > 0 "
            f"{cls._EXTRA_FILTER}"
            "ORDER BY CAST(TRIM(CAST(a.id_grado AS TEXT)) AS INTEGER), "
            "a.paterno, a.materno, a.nombres"
        )
        try:
            with sqlite3.connect(get_active_db_path()) as connection:
                rows = connection.execute(query).fetchall()
        except sqlite3.Error as exc:
            QMessageBox.critical(None, cls._WINDOW_TITLE, f"No se pudo cargar el reporte:\n{exc}")
            rows = []

        for grade_id, grade_name, *student in rows:
            groups[(grade_id, grade_name)].append(tuple(student))
        return dict(groups)

    def _build_html(self):
        sections = [
            f"<h1>{html.escape(self._REPORT_TITLE)}</h1>",
            f"<p>Total de alumnos: {sum(len(rows) for rows in self._groups.values())}</p>",
        ]
        if not self._groups:
            sections.append(f"<p>{html.escape(self._EMPTY_MESSAGE)}</p>")
            return "".join(sections)

        for index, ((grade_id, grade_name), rows) in enumerate(self._groups.items()):
            page_break = " style='page-break-before: always'" if index > 0 and not self._is_continuous_output() else ""
            sections.append(
                f"<div{page_break}><h2>{html.escape(str(grade_name))} "
                f"(ID {grade_id}) - {len(rows)} alumnos</h2>"
            )
            sections.append("<table border='1' cellspacing='0' cellpadding='4'><tr>")
            sections.extend(f"<th>{html.escape(header)}</th>" for header in self._HEADERS)
            sections.append("</tr>")
            for row in rows:
                sections.append("<tr>")
                sections.extend(f"<td>{html.escape(self._display(value))}</td>" for value in row)
                sections.append("</tr>")
            sections.append("</table></div>")
        return "".join(sections)

    def _refresh_document(self):
        self._document.setHtml(self._build_html())
        if self._is_continuous_output():
            return

        for grade_id, grade_name in list(self._groups)[1:]:
            heading = f"{grade_name} (ID {grade_id})"
            cursor = self._document.find(heading)
            if cursor.isNull():
                continue
            block_format = cursor.blockFormat()
            block_format.setPageBreakPolicy(
                QTextFormat.PageBreakFlag.PageBreak_AlwaysBefore
            )
            cursor.setBlockFormat(block_format)

    def _is_continuous_output(self):
        checkbox = getattr(self, "continuous_output_checkbox", None)
        return checkbox is None or checkbox.isChecked()

    @staticmethod
    def _display(value):
        return "" if value is None else str(value)

    def _flat_rows(self):
        for (grade_id, grade_name), students in self._groups.items():
            for student in students:
                yield (grade_id, grade_name, *student)

    def _print_preview(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle(self._PREVIEW_TITLE)
        preview.paintRequested.connect(self._document.print_)
        preview.exec()

    def _print_direct(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        if not printer.isValid():
            QMessageBox.warning(self, "Imprimir", "No hay una impresora disponible.")
            return
        self._document.print_(printer)
        QMessageBox.information(self, "Imprimir", "El reporte fue enviado a la impresora predeterminada.")

    def _choose_path(self, caption, default_name, file_filter):
        path, _selected_filter = QFileDialog.getSaveFileName(self, caption, default_name, file_filter)
        return Path(path) if path else None

    def _export_csv(self):
        path = self._choose_path("Exportar reporte a CSV", f"{self._DEFAULT_FILENAME}.csv", "CSV (*.csv)")
        if path is None:
            return
        try:
            with path.open("w", encoding="utf-8-sig", newline="") as output:
                writer = csv.writer(output)
                writer.writerow(("ID Grado", "Grado", *self._HEADERS))
                writer.writerows(self._flat_rows())
            self._show_export_success(path)
        except OSError as exc:
            self._show_export_error(exc)

    def _export_excel(self):
        path = self._choose_path("Exportar reporte a Excel", f"{self._DEFAULT_FILENAME}.xlsx", "Excel (*.xlsx)")
        if path is None:
            return
        try:
            self._write_xlsx(path, [("ID Grado", "Grado", *self._HEADERS), *self._flat_rows()])
            self._show_export_success(path)
        except OSError as exc:
            self._show_export_error(exc)

    def _export_markdown(self):
        path = self._choose_path("Exportar reporte a Markdown", f"{self._DEFAULT_FILENAME}.md", "Markdown (*.md)")
        if path is None:
            return
        try:
            path.write_text(self._build_markdown(), encoding="utf-8")
            self._show_export_success(path)
        except OSError as exc:
            self._show_export_error(exc)

    def _build_markdown(self):
        lines = [f"# {self._REPORT_TITLE}", ""]
        lines.append(f"Total de alumnos: {sum(len(rows) for rows in self._groups.values())}")
        lines.append("")
        if not self._groups:
            lines.append(self._EMPTY_MESSAGE)
            return "\n".join(lines) + "\n"

        for (grade_id, grade_name), rows in self._groups.items():
            lines.extend((f"## {grade_name} (ID {grade_id})", "", "| " + " | ".join(self._HEADERS) + " |"))
            lines.append("| " + " | ".join("---" for _header in self._HEADERS) + " |")
            for row in rows:
                values = [self._display(value).replace("|", "\\|").replace("\n", " ") for value in row]
                lines.append("| " + " | ".join(values) + " |")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _xml_text(value):
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value))
        return html.escape(text, quote=False)

    @classmethod
    def _write_xlsx(cls, path, rows):
        sheet_rows = []
        for row_number, row in enumerate(rows, start=1):
            cells = []
            for column_number, value in enumerate(row, start=1):
                column_name = ""
                number = column_number
                while number:
                    number, remainder = divmod(number - 1, 26)
                    column_name = chr(65 + remainder) + column_name
                reference = f"{column_name}{row_number}"
                cells.append(
                    f'<c r="{reference}" t="inlineStr"><is><t>{cls._xml_text(cls._display(value))}</t></is></c>'
                )
            sheet_rows.append(f'<row r="{row_number}">' + "".join(cells) + "</row>")

        content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>"""
        root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>"""
        workbook = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Alumnos por grado" sheetId="1" r:id="rId1"/></sheets></workbook>"""
        workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>"""
        worksheet = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>""" + "".join(sheet_rows) + "</sheetData></worksheet>"

        with ZipFile(path, "w", ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", content_types)
            archive.writestr("_rels/.rels", root_rels)
            archive.writestr("xl/workbook.xml", workbook)
            archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            archive.writestr("xl/worksheets/sheet1.xml", worksheet)

    def _show_export_success(self, path):
        QMessageBox.information(self, "Exportar", f"Reporte exportado correctamente:\n{path}")

    def _show_export_error(self, exc):
        QMessageBox.critical(self, "Exportar", f"No se pudo exportar el reporte:\n{exc}")


class ReporteAlumnosBecadosDialog(ReporteAlumnosPorGradoDialog):
    """Display and export enrolled alumnos whose pension is zero."""

    _HEADERS = ("Grado", "ID", "Nombres", "Paterno", "Materno", "Pension")

    _WINDOW_TITLE = "Alumnos - Reporte de becados"
    _REPORT_TITLE = "Alumnos becados"
    _EMPTY_MESSAGE = "No hay alumnos becados inscritos actualmente."
    _PREVIEW_TITLE = "Vista previa - Alumnos becados"
    _DEFAULT_FILENAME = "alumnos_becados"
    _EXTRA_FILTER = "AND COALESCE(a.pension, 0) = 0 "
    _SHOW_PAGINATION_TOGGLE = False

    def _build_html(self):
        rows = list(self._flat_rows())
        sections = [
            f"<h1>{html.escape(self._REPORT_TITLE)}</h1>",
            f"<p>Total de alumnos: {len(rows)}</p>",
        ]
        if not rows:
            sections.append(f"<p>{html.escape(self._EMPTY_MESSAGE)}</p>")
            return "".join(sections)

        sections.append("<table border='1' cellspacing='0' cellpadding='4'><tr>")
        sections.extend(f"<th>{html.escape(header)}</th>" for header in self._HEADERS)
        sections.append("</tr>")
        for _grade_id, grade_name, student_id, nombres, paterno, materno, _rude, _carnet, pension in rows:
            row = (grade_name, student_id, nombres, paterno, materno, pension)
            sections.append("<tr>")
            sections.extend(f"<td>{html.escape(self._display(value))}</td>" for value in row)
            sections.append("</tr>")
        sections.append("</table>")
        return "".join(sections)

    def _build_markdown(self):
        rows = list(self._flat_rows())
        lines = [f"# {self._REPORT_TITLE}", "", f"Total de alumnos: {len(rows)}", ""]
        if not rows:
            lines.append(self._EMPTY_MESSAGE)
            return "\n".join(lines) + "\n"

        lines.append("| " + " | ".join(self._HEADERS) + " |")
        lines.append("| " + " | ".join("---" for _header in self._HEADERS) + " |")
        for _grade_id, grade_name, student_id, nombres, paterno, materno, _rude, _carnet, pension in rows:
            row = (grade_name, student_id, nombres, paterno, materno, pension)
            values = [self._display(value).replace("|", "\\|").replace("\n", " ") for value in row]
            lines.append("| " + " | ".join(values) + " |")
        return "\n".join(lines) + "\n"


class ReporteAlumnosRudeDialog(ReporteAlumnosBecadosDialog):
    """Display and export enrolled alumnos with RUDE column."""

    _HEADERS = ("Grado", "ID", "Nombres", "Paterno", "Materno", "RUDE")
    _WINDOW_TITLE = "Alumnos - Reporte de rude"
    _REPORT_TITLE = "Alumnos con RUDE"
    _EMPTY_MESSAGE = "No hay alumnos inscritos actualmente."
    _PREVIEW_TITLE = "Vista previa - Alumnos con RUDE"
    _DEFAULT_FILENAME = "alumnos_rude"
    _EXTRA_FILTER = ""

    def _build_html(self):
        rows = list(self._flat_rows())
        sections = [
            f"<h1>{html.escape(self._REPORT_TITLE)}</h1>",
            f"<p>Total de alumnos: {len(rows)}</p>",
        ]
        if not rows:
            sections.append(f"<p>{html.escape(self._EMPTY_MESSAGE)}</p>")
            return "".join(sections)

        sections.append("<table border='1' cellspacing='0' cellpadding='4'><tr>")
        sections.extend(f"<th>{html.escape(header)}</th>" for header in self._HEADERS)
        sections.append("</tr>")
        for _grade_id, grade_name, student_id, nombres, paterno, materno, rude, _carnet, _pension in rows:
            row = (grade_name, student_id, nombres, paterno, materno, rude)
            sections.append("<tr>")
            sections.extend(f"<td>{html.escape(self._display(value))}</td>" for value in row)
            sections.append("</tr>")
        sections.append("</table>")
        return "".join(sections)

    def _build_markdown(self):
        rows = list(self._flat_rows())
        lines = [f"# {self._REPORT_TITLE}", "", f"Total de alumnos: {len(rows)}", ""]
        if not rows:
            lines.append(self._EMPTY_MESSAGE)
            return "\n".join(lines) + "\n"

        lines.append("| " + " | ".join(self._HEADERS) + " |")
        lines.append("| " + " | ".join("---" for _header in self._HEADERS) + " |")
        for _grade_id, grade_name, student_id, nombres, paterno, materno, rude, _carnet, _pension in rows:
            row = (grade_name, student_id, nombres, paterno, materno, rude)
            values = [self._display(value).replace("|", "\\|").replace("\n", " ") for value in row]
            lines.append("| " + " | ".join(values) + " |")
        return "\n".join(lines) + "\n"


class ReporteAlumnosCumpleanosDialog(ReporteAlumnosBecadosDialog):
    """Display and export enrolled alumnos with birthday columns."""

    _HEADERS = (
        "Cumpleanos MM-dd",
        "Grado",
        "ID",
        "Nombres",
        "Paterno",
        "Materno",
        "Cumpleanos",
    )
    _WINDOW_TITLE = "Alumnos - Reporte de cumpleanos"
    _REPORT_TITLE = "Alumnos - Cumpleanos"
    _EMPTY_MESSAGE = "No hay alumnos inscritos actualmente."
    _PREVIEW_TITLE = "Vista previa - Alumnos cumpleanos"
    _DEFAULT_FILENAME = "alumnos_cumpleanos"
    _EXTRA_FILTER = ""

    @classmethod
    def _load_groups(cls):
        groups = defaultdict(list)
        query = (
            "SELECT CAST(TRIM(CAST(a.id_grado AS TEXT)) AS INTEGER), "
            "COALESCE(g.grado, 'Grado ' || TRIM(CAST(a.id_grado AS TEXT))), "
            "a.id, a.nombres, a.paterno, a.materno, "
            "COALESCE(TRIM(a.cumpleanos), ''), "
            "CASE "
            "  WHEN a.cumpleanos IS NULL OR TRIM(a.cumpleanos) = '' THEN '' "
            "  WHEN LENGTH(TRIM(a.cumpleanos)) >= 10 THEN SUBSTR(TRIM(a.cumpleanos), 6, 5) "
            "  ELSE '' "
            "END "
            "FROM alumnos a "
            "LEFT JOIN grados g ON g.id = CAST(TRIM(CAST(a.id_grado AS TEXT)) AS INTEGER) "
            "WHERE a.id_grado IS NOT NULL "
            "AND TRIM(CAST(a.id_grado AS TEXT)) <> '' "
            "AND LOWER(TRIM(CAST(a.id_grado AS TEXT))) NOT IN ('null', 'none') "
            "AND CAST(TRIM(CAST(a.id_grado AS TEXT)) AS INTEGER) > 0 "
            "ORDER BY "
            "CASE "
            "  WHEN a.cumpleanos IS NULL OR TRIM(a.cumpleanos) = '' THEN '99-99' "
            "  WHEN LENGTH(TRIM(a.cumpleanos)) >= 10 THEN SUBSTR(TRIM(a.cumpleanos), 6, 5) "
            "  ELSE '99-99' "
            "END, "
            "CAST(TRIM(CAST(a.id_grado AS TEXT)) AS INTEGER), "
            "a.paterno, a.materno, a.nombres"
        )
        try:
            with sqlite3.connect(get_active_db_path()) as connection:
                rows = connection.execute(query).fetchall()
        except sqlite3.Error as exc:
            QMessageBox.critical(None, cls._WINDOW_TITLE, f"No se pudo cargar el reporte:\n{exc}")
            rows = []

        for grade_id, grade_name, *student in rows:
            groups[(grade_id, grade_name)].append(tuple(student))
        return dict(groups)

    def _flat_rows(self):
        rows = []
        for (_grade_id, grade_name), students in self._groups.items():
            for student in students:
                student_id, nombres, paterno, materno, cumpleanos, cumpleanos_mmdd = student
                rows.append(
                    (
                        self._display(cumpleanos_mmdd),
                        self._display(grade_name),
                        student_id,
                        nombres,
                        paterno,
                        materno,
                        self._display(cumpleanos),
                    )
                )
        return iter(sorted(rows, key=lambda row: (row[0], str(row[2]), row[3], row[4])))

    def _build_html(self):
        rows = list(self._flat_rows())
        sections = [
            f"<h1>{html.escape(self._REPORT_TITLE)}</h1>",
            f"<p>Total de alumnos: {len(rows)}</p>",
        ]
        if not rows:
            sections.append(f"<p>{html.escape(self._EMPTY_MESSAGE)}</p>")
            return "".join(sections)

        sections.append("<table border='1' cellspacing='0' cellpadding='4'><tr>")
        sections.extend(f"<th>{html.escape(header)}</th>" for header in self._HEADERS)
        sections.append("</tr>")
        for row in rows:
            sections.append("<tr>")
            sections.extend(f"<td>{html.escape(self._display(value))}</td>" for value in row)
            sections.append("</tr>")
        sections.append("</table>")
        return "".join(sections)

    def _build_markdown(self):
        rows = list(self._flat_rows())
        lines = [f"# {self._REPORT_TITLE}", "", f"Total de alumnos: {len(rows)}", ""]
        if not rows:
            lines.append(self._EMPTY_MESSAGE)
            return "\n".join(lines) + "\n"

        lines.append("| " + " | ".join(self._HEADERS) + " |")
        lines.append("| " + " | ".join("---" for _header in self._HEADERS) + " |")
        for row in rows:
            values = [self._display(value).replace("|", "\\|").replace("\n", " ") for value in row]
            lines.append("| " + " | ".join(values) + " |")
        return "\n".join(lines) + "\n"
