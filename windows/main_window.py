"""Main application window."""

# region - imports

import logging
import sqlite3
import shutil
import tempfile
import sys
import gc
import time
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QLabel, QDialog, QWidget,
    QVBoxLayout, QTextEdit, QDialogButtonBox, QMessageBox,
    QHBoxLayout,
)
from PySide6.QtGui import QAction, QShowEvent, QCloseEvent, QColor, QPalette
from PySide6.QtCore import Qt, QEvent, QTimer, QCoreApplication

try:
    from modules import config
    from __init__ import (
        PROJECT_NAME,
        VERSION,
        DB_PATH,
        get_active_db_path,
        set_active_db_path,
        reset_active_db_path,
    )
    from modules.utils import show_training_mode_notice
    from dialogs.login import LoginDialog
    import dialogs.alumnos as alumnos_dialogs
    import dialogs.parientes as parientes_dialogs
    from dialogs.alumnos import NuevoAlumnoDialog, BuscarAlumnoDialog
    from dialogs.reportes_alumnos import (
        ReporteAlumnosBecadosDialog,
        ReporteAlumnosCarnetDialog,
        ReporteAlumnosCumpleanosDialog,
        ReporteAlumnosParientesDialog,
        ReporteAlumnosPorGradoDialog,
        ReporteAlumnosRudeDialog,
        )
    from dialogs.reportes_adultos import ReporteAdultosConAlumnosDialog
    from dialogs.whatsapp import EnviarWhatsAppDialog
    from dialogs.email import EnviarEmailDialog
    from dialogs.parientes import NuevoParienteDialog, BuscarParienteDialog
    from dialogs.cuentas import NuevoCuentaDialog, BuscarCuentaDialog
    from dialogs.reportes_cuentas import ReporteCuentasTotalDialog, ReporteCuentasAlumnosDialog, ReporteCuentasDetallesDialog

except (ModuleNotFoundError, ImportError):
    # Support running this file directly from the windows/ directory.
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    # A first failed import can cache windows/__init__.py as "__init__".
    # Remove it so the fallback import resolves against project_root.
    sys.modules.pop("__init__", None)
    from modules import config
    from __init__ import (
        PROJECT_NAME,
        VERSION,
        DB_PATH,
        get_active_db_path,
        set_active_db_path,
        reset_active_db_path,
        )
    from modules.utils import show_training_mode_notice
    from dialogs.login import LoginDialog
    import dialogs.alumnos as alumnos_dialogs
    import dialogs.parientes as parientes_dialogs
    from dialogs.alumnos import NuevoAlumnoDialog, BuscarAlumnoDialog
    from dialogs.reportes_alumnos import (
        ReporteAlumnosBecadosDialog,
        ReporteAlumnosCarnetDialog,
        ReporteAlumnosCumpleanosDialog,
        ReporteAlumnosParientesDialog,
        ReporteAlumnosPorGradoDialog,
        ReporteAlumnosRudeDialog,
        )
    from dialogs.reportes_adultos import ReporteAdultosConAlumnosDialog
    from dialogs.whatsapp import EnviarWhatsAppDialog
    from dialogs.email import EnviarEmailDialog
    from dialogs.parientes import NuevoParienteDialog, BuscarParienteDialog
    from dialogs.cuentas import NuevoCuentaDialog, BuscarCuentaDialog
    from dialogs.reportes_cuentas import ReporteCuentasTotalDialog, ReporteCuentasAlumnosDialog, ReporteCuentasDetallesDialog

# endregion

log = logging.getLogger("app")
log.setLevel(logging.INFO)

class MainWindow(QMainWindow):
    """Primary application window shown after successful login."""

    _INACTIVITY_TIMEOUT_MS = config.INACTIVITY_TIMEOUT_MS
    _AUTO_BACKUP_INTERVAL_DAYS = 7
    _MAX_BACKUP_FILES = 7
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
        self._automatic_backup_checked = False
        self._apply_window_title()
        self.resize(800, 600)
        self._build_menu_bar()
        self._build_central()
        self._configure_session_database(self._username)
        self._refresh_backup_action_state()
        self._ensure_monthly_pension_records()
        self._setup_inactivity_timer()
        self._apply_window_title()
        self._apply_session_theme()

    def _backup_directory_for(self, db_path: Path) -> Path:
        """Return the folder used to store database backups."""
        return db_path.parent / "Backups"

    def _is_training_mode(self) -> bool:
        """Return True when the current session is running in training mode."""
        return self._username.strip().lower() == "trainee"

    def _refresh_backup_action_state(self):
        """Enable manual backups only for non-training sessions."""
        if hasattr(self, "backup_action"):
            self.backup_action.setEnabled(not self._is_training_mode())

    def _backup_glob_for(self, db_path: Path) -> str:
        """Return the filename pattern used for backups of a database."""
        return f"{db_path.stem}_backup_*{db_path.suffix}"

    def _list_backup_files(self, db_path: Path) -> list[Path]:
        """List existing backups sorted from oldest to newest."""
        backup_dir = self._backup_directory_for(db_path)
        if not backup_dir.exists():
            return []
        return sorted(
            backup_dir.glob(self._backup_glob_for(db_path)),
            key=lambda path: path.stat().st_mtime,
        )

    def _prune_old_backups(self, db_path: Path):
        """Keep at most the configured number of backup files."""
        backup_files = self._list_backup_files(db_path)
        excess_files = len(backup_files) - self._MAX_BACKUP_FILES
        for backup_file in backup_files[:max(excess_files, 0)]:
            try:
                backup_file.unlink()
            except OSError:
                log.exception("Error al eliminar backup antiguo: %s", backup_file)

    def _create_database_backup(self, db_path: Path) -> Path:
        """Create a timestamped database backup and enforce retention."""
        backup_dir = self._backup_directory_for(db_path)
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"

        shutil.copy2(db_path, backup_file)
        self._prune_old_backups(db_path)
        return backup_file

    def _should_run_weekly_backup(self, db_path: Path, now: datetime | None = None) -> bool:
        """Return True when the latest backup is at least one week old."""
        backup_files = self._list_backup_files(db_path)
        if not backup_files:
            return True

        current_time = now or datetime.now()
        latest_mtime = datetime.fromtimestamp(backup_files[-1].stat().st_mtime)
        return (current_time - latest_mtime).days >= self._AUTO_BACKUP_INTERVAL_DAYS

    def _run_weekly_database_backup(self):
        """Create a silent weekly backup of the production database when due."""
        if self._is_training_mode():
            log.info("Backup automático omitido en modo entrenamiento")
            return

        db_path = Path(DB_PATH)
        if not db_path.exists():
            log.warning("No se encontró la base de datos para backup automático: %s", db_path)
            return

        if not self._should_run_weekly_backup(db_path):
            return

        try:
            backup_file = self._create_database_backup(db_path)
        except OSError:
            log.exception("Error al crear backup automático de base de datos")
            return

        log.info("Backup automático semanal creado: %s", backup_file)

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
        if current.day != 1 or current.month < config.PENSION_FIRST_MONTH or current.month > config.PENSION_LAST_MONTH:
            return

        mes_actual = config.MONTH_NAMES_ES[current.month - 1]
        aclaracion = f"Pension para {mes_actual}"
        fecha_actual = current.strftime("%Y-%m-%d")

        conn = None
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
        except Exception:
            log.exception("No se pudo confirmar/agregar registros de pensión mensual en ctas")
        finally:
            if conn is not None:
                conn.close()

    def _apply_window_title(self):
        """Apply the current title text to the native window."""
        title = f"{PROJECT_NAME} - Versión: {VERSION} - Usuario: {self._username}"
        if self._trainee_temp_db_path is not None:
            title += " - Modo Entrenamiento DB Temporal"
        self.setWindowTitle(title)

    def showEvent(self, event: QShowEvent):
        """Reapply title on show to keep native title bar in sync."""
        self._apply_window_title()
        if not self._automatic_backup_checked:
            self._automatic_backup_checked = True
            self._run_weekly_database_backup()
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

        # On Windows a recently closed sqlite3 connection may still hold the
        # file briefly, and an unclosed connection object only releases its
        # handle once it is garbage collected. Force a collection and retry a
        # few times before giving up.
        last_error = None
        for attempt in range(5):
            try:
                temp_db.unlink(missing_ok=True)
                log.info("Base temporal de trainee eliminada: %s", temp_db)
                return
            except PermissionError as exc:
                last_error = exc
                gc.collect()
                time.sleep(0.2)
            except OSError as exc:
                last_error = exc
                break
        log.warning(
            "No se pudo eliminar base temporal de trainee: %s (%s)",
            temp_db,
            last_error,
        )

    def _build_menu_bar(self):
        """Create the menu bar and connect actions to handlers."""
        menu_bar = self.menuBar()
        menu_font = menu_bar.font()
        menu_font.setPixelSize(22)
        menu_bar.setFont(menu_font)
        menu_bar.setStyleSheet("QMenu::item { font-size: 18px; }")

        # Archivo menu
        self.file_menu = menu_bar.addMenu("&Archivo")
        self.backup_action = QAction("Crear &Backup de Base de Datos", self)
        self.backup_action.triggered.connect(self.on_backup_database)
        self.file_menu.addAction(self.backup_action)

        # Alumnos menu
        self.alumnos_menu = menu_bar.addMenu("&Alumnos")
        alumnos_nuevo_action = QAction("&Nuevo", self)
        alumnos_nuevo_action.triggered.connect(self.on_alumnos_nuevo)
        self.alumnos_menu.addAction(alumnos_nuevo_action)
        alumnos_buscar_action = QAction("&Buscar", self)
        alumnos_buscar_action.triggered.connect(self.on_alumnos_buscar)
        self.alumnos_menu.addAction(alumnos_buscar_action)
        self.alumnos_reportes_menu = self.alumnos_menu.addMenu("&Reportes")
        self.alumnos_reportes_action = self.alumnos_reportes_menu.menuAction()
        self.alumnos_por_grados_action = QAction("Por &grados", self)
        self.alumnos_por_grados_action.triggered.connect(self.on_alumnos_por_grados)
        self.alumnos_reportes_menu.addAction(self.alumnos_por_grados_action)
        self.alumnos_becados_action = QAction("&Becados", self)
        self.alumnos_becados_action.triggered.connect(self.on_alumnos_becados)
        self.alumnos_reportes_menu.addAction(self.alumnos_becados_action)
        self.alumnos_rude_action = QAction("&Rude", self)
        self.alumnos_rude_action.triggered.connect(self.on_alumnos_rude)
        self.alumnos_reportes_menu.addAction(self.alumnos_rude_action)
        self.alumnos_carnet_action = QAction("&Carnet", self)
        self.alumnos_carnet_action.triggered.connect(self.on_alumnos_carnet)
        self.alumnos_reportes_menu.addAction(self.alumnos_carnet_action)
        self.alumnos_cumpleanos_action = QAction("&Cumpleanos", self)
        self.alumnos_cumpleanos_action.triggered.connect(self.on_alumnos_cumpleanos)
        self.alumnos_reportes_menu.addAction(self.alumnos_cumpleanos_action)
        self.alumnos_parientes_action = QAction("&Parientes", self)
        self.alumnos_parientes_action.triggered.connect(self.on_alumnos_parientes)
        self.alumnos_reportes_menu.addAction(self.alumnos_parientes_action)

        # Parientes menu
        self.adultos_menu = menu_bar.addMenu("&Adultos")
        parientes_nuevo_action = QAction("&Nuevo", self)
        parientes_nuevo_action.triggered.connect(self.on_parientes_nuevo)
        self.adultos_menu.addAction(parientes_nuevo_action)
        parientes_buscar_action = QAction("&Buscar", self)
        parientes_buscar_action.triggered.connect(self.on_parientes_buscar)
        self.adultos_menu.addAction(parientes_buscar_action)
        self.adultos_reportes_menu = self.adultos_menu.addMenu("&Reportes")
        self.adultos_alumnos_action = QAction("Alumnos &relacionados", self)
        self.adultos_alumnos_action.triggered.connect(self.on_adultos_alumnos)
        self.adultos_reportes_menu.addAction(self.adultos_alumnos_action)
        self.adultos_whatsapp_action = QAction("Enviar &WhatsApp", self)
        self.adultos_whatsapp_action.triggered.connect(self.on_adultos_whatsapp)
        self.adultos_menu.addAction(self.adultos_whatsapp_action)
        self.adultos_email_action = QAction("Enviar &Email", self)
        self.adultos_email_action.triggered.connect(self.on_adultos_email)
        self.adultos_menu.addAction(self.adultos_email_action)

        # Cuentas menu
        self.cuentas_menu = menu_bar.addMenu("&Cuentas")
        cuentas_nuevo_credito_action = QAction("Nuevo &Crédito", self)
        cuentas_nuevo_credito_action.triggered.connect(self.on_cuentas_nuevo_credito)
        self.cuentas_menu.addAction(cuentas_nuevo_credito_action)
        cuentas_nuevo_debito_action = QAction("Nuevo &Débito", self)
        cuentas_nuevo_debito_action.triggered.connect(self.on_cuentas_nuevo_debito)
        self.cuentas_menu.addAction(cuentas_nuevo_debito_action)
        cuentas_buscar_action = QAction("&Buscar", self)
        cuentas_buscar_action.triggered.connect(self.on_cuentas_buscar)
        self.cuentas_menu.addAction(cuentas_buscar_action)
        self.cuentas_reportes_menu = self.cuentas_menu.addMenu("&Reportes")
        self.cuentas_reportes_action = self.cuentas_reportes_menu.menuAction()
        self.cuentas_total_action = QAction("&Total", self)
        self.cuentas_total_action.triggered.connect(self.on_cuentas_reportes)
        self.cuentas_reportes_menu.addAction(self.cuentas_total_action)
        self.cuentas_alumnos_action = QAction("&Alumnos", self)
        self.cuentas_alumnos_action.triggered.connect(self.on_cuentas_reportes_alumnos)
        self.cuentas_reportes_menu.addAction(self.cuentas_alumnos_action)
        self.cuentas_detalles_action = QAction("&Detalles", self)
        self.cuentas_detalles_action.triggered.connect(self.on_cuentas_reportes_detalles)
        self.cuentas_reportes_menu.addAction(self.cuentas_detalles_action)

        # Ayuda menu
        self.help_menu = menu_bar.addMenu("A&yuda")
        about_action = QAction("&Acerca de", self)
        about_action.triggered.connect(self.on_about)
        self.help_menu.addAction(about_action)

    def _build_central(self):
        """Create and attach the central welcome/status widget."""
        central = QWidget(self)
        central.setObjectName("sessionCentral")
        central.setAutoFillBackground(True)
        body_font = central.font()
        body_font.setPixelSize(18)
        central.setFont(body_font)
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

        palette = central_widget.palette()
        if self._username.strip().lower() == "trainee":
            palette.setColor(QPalette.Window, QColor("#ffd6d6"))
        else:
            palette.setColor(QPalette.Window, QColor(Qt.transparent))
        central_widget.setPalette(palette)

    def _clear_training_mode_notice(self):
        """Close and forget any visible training mode notice."""
        notice = getattr(self, "training_mode_notice", None)
        if notice is not None:
            notice.close()
            self.training_mode_notice = None

    def _start_user_session(self, username: str):
        """Apply session state for a newly authenticated user."""
        self._username = username or "unknown"
        self._automatic_backup_checked = False
        self._configure_session_database(self._username)
        self._refresh_backup_action_state()
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
        if self._is_training_mode():
            QMessageBox.information(
                self,
                "Backup",
                "Los backups están deshabilitados en modo entrenamiento.",
            )
            return

        db_path = Path(DB_PATH)
        if not db_path.exists():
            QMessageBox.warning(
                self,
                "Backup",
                f"No se encontró la base de datos en:\n{db_path}",
            )
            return

        try:
            backup_file = self._create_database_backup(db_path)
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

    def on_alumnos_por_grados(self):
        """Handle the Alumnos > Reportes > Por grados menu action."""
        log.info("Menú: Alumnos > Reportes > Por grados")
        ReporteAlumnosPorGradoDialog(self).exec()

    def on_alumnos_becados(self):
        """Handle the Alumnos > Reportes > Becados menu action."""
        log.info("Menú: Alumnos > Reportes > Becados")
        ReporteAlumnosBecadosDialog(self).exec()

    def on_alumnos_rude(self):
        """Handle the Alumnos > Reportes > Rude menu action."""
        log.info("Menú: Alumnos > Reportes > Rude")
        ReporteAlumnosRudeDialog(self).exec()

    def on_alumnos_carnet(self):
        """Handle the Alumnos > Reportes > Carnet menu action."""
        log.info("Menú: Alumnos > Reportes > Carnet")
        ReporteAlumnosCarnetDialog(self).exec()

    def on_alumnos_cumpleanos(self):
        """Handle the Alumnos > Reportes > Cumpleanos menu action."""
        log.info("Menú: Alumnos > Reportes > Cumpleanos")
        ReporteAlumnosCumpleanosDialog(self).exec()

    def on_alumnos_parientes(self):
        """Handle the Alumnos > Reportes > Parientes menu action."""
        log.info("Menú: Alumnos > Reportes > Parientes")
        ReporteAlumnosParientesDialog(self).exec()

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

    def on_adultos_alumnos(self):
        """Handle the Adultos > Reportes > Alumnos relacionados menu action."""
        log.info("Menú: Adultos > Reportes > Alumnos relacionados")
        ReporteAdultosConAlumnosDialog(self).exec()

    def on_adultos_whatsapp(self):
        """Handle the Adultos > Enviar WhatsApp menu action."""
        log.info("Menú: Adultos > Enviar WhatsApp")
        EnviarWhatsAppDialog(self).exec()

    def on_adultos_email(self):
        """Handle the Adultos > Enviar Email menu action."""
        log.info("Menú: Adultos > Enviar Email")
        EnviarEmailDialog(self).exec()

    def on_cuentas_nuevo_credito(self):
        """Handle the Cuentas > Nuevo Crédito menu action."""
        log.info("Menú: Cuentas > Nuevo Crédito")
        NuevoCuentaDialog(self, mode="credito").exec()
        self._refresh_current_alumno_id_label()
        self._refresh_current_adulto_id_label()

    def on_cuentas_nuevo_debito(self):
        """Handle the Cuentas > Nuevo Débito menu action."""
        log.info("Menú: Cuentas > Nuevo Débito")
        NuevoCuentaDialog(self, mode="debito").exec()
        self._refresh_current_alumno_id_label()
        self._refresh_current_adulto_id_label()

    def on_cuentas_buscar(self):
        """Handle the Cuentas > Buscar menu action."""
        log.info("Menú: Cuentas > Buscar")
        BuscarCuentaDialog(self, is_admin=self._username.strip().lower() == "admin").exec()
        self._refresh_current_alumno_id_label()
        self._refresh_current_adulto_id_label()

    def on_cuentas_reportes(self):
        """Handle the Cuentas > Reportes > Total menu action."""
        log.info("Menú: Cuentas > Reportes > Total")
        ReporteCuentasTotalDialog(self).exec()

    def on_cuentas_reportes_alumnos(self):
        """Handle the Cuentas > Reportes > Alumnos menu action."""
        log.info("Menú: Cuentas > Reportes > Alumnos")
        ReporteCuentasAlumnosDialog(self).exec()

    def on_cuentas_reportes_detalles(self):
        """Handle the Cuentas > Reportes > Detalles menu action."""
        log.info("Menú: Cuentas > Reportes > Detalles")
        ReporteCuentasDetallesDialog(self).exec()

    def on_about(self):
        """Display application About information."""
        log.info("Menú: Ayuda > Acerca de")
        about_path = Path(__file__).parent.parent / "md" / "About.md"
        about_text = (
            about_path.read_text(encoding="utf-8")
            if about_path.exists()
            else "# Acerca de\n\nNo se encontró md/About.md."
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
