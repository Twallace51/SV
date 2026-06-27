"""Utility functions for the application."""

# region - imports

import sys
import os
import json
import logging
import logging.handlers
import re
from pathlib import Path
from importlib import metadata
from urllib.error import URLError
from urllib.request import urlopen

from PySide6.QtWidgets import QMainWindow, QMessageBox
from PySide6.QtCore import QLockFile, QStandardPaths, QTimer

from __init__ import PROJECT_NAME

# endregion

log = logging.getLogger("app")
#logger.setLevel(logging.DEBUG)
log.setLevel(logging.INFO)


def setup_logging() -> logging.Logger:
    """Configure and return the application logger."""
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger("app")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(module)s:%(lineno)d\n  %(message)s",
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


def check_pytest_available() -> None:
    """Confirm that pytest is installed and report its version."""


def is_running_from_project_venv() -> bool:
    """Return True when the active interpreter comes from the repo .venv."""
    interpreter_path = Path(sys.executable).resolve()
    return ".venv" in interpreter_path.parts


def warn_if_not_running_from_project_venv(parent: QMainWindow | None = None) -> bool:
    """Warn the user when the app is not running from the repository .venv."""
    if is_running_from_project_venv():
        return False

    message = (
        "Este proyecto debe ejecutarse con la virtualenv del repositorio (.venv).\n"
        f"Intérprete actual: {sys.executable}\n"
        "Seleccione la opción .venv en VS Code o active esa virtualenv antes de iniciar."
    )
    log.warning(message.replace("\n", " "))
    QMessageBox.warning(parent, f"{PROJECT_NAME} - Entorno recomendado", message)
    return True


def show_training_mode_notice(parent: QMainWindow) -> QMessageBox:
    """Show the trainee session notice and auto-close it after 8 seconds."""
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


BOLIVIA_COUNTRY_CODE = "591"


def normalize_bolivia_phone(raw: str, country_code: str = BOLIVIA_COUNTRY_CODE) -> str | None:
    """Return a wa.me-ready phone number (digits only) for a Bolivian number.

    Strips spaces, dashes, parentheses and a leading ``+``/``00``. A bare
    local mobile (8 digits) is prefixed with ``country_code``. Returns ``None``
    when the input has no usable digits.
    """
    digits = "".join(ch for ch in str(raw or "") if ch.isdigit())
    if not digits:
        return None
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith(country_code):
        return digits
    return f"{country_code}{digits}"


def build_whatsapp_url(phone: str, message: str = "", country_code: str = BOLIVIA_COUNTRY_CODE) -> str | None:
    """Return a ``https://wa.me/...`` click-to-chat URL, or ``None`` if invalid."""
    from urllib.parse import quote

    number = normalize_bolivia_phone(phone, country_code)
    if number is None:
        return None
    url = f"https://wa.me/{number}"
    if message:
        url += f"?text={quote(message)}"
    return url


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(raw: str) -> str | None:
    """Return a trimmed, lower-cased email address, or ``None`` if invalid."""
    candidate = str(raw or "").strip()
    if not candidate:
        return None
    return candidate.lower() if _EMAIL_RE.match(candidate) else None


def build_mailto_url(
    recipients: "str | list[str] | tuple[str, ...]",
    subject: str = "",
    body: str = "",
    use_bcc: bool = False,
) -> str | None:
    """Return a ``mailto:`` URL, or ``None`` when no valid recipient is given.

    ``recipients`` may be a single address or an iterable of addresses; invalid
    ones are dropped. When ``use_bcc`` is True the recipients are placed in the
    ``bcc`` field (keeping addresses private for a group send) and the primary
    ``to`` is left empty.
    """
    from urllib.parse import quote, urlencode

    if isinstance(recipients, str):
        recipients = [recipients]
    valid = [email for email in (normalize_email(r) for r in recipients) if email]
    if not valid:
        return None

    params = {}
    if use_bcc:
        url = "mailto:"
        params["bcc"] = ",".join(valid)
    else:
        url = "mailto:" + ",".join(valid)
    if subject:
        params["subject"] = subject
    if body:
        params["body"] = body

    if params:
        url += "?" + urlencode(params, quote_via=quote)
    return url


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
