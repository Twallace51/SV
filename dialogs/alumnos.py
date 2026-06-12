"""Alumnos dialogs: Nuevo, Editar, Buscar."""

# region - imports

import logging
import sqlite3

from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit,
    QVBoxLayout, QFormLayout, QMessageBox, QHBoxLayout,
    QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QDateEdit, QComboBox, QHeaderView,
    QCheckBox, QWidget, QAbstractSpinBox, QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator

from __init__ import get_active_db_path
from dialogs import parientes as parientes_dialogs

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


def _normalize_related_adulto_id(value):
    """Normalize related adulto IDs for lookups and persistence."""
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
        return None


def _validate_alumno_integrity(conn, rude, carnet, id_padre, id_madre, current_id=None):
    """Return validation errors for related adults and unique alumno fields."""
    errors = []

    for label, related_id in (("padre", id_padre), ("madre", id_madre)):
        if related_id is None:
            continue
        exists = conn.execute(
            "SELECT 1 FROM adultos WHERE id = ?",
            (related_id,),
        ).fetchone()
        if not exists:
            errors.append(f"El ID de {label} no existe en adultos.")

    for label, value, column_name in (("RUDE", rude, "rude"), ("Carnet", carnet, "Carnet")):
        if not value:
            continue
        params = [value]
        query = f"SELECT 1 FROM alumnos WHERE {column_name} = ?"
        if current_id is not None:
            query += " AND id <> ?"
            params.append(current_id)
        duplicate = conn.execute(query, tuple(params)).fetchone()
        if duplicate:
            errors.append(f"{label} ya existe en otro alumno.")

    return errors


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
        self.cumpleanos.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.rude = QLineEdit()
        self.carnet = QLineEdit()
        self.pension = QLineEdit()
        self.pension.setValidator(QIntValidator(0, 99999, self))
        self.pension.setText("0")

        self.id_padre = QLineEdit()
        self.id_padre.setPlaceholderText("ID")
        self.id_padre.setValidator(QIntValidator(1, 999999999, self))
        self.id_padre.setMaximumWidth(100)
        self.current_padre_btn = QPushButton("Adulto Actual")
        self.current_padre_btn.clicked.connect(self._apply_current_adulto_to_padre)
        self.padre_lookup = QLineEdit()
        self.padre_lookup.setReadOnly(True)
        self.padre_lookup.setPlaceholderText("a_nombres a_paterno a_materno")
        self.id_padre.textChanged.connect(self._refresh_padre_lookup)

        self.id_madre = QLineEdit()
        self.id_madre.setPlaceholderText("ID")
        self.id_madre.setValidator(QIntValidator(1, 999999999, self))
        self.id_madre.setMaximumWidth(100)
        self.current_madre_btn = QPushButton("Adulto Actual")
        self.current_madre_btn.clicked.connect(self._apply_current_adulto_to_madre)
        self.madre_lookup = QLineEdit()
        self.madre_lookup.setReadOnly(True)
        self.madre_lookup.setPlaceholderText("a_nombres a_paterno a_materno")
        self.id_madre.textChanged.connect(self._refresh_madre_lookup)

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

        padre_row = QWidget(self)
        padre_layout = QHBoxLayout(padre_row)
        padre_layout.setContentsMargins(0, 0, 0, 0)
        padre_layout.addWidget(self.id_padre)
        padre_layout.addWidget(self.current_padre_btn)
        padre_layout.addWidget(self.padre_lookup, 1)
        form.addRow("ID Padre:", padre_row)

        madre_row = QWidget(self)
        madre_layout = QHBoxLayout(madre_row)
        madre_layout.setContentsMargins(0, 0, 0, 0)
        madre_layout.addWidget(self.id_madre)
        madre_layout.addWidget(self.current_madre_btn)
        madre_layout.addWidget(self.madre_lookup, 1)
        form.addRow("ID Madre:", madre_row)

        form.addRow("Grado:", self.grado)
        form.addRow("Pensión:", self.pension)
        layout.addLayout(form)

        self._refresh_current_adulto_buttons()
        self._refresh_padre_lookup()
        self._refresh_madre_lookup()

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _refresh_current_adulto_buttons(self):
        enabled = parientes_dialogs.current_adulto_id is not None
        self.current_padre_btn.setEnabled(enabled)
        self.current_madre_btn.setEnabled(enabled)

    def _apply_current_adulto_to_padre(self):
        current_id = parientes_dialogs.current_adulto_id
        if current_id is None:
            return
        self.id_padre.setText(str(current_id))

    def _apply_current_adulto_to_madre(self):
        current_id = parientes_dialogs.current_adulto_id
        if current_id is None:
            return
        self.id_madre.setText(str(current_id))

    def _save(self):
        nombres = self.nombres.text().strip().title()
        paterno = self.paterno.text().strip().title()
        if not nombres or not paterno:
            QMessageBox.warning(self, "Validación", "Nombres y apellido paterno son requeridos.")
            return
        cumpleanos = self.cumpleanos.date().toString("yyyy-MM-dd")
        if not self.cumpleanos.date().isValid():
            QMessageBox.warning(self, "Validación", "La fecha de cumpleaños debe tener el formato YYYY-MM-DD.")
            return

        pension_text = self.pension.text().strip()
        try:
            pension_value = int(pension_text) if pension_text else 0
        except (TypeError, ValueError):
            pension_value = 0
        pension_value = max(0, pension_value)
        self.pension.setText(str(pension_value))

        id_padre = _normalize_related_adulto_id(self.id_padre.text())
        id_madre = _normalize_related_adulto_id(self.id_madre.text())
        try:
            conn = sqlite3.connect(get_active_db_path())
            validation_errors = _validate_alumno_integrity(
                conn,
                self.rude.text().strip(),
                self.carnet.text().strip(),
                id_padre,
                id_madre,
            )
            if validation_errors:
                QMessageBox.warning(self, "Validación", "\n".join(validation_errors))
                conn.close()
                return

            columns = {
                column_row[1]
                for column_row in conn.execute("PRAGMA table_info(alumnos)").fetchall()
            }
            has_id_padre = "id_padre" in columns
            has_id_madre = "id_madre" in columns

            insert_fields = ["nombres", "paterno", "materno", "cumpleanos", "rude", "Carnet", "id_grado", "pension"]
            values = [
                nombres,
                paterno,
                self.materno.text().strip().title(),
                cumpleanos,
                self.rude.text().strip(),
                self.carnet.text().strip(),
                self.grado.currentData(),
                pension_value,
            ]
            if has_id_padre:
                insert_fields.append("id_padre")
                values.append(id_padre)
            if has_id_madre:
                insert_fields.append("id_madre")
                values.append(id_madre)

            placeholders = ", ".join("?" for _field in insert_fields)
            cur = conn.execute(
                f"INSERT INTO alumnos ({', '.join(insert_fields)}) VALUES ({placeholders})",
                tuple(values),
            )
            conn.commit()
            global current_alumno_id, current_alumno_name
            current_alumno_id = cur.lastrowid
            current_alumno_name = f"{nombres} {paterno}"
            conn.close()
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{exc}")

    @staticmethod
    def _build_adulto_lookup_name(nombres, paterno, materno):
        return " ".join(
            part.strip()
            for part in (str(nombres or ""), str(paterno or ""), str(materno or ""))
            if part and str(part).strip()
        )

    def _lookup_adulto_name(self, related_id_text):
        related_id = _normalize_related_adulto_id(related_id_text)
        if related_id is None:
            return ""
        try:
            with sqlite3.connect(get_active_db_path()) as conn:
                row = conn.execute(
                    "SELECT a_nombres, a_paterno, a_materno FROM adultos WHERE id = ?",
                    (related_id,),
                ).fetchone()
        except Exception:
            return ""

        if not row:
            return "No encontrado"
        return self._build_adulto_lookup_name(*row)

    def _refresh_padre_lookup(self):
        self.padre_lookup.setText(self._lookup_adulto_name(self.id_padre.text()))

    def _refresh_madre_lookup(self):
        self.madre_lookup.setText(self._lookup_adulto_name(self.id_madre.text()))


class EditAlumnoDialog(QDialog):
    """Edit form pre-populated with an existing alumno record."""

    def __init__(self, record_id: int, parent=None, is_admin: bool = False):
        super().__init__(parent)
        self._id = record_id
        self._is_admin = is_admin
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
        self.cumpleanos.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.rude = QLineEdit()
        self.carnet = QLineEdit()
        self.pension = QLineEdit()
        self.pension.setValidator(QIntValidator(0, 99999, self))
        self.pension.setText("0")

        self.id_padre = QLineEdit()
        self.id_padre.setPlaceholderText("ID")
        self.id_padre.setValidator(QIntValidator(1, 999999999, self))
        self.id_padre.setMaximumWidth(100)
        self.current_padre_btn = QPushButton("Adulto Actual")
        self.current_padre_btn.clicked.connect(self._apply_current_adulto_to_padre)
        self.padre_lookup = QLineEdit()
        self.padre_lookup.setReadOnly(True)
        self.padre_lookup.setPlaceholderText("a_nombres a_paterno a_materno")
        self.id_padre.textChanged.connect(self._refresh_padre_lookup)

        self.id_madre = QLineEdit()
        self.id_madre.setPlaceholderText("ID")
        self.id_madre.setValidator(QIntValidator(1, 999999999, self))
        self.id_madre.setMaximumWidth(100)
        self.current_madre_btn = QPushButton("Adulto Actual")
        self.current_madre_btn.clicked.connect(self._apply_current_adulto_to_madre)
        self.madre_lookup = QLineEdit()
        self.madre_lookup.setReadOnly(True)
        self.madre_lookup.setPlaceholderText("a_nombres a_paterno a_materno")
        self.id_madre.textChanged.connect(self._refresh_madre_lookup)

        self.grado = QComboBox()
        try:
            conn = sqlite3.connect(get_active_db_path())
            for gid, gname in conn.execute("SELECT id, grado FROM grados ORDER BY grado").fetchall():
                self.grado.addItem(gname, _normalize_grado_id(gid))
            columns = {
                column_row[1]
                for column_row in conn.execute("PRAGMA table_info(alumnos)").fetchall()
            }
            has_id_padre = "id_padre" in columns
            has_id_madre = "id_madre" in columns

            select_columns = [
                "nombres", "paterno", "materno", "cumpleanos", "rude", "Carnet", "id_grado", "pension",
            ]
            if has_id_padre:
                select_columns.append("id_padre")
            if has_id_madre:
                select_columns.append("id_madre")
            row = conn.execute(
                f"SELECT {', '.join(select_columns)} FROM alumnos WHERE id = ?", (self._id,)
            ).fetchone()
            conn.close()
        except Exception:
            row = None
            has_id_padre = False
            has_id_madre = False

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
            try:
                pension_value = int(float(row[7])) if row[7] is not None else 0
            except (TypeError, ValueError):
                pension_value = 0
            self.pension.setText(str(max(0, pension_value)))

            offset = 8
            if has_id_padre:
                self.id_padre.setText("" if row[offset] is None else str(row[offset]).strip())
                offset += 1
            if has_id_madre:
                self.id_madre.setText("" if row[offset] is None else str(row[offset]).strip())

        self._refresh_padre_lookup()
        self._refresh_madre_lookup()

        form.addRow("Nombres *:", self.nombres)
        form.addRow("Paterno *:", self.paterno)
        form.addRow("Materno:", self.materno)
        form.addRow("Cumpleaños:", self.cumpleanos)
        form.addRow("RUDE:", self.rude)
        form.addRow("Carnet:", self.carnet)

        padre_row = QWidget(self)
        padre_layout = QHBoxLayout(padre_row)
        padre_layout.setContentsMargins(0, 0, 0, 0)
        padre_layout.addWidget(self.id_padre)
        padre_layout.addWidget(self.current_padre_btn)
        padre_layout.addWidget(self.padre_lookup, 1)
        form.addRow("ID Padre:", padre_row)

        madre_row = QWidget(self)
        madre_layout = QHBoxLayout(madre_row)
        madre_layout.setContentsMargins(0, 0, 0, 0)
        madre_layout.addWidget(self.id_madre)
        madre_layout.addWidget(self.current_madre_btn)
        madre_layout.addWidget(self.madre_lookup, 1)
        form.addRow("ID Madre:", madre_row)

        form.addRow("Grado:", self.grado)
        form.addRow("Pensión:", self.pension)
        layout.addLayout(form)

        self._refresh_current_adulto_buttons()

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        self.delete_btn = buttons.addButton("Borrar", QDialogButtonBox.ActionRole)
        self.delete_btn.setEnabled(self._is_admin)
        if not self._is_admin:
            self.delete_btn.setToolTip("Solo administrador puede borrar registros.")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        self.delete_btn.clicked.connect(self._delete)
        layout.addWidget(buttons)

    def _refresh_current_adulto_buttons(self):
        enabled = parientes_dialogs.current_adulto_id is not None
        self.current_padre_btn.setEnabled(enabled)
        self.current_madre_btn.setEnabled(enabled)

    def _apply_current_adulto_to_padre(self):
        current_id = parientes_dialogs.current_adulto_id
        if current_id is None:
            return
        self.id_padre.setText(str(current_id))

    def _apply_current_adulto_to_madre(self):
        current_id = parientes_dialogs.current_adulto_id
        if current_id is None:
            return
        self.id_madre.setText(str(current_id))

    def _save(self):
        nombres = self.nombres.text().strip().title()
        paterno = self.paterno.text().strip().title()
        if not nombres or not paterno:
            QMessageBox.warning(self, "Validación", "Nombres y apellido paterno son requeridos.")
            return
        cumpleanos = self.cumpleanos.date().toString("yyyy-MM-dd")
        if not self.cumpleanos.date().isValid():
            QMessageBox.warning(self, "Validación", "La fecha de cumpleaños debe tener el formato YYYY-MM-DD.")
            return

        pension_text = self.pension.text().strip()
        try:
            pension_value = int(pension_text) if pension_text else 0
        except (TypeError, ValueError):
            pension_value = 0
        pension_value = max(0, pension_value)
        self.pension.setText(str(pension_value))

        id_padre = _normalize_related_adulto_id(self.id_padre.text())
        id_madre = _normalize_related_adulto_id(self.id_madre.text())
        try:
            conn = sqlite3.connect(get_active_db_path())
            validation_errors = _validate_alumno_integrity(
                conn,
                self.rude.text().strip(),
                self.carnet.text().strip(),
                id_padre,
                id_madre,
                current_id=self._id,
            )
            if validation_errors:
                QMessageBox.warning(self, "Validación", "\n".join(validation_errors))
                conn.close()
                return

            columns = {
                column_row[1]
                for column_row in conn.execute("PRAGMA table_info(alumnos)").fetchall()
            }
            has_id_padre = "id_padre" in columns
            has_id_madre = "id_madre" in columns

            set_fields = [
                "nombres=?", "paterno=?", "materno=?", "cumpleanos=?",
                "rude=?", "Carnet=?", "id_grado=?", "pension=?",
            ]
            values = [
                nombres, paterno, self.materno.text().strip().title(),
                cumpleanos,
                self.rude.text().strip(), self.carnet.text().strip(),
                self.grado.currentData(), pension_value,
            ]
            if has_id_padre:
                set_fields.append("id_padre=?")
                values.append(id_padre)
            if has_id_madre:
                set_fields.append("id_madre=?")
                values.append(id_madre)
            values.append(self._id)

            conn.execute(
                f"UPDATE alumnos SET {', '.join(set_fields)} WHERE id=?",
                tuple(values),
            )
            conn.commit()
            global current_alumno_id, current_alumno_name
            current_alumno_id = self._id
            current_alumno_name = f"{nombres} {paterno}"
            conn.close()
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{exc}")

    @staticmethod
    def _build_adulto_lookup_name(nombres, paterno, materno):
        return " ".join(
            part.strip()
            for part in (str(nombres or ""), str(paterno or ""), str(materno or ""))
            if part and str(part).strip()
        )

    def _lookup_adulto_name(self, related_id_text):
        related_id = _normalize_related_adulto_id(related_id_text)
        if related_id is None:
            return ""
        try:
            with sqlite3.connect(get_active_db_path()) as conn:
                row = conn.execute(
                    "SELECT a_nombres, a_paterno, a_materno FROM adultos WHERE id = ?",
                    (related_id,),
                ).fetchone()
        except Exception:
            return ""

        if not row:
            return "No encontrado"
        return self._build_adulto_lookup_name(*row)

    def _refresh_padre_lookup(self):
        self.padre_lookup.setText(self._lookup_adulto_name(self.id_padre.text()))

    def _refresh_madre_lookup(self):
        self.madre_lookup.setText(self._lookup_adulto_name(self.id_madre.text()))

    def _delete(self):
        if not self._is_admin:
            QMessageBox.warning(self, "Permisos", "Solo administrador puede borrar registros.")
            return

        reply = QMessageBox.question(
            self,
            "Confirmar borrado",
            "¿Desea borrar este alumno? Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            conn = sqlite3.connect(get_active_db_path())
            conn.execute("DELETE FROM alumnos WHERE id = ?", (self._id,))
            conn.commit()
            conn.close()
            global current_alumno_id, current_alumno_name
            current_alumno_id = None
            current_alumno_name = None
            QMessageBox.information(self, "Borrado", "Alumno borrado correctamente.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo borrar:\n{exc}")


class BuscarAlumnoDialog(QDialog):
    """Search dialog for alumnos."""

    _HEADERS = ["ID", "Nombres", "Paterno", "Materno", "RUDE", "Carnet", "Grado", "Pensión"]

    def __init__(self, parent=None, is_admin: bool = False):
        super().__init__(parent)
        self._is_admin = is_admin
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
        self.show_all_checkbox.toggled.connect(self._update_title)
        self.show_all_checkbox.toggled.connect(lambda _checked: self._load(self.search_edit.text()))
        search_row.addWidget(self.show_all_checkbox)
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

        self._update_title()
        self._load("")

    def _update_title(self):
        """Update window title based on checkbox state."""
        if self.show_all_checkbox.isChecked():
            self.setWindowTitle("Alumnos - Buscar entre todos alumnos registrados")
        else:
            self.setWindowTitle("Alumnos - Buscar entre alumnos inscritos actualmente")

    def _on_single_click(self, row: int, _col: int):
        self._set_current_alumno_from_row(row)

    def _set_current_alumno_from_row(self, row: int):
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

        global current_alumno_id, current_alumno_name
        current_alumno_id = selected_id
        current_alumno_name = " ".join(part for part in (selected_nombres, selected_paterno) if part)

    def _on_double_click(self, row: int, _col: int):
        self._set_current_alumno_from_row(row)
        id_item = self.table.item(row, 0)
        if id_item is None:
            return
        dlg = EditAlumnoDialog(int(id_item.text()), self, is_admin=self._is_admin)
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
