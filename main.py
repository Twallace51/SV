"""Application entry point."""

# region - imports

import sys

try:
    from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
except ModuleNotFoundError:
    sys.stderr.write(
        "Missing required dependency: PySide6\n"
        "Install it with: python -m pip install PySide6\n"
    )
    sys.exit(1)

from utils import setup_logging, check_latest_pip_available, check_pytest_available
from utils import acquire_single_instance_lock, show_training_mode_notice, clear_terminal
from dialogs.login import LoginDialog
from windows.main_window import MainWindow

# endregion

def main() -> int:
    """Run application startup, login flow, and event loop."""

    # region - stratup checks

    clear_terminal()
    check_latest_pip_available()
    check_pytest_available()

    # endregion

    app = QApplication(sys.argv)

    # region - instance_lock

    instance_lock = acquire_single_instance_lock()
    if instance_lock is None:
        QMessageBox.warning(None, "Ya en ejecución", "La aplicación ya está en ejecución.")
        return 1

    # endregion

    # region - login dialog

    login = LoginDialog()
    if login.exec() != QDialog.Accepted:
        app.quit()
        return 0

    window = MainWindow(login.logged_in_username or "unknown")
    window.show()
    if login.logged_in_username.strip().lower() == "trainee":
        window.training_mode_notice = show_training_mode_notice(window)

    # endregion

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
