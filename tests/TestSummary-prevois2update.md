Here’s what each test module currently covers:

test_login_dialog.py: validates LoginDialog UI and login behavior.

Window/title text, fixed size, default password masking, initial state.
Quit button rejects dialog.
Training mode button auto-fills trainee credentials and accepts.
Password show/hide toggle behavior.
Valid credentials for admin, user, trainee.
Invalid credentials handling (warning path, password cleared, username unchanged).
Trainee wrong-password reminder message content.
Username whitespace trimming.
Right-click press/release internal flag handling.
test_main_window.py: validates MainWindow construction, menu structure, menu actions, session flow, and monthly pension sync.

Initial title, size, central labels, inactivity timer.
Menu presence/order (Navegación, Archivo, Alumnos/Parientes/Cuentas Reportes, Ayuda).
Alumnos report actions present and wired (Por grados, Becados, Rude, Cumpleanos).
Action triggers open expected dialogs.
Logout/relogin behavior for accept/reject paths.
Trainee temporary DB creation/cleanup.
Running main_window module as script delegates to main.main.
Monthly pension auto-insert behavior and duplicate prevention.
test_reportes_alumnos.py: validates alumno report dialog data selection and rendering/export formatting.

Grouped report includes only valid positive-grade alumnos.
Markdown and HTML generation structure.
Continuous output vs page-break behavior.
XLSX writer creates valid package.
Becados report filters pension = 0 and shows expected columns.
Cumpleanos report column layout and MM-dd ordering.
Rude report includes RUDE column, excludes pension/carnet/id_grado columns, and has no becados filter.
test_utils.py: validates utility functions.

setup_logging returns app logger with DEBUG level and handlers.
Logging setup runs with expected directory assumptions.
Single-instance lock acquisition behavior (first succeeds, second fails while held).

Also, conftest.py provides a shared session-scoped QApplication fixture used by GUI tests.
