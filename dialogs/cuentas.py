"""Cuentas dialogs: Nuevo, Editar, Buscar."""

# region - imports

import logging
import sqlite3

from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit,
    QVBoxLayout, QFormLayout, QMessageBox, QHBoxLayout,
    QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QDateEdit, QComboBox, QDoubleSpinBox, QHeaderView,
)
from PySide6.QtCore import QDate

from __init__ import get_active_db_path

# endregion

log = logging.getLogger("app")

# Current-record global – updated on every successful INSERT/UPDATE;
# set to None when the corresponding record is deleted.
current_cta_id: int | None = None


class NuevoCuentaDialog(QDialog):
    """Form dialog to insert a new cuenta into SV.db."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cuentas - Nuevo")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.alumno = QComboBox()
        self._alumno_ids: list[int] = []
        try:
            conn = sqlite3.connect(get_active_db_path())
            for aid, nombres, paterno in conn.execute(
                "SELECT id, nombres, paterno FROM alumnos ORDER BY paterno, nombres"
            ).fetchall():
                self.alumno.addItem(f"{paterno}, {nombres}", aid)
                self._alumno_ids.append(aid)
            conn.close()
        except Exception:
            pass

        self.debito = QDoubleSpinBox()
        self.debito.setRange(0, 999999)
        self.debito.setDecimals(2)
        self.debito.setPrefix("Bs ")

        self.credito = QDoubleSpinBox()
        self.credito.setRange(0, 999999)
        self.credito.setDecimals(2)
        self.credito.setPrefix("Bs ")

        self.aclaracion = QLineEdit()
        self.fecha = QDateEdit()
        self.fecha.setCalendarPopup(True)
        self.fecha.setDisplayFormat("yyyy-MM-dd")
        self.fecha.setDate(QDate.currentDate())
        self.factura = QLineEdit()

        form.addRow("Alumno *:", self.alumno)
        form.addRow("Débito:", self.debito)
        form.addRow("Crédito:", self.credito)
        form.addRow("Aclaración:", self.aclaracion)
        form.addRow("Fecha:", self.fecha)
        form.addRow("Factura:", self.factura)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        if self.alumno.count() == 0:
            QMessageBox.warning(self, "Validación", "No hay alumnos registrados.")
            return
        try:
            conn = sqlite3.connect(get_active_db_path())
            cur = conn.execute(
                "INSERT INTO ctas (id_alumno, debito, credito, aclaracion, fecha, factura)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (self.alumno.currentData(), self.debito.value(), self.credito.value(),
                 self.aclaracion.text().strip(),
                 self.fecha.date().toString("yyyy-MM-dd"),
                 self.factura.text().strip()),
            )
            conn.commit()
            global current_cta_id
            current_cta_id = cur.lastrowid
            conn.close()
            QMessageBox.information(self, "Guardado", "Cuenta guardada.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{exc}")


class EditCuentaDialog(QDialog):
    """Edit form pre-populated with an existing cuenta record."""

    def __init__(self, record_id: int, parent=None):
        super().__init__(parent)
        self._id = record_id
        self.setWindowTitle("Cuentas - Editar")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.alumno = QComboBox()
        try:
            conn = sqlite3.connect(get_active_db_path())
            for aid, nombres, paterno in conn.execute(
                "SELECT id, nombres, paterno FROM alumnos ORDER BY paterno, nombres"
            ).fetchall():
                self.alumno.addItem(f"{paterno}, {nombres}", aid)
            row = conn.execute(
                "SELECT id_alumno, debito, credito, aclaracion, fecha, factura"
                " FROM ctas WHERE id = ?", (self._id,)
            ).fetchone()
            conn.close()
        except Exception:
            row = None

        self.debito = QDoubleSpinBox()
        self.debito.setRange(0, 999999)
        self.debito.setDecimals(2)
        self.debito.setPrefix("Bs ")

        self.credito = QDoubleSpinBox()
        self.credito.setRange(0, 999999)
        self.credito.setDecimals(2)
        self.credito.setPrefix("Bs ")

        self.aclaracion = QLineEdit()
        self.fecha = QDateEdit()
        self.fecha.setCalendarPopup(True)
        self.fecha.setDisplayFormat("yyyy-MM-dd")
        self.fecha.setDate(QDate.currentDate())
        self.factura = QLineEdit()

        if row:
            idx = self.alumno.findData(row[0])
            if idx >= 0:
                self.alumno.setCurrentIndex(idx)
            self.debito.setValue(row[1] or 0)
            self.credito.setValue(row[2] or 0)
            self.aclaracion.setText(row[3] or "")
            d = QDate.fromString(row[4] or "", "yyyy-MM-dd")
            if d.isValid():
                self.fecha.setDate(d)
            self.factura.setText(row[5] or "")

        form.addRow("Alumno *:", self.alumno)
        form.addRow("Débito:", self.debito)
        form.addRow("Crédito:", self.credito)
        form.addRow("Aclaración:", self.aclaracion)
        form.addRow("Fecha:", self.fecha)
        form.addRow("Factura:", self.factura)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        if self.alumno.count() == 0:
            QMessageBox.warning(self, "Validación", "No hay alumnos registrados.")
            return
        try:
            conn = sqlite3.connect(get_active_db_path())
            conn.execute(
                "UPDATE ctas SET id_alumno=?, debito=?, credito=?, aclaracion=?,"
                " fecha=?, factura=? WHERE id=?",
                (self.alumno.currentData(), self.debito.value(), self.credito.value(),
                 self.aclaracion.text().strip(),
                 self.fecha.date().toString("yyyy-MM-dd"),
                 self.factura.text().strip(), self._id),
            )
            conn.commit()
            global current_cta_id
            current_cta_id = self._id
            conn.close()
            QMessageBox.information(self, "Guardado", "Cuenta actualizada.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{exc}")


class BuscarCuentaDialog(QDialog):
    """Search dialog for cuentas."""

    _HEADERS = ["ID", "Alumno", "Débito", "Crédito", "Aclaración", "Fecha", "Factura"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cuentas - Buscar")
        self.resize(800, 400)
        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Alumno:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Nombre o apellido del alumno…")
        self.search_edit.textChanged.connect(self._load)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, len(self._HEADERS))
        self.table.setHorizontalHeaderLabels(self._HEADERS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load("")

    def _on_double_click(self, row: int, _col: int):
        id_item = self.table.item(row, 0)
        if id_item is None:
            return
        dlg = EditCuentaDialog(int(id_item.text()), self)
        if dlg.exec() == QDialog.Accepted:
            self._load(self.search_edit.text())

    def _load(self, text: str):
        like = f"%{text}%"
        try:
            conn = sqlite3.connect(get_active_db_path())
            rows = conn.execute(
                "SELECT c.id, a.paterno || ', ' || a.nombres,"
                " c.debito, c.credito, c.aclaracion, c.fecha, c.factura"
                " FROM ctas c JOIN alumnos a ON c.id_alumno = a.id"
                " WHERE a.nombres LIKE ? OR a.paterno LIKE ?"
                " ORDER BY c.fecha DESC",
                (like, like),
            ).fetchall()
            conn.close()
        except Exception:
            rows = []
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem("" if val is None else str(val)))
        self.table.setSortingEnabled(True)
