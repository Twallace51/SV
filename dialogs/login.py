"""Login dialog."""

# region - imports

import logging

from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QMessageBox, QHBoxLayout, QInputDialog,
)
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtCore import Qt

from modules import config
from __init__ import PROJECT_NAME, VERSION

# endregion

log = logging.getLogger("app")


class LoginDialog(QDialog):
    """Login dialog that validates credentials and tracks current user."""

    def __init__(self, parent=None):
        """Initialize login UI controls and interaction state."""
        super().__init__(parent)
        self.setWindowTitle(f"{PROJECT_NAME} - Versión: {VERSION}")
        self.setFixedSize(500, 190)
        self.setStyleSheet("font-size: 14px;")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)

        self.title_label = QLabel(
            f"{PROJECT_NAME} - Versión: {VERSION}\nIniciar Session Modo:",
            self,
        )
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        self.normal_user_mode_btn = QPushButton("Usuario Normal")
        self.normal_user_mode_btn.clicked.connect(self.login_as_user)
        self.training_mode_btn = QPushButton("Entrenamiento")
        self.training_mode_btn.clicked.connect(self.login_as_trainee)
        self.admin_mode_btn = QPushButton("Admin")
        self.admin_mode_btn.clicked.connect(self.login_as_admin)

        quick_login_layout = QVBoxLayout()
        quick_login_layout.setContentsMargins(0, 0, 0, 0)
        quick_login_layout.addWidget(self.admin_mode_btn)
        quick_login_layout.addWidget(self.training_mode_btn)
        quick_login_layout.addWidget(self.normal_user_mode_btn)
        layout.addLayout(quick_login_layout)

        button_layout = QHBoxLayout()

        self.quit_btn = QPushButton("Salir")
        self.quit_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.quit_btn)

        layout.addLayout(button_layout)

        self._right_btn_held = False
        self.logged_in_username = ""

    def mousePressEvent(self, event: QMouseEvent):
        """Track right-button state for the scroll-based admin shortcut."""
        if event.button() == Qt.RightButton:
            self._right_btn_held = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Clear right-button tracking when the button is released."""
        if event.button() == Qt.RightButton:
            self._right_btn_held = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        """Accept login as admin when right-click is held while scrolling."""
        if self._right_btn_held:
            self.logged_in_username = "admin"
            self.accept()
            return
        super().wheelEvent(event)

    def login_as_trainee(self):
        """Quick-login shortcut for training mode user."""
        self._quick_login_as("trainee")

    def login_as_user(self):
        """Quick-login shortcut for normal user mode."""
        self._quick_login_as("user")

    def login_as_admin(self):
        """Prompt for admin password and login as admin when valid."""
        password, accepted = QInputDialog.getText(
            self,
            "Modo Admin",
            "Ingrese contraseña admin:",
            QLineEdit.Password,
        )
        if not accepted:
            return

        if password == config.LOGIN_CREDENTIALS.get("admin"):
            self._quick_login_as("admin")
            return

        QMessageBox.warning(self, "Error de acceso", "Contraseña admin incorrecta.")

    def _quick_login_as(self, username: str):
        """Login as a built-in user and accept the dialog."""
        self.logged_in_username = username
        self.accept()
