"""Reports for adultos (parientes)."""

import csv
import html
import logging
import sqlite3
from datetime import date

from PySide6.QtWidgets import QMessageBox

from __init__ import get_active_db_path
from dialogs.reportes_alumnos import ReporteAlumnosParientesDialog

log = logging.getLogger("app")
log.setLevel(logging.INFO)

class ReporteAdultosConAlumnosDialog(ReporteAlumnosParientesDialog):
    """List adultos linked to alumnos as padre or madre.

    One row per adulto/alumno relationship, showing the adulto's surname and
    given names alongside the related alumno's id and full name. Includes every
    alumno that has an id_padre or id_madre pointing to an existing adulto.
    """

    _HEADERS = ("Paterno", "Nombres", "ID Alumno", "Alumno")
    _WINDOW_TITLE = "Adultos - Reporte de alumnos relacionados"
    _REPORT_TITLE = "Adultos con alumnos relacionados"
    _EMPTY_MESSAGE = "No hay adultos relacionados con alumnos."
    _PREVIEW_TITLE = "Vista previa - Adultos con alumnos"
    _DEFAULT_FILENAME = "adultos_alumnos"

    @classmethod
    def _load_groups(cls):
        # Normalize the related-adult id columns the same way the rest of the
        # app does (treat '', 'null', 'none' as NULL) before joining.
        related = (
            "JOIN adultos adulto ON adulto.id = CASE "
            "  WHEN a.{column} IS NULL THEN NULL "
            "  WHEN TRIM(CAST(a.{column} AS TEXT)) = '' THEN NULL "
            "  WHEN LOWER(TRIM(CAST(a.{column} AS TEXT))) IN ('null', 'none') THEN NULL "
            "  ELSE CAST(TRIM(CAST(a.{column} AS TEXT)) AS INTEGER) "
            "END "
        )
        select = (
            "SELECT adulto.a_paterno, adulto.a_nombres, a.id, a.nombres, a.paterno, a.materno "
            "FROM alumnos a "
        )
        query = (
            select + related.format(column="id_padre")
            + "UNION ALL "
            + select + related.format(column="id_madre")
            + "ORDER BY 1, 2, 3"
        )
        try:
            with sqlite3.connect(get_active_db_path()) as connection:
                rows = connection.execute(query).fetchall()
        except sqlite3.Error as exc:
            QMessageBox.critical(None, cls._WINDOW_TITLE, f"No se pudo cargar el reporte:\n{exc}")
            rows = []
        return {("", ""): [tuple(row) for row in rows]}

    def _flat_rows(self):
        rows = []
        for relationships in self._groups.values():
            for a_paterno, a_nombres, alumno_id, nombres, paterno, materno in relationships:
                rows.append(
                    (
                        self._display(a_paterno),
                        self._display(a_nombres),
                        alumno_id,
                        self._full_name(nombres, paterno, materno),
                    )
                )
        rows.sort(key=lambda row: (row[0].lower(), row[1].lower(), row[3].lower()))
        return iter(rows)

    def _build_html(self):
        rows = list(self._flat_rows())
        sections = [
            f"<h1>{html.escape(self._report_title_with_date())}</h1>",
            f"<p>Total de registros: {len(rows)}</p>",
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
        lines = [f"# {self._report_title_with_date()}", "", f"Total de registros: {len(rows)}", ""]
        if not rows:
            lines.append(self._EMPTY_MESSAGE)
            return "\n".join(lines) + "\n"

        lines.append("| " + " | ".join(self._HEADERS) + " |")
        lines.append("| " + " | ".join("---" for _header in self._HEADERS) + " |")
        for row in rows:
            values = [self._display(value).replace("|", "\\|").replace("\n", " ") for value in row]
            lines.append("| " + " | ".join(values) + " |")
        return "\n".join(lines) + "\n"

    def _export_csv(self):
        path = self._choose_path(
            "Exportar reporte a CSV",
            f"{self._DEFAULT_FILENAME}_{date.today():%Y-%m-%d}.csv",
            "CSV (*.csv)",
        )
        if path is None:
            return
        try:
            with path.open("w", encoding="utf-8-sig", newline="") as output:
                writer = csv.writer(output)
                writer.writerow(self._HEADERS)
                writer.writerows(self._flat_rows())
            self._show_export_success(path)
        except OSError as exc:
            self._show_export_error(exc)

    def _export_excel(self):
        path = self._choose_path(
            "Exportar reporte a Excel",
            f"{self._DEFAULT_FILENAME}_{date.today():%Y-%m-%d}.xlsx",
            "Excel (*.xlsx)",
        )
        if path is None:
            return
        try:
            self._write_xlsx(path, [self._HEADERS, *self._flat_rows()])
            self._show_export_success(path)
        except OSError as exc:
            self._show_export_error(exc)
