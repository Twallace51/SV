"""Bulk WhatsApp click-to-chat dialog.

Lists adultos that have a mobile number and lets the operator open a pre-filled
WhatsApp chat for each selected recipient. Opening a ``wa.me`` link only
*prepares* the message in WhatsApp; a human still presses send, so this stays
within WhatsApp's terms of service (no automated bulk delivery).
"""

import logging

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QDialogButtonBox, QMessageBox, QAbstractItemView,
)

import database
from utils import build_whatsapp_url, normalize_bolivia_phone

log = logging.getLogger("app")

# Opening more chats than this at once is almost always a mistake (it spawns a
# browser tab/WhatsApp window per recipient), so confirm before proceeding.
_CONFIRM_THRESHOLD = 10


class EnviarWhatsAppDialog(QDialog):
    """Pick recipients from the adultos list and open a WhatsApp chat for each."""

    _HEADERS = ["", "Nombre", "Celular"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adultos - Enviar WhatsApp")
        self.resize(680, 520)
        layout = QVBoxLayout(self)

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
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.itemChanged.connect(self._update_count)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        self.send_btn = buttons.addButton("Abrir chats", QDialogButtonBox.AcceptRole)
        self.send_btn.clicked.connect(self._open_chats)
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
        self._update_count()

    def _checked_phones(self) -> list[str]:
        phones = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item is not None and item.checkState() == Qt.Checked:
                phones.append(item.data(Qt.UserRole))
        return phones

    def _update_count(self, *_args):
        self.count_label.setText(f"Seleccionados: {len(self._checked_phones())}")

    def _open_chats(self):
        message = self.message_edit.toPlainText().strip()
        phones = self._checked_phones()
        if not phones:
            QMessageBox.information(self, "WhatsApp", "Seleccione al menos un destinatario.")
            return

        if len(phones) > _CONFIRM_THRESHOLD:
            reply = QMessageBox.question(
                self,
                "WhatsApp",
                f"Se abrirán {len(phones)} chats de WhatsApp, uno por destinatario.\n"
                "Deberá presionar Enviar en cada uno. ¿Desea continuar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        opened = 0
        for phone in phones:
            url = build_whatsapp_url(phone, message)
            if url is None:
                continue
            if QDesktopServices.openUrl(QUrl(url)):
                opened += 1
        log.info("WhatsApp: %s chats abiertos de %s seleccionados.", opened, len(phones))
        QMessageBox.information(
            self,
            "WhatsApp",
            f"Se abrieron {opened} chat(s). Presione Enviar en cada ventana de WhatsApp.",
        )
