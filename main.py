import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QFormLayout, QMessageBox, QMenuBar, QMenu
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login")
        self.setFixedSize(300, 160)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter username")
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter password")
        self.password_edit.setEchoMode(QLineEdit.Password)

        form.addRow("Username:", self.username_edit)
        form.addRow("Password:", self.password_edit)
        layout.addLayout(form)

        self.login_btn = QPushButton("Login")
        self.login_btn.setDefault(True)
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)

        self._right_btn_held = False

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            self._right_btn_held = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            self._right_btn_held = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        if self._right_btn_held:
            self.accept()
            return
        super().wheelEvent(event)

    def handle_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        # Replace this with real authentication logic
        if username == "admin" and password == "password":
            self.accept()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")
            self.password_edit.clear()
            self.password_edit.setFocus()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main Menu")
        self.resize(800, 600)
        self._build_menu_bar()
        self._build_central()

    def _build_menu_bar(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")
        new_action = QAction("&New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.on_new)
        file_menu.addAction(new_action)

        open_action = QAction("&Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.on_open)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")
        preferences_action = QAction("&Preferences", self)
        preferences_action.triggered.connect(self.on_preferences)
        edit_menu.addAction(preferences_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.on_about)
        help_menu.addAction(about_action)

    def _build_central(self):
        label = QLabel("Welcome!", self)
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)

    # --- Menu action handlers ---

    def on_new(self):
        QMessageBox.information(self, "New", "New action triggered.")

    def on_open(self):
        QMessageBox.information(self, "Open", "Open action triggered.")

    def on_preferences(self):
        QMessageBox.information(self, "Preferences", "Preferences action triggered.")

    def on_about(self):
        QMessageBox.about(self, "About", "Generic Main Menu Application\nPySide6")


def main():
    app = QApplication(sys.argv)

    login = LoginDialog()
    if login.exec() != QDialog.Accepted:
        sys.exit(0)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
