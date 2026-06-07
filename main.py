"""Main application module for login and menu-based PySide6 UI."""

# region - imports

import sys
import os
import json
import logging
import logging.handlers
import sqlite3
from pathlib import Path
from importlib import metadata
from urllib.error import URLError
from urllib.request import urlopen

try:
    import pytest
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QDialog, QLabel, QLineEdit,
        QPushButton, QVBoxLayout, QFormLayout, QMessageBox, QMenuBar, QMenu,
        QHBoxLayout, QTextEdit, QDialogButtonBox,
        QTableWidget, QTableWidgetItem, QDateEdit, QComboBox,
        QDoubleSpinBox, QHeaderView
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

DB_PATH = Path(__file__).parent / "SV.db"

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
    message_box.setWindowTitle(f"{PROJECT_NAME} - Modo Entrenamiento")
    message_box.setIcon(QMessageBox.Information)
    message_box.setText(
        "Puede explorar la aplicación libremente.\n"
        "Cualquier cambio, entrada de datos o error será descartado al terminar la sesión."
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
    # Non-blocking lock attempt keeps startup responsive if another instance owns the lock.
    if not lock.tryLock(0):
        return None
    return lock
# ---------------------------------------------------------------------------
# Alumnos dialogs
# ---------------------------------------------------------------------------

class NuevoAlumnoDialog(QDialog):
    """Form dialog to insert a new alumno into SV.db."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Alumnos - Nuevo")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.nombres = QLineEdit()
        self.paterno = QLineEdit()
        self.materno = QLineEdit()
        self.cumpleanos = QDateEdit()
        self.cumpleanos.setCalendarPopup(True)
        self.cumpleanos.setDisplayFormat("yyyy-MM-dd")
        self.rude = QLineEdit()
        self.carnet = QLineEdit()
        self.pension = QDoubleSpinBox()
        self.pension.setRange(0, 99999)
        self.pension.setDecimals(2)
        self.pension.setPrefix("Bs ")

        self.grado = QComboBox()
        try:
            conn = sqlite3.connect(DB_PATH)
            for gid, gname in conn.execute("SELECT id, grado FROM grados ORDER BY grado").fetchall():
                self.grado.addItem(gname, gid)
            conn.close()
        except Exception:
            pass

        form.addRow("Nombres *:", self.nombres)
        form.addRow("Paterno *:", self.paterno)
        form.addRow("Materno:", self.materno)
        form.addRow("Cumpleaños:", self.cumpleanos)
        form.addRow("RUDE:", self.rude)
        form.addRow("Carnet:", self.carnet)
        form.addRow("Grado:", self.grado)
        form.addRow("Pensión:", self.pension)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        nombres = self.nombres.text().strip()
        paterno = self.paterno.text().strip()
        if not nombres or not paterno:
            QMessageBox.warning(self, "Validación", "Nombres y apellido paterno son requeridos.")
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT INTO alumnos (nombres, paterno, materno, cumpleanos, rude, Carnet, id_grado, pension)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (nombres, paterno, self.materno.text().strip(),
                 self.cumpleanos.date().toString("yyyy-MM-dd"),
                 self.rude.text().strip(), self.carnet.text().strip(),
                 self.grado.currentData(), self.pension.value()),
            )
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Guardado", f"Alumno '{nombres} {paterno}' guardado.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{exc}")


class BuscarAlumnoDialog(QDialog):
    """Search dialog for alumnos."""

    _HEADERS = ["ID", "Nombres", "Paterno", "Materno", "RUDE", "Carnet", "Grado", "Pensión"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Alumnos - Buscar")
        self.resize(760, 420)
        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Nombres o apellidos…")
        self.search_edit.textChanged.connect(self._load)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, len(self._HEADERS))
        self.table.setHorizontalHeaderLabels(self._HEADERS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load("")

    def _load(self, text: str):
        like = f"%{text}%"
        try:
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute(
                "SELECT a.id, a.nombres, a.paterno, a.materno, a.rude, a.Carnet,"
                " g.grado, a.pension"
                " FROM alumnos a LEFT JOIN grados g ON a.id_grado = g.id"
                " WHERE a.nombres LIKE ? OR a.paterno LIKE ? OR a.materno LIKE ?"
                " ORDER BY a.paterno, a.nombres",
                (like, like, like),
            ).fetchall()
            conn.close()
        except Exception:
            rows = []
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem("" if val is None else str(val)))
        self.table.setSortingEnabled(True)


# ---------------------------------------------------------------------------
# Parientes dialogs
# ---------------------------------------------------------------------------

class NuevoParienteDialog(QDialog):
    """Form dialog to insert a new pariente (adulto) into SV.db."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Parientes - Nuevo")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.nombres = QLineEdit()
        self.paterno = QLineEdit()
        self.materno = QLineEdit()
        self.cell1 = QLineEdit()
        self.cell2 = QLineEdit()
        self.email = QLineEdit()
        self.carnet = QLineEdit()
        self.nit = QLineEdit()

        form.addRow("Nombres *:", self.nombres)
        form.addRow("Paterno *:", self.paterno)
        form.addRow("Materno:", self.materno)
        form.addRow("Celular 1:", self.cell1)
        form.addRow("Celular 2:", self.cell2)
        form.addRow("Email:", self.email)
        form.addRow("Carnet:", self.carnet)
        form.addRow("NIT:", self.nit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        nombres = self.nombres.text().strip()
        paterno = self.paterno.text().strip()
        if not nombres or not paterno:
            QMessageBox.warning(self, "Validación", "Nombres y apellido paterno son requeridos.")
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT INTO adultos (a_nombres, a_paterno, a_materno, cell1, cell2, email, a_carnet, NIT)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (nombres, paterno, self.materno.text().strip(),
                 self.cell1.text().strip(), self.cell2.text().strip(),
                 self.email.text().strip(), self.carnet.text().strip(),
                 self.nit.text().strip()),
            )
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Guardado", f"Pariente '{nombres} {paterno}' guardado.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{exc}")


class BuscarParienteDialog(QDialog):
    """Search dialog for parientes (adultos)."""

    _HEADERS = ["ID", "Nombres", "Paterno", "Materno", "Celular 1", "Celular 2", "Email", "Carnet", "NIT"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Parientes - Buscar")
        self.resize(820, 380)
        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Nombres o apellidos…")
        self.search_edit.textChanged.connect(self._load)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, len(self._HEADERS))
        self.table.setHorizontalHeaderLabels(self._HEADERS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load("")

    def _load(self, text: str):
        like = f"%{text}%"
        try:
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute(
                "SELECT id, a_nombres, a_paterno, a_materno, cell1, cell2, email, a_carnet, NIT"
                " FROM adultos"
                " WHERE a_nombres LIKE ? OR a_paterno LIKE ? OR a_materno LIKE ?"
                " ORDER BY a_paterno, a_nombres",
                (like, like, like),
            ).fetchall()
            conn.close()
        except Exception:
            rows = []
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem("" if val is None else str(val)))
        self.table.setSortingEnabled(True)


# ---------------------------------------------------------------------------
# Cuentas dialogs
# ---------------------------------------------------------------------------

class NuevoCuentaDialog(QDialog):
    """Form dialog to insert a new cuenta into SV.db."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cuentas - Nuevo")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.alumno = QComboBox()
        self._alumno_ids: list[int] = []
        try:
            conn = sqlite3.connect(DB_PATH)
            for aid, nombres, paterno in conn.execute(
                "SELECT id, nombres, paterno FROM alumnos ORDER BY paterno, nombres"
            ).fetchall():
                self.alumno.addItem(f"{paterno}, {nombres}", aid)
                self._alumno_ids.append(aid)
            conn.close()
        except Exception:
            pass

        self.debito = QDoubleSpinBox()
        self.debito.setRange(0, 999999)
        self.debito.setDecimals(2)
        self.debito.setPrefix("Bs ")

        self.credito = QDoubleSpinBox()
        self.credito.setRange(0, 999999)
        self.credito.setDecimals(2)
        self.credito.setPrefix("Bs ")

        self.aclaracion = QLineEdit()
        self.fecha = QDateEdit()
        self.fecha.setCalendarPopup(True)
        self.fecha.setDisplayFormat("yyyy-MM-dd")
        from PySide6.QtCore import QDate
        self.fecha.setDate(QDate.currentDate())
        self.factura = QLineEdit()

        form.addRow("Alumno *:", self.alumno)
        form.addRow("Débito:", self.debito)
        form.addRow("Crédito:", self.credito)
        form.addRow("Aclaración:", self.aclaracion)
        form.addRow("Fecha:", self.fecha)
        form.addRow("Factura:", self.factura)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        if self.alumno.count() == 0:
            QMessageBox.warning(self, "Validación", "No hay alumnos registrados.")
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT INTO ctas (id_alumno, debito, credito, aclaracion, fecha, factura)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (self.alumno.currentData(), self.debito.value(), self.credito.value(),
                 self.aclaracion.text().strip(),
                 self.fecha.date().toString("yyyy-MM-dd"),
                 self.factura.text().strip()),
            )
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Guardado", "Cuenta guardada.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{exc}")


class BuscarCuentaDialog(QDialog):
    """Search dialog for cuentas."""

    _HEADERS = ["ID", "Alumno", "Débito", "Crédito", "Aclaración", "Fecha", "Factura"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cuentas - Buscar")
        self.resize(800, 400)
        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Alumno:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Nombre o apellido del alumno…")
        self.search_edit.textChanged.connect(self._load)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, len(self._HEADERS))
        self.table.setHorizontalHeaderLabels(self._HEADERS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load("")

    def _load(self, text: str):
        like = f"%{text}%"
        try:
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute(
                "SELECT c.id, a.paterno || ', ' || a.nombres,"
                " c.debito, c.credito, c.aclaracion, c.fecha, c.factura"
                " FROM ctas c JOIN alumnos a ON c.id_alumno = a.id"
                " WHERE a.nombres LIKE ? OR a.paterno LIKE ?"
                " ORDER BY c.fecha DESC",
                (like, like),
            ).fetchall()
            conn.close()
        except Exception:
            rows = []
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem("" if val is None else str(val)))
        self.table.setSortingEnabled(True)


# ---------------------------------------------------------------------------
# Login dialog
# ---------------------------------------------------------------------------

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
            message = "Usuario o contraseña incorrectos."
            if username.lower() == "trainee":
                message += "\nRecuerda: usa 'trainee' como contraseña."
            QMessageBox.warning(self, "Error de acceso", message)
            self.password_edit.clear()
            self.password_edit.setFocus()

    def toggle_password_visibility(self, checked: bool):
        """Toggle password field visibility between masked and plain text."""
        if checked:
            self.password_edit.setEchoMode(QLineEdit.Normal)
            self.password_toggle_btn.setText("Ocultar")
        else:
            self.password_edit.setEchoMode(QLineEdit.Password)
            self.password_toggle_btn.setText("Mostrar")
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
            f"{PROJECT_NAME} - Versión: {VERSION} - Usuario: {self._username}"
        )

    def showEvent(self, event: QShowEvent):
        """Reapply title on show to keep native title bar in sync."""
        self._apply_window_title()
        super().showEvent(event)

    def _build_menu_bar(self):
        """Create the menu bar and connect actions to handlers."""
        menu_bar = self.menuBar()

        # Navegación menu
        self.navigation_menu = menu_bar.addMenu("&Navegación")
        self.logout_action = QAction("&Cerrar sesión", self)
        self.logout_action.triggered.connect(self.on_logout)
        self.navigation_menu.addAction(self.logout_action)

        self.exit_action = QAction("&Salir", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)
        self.navigation_menu.addAction(self.exit_action)

        # Archivo menu
        self.file_menu = menu_bar.addMenu("&Archivo")
        new_action = QAction("&Nuevo", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.on_new)
        self.file_menu.addAction(new_action)

        open_action = QAction("&Abrir", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.on_open)
        self.file_menu.addAction(open_action)

        # Editar menu
        self.edit_menu = menu_bar.addMenu("&Editar")
        preferences_action = QAction("&Preferencias", self)
        preferences_action.triggered.connect(self.on_preferences)
        self.edit_menu.addAction(preferences_action)

        # Alumnos menu
        self.alumnos_menu = menu_bar.addMenu("&Alumnos")
        alumnos_nuevo_action = QAction("&Nuevo", self)
        alumnos_nuevo_action.triggered.connect(self.on_alumnos_nuevo)
        self.alumnos_menu.addAction(alumnos_nuevo_action)
        alumnos_buscar_action = QAction("&Buscar", self)
        alumnos_buscar_action.triggered.connect(self.on_alumnos_buscar)
        self.alumnos_menu.addAction(alumnos_buscar_action)

        # Parientes menu
        self.parientes_menu = menu_bar.addMenu("&Parientes")
        parientes_nuevo_action = QAction("&Nuevo", self)
        parientes_nuevo_action.triggered.connect(self.on_parientes_nuevo)
        self.parientes_menu.addAction(parientes_nuevo_action)
        parientes_buscar_action = QAction("&Buscar", self)
        parientes_buscar_action.triggered.connect(self.on_parientes_buscar)
        self.parientes_menu.addAction(parientes_buscar_action)

        # Cuentas menu
        self.cuentas_menu = menu_bar.addMenu("&Cuentas")
        cuentas_nuevo_action = QAction("&Nuevo", self)
        cuentas_nuevo_action.triggered.connect(self.on_cuentas_nuevo)
        self.cuentas_menu.addAction(cuentas_nuevo_action)
        cuentas_buscar_action = QAction("&Buscar", self)
        cuentas_buscar_action.triggered.connect(self.on_cuentas_buscar)
        self.cuentas_menu.addAction(cuentas_buscar_action)

        # Ayuda menu
        self.help_menu = menu_bar.addMenu("A&yuda")
        about_action = QAction("&Acerca de", self)
        about_action.triggered.connect(self.on_about)
        self.help_menu.addAction(about_action)

    def _build_central(self):
        """Create and attach the central welcome label widget."""
        label = QLabel("¡Bienvenido!", self)
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
        """Handle the Archivo > Nuevo menu action."""
        log.info("Menú: Archivo > Nuevo")
        QMessageBox.information(self, "Nuevo", "Acción Nuevo activada.")

    def on_open(self):
        """Handle the Archivo > Abrir menu action."""
        #log.info("Menú: Archivo > Abrir")
        QMessageBox.information(self, "Abrir", "Acción Abrir activada.")

    def on_preferences(self):
        """Handle the Editar > Preferencias menu action."""
        #log.info("Menú: Editar > Preferencias")
        QMessageBox.information(self, "Preferencias", "Acción Preferencias activada.")

    def on_logout(self):
        """Handle the Navigation > Logout menu action."""
        #log.info("Menu: Navigation > Logout")
        self._clear_training_mode_notice()
        self.hide()

        # Use a top-level dialog during logout so it cannot be blocked by a hidden parent.
        login = LoginDialog()
        if login.exec() == QDialog.Accepted:
            self._start_user_session(login.logged_in_username)
            self.show()
        else:
            self.close()

    def on_alumnos_nuevo(self):
        """Handle the Alumnos > Nuevo menu action."""
        log.info("Menu: Alumnos > Nuevo")
        NuevoAlumnoDialog(self).exec()

    def on_alumnos_buscar(self):
        """Handle the Alumnos > Buscar menu action."""
        log.info("Menu: Alumnos > Buscar")
        BuscarAlumnoDialog(self).exec()

    def on_parientes_nuevo(self):
        """Handle the Parientes > Nuevo menu action."""
        log.info("Menu: Parientes > Nuevo")
        NuevoParienteDialog(self).exec()

    def on_parientes_buscar(self):
        """Handle the Parientes > Buscar menu action."""
        log.info("Menu: Parientes > Buscar")
        BuscarParienteDialog(self).exec()

    def on_cuentas_nuevo(self):
        """Handle the Cuentas > Nuevo menu action."""
        log.info("Menu: Cuentas > Nuevo")
        NuevoCuentaDialog(self).exec()

    def on_cuentas_buscar(self):
        """Handle the Cuentas > Buscar menu action."""
        log.info("Menu: Cuentas > Buscar")
        BuscarCuentaDialog(self).exec()

    def on_about(self):
        """Display application About information."""
        log.info("Menu: Help > About")
        about_path = Path(__file__).with_name("About.md")
        about_text = (
            about_path.read_text(encoding="utf-8")
            if about_path.exists()
            else "# Acerca de\n\nNo se encontró About.md."
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Acerca de")
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
        QMessageBox.warning(None, "Ya en ejecución", "La aplicación ya está en ejecución.")
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
