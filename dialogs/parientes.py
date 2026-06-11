"""Parientes (adultos) dialogs: Nuevo, Editar, Buscar."""

# region - imports

import logging
import sqlite3

from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit,
    QVBoxLayout, QFormLayout, QMessageBox, QHBoxLayout,
    QDialogButtonBox, QTableWidget, QTableWidgetItem, QHeaderView,
)

from __init__ import get_active_db_path

# endregion

log = logging.getLogger("app")

# Current-record global – updated on every successful INSERT/UPDATE;
# set to None when the corresponding record is deleted.
current_adulto_id: int | None = None
current_adulto_name: str | None = None


class NumericTableWidgetItem(QTableWidgetItem):
    """Table item that compares by integer value for proper numeric sorting."""

    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            try:
                return int(self.text()) < int(other.text())
            except (TypeError, ValueError):
                pass
        return super().__lt__(other)


class NuevoParienteDialog(QDialog):
    """Form dialog to insert a new pariente (adulto) into SV.db."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Parientes - Nuevo")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.nombres = QLineEdit()
        self.paterno = QLineEdit()
        self.materno = QLineEdit()
        self.cell1 = QLineEdit()
        self.cell2 = QLineEdit()
        self.email = QLineEdit()
        self.carnet = QLineEdit()
        self.nit = QLineEdit()

        form.addRow("Nombres *:", self.nombres)
        form.addRow("Paterno *:", self.paterno)
        form.addRow("Materno:", self.materno)
        form.addRow("Celular 1:", self.cell1)
        form.addRow("Celular 2:", self.cell2)
        form.addRow("Email:", self.email)
        form.addRow("Carnet:", self.carnet)
        form.addRow("NIT:", self.nit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        nombres = self.nombres.text().strip().title()
        paterno = self.paterno.text().strip().title()
        if not nombres or not paterno:
            QMessageBox.warning(self, "Validación", "Nombres y apellido paterno son requeridos.")
            return
        try:
            conn = sqlite3.connect(get_active_db_path())
            cur = conn.execute(
                "INSERT INTO adultos (a_nombres, a_paterno, a_materno, cell1, cell2, email, a_carnet, NIT)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (nombres, paterno, self.materno.text().strip().title(),
                 self.cell1.text().strip(), self.cell2.text().strip(),
                 self.email.text().strip(), self.carnet.text().strip(),
                 self.nit.text().strip()),
            )
            conn.commit()
            global current_adulto_id, current_adulto_name
            current_adulto_id = cur.lastrowid
            current_adulto_name = f"{paterno}, {nombres}"
            conn.close()
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{exc}")


class EditParienteDialog(QDialog):
    """Edit form pre-populated with an existing pariente record."""

    def __init__(self, record_id: int, parent=None, is_admin: bool = False):
        super().__init__(parent)
        self._id = record_id
        self._is_admin = is_admin
        self.setWindowTitle("Parientes - Editar")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.nombres = QLineEdit()
        self.paterno = QLineEdit()
        self.materno = QLineEdit()
        self.cell1 = QLineEdit()
        self.cell2 = QLineEdit()
        self.email = QLineEdit()
        self.carnet = QLineEdit()
        self.nit = QLineEdit()

        try:
            conn = sqlite3.connect(get_active_db_path())
            row = conn.execute(
                "SELECT a_nombres, a_paterno, a_materno, cell1, cell2, email, a_carnet, NIT"
                " FROM adultos WHERE id = ?", (self._id,)
            ).fetchone()
            conn.close()
        except Exception:
            row = None

        if row:
            self.nombres.setText(row[0] or "")
            self.paterno.setText(row[1] or "")
            self.materno.setText(row[2] or "")
            self.cell1.setText(row[3] or "")
            self.cell2.setText(row[4] or "")
            self.email.setText(row[5] or "")
            self.carnet.setText(row[6] or "")
            self.nit.setText(row[7] or "")

        form.addRow("Nombres *:", self.nombres)
        form.addRow("Paterno *:", self.paterno)
        form.addRow("Materno:", self.materno)
        form.addRow("Celular 1:", self.cell1)
        form.addRow("Celular 2:", self.cell2)
        form.addRow("Email:", self.email)
        form.addRow("Carnet:", self.carnet)
        form.addRow("NIT:", self.nit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        self.delete_btn = buttons.addButton("Borrar", QDialogButtonBox.ActionRole)
        self.delete_btn.setEnabled(self._is_admin)
        if not self._is_admin:
            self.delete_btn.setToolTip("Solo administrador puede borrar registros.")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        self.delete_btn.clicked.connect(self._delete)
        layout.addWidget(buttons)

    def _save(self):
        nombres = self.nombres.text().strip().title()
        paterno = self.paterno.text().strip().title()
        if not nombres or not paterno:
            QMessageBox.warning(self, "Validación", "Nombres y apellido paterno son requeridos.")
            return
        try:
            conn = sqlite3.connect(get_active_db_path())
            conn.execute(
                "UPDATE adultos SET a_nombres=?, a_paterno=?, a_materno=?,"
                " cell1=?, cell2=?, email=?, a_carnet=?, NIT=? WHERE id=?",
                (nombres, paterno, self.materno.text().strip().title(),
                 self.cell1.text().strip(), self.cell2.text().strip(),
                 self.email.text().strip(), self.carnet.text().strip(),
                 self.nit.text().strip(), self._id),
            )
            conn.commit()
            global current_adulto_id, current_adulto_name
            current_adulto_id = self._id
            current_adulto_name = f"{paterno}, {nombres}"
            conn.close()
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{exc}")

    def _delete(self):
        if not self._is_admin:
            QMessageBox.warning(self, "Permisos", "Solo administrador puede borrar registros.")
            return

        reply = QMessageBox.question(
            self,
            "Confirmar borrado",
            "¿Desea borrar este pariente? Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            conn = sqlite3.connect(get_active_db_path())
            conn.execute("DELETE FROM adultos WHERE id = ?", (self._id,))
            conn.commit()
            conn.close()
            global current_adulto_id, current_adulto_name
            current_adulto_id = None
            current_adulto_name = None
            QMessageBox.information(self, "Borrado", "Pariente borrado correctamente.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo borrar:\n{exc}")


class BuscarParienteDialog(QDialog):
    """Search dialog for parientes (adultos)."""

    _HEADERS = ["ID", "Nombres", "Paterno", "Materno", "Celular 1", "Celular 2", "Email", "Carnet", "NIT"]

    def __init__(self, parent=None, is_admin: bool = False):
        super().__init__(parent)
        self._is_admin = is_admin
        self.setWindowTitle("Parientes - Buscar")
        self.resize(820, 380)
        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Nombres o apellidos…")
        self.search_edit.textChanged.connect(self._load)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, len(self._HEADERS))
        self.table.setHorizontalHeaderLabels(self._HEADERS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)
        self.table.cellClicked.connect(self._on_single_click)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load("")

    def _on_single_click(self, row: int, _col: int):
        self._set_current_adulto_from_row(row)

    def _set_current_adulto_from_row(self, row: int):
        id_item = self.table.item(row, 0)
        if id_item is None:
            return
        nombres_item = self.table.item(row, 1)
        paterno_item = self.table.item(row, 2)

        try:
            selected_id = int(id_item.text())
        except (TypeError, ValueError):
            return

        selected_nombres = "" if nombres_item is None else nombres_item.text().strip()
        selected_paterno = "" if paterno_item is None else paterno_item.text().strip()

        global current_adulto_id, current_adulto_name
        current_adulto_id = selected_id
        current_adulto_name = f"{selected_paterno}, {selected_nombres}"

    def _on_double_click(self, row: int, _col: int):
        self._set_current_adulto_from_row(row)
        id_item = self.table.item(row, 0)
        if id_item is None:
            return
        dlg = EditParienteDialog(int(id_item.text()), self, is_admin=self._is_admin)
        if dlg.exec() == QDialog.Accepted:
            self._load(self.search_edit.text())

    def _load(self, text: str):
        like = f"%{text}%"
        try:
            conn = sqlite3.connect(get_active_db_path())
            rows = conn.execute(
                "SELECT id, a_nombres, a_paterno, a_materno, cell1, cell2, email, a_carnet, NIT"
                " FROM adultos"
                " WHERE a_nombres LIKE ? OR a_paterno LIKE ? OR a_materno LIKE ?"
                " ORDER BY a_paterno, a_nombres",
                (like, like, like),
            ).fetchall()
            conn.close()
        except Exception:
            rows = []
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                text = "" if val is None else str(val)
                item = NumericTableWidgetItem(text) if c == 0 else QTableWidgetItem(text)
                self.table.setItem(r, c, item)
        self.table.setSortingEnabled(True)
