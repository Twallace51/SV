"""WhatsApp click-to-chat dialog.

    Lists adultos that have a mobile number and lets the operator open a pre-filled
    WhatsApp chat for each selected recipient, one at a time. Opening a ``wa.me``
    link only *prepares* the message in WhatsApp; a human still presses send, so
    this stays within WhatsApp's terms of service (no automated bulk delivery).
    """

# region - imports
import logging

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QDialogButtonBox, QMessageBox, QAbstractItemView, QComboBox,
)

from modules import database
from modules.utils import build_whatsapp_url, normalize_bolivia_phone

# endregion

log = logging.getLogger("app")
log.setLevel(logging.INFO)

class EnviarWhatsAppDialog(QDialog):
    """Pick recipients from the adultos list and open one WhatsApp chat at a time."""

    _HEADERS = ["", "Nombre", "Celular"]
    _FILTER_OPTIONS = [
        ("Todos inscritos", False),
        ("Solo con cuentas pendientes", True),
    ]
    _TEMPLATES = {
        False: (
            "Hola {parent_name}        Fecha: {date}.\n"
            "Le escribimos respecto la cuenta por {student_name} ({grade}).\n"
            "Balance actual: {balance}."
        ),
        True: (
            "Hola {parent_name}        Fecha: {date}.\n"
            "Le escribimos por la deuda pendiente de {student_name} ({grade}).\n"
            "Monto pendiente: {balance}."
        ),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adultos - Enviar WhatsApp")
        self.resize(680, 540)
        layout = QVBoxLayout(self)

        # Pending row indices for the one-at-a-time flow and how many have been
        # opened so far in the current run.
        self._queue: list[int] = []
        self._sent_count = 0
        self._total_count = 0
        self._template_context = {
            "student_name": "",
            "grade": "",
            "balance": "+0",
            "alumno_id": "",
            "date": "",
        }
        self._current_filter_pending = False

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filtro:"))
        self.filter_combo = QComboBox(self)
        for label, is_pending in self._FILTER_OPTIONS:
            self.filter_combo.addItem(label, is_pending)
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.filter_combo)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        student_row = QHBoxLayout()
        student_row.addWidget(QLabel("Selecionar Alumno >"))
        self.student_combo = QComboBox(self)
        self.student_combo.currentIndexChanged.connect(self._on_student_changed)
        student_row.addWidget(self.student_combo)
        self.reload_student_btn = QPushButton("Recargar", self)
        self.reload_student_btn.clicked.connect(self._load_students)
        student_row.addWidget(self.reload_student_btn)
        layout.addLayout(student_row)

        layout.addWidget(QLabel("Mensaje basico - puede actualizarlo aqui para todos, y luego individualmente en Whatsapp"))
        self.message_edit = QPlainTextEdit()
        self.message_edit.setPlaceholderText("Escriba el mensaje a enviar…")
        self.message_edit.setFixedHeight(90)
        self.message_edit.setPlainText(self._TEMPLATES[False])
        layout.addWidget(self.message_edit)

        select_row = QHBoxLayout()
        self.select_all_btn = QPushButton("Seleccionar todos")
        self.select_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        self.select_none_btn = QPushButton("Quitar selección")
        self.select_none_btn.clicked.connect(lambda: self._set_all_checked(False))
        select_row.addWidget(self.select_all_btn)
        select_row.addWidget(self.select_none_btn)
        select_row.addStretch()
        self.count_label = QLabel("")
        select_row.addWidget(self.count_label)
        layout.addLayout(select_row)

        self.table = QTableWidget(0, len(self._HEADERS))
        self.table.setHorizontalHeaderLabels(self._HEADERS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        self.next_btn = buttons.addButton("Abrir Whatsapp  >", QDialogButtonBox.ActionRole)
        self.next_btn.clicked.connect(self._open_next)
        self.restart_btn = buttons.addButton("Reiniciar", QDialogButtonBox.ResetRole)
        self.restart_btn.clicked.connect(self._reset_run)
        self.restart_btn.setEnabled(False)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_students()

    def _selected_filter_pending(self) -> bool:
        value = self.filter_combo.currentData()
        return bool(value)

    def _default_template_for_filter(self, only_pending: bool) -> str:
        return self._TEMPLATES[only_pending]

    def _on_filter_changed(self, *_args):
        only_pending = self._selected_filter_pending()
        self._current_filter_pending = only_pending
        self.message_edit.setPlainText(self._default_template_for_filter(only_pending))
        self._load_students()

    def _load_students(self):
        rows = database.list_alumnos_para_whatsapp(self._selected_filter_pending())
        self.student_combo.blockSignals(True)
        self.student_combo.clear()
        for alumno_id, alumno_name, grade in rows:
            grade_text = str(grade or "").strip()
            label = f"{alumno_name} ({grade_text})" if grade_text else str(alumno_name)
            self.student_combo.addItem(label, int(alumno_id))
        self.student_combo.blockSignals(False)

        if self.student_combo.count() == 0:
            self._load_recipients([])
            if self._selected_filter_pending():
                self.status_label.setText("No hay alumnos con cuentas pendientes.")
            else:
                self.status_label.setText("No hay alumnos disponibles.")
            return

        self.student_combo.setCurrentIndex(0)
        self._on_student_changed(0)

    def _on_student_changed(self, index: int):
        if index < 0:
            self._load_recipients([])
            self.status_label.setText("Seleccione un alumno.")
            return

        alumno_id = self.student_combo.itemData(index)
        if alumno_id is None:
            self._load_recipients([])
            self.status_label.setText("Seleccione un alumno.")
            return

        self._template_context, rows = database.get_whatsapp_targets_for_alumno(int(alumno_id))
        self._load_recipients(rows)
        if not rows:
            self.status_label.setText("El alumno seleccionado no tiene padres vinculados con celular.")
        else:
            self.status_label.setText("")

    def _load_recipients(self, rows):
        recipients = []
        for name, phone in rows:
            normalized = normalize_bolivia_phone(phone)
            if normalized is not None:
                recipients.append((name, str(phone).strip(), normalized))

        self.table.blockSignals(True)
        self.table.setRowCount(len(recipients))
        for r, (name, phone_display, _normalized) in enumerate(recipients):
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Checked)
            check_item.setData(Qt.UserRole, phone_display)
            check_item.setData(Qt.UserRole + 1, name)
            self.table.setItem(r, 0, check_item)
            self.table.setItem(r, 1, QTableWidgetItem(name))
            self.table.setItem(r, 2, QTableWidgetItem(phone_display))
        self.table.blockSignals(False)
        self._reset_run()

    def _set_all_checked(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item is not None:
                item.setCheckState(state)
        self.table.blockSignals(False)
        self._reset_run()

    def _on_item_changed(self, *_args):
        # Changing the selection invalidates an in-progress run.
        self._reset_run()

    def _checked_rows(self) -> list[int]:
        rows = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item is not None and item.checkState() == Qt.Checked:
                rows.append(r)
        return rows

    def _update_count(self, *_args):
        self.count_label.setText(f"Seleccionados: {len(self._checked_rows())}")

    def _render_template_message(self, parent_name: str) -> str:
        template = self.message_edit.toPlainText().strip() or self._DEFAULT_TEMPLATE
        values = {
            "parent_name": parent_name,
            "student_name": self._template_context.get("student_name", ""),
            "grade": self._template_context.get("grade", ""),
            "balance": self._template_context.get("balance", "+0"),
            "alumno_id": self._template_context.get("alumno_id", ""),
            "date": self._template_context.get("date", ""),
        }
        message = template
        for key, value in values.items():
            message = message.replace("{" + key + "}", str(value))
        return message

    def _reset_run(self, *_args):
        self._queue = []
        self._sent_count = 0
        self._total_count = 0
        self.table.clearSelection()
        self.status_label.setText("")
        self.next_btn.setText("Abrir Whatsapp  >")
        self.restart_btn.setEnabled(False)
        self._update_count()

    def _open_next(self):
        # Start a new run on the first click (snapshot the current selection).
        if not self._queue and self._sent_count == 0:
            self._queue = self._checked_rows()
            self._total_count = len(self._queue)
            if not self._queue:
                QMessageBox.information(self, "WhatsApp", "Seleccione al menos un destinatario.")
                return
            self.restart_btn.setEnabled(True)

        if not self._queue:
            QMessageBox.information(
                self,
                "WhatsApp",
                f"No quedan destinatarios. Se abrieron {self._sent_count} chat(s).",
            )
            self._reset_run()
            return

        row = self._queue.pop(0)
        check_item = self.table.item(row, 0)
        phone = check_item.data(Qt.UserRole) if check_item is not None else None
        name = check_item.data(Qt.UserRole + 1) if check_item is not None else ""
        message = self._render_template_message(str(name or ""))

        url = build_whatsapp_url(phone, message)
        if url is None or not QDesktopServices.openUrl(QUrl(url)):
            log.warning("WhatsApp: no se pudo abrir el chat para %s (%s).", name, phone)
            QMessageBox.warning(self, "WhatsApp", f"No se pudo abrir el chat para {name}.")
        else:
            self._sent_count += 1
            self.table.selectRow(row)
            log.info("WhatsApp: chat abierto para %s (%s).", name, phone)

        remaining = len(self._queue)
        self.status_label.setText(
            f"Abierto {self._sent_count} de {self._total_count}: {name}. "
            f"Presione Enviar en WhatsApp."
            + (f" Quedan {remaining}." if remaining else " Completado.")
        )
        if remaining:
            self.next_btn.setText(f"Abrir Whatsapp  > ({remaining})")
        else:
            self.next_btn.setText("Finalizado")
            self.next_btn.setEnabled(False)
