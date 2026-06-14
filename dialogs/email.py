"""Bulk email dialog.

Lists adultos that have an email address and opens the operator's default mail
client with a pre-filled message for the selected recipients. Like the WhatsApp
dialog, nothing is sent automatically: the message is only *composed* in the
mail client, and the operator presses Send.
"""

import logging

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QCheckBox,
    QDialogButtonBox, QMessageBox, QAbstractItemView,
)

import database
from utils import build_mailto_url, normalize_email

log = logging.getLogger("app")


class EnviarEmailDialog(QDialog):
    """Pick recipients from the adultos list and compose an email for them."""

    _HEADERS = ["", "Nombre", "Email"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adultos - Enviar Email")
        self.resize(680, 560)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Asunto:"))
        self.subject_edit = QLineEdit()
        self.subject_edit.setPlaceholderText("Asunto del correo…")
        layout.addWidget(self.subject_edit)

        layout.addWidget(QLabel("Mensaje (se rellena en el cliente de correo; usted presiona Enviar):"))
        self.body_edit = QPlainTextEdit()
        self.body_edit.setPlaceholderText("Escriba el mensaje a enviar…")
        self.body_edit.setFixedHeight(110)
        layout.addWidget(self.body_edit)

        self.bcc_checkbox = QCheckBox("Enviar como copia oculta (CCO) para proteger las direcciones")
        self.bcc_checkbox.setChecked(True)
        layout.addWidget(self.bcc_checkbox)

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
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.itemChanged.connect(self._update_count)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        self.compose_btn = buttons.addButton("Redactar correo", QDialogButtonBox.AcceptRole)
        self.compose_btn.clicked.connect(self._compose)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load()

    def _load(self):
        rows = database.list_adultos_con_email()
        recipients = []
        for _adulto_id, nombres, paterno, materno, email in rows:
            normalized = normalize_email(email)
            if normalized is None:
                continue
            name = " ".join(
                part for part in (
                    str(paterno or "").strip(),
                    str(nombres or "").strip(),
                    str(materno or "").strip(),
                ) if part
            )
            recipients.append((name, normalized))

        self.table.blockSignals(True)
        self.table.setRowCount(len(recipients))
        for r, (name, email) in enumerate(recipients):
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Checked)
            check_item.setData(Qt.UserRole, email)
            self.table.setItem(r, 0, check_item)
            self.table.setItem(r, 1, QTableWidgetItem(name))
            self.table.setItem(r, 2, QTableWidgetItem(email))
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

    def _checked_emails(self) -> list[str]:
        emails = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item is not None and item.checkState() == Qt.Checked:
                emails.append(item.data(Qt.UserRole))
        return emails

    def _update_count(self, *_args):
        self.count_label.setText(f"Seleccionados: {len(self._checked_emails())}")

    def _compose(self):
        emails = self._checked_emails()
        if not emails:
            QMessageBox.information(self, "Email", "Seleccione al menos un destinatario.")
            return

        url = build_mailto_url(
            emails,
            subject=self.subject_edit.text().strip(),
            body=self.body_edit.toPlainText().strip(),
            use_bcc=self.bcc_checkbox.isChecked(),
        )
        if url is None:
            QMessageBox.warning(self, "Email", "No hay direcciones de correo válidas.")
            return

        if QDesktopServices.openUrl(QUrl(url)):
            log.info("Email: cliente de correo abierto con %s destinatario(s).", len(emails))
            QMessageBox.information(
                self,
                "Email",
                f"Se abrió el cliente de correo con {len(emails)} destinatario(s).\n"
                "Revise el mensaje y presione Enviar.",
            )
        else:
            log.warning("Email: no se pudo abrir el cliente de correo.")
            QMessageBox.critical(
                self,
                "Email",
                "No se pudo abrir el cliente de correo predeterminado.",
            )
