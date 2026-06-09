"""Login dialog."""

# region - imports

import logging

from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QFormLayout, QMessageBox, QHBoxLayout,
)
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtCore import Qt

from __init__ import PROJECT_NAME, VERSION

# endregion

log = logging.getLogger("app")


class LoginDialog(QDialog):
    """Login dialog that validates credentials and tracks current user."""

    def __init__(self, parent=None):
        """Initialize login UI controls and interaction state."""
        super().__init__(parent)
        self.setWindowTitle(f"{PROJECT_NAME} - Versión: {VERSION}")
        self.setFixedSize(500, 160)
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
        self.training_mode_btn = QPushButton("Modo Entrenamiento")
        self.training_mode_btn.clicked.connect(self.login_as_trainee)
        username_layout = QHBoxLayout()
        username_layout.setContentsMargins(0, 0, 0, 0)
        username_layout.addWidget(self.username_edit)
        username_layout.addWidget(self.training_mode_btn)

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

        form.addRow("Usuario:", username_layout)
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
        valid_credentials = {
            "admin": "admin",
            "user": "user",
            "trainee": "trainee",
        }
        if valid_credentials.get(username) == password:
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
        self.username_edit.setText("trainee")
        self.password_edit.setText("trainee")
        self.logged_in_username = "trainee"
        self.accept()

    def toggle_password_visibility(self, checked: bool):
        """Toggle password field visibility between masked and plain text."""
        if checked:
            self.password_edit.setEchoMode(QLineEdit.Normal)
            self.password_toggle_btn.setText("Ocultar")
        else:
            self.password_edit.setEchoMode(QLineEdit.Password)
            self.password_toggle_btn.setText("Mostrar")
