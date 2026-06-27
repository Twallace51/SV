"""Cuentas dialogs: Nuevo, Editar, Buscar.

``NuevoCuentaDialog`` and ``EditCuentaDialog`` share almost all of their form
behaviour, so the common pieces live in the private ``_CuentaFormDialog`` base
class. ``BuscarCuentaDialog`` is the search/list view. All database access is
delegated to :mod:`database`.
"""

# region - imports

import logging

from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit,
    QVBoxLayout, QFormLayout, QMessageBox, QHBoxLayout,
    QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QDateEdit, QSpinBox, QHeaderView, QComboBox,
    QAbstractSpinBox, QPushButton,
)
from PySide6.QtCore import QDate, Qt

from modules import config
from modules import database
from dialogs.widgets import NumericTableWidgetItem
from dialogs import alumnos as alumnos_dialogs
from dialogs import parientes as parientes_dialogs

# endregion

log = logging.getLogger("app")
#logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)

# Current-record global – updated on every successful INSERT/UPDATE;
# set to None when the corresponding record is deleted.
current_cta_id: int | None = None


class _CuentaFormDialog(QDialog):
    """Shared form behaviour for creating and editing a cuenta."""

    DEBITO_ACLARACIONES = config.DEBITO_ACLARACIONES
    CREDITO_ACLARACIONES = config.CREDITO_ACLARACIONES

    # --- field construction ------------------------------------------------

    def _create_fields(self):
        """Build every form widget and wire up its signals."""
        self.id_alumno = QLineEdit()
        self.id_alumno.setPlaceholderText("Ingrese ID de alumno")
        self.id_alumno.textChanged.connect(self._sync_alumno_nombre)
        self.current_alumno_btn = QPushButton("Alumno Actual")
        self.current_alumno_btn.clicked.connect(self._apply_current_alumno)
        self._alumno_row = QHBoxLayout()
        self._alumno_row.setContentsMargins(0, 0, 0, 0)
        self._alumno_row.addWidget(self.id_alumno)
        self._alumno_row.addWidget(self.current_alumno_btn)
        self.alumno = QLabel("-")

        self.id_creditor = QLineEdit()
        self.id_creditor.setPlaceholderText("Ingrese ID de creditor")
        self.id_creditor.textChanged.connect(self._sync_creditor_nombre)
        self.id_creditor.textChanged.connect(self._sync_amount_fields)
        self.current_adulto_btn = QPushButton("Adulto Actual")
        self.current_adulto_btn.clicked.connect(self._apply_current_adulto)
        self._creditor_row = QHBoxLayout()
        self._creditor_row.setContentsMargins(0, 0, 0, 0)
        self._creditor_row.addWidget(self.id_creditor)
        self._creditor_row.addWidget(self.current_adulto_btn)
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
        self.aclaracion_select.currentTextChanged.connect(self._apply_aclaracion_option)
        self.debito.valueChanged.connect(self._update_aclaracion_options)
        self.credito.valueChanged.connect(self._update_aclaracion_options)
        self._update_aclaracion_options()
        self._aclaracion_row = QHBoxLayout()
        self._aclaracion_row.addWidget(self.aclaracion)
        self._aclaracion_row.addWidget(self.aclaracion_select)

        self.fecha = QDateEdit()
        self.fecha.setCalendarPopup(True)
        self.fecha.setDisplayFormat("yyyy-MM-dd")
        self.fecha.setDate(QDate.currentDate())
        self.fecha.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.factura = QLineEdit()

    def _add_form_rows(self, form: QFormLayout):
        """Append all the cuenta fields to the form layout, in order."""
        form.addRow("ID Alumno *:", self._alumno_row)
        form.addRow("Alumno:", self.alumno)
        form.addRow("ID Creditor:", self._creditor_row)
        form.addRow("Creditor:", self.creditor)
        form.addRow("Débito:", self.debito)
        form.addRow("Crédito:", self.credito)
        form.addRow("Aclaración:", self._aclaracion_row)
        form.addRow("Fecha:", self.fecha)
        form.addRow("Numero Factura:", self.factura)

    def _apply_mode_visibility(self, form: QFormLayout):
        """Hide the rows that do not apply to a credito/debito-only form."""
        if self._mode == "credito":
            form.setRowVisible(self.debito, False)
        elif self._mode == "debito":
            form.setRowVisible(self._creditor_row, False)
            form.setRowVisible(self.creditor, False)
            form.setRowVisible(self.credito, False)
            form.setRowVisible(self.factura, False)

    def _build_buttons(self, layout: QVBoxLayout):
        """Create the Save/Cancel button box and attach it to ``layout``."""
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        return buttons

    # --- current-record buttons -------------------------------------------

    def _refresh_current_id_buttons(self):
        alumno_parts = []
        if alumnos_dialogs.current_alumno_id is not None:
            alumno_parts.append(str(alumnos_dialogs.current_alumno_id))
        if alumnos_dialogs.current_alumno_name:
            alumno_parts.append(str(alumnos_dialogs.current_alumno_name))
        self.current_alumno_btn.setText(
            f"Alumno Actual: {' - '.join(alumno_parts)}" if alumno_parts else "Alumno Actual: -"
        )

        adulto_parts = []
        if parientes_dialogs.current_adulto_id is not None:
            adulto_parts.append(str(parientes_dialogs.current_adulto_id))
        if parientes_dialogs.current_adulto_name:
            adulto_parts.append(str(parientes_dialogs.current_adulto_name))
        self.current_adulto_btn.setText(
            f"Adulto Actual: {' - '.join(adulto_parts)}" if adulto_parts else "Adulto Actual: -"
        )

        self.current_alumno_btn.setEnabled(alumnos_dialogs.current_alumno_id is not None)
        self.current_adulto_btn.setEnabled(parientes_dialogs.current_adulto_id is not None)

    def _apply_current_alumno(self):
        current_id = alumnos_dialogs.current_alumno_id
        if current_id is None:
            return
        self.id_alumno.setText(str(current_id))

    def _apply_current_adulto(self):
        current_id = parientes_dialogs.current_adulto_id
        if current_id is None:
            return
        self.id_creditor.setText(str(current_id))

    # --- name lookups ------------------------------------------------------

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

        row = database.fetch_alumno_name_pair(alumno_id)
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

        row = database.fetch_adulto_name_pair(creditor_id)
        self.creditor.setText(f"{row[0]} {row[1]}" if row else "No encontrado")

    # --- debit/credit interaction -----------------------------------------

    def _sync_amount_fields(self):
        debito_has_value = self.debito.value() > 0
        credito_has_value = self.credito.value() > 0
        creditor_has_value = bool(self.id_creditor.text().strip())

        self.factura.setEnabled(credito_has_value)
        id_creditor_enabled = not debito_has_value
        self.id_creditor.setEnabled(id_creditor_enabled)
        self.current_adulto_btn.setEnabled(
            id_creditor_enabled and parientes_dialogs.current_adulto_id is not None
        )

        if not debito_has_value and not credito_has_value:
            self.debito.setEnabled(not creditor_has_value)
            self.credito.setEnabled(True)
            return

        self.credito.setEnabled(not debito_has_value)
        debito_locked_by_creditor = creditor_has_value and not debito_has_value
        self.debito.setEnabled((not credito_has_value) and (not debito_locked_by_creditor))

    def _update_aclaracion_options(self):
        if self.credito.value() > 0:
            options = self.CREDITO_ACLARACIONES
        else:
            options = self.DEBITO_ACLARACIONES

        current_items = [
            self.aclaracion_select.itemText(i)
            for i in range(self.aclaracion_select.count())
        ]
        if current_items == options:
            return

        self.aclaracion_select.blockSignals(True)
        self.aclaracion_select.clear()
        self.aclaracion_select.addItems(options)
        self.aclaracion_select.setCurrentIndex(-1)
        self.aclaracion_select.blockSignals(False)

    def _apply_aclaracion_option(self, option: str):
        current = self.aclaracion.text().strip()
        preset_values = set(self.DEBITO_ACLARACIONES) | set(self.CREDITO_ACLARACIONES)
        if option and (not current or current in preset_values):
            self.aclaracion.setText(option)

    # --- validation --------------------------------------------------------

    def _collect_form_values(self):
        """Validate the form and return the column values tuple, or None.

        On any validation failure a warning is shown and None is returned.
        """
        raw_id = self.id_alumno.text().strip()
        if not raw_id:
            QMessageBox.warning(self, "Validación", "ID Alumno es requerido.")
            return None
        try:
            alumno_id = int(raw_id)
        except ValueError:
            QMessageBox.warning(self, "Validación", "ID Alumno debe ser un número entero.")
            return None

        if self.alumno.text() in {"No encontrado", "ID inválido", "-"}:
            QMessageBox.warning(self, "Validación", "El ID Alumno no existe.")
            return None

        debito = self.debito.value()
        credito = self.credito.value()
        if (debito == 0 and credito == 0) or (debito > 0 and credito > 0):
            QMessageBox.warning(self, "Validación", "Debe ingresar solo Débito o solo Crédito (uno es obligatorio).")
            return None

        raw_creditor = self.id_creditor.text().strip()
        creditor_id: int | None = None
        if raw_creditor:
            try:
                creditor_id = int(raw_creditor)
            except ValueError:
                QMessageBox.warning(self, "Validación", "ID Creditor debe ser un número entero.")
                return None
            if self.creditor.text() in {"No encontrado", "ID inválido"}:
                QMessageBox.warning(self, "Validación", "El ID Creditor no existe.")
                return None

        return (
            alumno_id, creditor_id, debito, credito,
            self.aclaracion.text().strip(),
            self.fecha.date().toString("yyyy-MM-dd"),
            self.factura.text().strip(),
        )


class NuevoCuentaDialog(_CuentaFormDialog):
    """Form dialog to insert a new cuenta into SV.db."""

    def __init__(self, parent=None, mode: str | None = None):
        super().__init__(parent)
        self._mode = mode
        titles = {
            "credito": "Cuentas - Nuevo Crédito",
            "debito": "Cuentas - Nuevo Débito",
        }
        self.setWindowTitle(titles.get(mode, "Cuentas - Nuevo"))
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._create_fields()
        self._add_form_rows(form)
        layout.addLayout(form)

        self._apply_mode_visibility(form)
        if self._mode == "credito":
            self.aclaracion_select.blockSignals(True)
            self.aclaracion_select.clear()
            self.aclaracion_select.addItems(self.CREDITO_ACLARACIONES)
            self.aclaracion_select.setCurrentIndex(-1)
            self.aclaracion_select.blockSignals(False)

        self._refresh_current_id_buttons()
        self._sync_alumno_nombre()
        self._sync_creditor_nombre()
        self._sync_amount_fields()

        self._build_buttons(layout)

    def _save(self):
        values = self._collect_form_values()
        if values is None:
            return
        try:
            new_id = database.insert_cuenta(values)
            global current_cta_id
            current_cta_id = new_id
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{exc}")


class EditCuentaDialog(_CuentaFormDialog):
    """Edit form pre-populated with an existing cuenta record."""

    def __init__(self, record_id: int, parent=None, is_admin: bool = False, mode: str | None = None):
        super().__init__(parent)
        self._id = record_id
        self._is_admin = is_admin
        self._mode = mode
        self.setWindowTitle("Cuentas - Editar")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._create_fields()

        row = database.fetch_cuenta(self._id)
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
            self._update_aclaracion_options()
            aclaracion_idx = self.aclaracion_select.findText(self.aclaracion.text())
            if aclaracion_idx >= 0:
                self.aclaracion_select.setCurrentIndex(aclaracion_idx)

        if self._mode is None:
            self._mode = "credito" if self.credito.value() > 0 else "debito"
        titles = {
            "credito": "Cuentas - Editar Crédito",
            "debito": "Cuentas - Editar Débito",
        }
        self.setWindowTitle(titles.get(self._mode, "Cuentas - Editar"))

        self._add_form_rows(form)
        layout.addLayout(form)
        self._apply_mode_visibility(form)

        self._refresh_current_id_buttons()
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

    def _save(self):
        values = self._collect_form_values()
        if values is None:
            return
        try:
            database.update_cuenta(self._id, values)
            global current_cta_id
            current_cta_id = self._id
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
            database.delete_cuenta(self._id)
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
        self.resize(1200, 650)
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
        self.current_creditor_btn = QPushButton()
        self.current_creditor_btn.clicked.connect(self._apply_current_creditor_filter)
        creditor_search_row.addWidget(self.current_creditor_btn)
        layout.addLayout(creditor_search_row)

        self.table = QTableWidget(0, len(self._HEADERS))
        self.table.setHorizontalHeaderLabels(self._HEADERS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(1, 220)  # Alumno
        self.table.setColumnWidth(3, 220)  # Creditor
        self.table.setColumnWidth(6, 200)  # Aclaración
        self.table.setSortingEnabled(True)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
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
        self._update_current_from_row(row)
        cuenta_id = alumno_id_item.data(Qt.UserRole)
        if cuenta_id is None:
            return
        dlg = EditCuentaDialog(int(cuenta_id), self, is_admin=self._is_admin)
        if dlg.exec() == QDialog.Accepted:
            self._load()
            self._refresh_current_alumno_label()
            self._refresh_current_creditor_label()

    def _on_selection_changed(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        self._update_current_from_row(rows[0].row())
        self._refresh_current_alumno_label()
        self._refresh_current_creditor_label()

    def _update_current_from_row(self, row: int):
        """Update the current alumno/adulto globals from the selected ctas row."""
        alumno_id_item = self.table.item(row, 0)
        alumno_name_item = self.table.item(row, 1)
        creditor_id_item = self.table.item(row, 2)
        creditor_name_item = self.table.item(row, 3)

        if alumno_id_item is not None:
            alumno_text = alumno_id_item.text().strip()
            if alumno_text:
                try:
                    alumnos_dialogs.current_alumno_id = int(alumno_text)
                except ValueError:
                    alumnos_dialogs.current_alumno_id = None
                alumnos_dialogs.current_alumno_name = (
                    alumno_name_item.text().strip() if alumno_name_item is not None else None
                ) or None

        if creditor_id_item is not None:
            creditor_text = creditor_id_item.text().strip()
            if creditor_text:
                try:
                    parientes_dialogs.current_adulto_id = int(creditor_text)
                except ValueError:
                    parientes_dialogs.current_adulto_id = None
                parientes_dialogs.current_adulto_name = (
                    creditor_name_item.text().strip() if creditor_name_item is not None else None
                ) or None

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
        self.current_creditor_btn.setText(
            f"Creditor Actual: {' - '.join(parts)}" if parts else "Creditor Actual: -"
        )

    def _load(self, _text: str = ""):
        alumno_search = self.search_edit.text().strip()
        creditor_search = self.search_creditor_edit.text().strip()
        rows = database.search_cuentas(alumno_search, creditor_search)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            cuenta_id = row[0]
            for c, val in enumerate(row[1:]):
                if c in (4, 5) and (val is None or val == 0 or str(val).strip() == "0"):
                    text = ""
                else:
                    text = "" if val is None else str(val)
                item = NumericTableWidgetItem(text) if c == 0 else QTableWidgetItem(text)
                if c == 0:
                    item.setData(Qt.UserRole, cuenta_id)
                self.table.setItem(r, c, item)
        self.table.setSortingEnabled(True)
