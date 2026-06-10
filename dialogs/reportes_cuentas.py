"""Reports for cuentas."""

import sqlite3
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
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
