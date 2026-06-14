"""Alumnos dialogs: Nuevo, Editar, Buscar."""

# region - imports

import logging

from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit,
    QVBoxLayout, QFormLayout, QMessageBox, QHBoxLayout,
    QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QDateEdit, QComboBox, QHeaderView,
    QCheckBox, QWidget, QAbstractSpinBox, QPushButton,
)
from PySide6.QtCore import QDate
from PySide6.QtGui import QIntValidator

import database
from dialogs.widgets import NumericTableWidgetItem, SORT_ROLE
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


class _AlumnoFormDialog(QDialog):
    """Shared widgets and behaviour for the Nuevo/Editar alumno forms."""

    # Label prefix for the "Adulto Actual" buttons and whether those buttons
    # are placed after the lookup field (last widget in their row).
    _ADULTO_BUTTON_PREFIX = "Adulto Actual"
    _ADULTO_BUTTON_LAST = False

    # --- Widget construction ---------------------------------------------

    def _create_common_fields(self):
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
        self.current_padre_btn = QPushButton(self._ADULTO_BUTTON_PREFIX)
        self.current_padre_btn.clicked.connect(self._apply_current_adulto_to_padre)
        self.padre_lookup = QLineEdit()
        self.padre_lookup.setReadOnly(True)
        self.padre_lookup.setPlaceholderText("a_nombres a_paterno a_materno")
        self.id_padre.textChanged.connect(self._refresh_padre_lookup)

        self.id_madre = QLineEdit()
        self.id_madre.setPlaceholderText("ID")
        self.id_madre.setValidator(QIntValidator(1, 999999999, self))
        self.id_madre.setMaximumWidth(100)
        self.current_madre_btn = QPushButton(self._ADULTO_BUTTON_PREFIX)
        self.current_madre_btn.clicked.connect(self._apply_current_adulto_to_madre)
        self.madre_lookup = QLineEdit()
        self.madre_lookup.setReadOnly(True)
        self.madre_lookup.setPlaceholderText("a_nombres a_paterno a_materno")
        self.id_madre.textChanged.connect(self._refresh_madre_lookup)

        self.grado = QComboBox()

    def _populate_grado_combo(self, include_sin_grado: bool):
        if include_sin_grado:
            self.grado.addItem("Sin grado", 0)
        for gid, gname in database.list_grados():
            self.grado.addItem(gname, _normalize_grado_id(gid))

    def _add_form_rows(self, form: QFormLayout):
        form.addRow("Nombres *:", self.nombres)
        form.addRow("Paterno *:", self.paterno)
        form.addRow("Materno:", self.materno)
        form.addRow("Cumpleaños:", self.cumpleanos)
        form.addRow("RUDE:", self.rude)
        form.addRow("Carnet:", self.carnet)

        for label, id_field, button, lookup in (
            ("ID Padre:", self.id_padre, self.current_padre_btn, self.padre_lookup),
            ("ID Madre:", self.id_madre, self.current_madre_btn, self.madre_lookup),
        ):
            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(id_field)
            if self._ADULTO_BUTTON_LAST:
                row_layout.addWidget(lookup, 1)
                row_layout.addWidget(button)
            else:
                row_layout.addWidget(button)
                row_layout.addWidget(lookup, 1)
            form.addRow(label, row)

        form.addRow("Grado:", self.grado)
        form.addRow("Pensión:", self.pension)

    # --- Shared "Adulto Actual" helpers ----------------------------------

    def _refresh_current_adulto_buttons(self):
        parts = []
        if parientes_dialogs.current_adulto_id is not None:
            parts.append(str(parientes_dialogs.current_adulto_id))
        if parientes_dialogs.current_adulto_name:
            parts.append(str(parientes_dialogs.current_adulto_name))
        text = f"{self._ADULTO_BUTTON_PREFIX}: {' - '.join(parts)}" if parts else f"{self._ADULTO_BUTTON_PREFIX}: -"
        self.current_padre_btn.setText(text)
        self.current_madre_btn.setText(text)

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

    # --- Shared adulto lookup helpers ------------------------------------

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
        row = database.fetch_adulto_lookup_name(related_id)
        if not row:
            return "No encontrado"
        return self._build_adulto_lookup_name(*row)

    def _refresh_padre_lookup(self):
        self.padre_lookup.setText(self._lookup_adulto_name(self.id_padre.text()))

    def _refresh_madre_lookup(self):
        self.madre_lookup.setText(self._lookup_adulto_name(self.id_madre.text()))

    # --- Shared validation / persistence ---------------------------------

    def _normalized_form(self):
        """Validate the form and return ``(data, display_name)`` or None."""
        nombres = self.nombres.text().strip().title()
        paterno = self.paterno.text().strip().title()
        if not nombres or not paterno:
            QMessageBox.warning(self, "Validación", "Nombres y apellido paterno son requeridos.")
            return None
        cumpleanos = self.cumpleanos.date().toString("yyyy-MM-dd")
        if not self.cumpleanos.date().isValid():
            QMessageBox.warning(self, "Validación", "La fecha de cumpleaños debe tener el formato YYYY-MM-DD.")
            return None

        pension_text = self.pension.text().strip()
        try:
            pension_value = int(pension_text) if pension_text else 0
        except (TypeError, ValueError):
            pension_value = 0
        pension_value = max(0, pension_value)
        self.pension.setText(str(pension_value))

        data = {
            "nombres": nombres,
            "paterno": paterno,
            "materno": self.materno.text().strip().title(),
            "cumpleanos": cumpleanos,
            "rude": self.rude.text().strip(),
            "Carnet": self.carnet.text().strip(),
            "id_grado": self.grado.currentData(),
            "pension": pension_value,
            "id_padre": _normalize_related_adulto_id(self.id_padre.text()),
            "id_madre": _normalize_related_adulto_id(self.id_madre.text()),
        }
        return data, f"{nombres} {paterno}"


class NuevoAlumnoDialog(_AlumnoFormDialog):
    """Form dialog to insert a new alumno into SV.db."""

    _ADULTO_BUTTON_PREFIX = "<< Adulto Actual"
    _ADULTO_BUTTON_LAST = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Alumnos - Nuevo")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._create_common_fields()
        self._populate_grado_combo(include_sin_grado=True)
        self.grado.setCurrentIndex(0)
        self._add_form_rows(form)
        layout.addLayout(form)

        self._refresh_current_adulto_buttons()
        self._refresh_padre_lookup()
        self._refresh_madre_lookup()

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        prepared = self._normalized_form()
        if prepared is None:
            return
        data, display_name = prepared
        try:
            errors = database.validate_alumno(
                data["rude"], data["Carnet"], data["id_padre"], data["id_madre"],
            )
            if errors:
                QMessageBox.warning(self, "Validación", "\n".join(errors))
                return

            new_id = database.insert_alumno(data)
            global current_alumno_id, current_alumno_name
            current_alumno_id = new_id
            current_alumno_name = display_name
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{exc}")


class EditAlumnoDialog(_AlumnoFormDialog):
    """Edit form pre-populated with an existing alumno record."""

    _ADULTO_BUTTON_PREFIX = "<< Adulto Actual"
    _ADULTO_BUTTON_LAST = True

    def __init__(self, record_id: int, parent=None, is_admin: bool = False):
        super().__init__(parent)
        self._id = record_id
        self._is_admin = is_admin
        self.setWindowTitle("Alumnos - Editar")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._create_common_fields()
        self._populate_grado_combo(include_sin_grado=False)

        record = database.fetch_alumno(self._id)
        if record:
            self.nombres.setText(record.get("nombres") or "")
            self.paterno.setText(record.get("paterno") or "")
            self.materno.setText(record.get("materno") or "")
            d = QDate.fromString(record.get("cumpleanos") or "", "yyyy-MM-dd")
            if d.isValid():
                self.cumpleanos.setDate(d)
            self.rude.setText(record.get("rude") or "")
            self.carnet.setText(record.get("Carnet") or "")
            grado_id = _normalize_grado_id(record.get("id_grado"))
            idx = self.grado.findData(grado_id)
            if idx >= 0:
                self.grado.setCurrentIndex(idx)
            try:
                pension_raw = record.get("pension")
                pension_value = int(float(pension_raw)) if pension_raw is not None else 0
            except (TypeError, ValueError):
                pension_value = 0
            self.pension.setText(str(max(0, pension_value)))

            if "id_padre" in record:
                value = record["id_padre"]
                self.id_padre.setText("" if value is None else str(value).strip())
            if "id_madre" in record:
                value = record["id_madre"]
                self.id_madre.setText("" if value is None else str(value).strip())

        self._refresh_padre_lookup()
        self._refresh_madre_lookup()

        self._add_form_rows(form)
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

    def _save(self):
        prepared = self._normalized_form()
        if prepared is None:
            return
        data, display_name = prepared
        try:
            errors = database.validate_alumno(
                data["rude"], data["Carnet"], data["id_padre"], data["id_madre"],
                current_id=self._id,
            )
            if errors:
                QMessageBox.warning(self, "Validación", "\n".join(errors))
                return

            database.update_alumno(self._id, data)
            global current_alumno_id, current_alumno_name
            current_alumno_id = self._id
            current_alumno_name = display_name
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
            "¿Desea borrar este alumno? Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            database.delete_alumno(self._id)
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
        rows = database.search_alumnos(text, only_inscritos=not self.show_all_checkbox.isChecked())
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
                    item.setData(SORT_ROLE, 0 if grado_sort_key is None else grado_sort_key)
                self.table.setItem(r, c, item)
        self.table.setSortingEnabled(True)
