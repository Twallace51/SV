"""Reports for cuentas."""

import csv
import html
import re
import sqlite3
from datetime import date
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrintPreviewDialog, QPrinter
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from __init__ import get_active_db_path


class ReporteCuentasTotalDialog(QDialog):
    """Show the running total: SUM(credito) - SUM(debito) across all ctas rows."""

    _WINDOW_TITLE = "Cuentas - Total"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self._WINDOW_TITLE)
        self.setMinimumWidth(320)

        self._total = self._compute_total()

        layout = QVBoxLayout(self)

        date_label = QLabel(f"Fecha: {date.today():%Y-%m-%d}", self)
        date_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(date_label)

        self.total_label = QLabel(self)
        self.total_label.setAlignment(Qt.AlignCenter)
        self.total_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 12px;")
        self._refresh_total_label()
        layout.addWidget(self.total_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _compute_total(self) -> float:
        try:
            with sqlite3.connect(get_active_db_path()) as conn:
                row = conn.execute(
                    "SELECT COALESCE(SUM(COALESCE(credito, 0)), 0) - "
                    "COALESCE(SUM(COALESCE(debito, 0)), 0) FROM ctas"
                ).fetchone()
            return float(row[0]) if row and row[0] is not None else 0.0
        except sqlite3.Error as exc:
            QMessageBox.critical(None, self._WINDOW_TITLE, f"No se pudo calcular el total:\n{exc}")
            return 0.0

    def _refresh_total_label(self):
        sign = "+" if self._total >= 0 else ""
        self.total_label.setText(f"Total (créditos − débitos): {sign}{self._total:,.0f}")


class ReporteCuentasAlumnosDialog(QDialog):
    """Per-alumno balance: SUM(credito) - SUM(debito), only where total != 0."""

    _WINDOW_TITLE = "Cuentas - Balance por alumno"
    _REPORT_TITLE = "Cuentas - Balance por alumno"
    _PREVIEW_TITLE = "Vista previa - Cuentas balance por alumno"
    _DEFAULT_FILENAME = "cuentas_balance_por_alumno"
    _HEADERS = ("ID", "Alumno", "Balance")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self._WINDOW_TITLE)
        self.resize(560, 420)

        self._rows = self._load_rows()

        layout = QVBoxLayout(self)

        self._document = QTextDocument(self)
        self._document.setHtml(self._build_html())

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

    def _load_rows(self) -> list[tuple]:
        """Return [(alumno_id, nombre_completo, balance), ...] sorted by nombre, total != 0."""
        query = (
            "SELECT c.id_alumno, "
            "COALESCE(a.nombres, '') || ' ' || COALESCE(a.paterno, '') || "
            "CASE WHEN COALESCE(a.materno, '') != '' THEN ' ' || a.materno ELSE '' END, "
            "COALESCE(SUM(COALESCE(c.credito, 0)), 0) - COALESCE(SUM(COALESCE(c.debito, 0)), 0) "
            "FROM ctas c "
            "LEFT JOIN alumnos a ON a.id = c.id_alumno "
            "GROUP BY c.id_alumno "
            "HAVING COALESCE(SUM(COALESCE(c.credito, 0)), 0) - "
            "COALESCE(SUM(COALESCE(c.debito, 0)), 0) != 0 "
            "ORDER BY 2"
        )
        try:
            with sqlite3.connect(get_active_db_path()) as conn:
                return [(row[0], row[1].strip(), float(row[2])) for row in conn.execute(query).fetchall()]
        except sqlite3.Error as exc:
            QMessageBox.critical(None, self._WINDOW_TITLE, f"No se pudo cargar el reporte:\n{exc}")
            return []

    @staticmethod
    def _fmt(value: float) -> str:
        sign = "+" if value >= 0 else ""
        return f"{sign}{value:,.0f}"

    def _build_html(self) -> str:
        title = f"{self._REPORT_TITLE} - {date.today():%Y-%m-%d}"
        sections = [f"<h2>{html.escape(title)}</h2>"]
        if not self._rows:
            sections.append("<p>No hay saldos pendientes.</p>")
            return "".join(sections)

        sections.append(
            "<table border='1' cellspacing='0' cellpadding='4'>"
            "<tr><th>ID</th><th>Alumno</th><th>Balance</th></tr>"
        )
        for alumno_id, nombre, balance in self._rows:
            color = "#d4edda" if balance >= 0 else "#f8d7da"
            sections.append(
                f"<tr style='background:{color}'>"
                f"<td>{html.escape(str(alumno_id))}</td>"
                f"<td>{html.escape(nombre)}</td>"
                f"<td align='right'>{html.escape(self._fmt(balance))}</td>"
                "</tr>"
            )
        sections.append("</table>")
        return "".join(sections)

    def _build_markdown(self) -> str:
        lines = [f"# {self._REPORT_TITLE} - {date.today():%Y-%m-%d}", ""]
        lines.append(f"Total de registros: {len(self._rows)}")
        lines.append("")
        if not self._rows:
            lines.append("No hay saldos pendientes.")
            return "\n".join(lines) + "\n"

        lines.append("| " + " | ".join(self._HEADERS) + " |")
        lines.append("| " + " | ".join("---" for _header in self._HEADERS) + " |")
        for alumno_id, nombre, balance in self._rows:
            values = [
                str(alumno_id),
                nombre.replace("|", "\\|").replace("\n", " "),
                self._fmt(balance),
            ]
            lines.append("| " + " | ".join(values) + " |")
        return "\n".join(lines) + "\n"

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
                writer.writerow(self._HEADERS)
                writer.writerows(self._rows)
            self._show_export_success(path)
        except OSError as exc:
            self._show_export_error(exc)

    def _export_excel(self):
        path = self._choose_path("Exportar reporte a Excel", f"{self._DEFAULT_FILENAME}.xlsx", "Excel (*.xlsx)")
        if path is None:
            return
        try:
            self._write_xlsx(path, [self._HEADERS, *self._rows])
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

    @staticmethod
    def _display(value):
        return "" if value is None else str(value)

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
                # For balance values, preserve the formatted string
                if isinstance(value, float):
                    display_value = cls._fmt(value)
                else:
                    display_value = cls._display(value)
                cells.append(
                    f'<c r="{reference}" t="inlineStr"><is><t>{cls._xml_text(display_value)}</t></is></c>'
                )
            sheet_rows.append(f'<row r="{row_number}">' + "".join(cells) + "</row>")

        content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>"""
        root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>"""
        workbook = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Cuentas por alumno" sheetId="1" r:id="rId1"/></sheets></workbook>"""
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
