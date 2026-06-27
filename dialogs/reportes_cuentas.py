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
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
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
    _HEADERS = ("ID", "Alumno", "Grado", "Balance")

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
        """Return [(alumno_id, nombre_completo, grado, balance), ...] sorted by nombre, total != 0."""
        try:
            with sqlite3.connect(get_active_db_path()) as conn:
                alumnos_columns = {
                    row[1] for row in conn.execute("PRAGMA table_info(alumnos)").fetchall()
                }
                has_id_grado = "id_grado" in alumnos_columns
                has_grados_table = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='grados'"
                ).fetchone() is not None

                grade_expr = "''"
                grade_join = ""
                if has_id_grado and has_grados_table:
                    grade_expr = "COALESCE(g.grado, '')"
                    grade_join = (
                        " LEFT JOIN grados g ON g.id = CASE"
                        "   WHEN a.id_grado IS NULL THEN NULL"
                        "   WHEN TRIM(CAST(a.id_grado AS TEXT)) = '' THEN NULL"
                        "   WHEN LOWER(TRIM(CAST(a.id_grado AS TEXT))) IN ('null', 'none') THEN NULL"
                        "   ELSE CAST(TRIM(CAST(a.id_grado AS TEXT)) AS INTEGER)"
                        " END"
                    )

                query = (
                    "SELECT c.id_alumno, "
                    "COALESCE(a.nombres, '') || ' ' || COALESCE(a.paterno, '') || "
                    "CASE WHEN COALESCE(a.materno, '') != '' THEN ' ' || a.materno ELSE '' END, "
                    f"{grade_expr}, "
                    "COALESCE(SUM(COALESCE(c.credito, 0)), 0) - COALESCE(SUM(COALESCE(c.debito, 0)), 0) "
                    "FROM ctas c "
                    "LEFT JOIN alumnos a ON a.id = c.id_alumno "
                    f"{grade_join} "
                    "GROUP BY c.id_alumno "
                    "HAVING COALESCE(SUM(COALESCE(c.credito, 0)), 0) - "
                    "COALESCE(SUM(COALESCE(c.debito, 0)), 0) != 0 "
                    "ORDER BY 2"
                )

                return [
                    (row[0], row[1].strip(), (row[2] or "").strip(), float(row[3]))
                    for row in conn.execute(query).fetchall()
                ]
        except sqlite3.Error as exc:
            QMessageBox.critical(None, self._WINDOW_TITLE, f"No se pudo cargar el reporte:\n{exc}")
            return []

    @staticmethod
    def _fmt(value: float) -> str:
        if not value:
            return ""
        sign = "+" if value >= 0 else ""
        return f"{sign}{value:,.0f}"

    def _build_html(self) -> str:
        title = f"{self._REPORT_TITLE} - {date.today():%Y-%m-%d}"
        sections = [
            "<style>"
            "body{font-size:14pt;}"
            "h2{font-size:20pt;margin-bottom:12pt;}"
            "table{font-size:14pt;border-collapse:collapse;}"
            "th,td{padding:6pt;}"
            "</style>",
            f"<h2>{html.escape(title)}</h2>",
        ]
        if not self._rows:
            sections.append("<p>No hay saldos pendientes.</p>")
            return "".join(sections)

        sections.append(
            "<table border='1' cellspacing='0' cellpadding='4'>"
            "<tr><th>ID</th><th>Alumno</th><th>Grado</th><th>Balance</th></tr>"
        )
        for alumno_id, nombre, grado, balance in self._rows:
            row_style = " style='background:#eeeeee;'" if balance > 0 else ""
            sections.append(
                f"<tr{row_style}>"
                f"<td>{html.escape(str(alumno_id))}</td>"
                f"<td>{html.escape(nombre)}</td>"
                f"<td>{html.escape(grado)}</td>"
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
        for alumno_id, nombre, grado, balance in self._rows:
            values = [
                str(alumno_id),
                nombre.replace("|", "\\|").replace("\n", " "),
                grado.replace("|", "\\|").replace("\n", " "),
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
        desktop_dir = Path.home() / "Desktop"
        initial_path = (desktop_dir if desktop_dir.exists() else Path.home()) / default_name
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            caption,
            str(initial_path),
            file_filter,
        )
        return Path(path) if path else None

    def _export_csv(self):
        path = self._choose_path("Exportar reporte a CSV", f"{self._DEFAULT_FILENAME}_{date.today():%Y-%m-%d}.csv", "CSV (*.csv)")
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
        path = self._choose_path("Exportar reporte a Excel", f"{self._DEFAULT_FILENAME}_{date.today():%Y-%m-%d}.xlsx", "Excel (*.xlsx)")
        if path is None:
            return
        try:
            self._write_xlsx(path, [self._HEADERS, *self._rows])
            self._show_export_success(path)
        except OSError as exc:
            self._show_export_error(exc)

    def _export_markdown(self):
        path = self._choose_path("Exportar reporte a Markdown", f"{self._DEFAULT_FILENAME}_{date.today():%Y-%m-%d}.md", "Markdown (*.md)")
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


class ReporteCuentasDetallesDialog(QDialog):
    """Show detailed transactions for a specific alumno: all records in ctas for that id."""

    _WINDOW_TITLE = "Cuentas - Detalles por alumno"
    _REPORT_TITLE = "Cuentas - Detalles por alumno"
    _PREVIEW_TITLE = "Vista previa - Cuentas detalles"
    _DEFAULT_FILENAME = "cuentas_detalles"
    _HEADERS = ("Fecha", "Aclaración", "ID Creditor", "Creditor", "Débito", "Crédito")

    def __init__(self, parent=None, alumno_id=None):
        super().__init__(parent)
        self.setWindowTitle(self._WINDOW_TITLE)
        self.resize(700, 500)

        # Use provided alumno_id, or try to get from current_alumno_id
        if alumno_id is None or alumno_id == 0:
            try:
                import dialogs.alumnos as alumnos_dialogs
                alumno_id = alumnos_dialogs.current_alumno_id
            except (ImportError, AttributeError):
                alumno_id = None

        # If still no alumno_id, ask user
        if alumno_id is None or alumno_id == 0:
            self._alumno_id = self._ask_for_alumno_id()
            if self._alumno_id is None:
                self.reject()
                return
        else:
            self._alumno_id = alumno_id

        self._alumno_nombre = self._get_alumno_nombre(self._alumno_id)
        self._rows = self._load_rows()
        self._balance = self._compute_balance()

        layout = QVBoxLayout(self)

        # Header with alumno info
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel(f"Alumno ID:", self))
        header_layout.addWidget(QLabel(f"{self._alumno_id}", self))
        if self._alumno_nombre:
            header_layout.addWidget(QLabel(f" - {self._alumno_nombre}", self))
        header_layout.addStretch(1)
        layout.addLayout(header_layout)

        # Document viewer
        self._document = QTextDocument(self)
        self._document.setHtml(self._build_html())

        self.viewer = QTextBrowser(self)
        self.viewer.setDocument(self._document)
        layout.addWidget(self.viewer)

        # Action buttons
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

    @staticmethod
    def _ask_for_alumno_id():
        """Prompt user to enter an alumno ID."""
        dialog = QDialog()
        dialog.setWindowTitle("Seleccionar Alumno")
        dialog.resize(300, 100)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Ingrese ID del alumno:", dialog))

        spinbox = QSpinBox(dialog)
        spinbox.setMinimum(1)
        spinbox.setMaximum(999999)
        spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        layout.addWidget(spinbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.Accepted:
            return spinbox.value()
        return None

    def _get_alumno_nombre(self, alumno_id) -> str:
        """Fetch alumno name from database."""
        try:
            with sqlite3.connect(get_active_db_path()) as conn:
                row = conn.execute(
                    "SELECT nombres, paterno, materno FROM alumnos WHERE id = ?",
                    (alumno_id,),
                ).fetchone()
            if row:
                parts = [part.strip() for part in row if part and str(part).strip()]
                return " ".join(parts)
        except sqlite3.Error:
            pass
        return ""

    def _load_rows(self) -> list[tuple]:
        """Return [(fecha, aclaracion, id_creditor, creditor_nombre, debito, credito), ...]."""
        try:
            with sqlite3.connect(get_active_db_path()) as conn:
                ctas_columns = {
                    row[1] for row in conn.execute("PRAGMA table_info(ctas)").fetchall()
                }
                has_creditor = "id_creditor" in ctas_columns
                creditor_id_expr = "c.id_creditor" if has_creditor else "NULL"

                tables = {
                    row[0] for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                creditor_name_expr = "''"
                creditor_join = ""
                if has_creditor and "adultos" in tables:
                    adulto_columns = {
                        row[1] for row in conn.execute("PRAGMA table_info(adultos)").fetchall()
                    }
                    name_parts = []
                    if "a_nombres" in adulto_columns:
                        name_parts.append("COALESCE(ad.a_nombres, '')")
                    if "a_paterno" in adulto_columns:
                        name_parts.append("COALESCE(ad.a_paterno, '')")
                    if name_parts:
                        creditor_name_expr = "TRIM(" + " || ' ' || ".join(name_parts) + ")"
                    creditor_join = " LEFT JOIN adultos ad ON ad.id = CAST(c.id_creditor AS INTEGER)"

                query = (
                    f"SELECT c.fecha, c.aclaracion, {creditor_id_expr}, {creditor_name_expr}, "
                    "c.debito, c.credito "
                    "FROM ctas c"
                    f"{creditor_join} "
                    "WHERE c.id_alumno = ? "
                    "ORDER BY c.fecha DESC"
                )
                rows = conn.execute(query, (self._alumno_id,)).fetchall()
                return [
                    (
                        row[0] or "",
                        row[1] or "",
                        "" if row[2] is None else row[2],
                        row[3] or "",
                        float(row[4] or 0),
                        float(row[5] or 0),
                    )
                    for row in rows
                ]
        except sqlite3.Error as exc:
            QMessageBox.critical(None, self._WINDOW_TITLE, f"No se pudo cargar el reporte:\n{exc}")
            return []

    def _compute_balance(self) -> float:
        """Return SUM(credito) - SUM(debito)."""
        total_credito = sum(row[5] for row in self._rows)
        total_debito = sum(row[4] for row in self._rows)
        return total_credito - total_debito

    @staticmethod
    def _fmt(value: float) -> str:
        if not value:
            return ""
        sign = "+" if value >= 0 else ""
        return f"{sign}{value:,.0f}"

    def _build_html(self) -> str:
        title = f"{self._REPORT_TITLE} - {date.today():%Y-%m-%d}"
        sections = [
            "<style>"
            "body{font-size:14pt;}"
            "h2{font-size:20pt;margin-bottom:12pt;}"
            "table{font-size:14pt;border-collapse:collapse;}"
            "th,td{padding:6pt;}"
            "</style>",
            f"<h2>{html.escape(title)}</h2>",
            f"<p>Alumno ID: {self._alumno_id}",
        ]
        if self._alumno_nombre:
            sections.append(f" - {html.escape(self._alumno_nombre)}")
        sections.append("</p>")

        if not self._rows:
            sections.append("<p>No hay transacciones para este alumno.</p>")
        else:
            sections.append(
                "<table border='1' cellspacing='0' cellpadding='4'>"
                "<tr><th>Fecha</th><th>Aclaración</th><th>ID Creditor</th><th>Creditor</th><th>Débito</th><th>Crédito</th></tr>"
            )
            for fecha, aclaracion, id_creditor, creditor, debito, credito in self._rows:
                sections.append(
                    f"<tr>"
                    f"<td>{html.escape(str(fecha))}</td>"
                    f"<td>{html.escape(str(aclaracion))}</td>"
                    f"<td>{html.escape(str(id_creditor))}</td>"
                    f"<td>{html.escape(str(creditor))}</td>"
                    f"<td align='right'>{html.escape(self._fmt(debito))}</td>"
                    f"<td align='right'>{html.escape(self._fmt(credito))}</td>"
                    "</tr>"
                )
            sections.append("</table>")

        # Summary
        balance_sign = "+" if self._balance >= 0 else ""
        balance_color = "#d4edda" if self._balance >= 0 else "#f8d7da"
        sections.append(
            f"<p style='background:{balance_color}; padding: 8px; margin-top: 12px;'>"
            f"<strong>Balance (Créditos − Débitos): {balance_sign}{self._balance:,.0f}</strong>"
            "</p>"
        )

        return "".join(sections)

    def _build_markdown(self) -> str:
        lines = [f"# {self._REPORT_TITLE} - {date.today():%Y-%m-%d}", ""]
        lines.append(f"**Alumno ID:** {self._alumno_id}")
        if self._alumno_nombre:
            lines.append(f"**Alumno:** {self._alumno_nombre}")
        lines.append("")

        if not self._rows:
            lines.append("No hay transacciones para este alumno.")
            return "\n".join(lines) + "\n"

        lines.append("| " + " | ".join(self._HEADERS) + " |")
        lines.append("| " + " | ".join("---" for _header in self._HEADERS) + " |")
        for fecha, aclaracion, id_creditor, creditor, debito, credito in self._rows:
            values = [
                str(fecha),
                aclaracion.replace("|", "\\|").replace("\n", " "),
                str(id_creditor),
                str(creditor).replace("|", "\\|").replace("\n", " "),
                self._fmt(debito),
                self._fmt(credito),
            ]
            lines.append("| " + " | ".join(values) + " |")
        lines.append("")

        balance_sign = "+" if self._balance >= 0 else ""
        lines.append(f"**Balance (Créditos − Débitos):** {balance_sign}{self._balance:,.0f}")
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
        desktop_dir = Path.home() / "Desktop"
        initial_path = (desktop_dir if desktop_dir.exists() else Path.home()) / default_name
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            caption,
            str(initial_path),
            file_filter,
        )
        return Path(path) if path else None

    def _filename_stem(self, extension: str) -> str:
        """Build the default export filename, prefixed with the alumno name."""
        name_prefix = re.sub(r"[^\w]+", "_", (self._alumno_nombre or "").strip()).strip("_")
        prefix = f"{name_prefix}_" if name_prefix else ""
        return f"{prefix}{self._DEFAULT_FILENAME}_{self._alumno_id}_{date.today():%Y-%m-%d}.{extension}"

    def _export_csv(self):
        path = self._choose_path(
            "Exportar reporte a CSV",
            self._filename_stem("csv"),
            "CSV (*.csv)",
        )
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
        path = self._choose_path(
            "Exportar reporte a Excel",
            self._filename_stem("xlsx"),
            "Excel (*.xlsx)",
        )
        if path is None:
            return
        try:
            self._write_xlsx(path, [self._HEADERS, *self._rows])
            self._show_export_success(path)
        except OSError as exc:
            self._show_export_error(exc)

    def _export_markdown(self):
        path = self._choose_path(
            "Exportar reporte a Markdown",
            self._filename_stem("md"),
            "Markdown (*.md)",
        )
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
                # For float values, use formatted string
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
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Cuentas detalles" sheetId="1" r:id="rId1"/></sheets></workbook>"""
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
