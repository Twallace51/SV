"""Cuentas dialogs: Nuevo, Editar, Buscar."""

# region - imports

import logging
import sqlite3

from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit,
    QVBoxLayout, QFormLayout, QMessageBox, QHBoxLayout,
    QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QDateEdit, QSpinBox, QHeaderView, QComboBox,
    QAbstractSpinBox,
)
from PySide6.QtCore import QDate, Qt

from __init__ import get_active_db_path

# endregion

log = logging.getLogger("app")

# Current-record global – updated on every successful INSERT/UPDATE;
# set to None when the corresponding record is deleted.
current_cta_id: int | None = None


class NumericTableWidgetItem(QTableWidgetItem):
    """Table item that compares by integer value for proper numeric sorting."""

    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            try:
                return int(self.text()) < int(other.text())
            except (TypeError, ValueError):
                pass
        return super().__lt__(other)


class NuevoCuentaDialog(QDialog):
    """Form dialog to insert a new cuenta into SV.db."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cuentas - Nuevo")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.id_alumno = QLineEdit()
        self.id_alumno.setPlaceholderText("Ingrese ID de alumno")
        self.id_alumno.textChanged.connect(self._sync_alumno_nombre)
        self.alumno = QLabel("-")

        self.debito = QSpinBox()
        self.debito.setRange(0, 999999)
        self.debito.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.debito.valueChanged.connect(self._sync_amount_fields)

        self.credito = QSpinBox()
        self.credito.setRange(0, 999999)
        self.credito.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.credito.valueChanged.connect(self._sync_amount_fields)

        self.aclaracion = QLineEdit()
        self.aclaracion_select = QComboBox()
        self.aclaracion_select.addItems(["Pension", "Comedor", "Insumos"])
        self.aclaracion_select.setCurrentIndex(-1)
        self.aclaracion_select.currentTextChanged.connect(self._apply_aclaracion_option)
        aclaracion_row = QHBoxLayout()
        aclaracion_row.addWidget(self.aclaracion)
        aclaracion_row.addWidget(self.aclaracion_select)
        self.fecha = QDateEdit()
        self.fecha.setCalendarPopup(True)
        self.fecha.setDisplayFormat("yyyy-MM-dd")
        self.fecha.setDate(QDate.currentDate())
        self.fecha.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.factura = QLineEdit()

        form.addRow("ID Alumno *:", self.id_alumno)
        form.addRow("Alumno:", self.alumno)
        form.addRow("Débito:", self.debito)
        form.addRow("Crédito:", self.credito)
        form.addRow("Aclaración:", aclaracion_row)
        form.addRow("Fecha:", self.fecha)
        form.addRow("Numero Factura:", self.factura)
        layout.addLayout(form)

        self._sync_alumno_nombre()
        self._sync_amount_fields()

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _sync_alumno_nombre(self):
        raw_id = self.id_alumno.text().strip()
        if not raw_id:
            self.alumno.setText("-")
            return

        try:
            alumno_id = int(raw_id)
        except ValueError:
            self.alumno.setText("ID inválido")
            return

        try:
            conn = sqlite3.connect(get_active_db_path())
            row = conn.execute(
                "SELECT paterno, nombres FROM alumnos WHERE id = ?",
                (alumno_id,),
            ).fetchone()
            conn.close()
        except Exception:
            row = None

        self.alumno.setText(f"{row[0]}, {row[1]}" if row else "No encontrado")

    def _sync_amount_fields(self):
        debito_has_value = self.debito.value() > 0
        credito_has_value = self.credito.value() > 0
        self.factura.setEnabled(credito_has_value)
        if not debito_has_value and not credito_has_value:
            self.debito.setEnabled(True)
            self.credito.setEnabled(True)
            return
        self.credito.setEnabled(not debito_has_value)
        self.debito.setEnabled(not credito_has_value)

    def _apply_aclaracion_option(self, option: str):
        current = self.aclaracion.text().strip()
        preset_values = {"Pension", "Comedor", "Insumos"}
        if option and (not current or current in preset_values):
            self.aclaracion.setText(option)

    def _save(self):
        raw_id = self.id_alumno.text().strip()
        if not raw_id:
            QMessageBox.warning(self, "Validación", "ID Alumno es requerido.")
            return
        try:
            alumno_id = int(raw_id)
        except ValueError:
            QMessageBox.warning(self, "Validación", "ID Alumno debe ser un número entero.")
            return

        if self.alumno.text() in {"No encontrado", "ID inválido", "-"}:
            QMessageBox.warning(self, "Validación", "El ID Alumno no existe.")
            return

        debito = self.debito.value()
        credito = self.credito.value()
        if (debito == 0 and credito == 0) or (debito > 0 and credito > 0):
            QMessageBox.warning(self, "Validación", "Debe ingresar solo Débito o solo Crédito (uno es obligatorio).")
            return

        try:
            conn = sqlite3.connect(get_active_db_path())
            cur = conn.execute(
                "INSERT INTO ctas (id_alumno, debito, credito, aclaracion, fecha, factura)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (alumno_id, debito, credito,
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

    def __init__(self, record_id: int, parent=None, is_admin: bool = False):
        super().__init__(parent)
        self._id = record_id
        self._is_admin = is_admin
        self.setWindowTitle("Cuentas - Editar")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.id_alumno = QLineEdit()
        self.id_alumno.setPlaceholderText("Ingrese ID de alumno")
        self.id_alumno.textChanged.connect(self._sync_alumno_nombre)
        self.alumno = QLabel("-")

        try:
            conn = sqlite3.connect(get_active_db_path())
            row = conn.execute(
                "SELECT id_alumno, debito, credito, aclaracion, fecha, factura"
                " FROM ctas WHERE id = ?", (self._id,)
            ).fetchone()
            conn.close()
        except Exception:
            row = None

        self.debito = QSpinBox()
        self.debito.setRange(0, 999999)
        self.debito.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.debito.valueChanged.connect(self._sync_amount_fields)

        self.credito = QSpinBox()
        self.credito.setRange(0, 999999)
        self.credito.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.credito.valueChanged.connect(self._sync_amount_fields)

        self.aclaracion = QLineEdit()
        self.aclaracion_select = QComboBox()
        self.aclaracion_select.addItems(["Pension", "Comedor", "Insumos"])
        self.aclaracion_select.setCurrentIndex(-1)
        self.aclaracion_select.currentTextChanged.connect(self._apply_aclaracion_option)
        aclaracion_row = QHBoxLayout()
        aclaracion_row.addWidget(self.aclaracion)
        aclaracion_row.addWidget(self.aclaracion_select)
        self.fecha = QDateEdit()
        self.fecha.setCalendarPopup(True)
        self.fecha.setDisplayFormat("yyyy-MM-dd")
        self.fecha.setDate(QDate.currentDate())
        self.fecha.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.factura = QLineEdit()

        if row:
            self.id_alumno.setText(str(row[0] or ""))
            self.debito.setValue(row[1] or 0)
            self.credito.setValue(row[2] or 0)
            self.aclaracion.setText(row[3] or "")
            d = QDate.fromString(row[4] or "", "yyyy-MM-dd")
            if d.isValid():
                self.fecha.setDate(d)
            self.factura.setText(row[5] or "")
            aclaracion_idx = self.aclaracion_select.findText(self.aclaracion.text())
            if aclaracion_idx >= 0:
                self.aclaracion_select.setCurrentIndex(aclaracion_idx)

        form.addRow("ID Alumno *:", self.id_alumno)
        form.addRow("Alumno:", self.alumno)
        form.addRow("Débito:", self.debito)
        form.addRow("Crédito:", self.credito)
        form.addRow("Aclaración:", aclaracion_row)
        form.addRow("Fecha:", self.fecha)
        form.addRow("Numero Factura:", self.factura)
        layout.addLayout(form)

        self._sync_alumno_nombre()
        self._sync_amount_fields()

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        self.delete_btn = buttons.addButton("Borrar", QDialogButtonBox.ActionRole)
        self.delete_btn.setEnabled(self._is_admin)
        if not self._is_admin:
            self.delete_btn.setToolTip("Solo administrador puede borrar registros.")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        self.delete_btn.clicked.connect(self._delete)
        layout.addWidget(buttons)

    def _sync_alumno_nombre(self):
        raw_id = self.id_alumno.text().strip()
        if not raw_id:
            self.alumno.setText("-")
            return

        try:
            alumno_id = int(raw_id)
        except ValueError:
            self.alumno.setText("ID inválido")
            return

        try:
            conn = sqlite3.connect(get_active_db_path())
            row = conn.execute(
                "SELECT paterno, nombres FROM alumnos WHERE id = ?",
                (alumno_id,),
            ).fetchone()
            conn.close()
        except Exception:
            row = None

        self.alumno.setText(f"{row[0]}, {row[1]}" if row else "No encontrado")

    def _sync_amount_fields(self):
        debito_has_value = self.debito.value() > 0
        credito_has_value = self.credito.value() > 0
        self.factura.setEnabled(credito_has_value)
        if not debito_has_value and not credito_has_value:
            self.debito.setEnabled(True)
            self.credito.setEnabled(True)
            return
        self.credito.setEnabled(not debito_has_value)
        self.debito.setEnabled(not credito_has_value)

    def _apply_aclaracion_option(self, option: str):
        current = self.aclaracion.text().strip()
        preset_values = {"Pension", "Comedor", "Insumos"}
        if option and (not current or current in preset_values):
            self.aclaracion.setText(option)

    def _save(self):
        raw_id = self.id_alumno.text().strip()
        if not raw_id:
            QMessageBox.warning(self, "Validación", "ID Alumno es requerido.")
            return
        try:
            alumno_id = int(raw_id)
        except ValueError:
            QMessageBox.warning(self, "Validación", "ID Alumno debe ser un número entero.")
            return

        if self.alumno.text() in {"No encontrado", "ID inválido", "-"}:
            QMessageBox.warning(self, "Validación", "El ID Alumno no existe.")
            return

        debito = self.debito.value()
        credito = self.credito.value()
        if (debito == 0 and credito == 0) or (debito > 0 and credito > 0):
            QMessageBox.warning(self, "Validación", "Debe ingresar solo Débito o solo Crédito (uno es obligatorio).")
            return

        try:
            conn = sqlite3.connect(get_active_db_path())
            conn.execute(
                "UPDATE ctas SET id_alumno=?, debito=?, credito=?, aclaracion=?,"
                " fecha=?, factura=? WHERE id=?",
                (alumno_id, debito, credito,
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

    def _delete(self):
        if not self._is_admin:
            QMessageBox.warning(self, "Permisos", "Solo administrador puede borrar registros.")
            return

        reply = QMessageBox.question(
            self,
            "Confirmar borrado",
            "¿Desea borrar esta cuenta? Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            conn = sqlite3.connect(get_active_db_path())
            conn.execute("DELETE FROM ctas WHERE id = ?", (self._id,))
            conn.commit()
            conn.close()

            global current_cta_id
            if current_cta_id == self._id:
                current_cta_id = None

            QMessageBox.information(self, "Borrado", "Cuenta borrada correctamente.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo borrar:\n{exc}")


class BuscarCuentaDialog(QDialog):
    """Search dialog for cuentas."""

    _HEADERS = ["ID Alumno", "Alumno", "Débito", "Crédito", "Aclaración", "Fecha", "Factura"]

    def __init__(self, parent=None, is_admin: bool = False):
        super().__init__(parent)
        self._is_admin = is_admin
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
        alumno_id_item = self.table.item(row, 0)
        if alumno_id_item is None:
            return
        cuenta_id = alumno_id_item.data(Qt.UserRole)
        if cuenta_id is None:
            return
        dlg = EditCuentaDialog(int(cuenta_id), self, is_admin=self._is_admin)
        if dlg.exec() == QDialog.Accepted:
            self._load(self.search_edit.text())

    def _load(self, text: str):
        like = f"%{text}%"
        try:
            conn = sqlite3.connect(get_active_db_path())
            rows = conn.execute(
                "SELECT c.id, a.id, a.paterno || ', ' || a.nombres,"
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
            cuenta_id = row[0]
            for c, val in enumerate(row[1:]):
                text = "" if val is None else str(val)
                item = NumericTableWidgetItem(text) if c == 0 else QTableWidgetItem(text)
                if c == 0:
                    item.setData(Qt.UserRole, cuenta_id)
                self.table.setItem(r, c, item)
        self.table.setSortingEnabled(True)
