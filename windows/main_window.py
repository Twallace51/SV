"""Main application window."""

# region - imports

import logging
import sqlite3
import shutil
import tempfile
import sys
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QLabel, QDialog, QWidget,
    QVBoxLayout, QTextEdit, QDialogButtonBox, QMessageBox,
    QHBoxLayout,
)
from PySide6.QtGui import QAction, QShowEvent, QCloseEvent
from PySide6.QtCore import Qt, QEvent, QTimer, QCoreApplication

try:
    from __init__ import (
        PROJECT_NAME,
        VERSION,
        DB_PATH,
        get_active_db_path,
        set_active_db_path,
        reset_active_db_path,
    )
    from utils import show_training_mode_notice
    from dialogs.login import LoginDialog
    import dialogs.alumnos as alumnos_dialogs
    import dialogs.parientes as parientes_dialogs
    from dialogs.alumnos import NuevoAlumnoDialog, BuscarAlumnoDialog
    from dialogs.parientes import NuevoParienteDialog, BuscarParienteDialog
    from dialogs.cuentas import NuevoCuentaDialog, BuscarCuentaDialog
except (ModuleNotFoundError, ImportError):
    # Support running this file directly from the windows/ directory.
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    # A first failed import can cache windows/__init__.py as "__init__".
    # Remove it so the fallback import resolves against project_root.
    sys.modules.pop("__init__", None)
    from __init__ import (
        PROJECT_NAME,
        VERSION,
        DB_PATH,
        get_active_db_path,
        set_active_db_path,
        reset_active_db_path,
    )
    from utils import show_training_mode_notice
    from dialogs.login import LoginDialog
    import dialogs.alumnos as alumnos_dialogs
    import dialogs.parientes as parientes_dialogs
    from dialogs.alumnos import NuevoAlumnoDialog, BuscarAlumnoDialog
    from dialogs.parientes import NuevoParienteDialog, BuscarParienteDialog
    from dialogs.cuentas import NuevoCuentaDialog, BuscarCuentaDialog

# endregion

log = logging.getLogger("app")

class MainWindow(QMainWindow):
    """Primary application window shown after successful login."""

    _INACTIVITY_TIMEOUT_MS = 5 * 60 * 1000
    _USER_ACTIVITY_EVENTS = {
        QEvent.Type.MouseMove,
        QEvent.Type.MouseButtonPress,
        QEvent.Type.MouseButtonRelease,
        QEvent.Type.KeyPress,
        QEvent.Type.KeyRelease,
        QEvent.Type.Wheel,
        QEvent.Type.TouchBegin,
        QEvent.Type.TouchUpdate,
        QEvent.Type.TouchEnd,
    }

    def __init__(self, username: str):
        """Initialize the main window and include version/user in title."""
        super().__init__()
        self._username = username
        self._trainee_temp_db_path: Path | None = None
        self._allow_close = False
        self._handling_close_flow = False
        self._apply_window_title()
        self.resize(800, 600)
        self._build_menu_bar()
        self._build_central()
        self._configure_session_database(self._username)
        self._ensure_monthly_pension_records()
        self._setup_inactivity_timer()
        self._apply_window_title()
        self._apply_session_theme()

    def _setup_inactivity_timer(self):
        """Initialize and start inactivity tracking for automatic logout."""
        self._inactivity_timer = QTimer(self)
        self._inactivity_timer.setSingleShot(True)
        self._inactivity_timer.setInterval(self._INACTIVITY_TIMEOUT_MS)
        self._inactivity_timer.timeout.connect(self._handle_inactivity_timeout)

        app = QCoreApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        self._restart_inactivity_timer()

    def _restart_inactivity_timer(self):
        """Restart inactivity countdown from zero."""
        if hasattr(self, "_inactivity_timer") and self._inactivity_timer is not None:
            self._inactivity_timer.start()

    def _stop_inactivity_timer(self):
        """Stop inactivity tracking and remove the app-level event filter."""
        if hasattr(self, "_inactivity_timer") and self._inactivity_timer is not None:
            self._inactivity_timer.stop()

        app = QCoreApplication.instance()
        if app is not None:
            app.removeEventFilter(self)

    def _handle_inactivity_timeout(self):
        """Automatically log out when no user activity is detected for 5 minutes."""
        if not self.isVisible() or self._handling_close_flow:
            return

        log.info("Cierre de sesión automático por inactividad")
        self.on_logout()

    def eventFilter(self, watched, event):
        """Reset inactivity timer on user activity events while window is visible."""
        if self.isVisible() and event.type() in self._USER_ACTIVITY_EVENTS:
            self._restart_inactivity_timer()
        return super().eventFilter(watched, event)

    def _ensure_monthly_pension_records(self, now: datetime | None = None):
        """Ensure monthly pension charges exist in ctas on day 1 of Feb-Nov."""
        current = now or datetime.now()
        if current.day != 1 or current.month < 2 or current.month > 11:
            return

        month_names = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        ]
        mes_actual = month_names[current.month - 1]
        aclaracion = f"Pension para {mes_actual}"
        fecha_actual = current.strftime("%Y-%m-%d")

        try:
            conn = sqlite3.connect(get_active_db_path())
            alumnos_con_pension = conn.execute(
                "SELECT id, pension FROM alumnos WHERE pension IS NOT NULL AND pension > 0"
            ).fetchall()

            inserted = 0
            for alumno_id, pension in alumnos_con_pension:
                exists = conn.execute(
                    "SELECT 1 FROM ctas WHERE id_alumno = ? AND aclaracion = ? LIMIT 1",
                    (alumno_id, aclaracion),
                ).fetchone()
                if exists:
                    continue

                conn.execute(
                    "INSERT INTO ctas (id_alumno, debito, credito, aclaracion, fecha, factura)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (alumno_id, pension, 0, aclaracion, fecha_actual, ""),
                )
                inserted += 1

            if inserted > 0:
                conn.commit()
                log.info("Pensión mensual: %s registros agregados para %s.", inserted, mes_actual)
            conn.close()
        except Exception:
            log.exception("No se pudo confirmar/agregar registros de pensión mensual en ctas")

    def _apply_window_title(self):
        """Apply the current title text to the native window."""
        title = f"{PROJECT_NAME} - Versión: {VERSION} - Usuario: {self._username}"
        if self._trainee_temp_db_path is not None:
            title += " - Modo Entrenamiento DB Temporal"
        self.setWindowTitle(title)

    def showEvent(self, event: QShowEvent):
        """Reapply title on show to keep native title bar in sync."""
        self._apply_window_title()
        self._restart_inactivity_timer()
        super().showEvent(event)

    def closeEvent(self, event: QCloseEvent):
        """Return to login on close; only exit when relogin is cancelled."""
        if not self._allow_close and self.isVisible():
            if self._handling_close_flow:
                event.ignore()
                return

            self._handling_close_flow = True
            try:
                event.ignore()
                if self._relogin_or_close_app():
                    return
                self._allow_close = True
                self.close()
            finally:
                self._handling_close_flow = False
            return

        self._clear_training_mode_notice()
        self._stop_inactivity_timer()
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
        backup_action = QAction("Crear &Backup de Base de Datos", self)
        backup_action.triggered.connect(self.on_backup_database)
        self.file_menu.addAction(backup_action)

        # Alumnos menu
        self.alumnos_menu = menu_bar.addMenu("&Alumnos")
        alumnos_nuevo_action = QAction("&Nuevo", self)
        alumnos_nuevo_action.triggered.connect(self.on_alumnos_nuevo)
        self.alumnos_menu.addAction(alumnos_nuevo_action)
        alumnos_buscar_action = QAction("&Buscar", self)
        alumnos_buscar_action.triggered.connect(self.on_alumnos_buscar)
        self.alumnos_menu.addAction(alumnos_buscar_action)
        self.alumnos_reportes_action = QAction("&Reportes", self)
        self.alumnos_reportes_action.triggered.connect(self.on_alumnos_reportes)
        self.alumnos_menu.addAction(self.alumnos_reportes_action)

        # Parientes menu
        self.parientes_menu = menu_bar.addMenu("&Parientes")
        parientes_nuevo_action = QAction("&Nuevo", self)
        parientes_nuevo_action.triggered.connect(self.on_parientes_nuevo)
        self.parientes_menu.addAction(parientes_nuevo_action)
        parientes_buscar_action = QAction("&Buscar", self)
        parientes_buscar_action.triggered.connect(self.on_parientes_buscar)
        self.parientes_menu.addAction(parientes_buscar_action)
        self.parientes_reportes_action = QAction("&Reportes", self)
        self.parientes_reportes_action.triggered.connect(self.on_parientes_reportes)
        self.parientes_menu.addAction(self.parientes_reportes_action)

        # Cuentas menu
        self.cuentas_menu = menu_bar.addMenu("&Cuentas")
        cuentas_nuevo_action = QAction("&Nuevo", self)
        cuentas_nuevo_action.triggered.connect(self.on_cuentas_nuevo)
        self.cuentas_menu.addAction(cuentas_nuevo_action)
        cuentas_buscar_action = QAction("&Buscar", self)
        cuentas_buscar_action.triggered.connect(self.on_cuentas_buscar)
        self.cuentas_menu.addAction(cuentas_buscar_action)
        self.cuentas_reportes_action = QAction("&Reportes", self)
        self.cuentas_reportes_action.triggered.connect(self.on_cuentas_reportes)
        self.cuentas_menu.addAction(self.cuentas_reportes_action)

        # Ayuda menu
        self.help_menu = menu_bar.addMenu("A&yuda")
        about_action = QAction("&Acerca de", self)
        about_action.triggered.connect(self.on_about)
        self.help_menu.addAction(about_action)

    def _build_central(self):
        """Create and attach the central welcome/status widget."""
        central = QWidget(self)
        layout = QVBoxLayout(central)

        self.welcome_label = QLabel("¡Bienvenido!", self)
        self.welcome_label.setAlignment(Qt.AlignCenter)
        self.welcome_label.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(self.welcome_label)

        current_row = QHBoxLayout()
        self.current_alumno_id_label = QLabel("ID de alumno actual:", self)
        self.current_alumno_id_value = QLabel("-", self)
        current_row.addWidget(self.current_alumno_id_label)
        current_row.addWidget(self.current_alumno_id_value)
        current_row.addStretch(1)
        layout.addLayout(current_row)

        current_adulto_row = QHBoxLayout()
        self.current_adulto_id_label = QLabel("ID de adulto actual:", self)
        self.current_adulto_id_value = QLabel("-", self)
        current_adulto_row.addWidget(self.current_adulto_id_label)
        current_adulto_row.addWidget(self.current_adulto_id_value)
        current_adulto_row.addStretch(1)
        layout.addLayout(current_adulto_row)

        layout.addStretch(1)
        self.setCentralWidget(central)
        self._refresh_current_alumno_id_label()
        self._refresh_current_adulto_id_label()

    def _refresh_current_alumno_id_label(self):
        """Update the current alumno ID status label from shared dialog state."""
        alumno_id = alumnos_dialogs.current_alumno_id
        alumno_name = alumnos_dialogs.current_alumno_name

        if alumno_id is None:
            self.current_alumno_id_value.setText("-")
        else:
            text = str(alumno_id)
            if alumno_name:
                text += f" - {alumno_name}"
            self.current_alumno_id_value.setText(text)

    def _refresh_current_adulto_id_label(self):
        """Update the current adulto ID status label from shared dialog state."""
        adulto_id = parientes_dialogs.current_adulto_id
        adulto_name = parientes_dialogs.current_adulto_name

        if adulto_id is None:
            self.current_adulto_id_value.setText("-")
        else:
            text = str(adulto_id)
            if adulto_name:
                text += f" - {adulto_name}"
            self.current_adulto_id_value.setText(text)

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
        self._restart_inactivity_timer()
        self._clear_training_mode_notice()
        if self._username.strip().lower() == "trainee":
            self.training_mode_notice = show_training_mode_notice(self)

    def _relogin_or_close_app(self) -> bool:
        """Hide the main window and relogin; return True when relogin succeeds."""
        self._clear_training_mode_notice()
        self._cleanup_trainee_temp_database()
        self.hide()

        # Use a top-level dialog so it cannot be blocked by a hidden parent.
        login = LoginDialog()
        if login.exec() == QDialog.Accepted:
            self._start_user_session(login.logged_in_username)
            self.show()
            return True

        return False

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
        if not self._relogin_or_close_app():
            self._allow_close = True
            self.close()

    def on_alumnos_nuevo(self):
        """Handle the Alumnos > Nuevo menu action."""
        log.info("Menú: Alumnos > Nuevo")
        NuevoAlumnoDialog(self).exec()
        self._refresh_current_alumno_id_label()

    def on_alumnos_buscar(self):
        """Handle the Alumnos > Buscar menu action."""
        log.info("Menú: Alumnos > Buscar")
        BuscarAlumnoDialog(self, is_admin=self._username.strip().lower() == "admin").exec()
        self._refresh_current_alumno_id_label()

    def on_alumnos_reportes(self):
        """Handle the Alumnos > Reportes menu action."""
        log.info("Menú: Alumnos > Reportes")
        QMessageBox.information(self, "Reportes de Alumnos", "Reportes de alumnos próximamente.")

    def on_parientes_nuevo(self):
        """Handle the Parientes > Nuevo menu action."""
        log.info("Menú: Parientes > Nuevo")
        NuevoParienteDialog(self).exec()
        self._refresh_current_adulto_id_label()

    def on_parientes_buscar(self):
        """Handle the Parientes > Buscar menu action."""
        log.info("Menú: Parientes > Buscar")
        BuscarParienteDialog(self, is_admin=self._username.strip().lower() == "admin").exec()
        self._refresh_current_adulto_id_label()

    def on_parientes_reportes(self):
        """Handle the Parientes > Reportes menu action."""
        log.info("Menú: Parientes > Reportes")
        QMessageBox.information(self, "Reportes de Parientes", "Reportes de parientes próximamente.")

    def on_cuentas_nuevo(self):
        """Handle the Cuentas > Nuevo menu action."""
        log.info("Menú: Cuentas > Nuevo")
        NuevoCuentaDialog(self).exec()

    def on_cuentas_buscar(self):
        """Handle the Cuentas > Buscar menu action."""
        log.info("Menú: Cuentas > Buscar")
        BuscarCuentaDialog(self, is_admin=self._username.strip().lower() == "admin").exec()

    def on_cuentas_reportes(self):
        """Handle the Cuentas > Reportes menu action."""
        log.info("Menú: Cuentas > Reportes")
        QMessageBox.information(self, "Reportes de Cuentas", "Reportes de cuentas próximamente.")

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

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from main import main as run_main

    run_main()
