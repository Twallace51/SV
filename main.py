"""Main application module for login and menu-based PySide6 UI."""

# region - imports

import sys
import os
import json
import logging
import logging.handlers
from pathlib import Path
from importlib import metadata
from urllib.error import URLError
from urllib.request import urlopen

try:
    import pytest
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QDialog, QLabel, QLineEdit,
        QPushButton, QVBoxLayout, QFormLayout, QMessageBox, QMenuBar, QMenu,
        QHBoxLayout, QTextEdit, QDialogButtonBox
    )
    from PySide6.QtGui import QAction
    from PySide6.QtCore import Qt, QLockFile, QStandardPaths, QTimer
    from PySide6.QtGui import QMouseEvent, QWheelEvent, QShowEvent
except ModuleNotFoundError as exc:
    if exc.name == "pytest":
        sys.stderr.write(
            "Missing required test dependency: pytest\n"
            "Install it with: python -m pip install pytest\n"
        )
        sys.exit(1)
    if exc.name == "PySide6":
        sys.stderr.write(
            "Missing required dependency: PySide6\n"
            "Install it with: python -m pip install PySide6\n"
        )
        sys.exit(1)
    raise

from __init__ import PROJECT_NAME, VERSION

# endregion

def setup_logging() -> logging.Logger:
    """Configure and return the application logger."""
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

def check_latest_pip_available() -> None:
    """Verify that pip is installed and report whether it is current."""
    try:
        installed_version = metadata.version("pip")
    except metadata.PackageNotFoundError:
        sys.stderr.write(
            "Missing required dependency manager: pip\n"
            "Repair it with: python -m ensurepip --upgrade\n"
        )
        sys.exit(1)

    try:
        with urlopen("https://pypi.org/pypi/pip/json", timeout=3) as response:
            latest_version = json.load(response)["info"]["version"]
    except (OSError, URLError, TimeoutError, ValueError, KeyError) as exc:
        log.warning("Could not verify the latest pip version: %s", exc)
        return

    if installed_version != latest_version:
        log.info(
            "pip %s is installed; but latest available is %s.",
            installed_version,
            latest_version,
            )
    else:
        ...
        #log.info("pip %s is up to date.", installed_version)

def check_pytest_available() -> None:
    """Confirm that pytest is installed and report its version."""
    #log.info("pytest %s is available.", pytest.VERSION)

def show_training_mode_notice(parent: QMainWindow) -> QMessageBox:
    """Show the trainee session notice and auto-close it after 15 seconds."""
    message_box = QMessageBox(parent)
    message_box.setWindowTitle(f"{PROJECT_NAME} - Training Mode")
    message_box.setIcon(QMessageBox.Information)
    message_box.setText(
        "Feel free to explore the application\n"
        "Any changes, data input or errors will be discarded when session ends."
    )
    message_box.setStandardButtons(QMessageBox.Close)
    message_box.setDefaultButton(QMessageBox.Close)
    message_box.show()
    QTimer.singleShot(8000, message_box.close)
    return message_box

def clear_terminal() -> None:
    """Clear the terminal screen before app startup logs are printed."""
    os.system("cls" if os.name == "nt" else "clear")

def acquire_single_instance_lock() -> QLockFile | None:
    """Acquire and return an instance lock, or None if already running."""
    temp_dir = Path(QStandardPaths.writableLocation(QStandardPaths.TempLocation))
    lock_file_path = temp_dir / "template_app.lock"

    lock = QLockFile(str(lock_file_path))
    lock.setStaleLockTime(0)
    if not lock.lock():
        return None
    return lock
class LoginDialog(QDialog):
    """Login dialog that validates credentials and tracks current user."""

    def __init__(self, parent=None):
        """Initialize login UI controls and interaction state."""
        super().__init__(parent)
        self.setWindowTitle(f"{PROJECT_NAME} - Version: {VERSION}")
        self.setFixedSize(500, 160)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)

        self.title_label = QLabel(
            f"{PROJECT_NAME} - Version: {VERSION}\nLogin Dialog",
            self,
        )
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        form = QFormLayout()

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter: admin, user or trainee")
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter password")
        self.password_edit.setEchoMode(QLineEdit.Password)

        self.password_toggle_btn = QPushButton("Show")
        self.password_toggle_btn.setCheckable(True)
        self.password_toggle_btn.setFixedWidth(60)
        self.password_toggle_btn.clicked.connect(self.toggle_password_visibility)

        password_layout = QHBoxLayout()
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.addWidget(self.password_edit)
        password_layout.addWidget(self.password_toggle_btn)

        form.addRow("Username:", self.username_edit)
        form.addRow("Password:", password_layout)
        layout.addLayout(form)

        button_layout = QHBoxLayout()

        self.login_btn = QPushButton("Login")
        self.login_btn.setDefault(True)
        self.login_btn.clicked.connect(self.handle_login)
        button_layout.addWidget(self.login_btn)

        self.quit_btn = QPushButton("Quit")
        self.quit_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.quit_btn)

        layout.addLayout(button_layout)

        self._right_btn_held = False
        self.logged_in_username = ""

    def mousePressEvent(self, event: QMouseEvent):
        """Track right-button state for the scroll-based admin shortcut."""
        if event.button() == Qt.RightButton:
            self._right_btn_held = True
            #log.debug("Login dialog: right mouse button pressed")
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Clear right-button tracking when the button is released."""
        if event.button() == Qt.RightButton:
            self._right_btn_held = False
            #.debug("Login dialog: right mouse button released")
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        """Accept login as admin when right-click is held while scrolling."""
        if self._right_btn_held:
            self.logged_in_username = "admin"
            #log.info("Login: admin shortcut used (right-click + scroll)")
            self.accept()
            return
        super().wheelEvent(event)

    def handle_login(self):
        """Validate entered credentials and accept or reject login attempt."""
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        #log.info("Login attempt for user: %s", username)
        # Replace this with real authentication logic
        valid_credentials = {
            "admin": "admin",
            "user": "user",
            "trainee": "trainee",
        }
        if valid_credentials.get(username) == password:
            self.logged_in_username = username
            #log.info("Login successful for user: %s", username)
            self.accept()
        else:
            #log.warning("Login failed for user: %s", username)
            message = "Invalid username or password."
            if username.lower() == "trainee":
                message += "\nReminder: try 'trainee' as password."
            QMessageBox.warning(self, "Login Failed", message)
            self.password_edit.clear()
            self.password_edit.setFocus()

    def toggle_password_visibility(self, checked: bool):
        """Toggle password field visibility between masked and plain text."""
        if checked:
            self.password_edit.setEchoMode(QLineEdit.Normal)
            self.password_toggle_btn.setText("Hide")
        else:
            self.password_edit.setEchoMode(QLineEdit.Password)
            self.password_toggle_btn.setText("Show")
class MainWindow(QMainWindow):
    """Primary application window shown after successful login."""

    def __init__(self, username: str):
        """Initialize the main window and include version/user in title."""
        super().__init__()
        self._username = username
        self._apply_window_title()
        self.resize(800, 600)
        self._build_menu_bar()
        self._build_central()
        self._apply_session_theme()

    def _apply_window_title(self):
        """Apply the current title text to the native window."""
        self.setWindowTitle(
            f"{PROJECT_NAME} - Version: {VERSION} - Current login: {self._username}"
        )

    def showEvent(self, event: QShowEvent):
        """Reapply title on show to keep native title bar in sync."""
        self._apply_window_title()
        super().showEvent(event)

    def _build_menu_bar(self):
        """Create the menu bar and connect actions to handlers."""
        menu_bar = self.menuBar()

        # Navigation menu
        self.navigation_menu = menu_bar.addMenu("&Navigation")
        self.logout_action = QAction("&Logout", self)
        self.logout_action.triggered.connect(self.on_logout)
        self.navigation_menu.addAction(self.logout_action)

        self.exit_action = QAction("&Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)
        self.navigation_menu.addAction(self.exit_action)

        # File menu
        self.file_menu = menu_bar.addMenu("&File")
        new_action = QAction("&New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.on_new)
        self.file_menu.addAction(new_action)

        open_action = QAction("&Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.on_open)
        self.file_menu.addAction(open_action)

        # Edit menu
        self.edit_menu = menu_bar.addMenu("&Edit")
        preferences_action = QAction("&Preferences", self)
        preferences_action.triggered.connect(self.on_preferences)
        self.edit_menu.addAction(preferences_action)

        # Help menu
        self.help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.on_about)
        self.help_menu.addAction(about_action)

    def _build_central(self):
        """Create and attach the central welcome label widget."""
        label = QLabel("Welcome!", self)
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)

    def _apply_session_theme(self):
        """Apply a trainee-only background tint for the current session."""
        central_widget = self.centralWidget()
        if central_widget is None:
            return

        if self._username.strip().lower() == "trainee":
            central_widget.setStyleSheet("background-color: #ffd6d6;")
        else:
            central_widget.setStyleSheet("")

    def _clear_training_mode_notice(self):
        """Close and forget any visible training mode notice."""
        notice = getattr(self, "training_mode_notice", None)
        if notice is not None:
            notice.close()
            self.training_mode_notice = None

    def _start_user_session(self, username: str):
        """Apply session state for a newly authenticated user."""
        self._username = username or "unknown"
        self._apply_window_title()
        self._apply_session_theme()
        self._clear_training_mode_notice()
        if self._username.strip().lower() == "trainee":
            self.training_mode_notice = show_training_mode_notice(self)

    # --- Menu action handlers ---

    def on_new(self):
        """Handle the File > New menu action."""
        log.info("Menu: File > New")
        QMessageBox.information(self, "New", "New action triggered.")

    def on_open(self):
        """Handle the File > Open menu action."""
        #log.info("Menu: File > Open")
        QMessageBox.information(self, "Open", "Open action triggered.")

    def on_preferences(self):
        """Handle the Edit > Preferences menu action."""
        #log.info("Menu: Edit > Preferences")
        QMessageBox.information(self, "Preferences", "Preferences action triggered.")

    def on_logout(self):
        """Handle the Navigation > Logout menu action."""
        #log.info("Menu: Navigation > Logout")
        self._clear_training_mode_notice()
        self.hide()

        login = LoginDialog(self)
        if login.exec() == QDialog.Accepted:
            self._start_user_session(login.logged_in_username)
            self.show()
        else:
            self.close()

    def on_about(self):
        """Display application About information."""
        log.info("Menu: Help > About")
        about_path = Path(__file__).with_name("About.md")
        about_text = (
            about_path.read_text(encoding="utf-8")
            if about_path.exists()
            else "# About\n\nAbout.md was not found."
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("About")
        dialog.resize(640, 520)

        layout = QVBoxLayout(dialog)

        viewer = QTextEdit(dialog)
        viewer.setReadOnly(True)
        viewer.setMarkdown(about_text)
        layout.addWidget(viewer)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=dialog)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.exec()

def main():
    """Run application startup, login flow, and event loop."""
    clear_terminal()
    check_latest_pip_available()
    check_pytest_available()
    #log.info("Application starting")
    app = QApplication(sys.argv)

    instance_lock = acquire_single_instance_lock()
    if instance_lock is None:
        #log.warning("Application already running; exiting duplicate instance")
        QMessageBox.warning(None, "Already Running", "This application is already running.")
        sys.exit(1)

    login = LoginDialog()
    if login.exec() != QDialog.Accepted:
        #log.info("Login cancelled – application exiting")
        sys.exit(0)

    #log.info("Login accepted – opening main window")
    window = MainWindow(login.logged_in_username or "unknown")
    window.show()
    if login.logged_in_username.strip().lower() == "trainee":
        window.training_mode_notice = show_training_mode_notice(window)
    exit_code = app.exec()
    #log.info("Application exiting with code %d", exit_code)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
