"""Alumnos dialogs: Nuevo, Editar, Buscar."""

# region - imports

import logging
import sqlite3

from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit,
    QVBoxLayout, QFormLayout, QMessageBox, QHBoxLayout,
    QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QDateEdit, QComboBox, QDoubleSpinBox, QHeaderView,
    QAbstractSpinBox, QCheckBox,
)
from PySide6.QtCore import Qt

from __init__ import get_active_db_path

# endregion

log = logging.getLogger("app")

# Current-record global – updated on every successful INSERT/UPDATE;
# set to None when the corresponding record is deleted.
current_alumno_id: int | None = None
current_alumno_name: str | None = None


def _normalize_grado_id(value):
    """Normalize grade IDs so combo data and alumno id_grado compare consistently."""
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None
    if text.lower() in {"null", "none"}:
        return None

    try:
        return int(text)
    except (TypeError, ValueError):
        return text


class NumericTableWidgetItem(QTableWidgetItem):
    """Table item that compares by integer value for proper numeric sorting."""

    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            left_key = self.data(Qt.ItemDataRole.UserRole)
            right_key = other.data(Qt.ItemDataRole.UserRole)
            if left_key is not None and right_key is not None:
                try:
                    return int(left_key) < int(right_key)
                except (TypeError, ValueError):
                    return str(left_key) < str(right_key)
        if isinstance(other, QTableWidgetItem):
            try:
                return int(self.text()) < int(other.text())
            except (TypeError, ValueError):
                pass
        return super().__lt__(other)


class NuevoAlumnoDialog(QDialog):
    """Form dialog to insert a new alumno into SV.db."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Alumnos - Nuevo")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.nombres = QLineEdit()
        self.paterno = QLineEdit()
        self.materno = QLineEdit()
        self.cumpleanos = QDateEdit()
        self.cumpleanos.setCalendarPopup(True)
        self.cumpleanos.setDisplayFormat("yyyy-MM-dd")
        self.rude = QLineEdit()
        self.carnet = QLineEdit()
        self.pension = QDoubleSpinBox()
        self.pension.setRange(0, 99999)
        self.pension.setDecimals(2)
        self.pension.setPrefix("Bs ")
        self.pension.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        self.grado = QComboBox()
        self.grado.addItem("Sin grado", 0)
        try:
            conn = sqlite3.connect(get_active_db_path())
            for gid, gname in conn.execute("SELECT id, grado FROM grados ORDER BY grado").fetchall():
                self.grado.addItem(gname, _normalize_grado_id(gid))
            conn.close()
        except Exception:
            pass
        self.grado.setCurrentIndex(0)

        form.addRow("Nombres *:", self.nombres)
        form.addRow("Paterno *:", self.paterno)
        form.addRow("Materno:", self.materno)
        form.addRow("Cumpleaños:", self.cumpleanos)
        form.addRow("RUDE:", self.rude)
        form.addRow("Carnet:", self.carnet)
        form.addRow("Grado:", self.grado)
        form.addRow("Pensión:", self.pension)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        nombres = self.nombres.text().strip()
        paterno = self.paterno.text().strip()
        if not nombres or not paterno:
            QMessageBox.warning(self, "Validación", "Nombres y apellido paterno son requeridos.")
            return
        try:
            conn = sqlite3.connect(get_active_db_path())
            cur = conn.execute(
                "INSERT INTO alumnos (nombres, paterno, materno, cumpleanos, rude, Carnet, id_grado, pension)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (nombres, paterno, self.materno.text().strip(),
                 self.cumpleanos.date().toString("yyyy-MM-dd"),
                 self.rude.text().strip(), self.carnet.text().strip(),
                 self.grado.currentData(), self.pension.value()),
            )
            conn.commit()
            global current_alumno_id, current_alumno_name
            current_alumno_id = cur.lastrowid
            current_alumno_name = f"{nombres} {paterno}"
            conn.close()
            QMessageBox.information(self, "Guardado", f"Alumno '{nombres} {paterno}' guardado.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{exc}")


class EditAlumnoDialog(QDialog):
    """Edit form pre-populated with an existing alumno record."""

    def __init__(self, record_id: int, parent=None):
        super().__init__(parent)
        self._id = record_id
        self.setWindowTitle("Alumnos - Editar")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.nombres = QLineEdit()
        self.paterno = QLineEdit()
        self.materno = QLineEdit()
        self.cumpleanos = QDateEdit()
        self.cumpleanos.setCalendarPopup(True)
        self.cumpleanos.setDisplayFormat("yyyy-MM-dd")
        self.rude = QLineEdit()
        self.carnet = QLineEdit()
        self.pension = QDoubleSpinBox()
        self.pension.setRange(0, 99999)
        self.pension.setDecimals(2)
        self.pension.setPrefix("Bs ")

        self.grado = QComboBox()
        try:
            conn = sqlite3.connect(get_active_db_path())
            for gid, gname in conn.execute("SELECT id, grado FROM grados ORDER BY grado").fetchall():
                self.grado.addItem(gname, _normalize_grado_id(gid))
            row = conn.execute(
                "SELECT nombres, paterno, materno, cumpleanos, rude, Carnet, id_grado, pension"
                " FROM alumnos WHERE id = ?", (self._id,)
            ).fetchone()
            conn.close()
        except Exception:
            row = None

        if row:
            self.nombres.setText(row[0] or "")
            self.paterno.setText(row[1] or "")
            self.materno.setText(row[2] or "")
            from PySide6.QtCore import QDate
            d = QDate.fromString(row[3] or "", "yyyy-MM-dd")
            if d.isValid():
                self.cumpleanos.setDate(d)
            self.rude.setText(row[4] or "")
            self.carnet.setText(row[5] or "")
            grado_id = _normalize_grado_id(row[6])
            idx = self.grado.findData(grado_id)
            if idx >= 0:
                self.grado.setCurrentIndex(idx)
            self.pension.setValue(row[7] or 0)

        form.addRow("Nombres *:", self.nombres)
        form.addRow("Paterno *:", self.paterno)
        form.addRow("Materno:", self.materno)
        form.addRow("Cumpleaños:", self.cumpleanos)
        form.addRow("RUDE:", self.rude)
        form.addRow("Carnet:", self.carnet)
        form.addRow("Grado:", self.grado)
        form.addRow("Pensión:", self.pension)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        nombres = self.nombres.text().strip()
        paterno = self.paterno.text().strip()
        if not nombres or not paterno:
            QMessageBox.warning(self, "Validación", "Nombres y apellido paterno son requeridos.")
            return
        try:
            conn = sqlite3.connect(get_active_db_path())
            conn.execute(
                "UPDATE alumnos SET nombres=?, paterno=?, materno=?, cumpleanos=?,"
                " rude=?, Carnet=?, id_grado=?, pension=? WHERE id=?",
                (nombres, paterno, self.materno.text().strip(),
                 self.cumpleanos.date().toString("yyyy-MM-dd"),
                 self.rude.text().strip(), self.carnet.text().strip(),
                 self.grado.currentData(), self.pension.value(), self._id),
            )
            conn.commit()
            global current_alumno_id, current_alumno_name
            current_alumno_id = self._id
            current_alumno_name = f"{nombres} {paterno}"
            conn.close()
            QMessageBox.information(self, "Guardado", f"Alumno '{nombres} {paterno}' actualizado.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{exc}")


class BuscarAlumnoDialog(QDialog):
    """Search dialog for alumnos."""

    _HEADERS = ["ID", "Nombres", "Paterno", "Materno", "RUDE", "Carnet", "Grado", "Pensión"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Alumnos - Buscar")
        self.resize(760, 420)
        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Nombres o apellidos…")
        self.search_edit.textChanged.connect(self._load)
        search_row.addWidget(self.search_edit)

        self.show_all_checkbox = QCheckBox("Todos")
        self.show_all_checkbox.setToolTip("Desactive para mostrar solo inscritos")
        self.show_all_checkbox.toggled.connect(lambda _checked: self._load(self.search_edit.text()))
        search_row.addWidget(self.show_all_checkbox)
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
        dlg = EditAlumnoDialog(int(id_item.text()), self)
        if dlg.exec() == QDialog.Accepted:
            self._load(self.search_edit.text())

    def _load(self, text: str):
        like = f"%{text}%"
        try:
            conn = sqlite3.connect(get_active_db_path())
            query = (
                "SELECT a.id, a.nombres, a.paterno, a.materno, a.rude, a.Carnet,"
                " g.grado, a.pension, a.id_grado"
                " FROM alumnos a"
                " LEFT JOIN grados g ON g.id = CASE"
                "   WHEN a.id_grado IS NULL THEN NULL"
                "   WHEN TRIM(CAST(a.id_grado AS TEXT)) = '' THEN NULL"
                "   WHEN LOWER(TRIM(CAST(a.id_grado AS TEXT))) IN ('null', 'none') THEN NULL"
                "   ELSE CAST(TRIM(CAST(a.id_grado AS TEXT)) AS INTEGER)"
                " END"
                " WHERE (a.nombres LIKE ? OR a.paterno LIKE ? OR a.materno LIKE ?)"
            )
            params = [like, like, like]
            if not self.show_all_checkbox.isChecked():
                query += (
                    " AND a.id_grado IS NOT NULL"
                    " AND TRIM(CAST(a.id_grado AS TEXT)) <> ''"
                    " AND LOWER(TRIM(CAST(a.id_grado AS TEXT))) NOT IN ('null', 'none')"
                    " AND CAST(TRIM(CAST(a.id_grado AS TEXT)) AS INTEGER) > 0"
                )
            query += " ORDER BY a.paterno, a.nombres"

            rows = conn.execute(query, params).fetchall()
            conn.close()
        except Exception:
            rows = []
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            grado_sort_key = row[8] if len(row) > 8 else None
            try:
                grado_sort_key = int(str(grado_sort_key).strip()) if grado_sort_key is not None else None
            except (TypeError, ValueError):
                grado_sort_key = None
            for c, val in enumerate(row[:8]):
                text = "" if val is None else str(val)
                if c in (0, 6):
                    item = NumericTableWidgetItem(text)
                else:
                    item = QTableWidgetItem(text)
                if c == 6:
                    item.setData(Qt.ItemDataRole.UserRole, 0 if grado_sort_key is None else grado_sort_key)
                self.table.setItem(r, c, item)
        self.table.setSortingEnabled(True)
