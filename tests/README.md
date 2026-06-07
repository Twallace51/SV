# Tests

Unit tests for the generic_template application, written with [pytest](https://docs.pytest.org/).

## Structure

| File                   | What it covers                                                                                           |
| ---------------------- | -------------------------------------------------------------------------------------------------------- |
| `conftest.py`          | Session-scoped `QApplication` fixture shared across all test modules                                     |
| `test_utils.py`        | `setup_logging()` and `acquire_single_instance_lock()`                                                   |
| `test_login_dialog.py` | `LoginDialog` — initialisation, password visibility toggle, credential validation, mouse-event shortcuts |
| `test_main_window.py`  | `MainWindow` — title bar, default size, central widget, menu bar actions                                 |

## Requirements

The application dependencies must be installed before running the tests:

```
pip install PySide6 pytest
```

## Running the tests

From the repository root:

```
pytest tests/ -v
```

Run a single module:

```
pytest tests/test_login_dialog.py -v
```

Run a specific test:

```
pytest tests/test_login_dialog.py::TestHandleLogin::test_valid_credentials_set_username -v
```

## Notes

- A headless display (e.g. `Xvfb` on Linux) is required when running in a CI environment without a GUI.  
  Set `QT_QPA_PLATFORM=offscreen` to avoid needing a real display:

    ```
    QT_QPA_PLATFORM=offscreen pytest tests/ -v
    ```

- The `acquire_single_instance_lock` tests acquire and release a real lock file in the system temp directory;  
  they are run serially by pytest and clean up after themselves.
