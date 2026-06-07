"""Main application window."""

# region - imports

import logging
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QLabel, QDialog,
    QVBoxLayout, QTextEdit, QDialogButtonBox, QMessageBox,
)
from PySide6.QtGui import QAction, QShowEvent, QCloseEvent
from PySide6.QtCore import Qt

from __init__ import (
    PROJECT_NAME,
    VERSION,
    DB_PATH,
    set_active_db_path,
    reset_active_db_path,
)
from utils import show_training_mode_notice
from dialogs.login import LoginDialog
from dialogs.alumnos import NuevoAlumnoDialog, BuscarAlumnoDialog
from dialogs.parientes import NuevoParienteDialog, BuscarParienteDialog
from dialogs.cuentas import NuevoCuentaDialog, BuscarCuentaDialog

# endregion

log = logging.getLogger("app")


class MainWindow(QMainWindow):
    """Primary application window shown after successful login."""

    def __init__(self, username: str):
        """Initialize the main window and include version/user in title."""
        super().__init__()
        self._username = username
        self._trainee_temp_db_path: Path | None = None
        self._apply_window_title()
        self.resize(800, 600)
        self._build_menu_bar()
        self._build_central()
        self._configure_session_database(self._username)
        self._apply_window_title()
        self._apply_session_theme()

    def _apply_window_title(self):
        """Apply the current title text to the native window."""
        title = f"{PROJECT_NAME} - Versión: {VERSION} - Usuario: {self._username}"
        if self._trainee_temp_db_path is not None:
            title += " - Modo Entrenamiento DB Temporal"
        self.setWindowTitle(title)

    def showEvent(self, event: QShowEvent):
        """Reapply title on show to keep native title bar in sync."""
        self._apply_window_title()
        super().showEvent(event)

    def closeEvent(self, event: QCloseEvent):
        """Ensure temporary trainee session artifacts are cleaned up on close."""
        self._clear_training_mode_notice()
        self._cleanup_trainee_temp_database()
        super().closeEvent(event)

    def _configure_session_database(self, username: str):
        """Select default DB or a temporary trainee DB for the current session."""
        self._cleanup_trainee_temp_database()

        if username.strip().lower() != "trainee":
            reset_active_db_path()
            return

        source_db = Path(DB_PATH)
        if not source_db.exists():
            reset_active_db_path()
            QMessageBox.warning(
                self,
                "Base de Datos",
                f"No se encontró la base de datos principal en:\n{source_db}",
            )
            return

        session_dir = Path(tempfile.gettempdir()) / "template_sv_sessions"
        session_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        temp_db = session_dir / f"{source_db.stem}_trainee_{timestamp}{source_db.suffix}"

        try:
            shutil.copy2(source_db, temp_db)
            set_active_db_path(temp_db)
            self._trainee_temp_db_path = temp_db
            log.info("Base temporal de trainee creada: %s", temp_db)
        except OSError as exc:
            reset_active_db_path()
            log.exception("No se pudo crear base temporal para trainee")
            QMessageBox.critical(
                self,
                "Base de Datos",
                f"No se pudo iniciar sesión temporal de trainee.\n\nDetalle: {exc}",
            )

    def _cleanup_trainee_temp_database(self):
        """Remove trainee temporary DB and restore default DB path."""
        temp_db = self._trainee_temp_db_path
        self._trainee_temp_db_path = None
        reset_active_db_path()

        if temp_db is None:
            return

        try:
            temp_db.unlink(missing_ok=True)
            log.info("Base temporal de trainee eliminada: %s", temp_db)
        except OSError:
            log.exception("No se pudo eliminar base temporal de trainee: %s", temp_db)

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

        backup_action = QAction("Crear &Backup de Base de Datos", self)
        backup_action.triggered.connect(self.on_backup_database)
        self.file_menu.addAction(backup_action)

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
        self._configure_session_database(self._username)
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
        QMessageBox.information(self, "Abrir", "Acción Abrir activada.")

    def on_backup_database(self):
        """Handle the Archivo > Crear Backup de Base de Datos action."""
        db_path = Path(DB_PATH)
        if not db_path.exists():
            QMessageBox.warning(
                self,
                "Backup",
                f"No se encontró la base de datos en:\n{db_path}",
            )
            return

        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"

        try:
            shutil.copy2(db_path, backup_file)
        except OSError as exc:
            log.exception("Error al crear backup de base de datos")
            QMessageBox.critical(
                self,
                "Backup",
                f"No se pudo crear el backup.\n\nDetalle: {exc}",
            )
            return

        QMessageBox.information(
            self,
            "Backup",
            f"Backup creado correctamente:\n{backup_file}",
        )

    def on_preferences(self):
        """Handle the Editar > Preferencias menu action."""
        QMessageBox.information(self, "Preferencias", "Acción Preferencias activada.")

    def on_logout(self):
        """Handle the Navegación > Cerrar sesión menu action."""
        self._clear_training_mode_notice()
        self._cleanup_trainee_temp_database()
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
        log.info("Menú: Alumnos > Nuevo")
        NuevoAlumnoDialog(self).exec()

    def on_alumnos_buscar(self):
        """Handle the Alumnos > Buscar menu action."""
        log.info("Menú: Alumnos > Buscar")
        BuscarAlumnoDialog(self).exec()

    def on_parientes_nuevo(self):
        """Handle the Parientes > Nuevo menu action."""
        log.info("Menú: Parientes > Nuevo")
        NuevoParienteDialog(self).exec()

    def on_parientes_buscar(self):
        """Handle the Parientes > Buscar menu action."""
        log.info("Menú: Parientes > Buscar")
        BuscarParienteDialog(self).exec()

    def on_cuentas_nuevo(self):
        """Handle the Cuentas > Nuevo menu action."""
        log.info("Menú: Cuentas > Nuevo")
        NuevoCuentaDialog(self).exec()

    def on_cuentas_buscar(self):
        """Handle the Cuentas > Buscar menu action."""
        log.info("Menú: Cuentas > Buscar")
        BuscarCuentaDialog(self).exec()

    def on_about(self):
        """Display application About information."""
        log.info("Menú: Ayuda > Acerca de")
        about_path = Path(__file__).parent.parent / "About.md"
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
