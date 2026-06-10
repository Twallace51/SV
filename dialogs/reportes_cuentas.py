"""Reports for cuentas."""

import html
import sqlite3
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
    QMessageBox,
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self._WINDOW_TITLE)
        self.resize(560, 420)

        self._rows = self._load_rows()

        layout = QVBoxLayout(self)

        self.viewer = QTextBrowser(self)
        self.viewer.setHtml(self._build_html())
        layout.addWidget(self.viewer)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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
