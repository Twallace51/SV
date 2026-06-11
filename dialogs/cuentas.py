"""Cuentas dialogs: Nuevo, Editar, Buscar."""

# region - imports

import logging
import sqlite3

from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit,
    QVBoxLayout, QFormLayout, QMessageBox, QHBoxLayout,
    QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QDateEdit, QSpinBox, QHeaderView, QComboBox,
    QAbstractSpinBox, QPushButton,
)
from PySide6.QtCore import QDate, Qt

from __init__ import get_active_db_path
from dialogs import alumnos as alumnos_dialogs
from dialogs import parientes as parientes_dialogs

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

        self.id_creditor = QLineEdit()
        self.id_creditor.setPlaceholderText("Ingrese ID de creditor")
        self.id_creditor.textChanged.connect(self._sync_creditor_nombre)
        self.creditor = QLabel("-")

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
        form.addRow("ID Creditor:", self.id_creditor)
        form.addRow("Creditor:", self.creditor)
        form.addRow("Débito:", self.debito)
        form.addRow("Crédito:", self.credito)
        form.addRow("Aclaración:", aclaracion_row)
        form.addRow("Fecha:", self.fecha)
        form.addRow("Numero Factura:", self.factura)
        layout.addLayout(form)

        self._sync_alumno_nombre()
        self._sync_creditor_nombre()
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

    def _sync_creditor_nombre(self):
        raw_id = self.id_creditor.text().strip()
        if not raw_id:
            self.creditor.setText("-")
            return

        try:
            creditor_id = int(raw_id)
        except ValueError:
            self.creditor.setText("ID inválido")
            return

        try:
            conn = sqlite3.connect(get_active_db_path())
            row = conn.execute(
                "SELECT a_nombres, a_paterno FROM adultos WHERE id = ?",
                (creditor_id,),
            ).fetchone()
            conn.close()
        except Exception:
            row = None

        self.creditor.setText(f"{row[0]} {row[1]}" if row else "No encontrado")

    def _sync_amount_fields(self):
        debito_has_value = self.debito.value() > 0
        credito_has_value = self.credito.value() > 0
        self.factura.setEnabled(credito_has_value)
        self.id_creditor.setEnabled(debito_has_value is False)
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

        raw_creditor = self.id_creditor.text().strip()
        creditor_id: int | None = None
        if raw_creditor:
            try:
                creditor_id = int(raw_creditor)
            except ValueError:
                QMessageBox.warning(self, "Validación", "ID Creditor debe ser un número entero.")
                return
            if self.creditor.text() in {"No encontrado", "ID inválido"}:
                QMessageBox.warning(self, "Validación", "El ID Creditor no existe.")
                return

        try:
            conn = sqlite3.connect(get_active_db_path())
            cur = conn.execute(
                "INSERT INTO ctas (id_alumno, id_creditor, debito, credito, aclaracion, fecha, factura)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (alumno_id, creditor_id, debito, credito,
                 self.aclaracion.text().strip(),
                 self.fecha.date().toString("yyyy-MM-dd"),
                 self.factura.text().strip()),
            )
            conn.commit()
            global current_cta_id
            current_cta_id = cur.lastrowid
            conn.close()
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

        self.id_creditor = QLineEdit()
        self.id_creditor.setPlaceholderText("Ingrese ID de creditor")
        self.id_creditor.textChanged.connect(self._sync_creditor_nombre)
        self.creditor = QLabel("-")

        try:
            conn = sqlite3.connect(get_active_db_path())
            row = conn.execute(
                "SELECT id_alumno, id_creditor, debito, credito, aclaracion, fecha, factura"
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
            self.id_creditor.setText(str(row[1] or ""))
            self.debito.setValue(row[2] or 0)
            self.credito.setValue(row[3] or 0)
            self.aclaracion.setText(row[4] or "")
            d = QDate.fromString(row[5] or "", "yyyy-MM-dd")
            if d.isValid():
                self.fecha.setDate(d)
            self.factura.setText(row[6] or "")
            aclaracion_idx = self.aclaracion_select.findText(self.aclaracion.text())
            if aclaracion_idx >= 0:
                self.aclaracion_select.setCurrentIndex(aclaracion_idx)

        form.addRow("ID Alumno *:", self.id_alumno)
        form.addRow("Alumno:", self.alumno)
        form.addRow("ID Creditor:", self.id_creditor)
        form.addRow("Creditor:", self.creditor)
        form.addRow("Débito:", self.debito)
        form.addRow("Crédito:", self.credito)
        form.addRow("Aclaración:", aclaracion_row)
        form.addRow("Fecha:", self.fecha)
        form.addRow("Numero Factura:", self.factura)
        layout.addLayout(form)

        self._sync_alumno_nombre()
        self._sync_creditor_nombre()
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

    def _sync_creditor_nombre(self):
        raw_id = self.id_creditor.text().strip()
        if not raw_id:
            self.creditor.setText("-")
            return

        try:
            creditor_id = int(raw_id)
        except ValueError:
            self.creditor.setText("ID inválido")
            return

        try:
            conn = sqlite3.connect(get_active_db_path())
            row = conn.execute(
                "SELECT a_nombres, a_paterno FROM adultos WHERE id = ?",
                (creditor_id,),
            ).fetchone()
            conn.close()
        except Exception:
            row = None

        self.creditor.setText(f"{row[0]} {row[1]}" if row else "No encontrado")

    def _sync_amount_fields(self):
        debito_has_value = self.debito.value() > 0
        credito_has_value = self.credito.value() > 0
        self.factura.setEnabled(credito_has_value)
        self.id_creditor.setEnabled(debito_has_value is False)
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

        raw_creditor = self.id_creditor.text().strip()
        creditor_id: int | None = None
        if raw_creditor:
            try:
                creditor_id = int(raw_creditor)
            except ValueError:
                QMessageBox.warning(self, "Validación", "ID Creditor debe ser un número entero.")
                return
            if self.creditor.text() in {"No encontrado", "ID inválido"}:
                QMessageBox.warning(self, "Validación", "El ID Creditor no existe.")
                return

        try:
            conn = sqlite3.connect(get_active_db_path())
            conn.execute(
                "UPDATE ctas SET id_alumno=?, id_creditor=?, debito=?, credito=?, aclaracion=?,"
                " fecha=?, factura=? WHERE id=?",
                (alumno_id, creditor_id, debito, credito,
                 self.aclaracion.text().strip(),
                 self.fecha.date().toString("yyyy-MM-dd"),
                 self.factura.text().strip(), self._id),
            )
            conn.commit()
            global current_cta_id
            current_cta_id = self._id
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

    _HEADERS = [
        "ID Alumno",
        "Alumno",
        "ID Creditor",
        "Creditor",
        "Débito",
        "Crédito",
        "Aclaración",
        "Fecha",
        "Factura",
    ]

    def __init__(self, parent=None, is_admin: bool = False):
        super().__init__(parent)
        self._is_admin = is_admin
        self.setWindowTitle("Cuentas - Buscar")
        self.resize(800, 400)
        layout = QVBoxLayout(self)

        alumno_search_row = QHBoxLayout()
        alumno_search_row.addWidget(QLabel("Alumno:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Nombre o apellido del alumno…")
        self.search_edit.textChanged.connect(self._load)
        alumno_search_row.addWidget(self.search_edit)
        self.current_alumno_btn = QPushButton()
        self.current_alumno_btn.clicked.connect(self._apply_current_alumno_filter)
        alumno_search_row.addWidget(self.current_alumno_btn)
        layout.addLayout(alumno_search_row)

        creditor_search_row = QHBoxLayout()
        creditor_search_row.addWidget(QLabel("Creditor:"))
        self.search_creditor_edit = QLineEdit()
        self.search_creditor_edit.setPlaceholderText("ID o nombre del creditor…")
        self.search_creditor_edit.textChanged.connect(self._load)
        creditor_search_row.addWidget(self.search_creditor_edit)
        self.current_creditor_btn = QPushButton("Usar actual")
        self.current_creditor_btn.clicked.connect(self._apply_current_creditor_filter)
        creditor_search_row.addWidget(self.current_creditor_btn)
        self.current_creditor_label = QLabel()
        creditor_search_row.addWidget(self.current_creditor_label)
        layout.addLayout(creditor_search_row)

        self.table = QTableWidget(0, len(self._HEADERS))
        self.table.setHorizontalHeaderLabels(self._HEADERS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_current_alumno_label()
        self._refresh_current_creditor_label()
        self._load()

    def _on_double_click(self, row: int, _col: int):
        alumno_id_item = self.table.item(row, 0)
        if alumno_id_item is None:
            return
        cuenta_id = alumno_id_item.data(Qt.UserRole)
        if cuenta_id is None:
            return
        dlg = EditCuentaDialog(int(cuenta_id), self, is_admin=self._is_admin)
        if dlg.exec() == QDialog.Accepted:
            self._load()

    def _apply_current_alumno_filter(self):
        if alumnos_dialogs.current_alumno_id is not None:
            self.search_edit.setText(str(alumnos_dialogs.current_alumno_id))
            return
        if alumnos_dialogs.current_alumno_name:
            self.search_edit.setText(str(alumnos_dialogs.current_alumno_name))

    def _refresh_current_alumno_label(self):
        alumno_id = alumnos_dialogs.current_alumno_id
        alumno_name = alumnos_dialogs.current_alumno_name
        parts = []
        if alumno_id is not None:
            parts.append(str(alumno_id))
        if alumno_name:
            parts.append(str(alumno_name))
        self.current_alumno_btn.setText(
            f"Alumno Actual: {' - '.join(parts)}" if parts else "Alumno Actual: -"
        )

    def _apply_current_creditor_filter(self):
        if parientes_dialogs.current_adulto_id is not None:
            self.search_creditor_edit.setText(str(parientes_dialogs.current_adulto_id))
            return
        if parientes_dialogs.current_adulto_name:
            self.search_creditor_edit.setText(str(parientes_dialogs.current_adulto_name))

    def _refresh_current_creditor_label(self):
        creditor_id = parientes_dialogs.current_adulto_id
        creditor_name = parientes_dialogs.current_adulto_name
        parts = []
        if creditor_id is not None:
            parts.append(str(creditor_id))
        if creditor_name:
            parts.append(str(creditor_name))
        self.current_creditor_label.setText(
            f"Creditor Actual: {' - '.join(parts)}" if parts else "Creditor Actual: -"
        )

    def _load(self, _text: str = ""):
        alumno_search = self.search_edit.text().strip()
        creditor_search = self.search_creditor_edit.text().strip()
        alumno_like = f"%{alumno_search}%"
        creditor_like = f"%{creditor_search}%"
        try:
            conn = sqlite3.connect(get_active_db_path())
            alumno_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(alumnos)").fetchall()
            }
            ctas_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(ctas)").fetchall()
            }
            creditor_id_expr = "c.id_creditor" if "id_creditor" in ctas_columns else "NULL"
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            creditor_name_expr = "''"
            creditor_join = ""
            has_creditor_name = False
            if "adultos" in tables:
                adulto_columns = {
                    row[1] for row in conn.execute("PRAGMA table_info(adultos)").fetchall()
                }
                adultos_name_parts = []
                if "a_paterno" in adulto_columns:
                    adultos_name_parts.append("COALESCE(ad.a_paterno, '')")
                if "a_nombres" in adulto_columns:
                    adultos_name_parts.append("COALESCE(ad.a_nombres, '')")
                if "a_materno" in adulto_columns:
                    adultos_name_parts.append("COALESCE(ad.a_materno, '')")
                if adultos_name_parts:
                    creditor_name_expr = "TRIM(" + " || ' ' || ".join(adultos_name_parts) + ")"
                    has_creditor_name = True
                creditor_join = f" LEFT JOIN adultos ad ON ad.id = CAST({creditor_id_expr} AS INTEGER)"

            where_clauses = ["(CAST(a.id AS TEXT) LIKE ? OR a.nombres LIKE ? OR a.paterno LIKE ?)"]
            params = [alumno_like, alumno_like, alumno_like]

            if creditor_search:
                creditor_filters = []
                if "id_creditor" in ctas_columns:
                    creditor_filters.append("CAST(c.id_creditor AS TEXT) LIKE ?")
                    params.append(creditor_like)
                if has_creditor_name:
                    creditor_filters.append(f"{creditor_name_expr} LIKE ?")
                    params.append(creditor_like)
                if creditor_filters:
                    where_clauses.append("(" + " OR ".join(creditor_filters) + ")")
                else:
                    where_clauses.append("1 = 0")

            rows = conn.execute(
                "SELECT c.id, a.id, a.paterno || ', ' || a.nombres,"
                f" {creditor_id_expr}, {creditor_name_expr},"
                " c.debito, c.credito, c.aclaracion, c.fecha, c.factura"
                " FROM ctas c JOIN alumnos a ON c.id_alumno = a.id"
                f"{creditor_join}"
                f" WHERE {' AND '.join(where_clauses)}"
                " ORDER BY c.fecha DESC",
                params,
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
