"""Login dialog."""

# region - imports

import logging

from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QFormLayout, QMessageBox, QHBoxLayout, QInputDialog,
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
            f"{PROJECT_NAME} - Versión: {VERSION}\nIniciar Sesión",
            self,
        )
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        form = QFormLayout()

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Ingrese: admin, user o trainee")
        self.normal_user_mode_btn = QPushButton("Modo Usuario Normal")
        self.normal_user_mode_btn.clicked.connect(self.login_as_user)
        self.training_mode_btn = QPushButton("Modo Entrenamiento")
        self.training_mode_btn.clicked.connect(self.login_as_trainee)
        self.admin_mode_btn = QPushButton("Modo Admin")
        self.admin_mode_btn.clicked.connect(self.login_as_admin)

        quick_login_layout = QVBoxLayout()
        quick_login_layout.setContentsMargins(0, 0, 0, 0)
        quick_login_layout.addWidget(self.admin_mode_btn)
        quick_login_layout.addWidget(self.training_mode_btn)
        quick_login_layout.addWidget(self.normal_user_mode_btn)
        layout.addLayout(quick_login_layout)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Ingrese contraseña")
        self.password_edit.setEchoMode(QLineEdit.Password)

        self.password_toggle_btn = QPushButton("Mostrar")
        self.password_toggle_btn.setCheckable(True)
        self.password_toggle_btn.setFixedWidth(60)
        self.password_toggle_btn.clicked.connect(self.toggle_password_visibility)

        password_layout = QHBoxLayout()
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.addWidget(self.password_edit)
        password_layout.addWidget(self.password_toggle_btn)

        form.addRow("Usuario:", self.username_edit)
        form.addRow("Contraseña:", password_layout)
        layout.addLayout(form)

        button_layout = QHBoxLayout()

        self.login_btn = QPushButton("Ingresar")
        self.login_btn.setDefault(True)
        self.login_btn.clicked.connect(self.handle_login)
        button_layout.addWidget(self.login_btn)

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

    def handle_login(self):
        """Validate entered credentials and accept or reject login attempt."""
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        # Replace this with real authentication logic
        if config.LOGIN_CREDENTIALS.get(username) == password:
            self.logged_in_username = username
            self.accept()
        else:
            message = "Usuario o contraseña incorrectos."
            if username.lower() == "trainee":
                message += "\nRecuerda: usa 'trainee' como contraseña."
            QMessageBox.warning(self, "Error de acceso", message)
            self.password_edit.clear()
            self.password_edit.setFocus()

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
        """Fill credentials for a built-in user and accept the dialog."""
        self.username_edit.setText(username)
        self.password_edit.setText(username)
        self.logged_in_username = username
        self.accept()

    def toggle_password_visibility(self, checked: bool):
        """Toggle password field visibility between masked and plain text."""
        if checked:
            self.password_edit.setEchoMode(QLineEdit.Normal)
            self.password_toggle_btn.setText("Ocultar")
        else:
            self.password_edit.setEchoMode(QLineEdit.Password)
            self.password_toggle_btn.setText("Mostrar")
