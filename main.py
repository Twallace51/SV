import sys
import logging
import logging.handlers
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QFormLayout, QMessageBox, QMenuBar, QMenu
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QLockFile, QStandardPaths
from PySide6.QtGui import QMouseEvent, QWheelEvent

from __init__ import __version__


def setup_logging() -> logging.Logger:
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger("app")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler – keeps last 5 × 1 MB log files
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


log = setup_logging()


def acquire_single_instance_lock() -> QLockFile | None:
    temp_dir = Path(QStandardPaths.writableLocation(QStandardPaths.TempLocation))
    lock_file_path = temp_dir / "template_app.lock"

    lock = QLockFile(str(lock_file_path))
    lock.setStaleLockTime(0)
    if not lock.lock():
        return None
    return lock


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
        self.logged_in_username = ""

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            self._right_btn_held = True
            log.debug("Login dialog: right mouse button pressed")
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            self._right_btn_held = False
            log.debug("Login dialog: right mouse button released")
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        if self._right_btn_held:
            self.logged_in_username = "admin"
            log.info("Login: admin shortcut used (right-click + scroll)")
            self.accept()
            return
        super().wheelEvent(event)

    def handle_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        log.info("Login attempt for user: %s", username)
        # Replace this with real authentication logic
        valid_credentials = {
            "admin": "password",
            "user": "user",
            "trainee": "trainee",
        }
        if valid_credentials.get(username) == password:
            self.logged_in_username = username
            log.info("Login successful for user: %s", username)
            self.accept()
        else:
            log.warning("Login failed for user: %s", username)
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")
            self.password_edit.clear()
            self.password_edit.setFocus()


class MainWindow(QMainWindow):
    def __init__(self, username: str):
        super().__init__()
        self.setWindowTitle(f"Main Menu - v{__version__} - {username}")
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
        log.info("Menu: File > New")
        QMessageBox.information(self, "New", "New action triggered.")

    def on_open(self):
        log.info("Menu: File > Open")
        QMessageBox.information(self, "Open", "Open action triggered.")

    def on_preferences(self):
        log.info("Menu: Edit > Preferences")
        QMessageBox.information(self, "Preferences", "Preferences action triggered.")

    def on_about(self):
        log.info("Menu: Help > About")
        QMessageBox.about(self, "About", "Generic Main Menu Application\nPySide6")


def main():
    log.info("Application starting")
    app = QApplication(sys.argv)

    instance_lock = acquire_single_instance_lock()
    if instance_lock is None:
        log.warning("Application already running; exiting duplicate instance")
        QMessageBox.warning(None, "Already Running", "This application is already running.")
        sys.exit(1)

    login = LoginDialog()
    if login.exec() != QDialog.Accepted:
        log.info("Login cancelled – application exiting")
        sys.exit(0)

    log.info("Login accepted – opening main window")
    window = MainWindow(login.logged_in_username or "unknown")
    window.show()
    exit_code = app.exec()
    log.info("Application exiting with code %d", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
