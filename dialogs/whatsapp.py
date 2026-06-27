"""WhatsApp click-to-chat dialog.

Lists adultos that have a mobile number and lets the operator open a pre-filled
WhatsApp chat for each selected recipient, one at a time. Opening a ``wa.me``
link only *prepares* the message in WhatsApp; a human still presses send, so
this stays within WhatsApp's terms of service (no automated bulk delivery).
"""

import logging

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QDialogButtonBox, QMessageBox, QAbstractItemView,
)

from modules import database
from modules.utils import build_whatsapp_url, normalize_bolivia_phone

log = logging.getLogger("app")


class EnviarWhatsAppDialog(QDialog):
    """Pick recipients from the adultos list and open one WhatsApp chat at a time."""

    _HEADERS = ["", "Nombre", "Celular"]

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

        layout.addWidget(QLabel("Mensaje (se rellena en cada chat; usted presiona Enviar):"))
        self.message_edit = QPlainTextEdit()
        self.message_edit.setPlaceholderText("Escriba el mensaje a enviar…")
        self.message_edit.setFixedHeight(90)
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
        self.next_btn = buttons.addButton("Abrir siguiente chat", QDialogButtonBox.ActionRole)
        self.next_btn.clicked.connect(self._open_next)
        self.restart_btn = buttons.addButton("Reiniciar", QDialogButtonBox.ResetRole)
        self.restart_btn.clicked.connect(self._reset_run)
        self.restart_btn.setEnabled(False)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load()

    def _load(self):
        rows = database.list_adultos_con_celular()
        recipients = []
        for adulto_id, nombres, paterno, materno, cell1, cell2 in rows:
            name = " ".join(
                part for part in (
                    str(paterno or "").strip(),
                    str(nombres or "").strip(),
                    str(materno or "").strip(),
                ) if part
            )
            for phone in (cell1, cell2):
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
            self.table.setItem(r, 0, check_item)
            self.table.setItem(r, 1, QTableWidgetItem(name))
            self.table.setItem(r, 2, QTableWidgetItem(phone_display))
        self.table.blockSignals(False)
        self._update_count()

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

    def _reset_run(self, *_args):
        self._queue = []
        self._sent_count = 0
        self._total_count = 0
        self.table.clearSelection()
        self.status_label.setText("")
        self.next_btn.setText("Abrir siguiente chat")
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

        message = self.message_edit.toPlainText().strip()
        row = self._queue.pop(0)
        check_item = self.table.item(row, 0)
        phone = check_item.data(Qt.UserRole) if check_item is not None else None
        name_item = self.table.item(row, 1)
        name = name_item.text() if name_item is not None else ""

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
            self.next_btn.setText(f"Abrir siguiente chat ({remaining})")
        else:
            self.next_btn.setText("Finalizado")
            self.next_btn.setEnabled(False)
