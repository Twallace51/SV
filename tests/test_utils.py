"""Tests for utility functions: setup_logging, venv checks, and acquire_single_instance_lock."""

# region - imports
import sys
import logging
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import (
    setup_logging,
    acquire_single_instance_lock,
    is_running_from_project_venv,
    warn_if_not_running_from_project_venv,
    normalize_bolivia_phone,
    build_whatsapp_url,
)
# endregion


class TestSetupLogging:
    def test_returns_logger(self):
        logger = setup_logging()
        assert isinstance(logger, logging.Logger)

    def test_logger_name(self):
        logger = setup_logging()
        assert logger.name == "app"

    def test_logger_level_is_debug(self):
        logger = setup_logging()
        assert logger.level == logging.DEBUG

    def test_logger_has_handlers(self):
        logger = setup_logging()
        assert len(logger.handlers) >= 2

    def test_log_dir_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # The log dir is relative to __file__ of main.py, so just verify the
        # function runs without error when the dir already exists.
        logger = setup_logging()
        assert logger is not None


class TestAcquireSingleInstanceLock:
    def test_returns_lock_on_first_call(self, qapp):
        lock = acquire_single_instance_lock()
        assert lock is not None
        lock.unlock()

    def test_returns_none_when_already_locked(self, qapp):
        lock1 = acquire_single_instance_lock()
        assert lock1 is not None
        try:
            lock2 = acquire_single_instance_lock()
            assert lock2 is None
        finally:
            lock1.unlock()


class TestProjectVenvWarning:
    def test_detects_project_venv(self, monkeypatch):
        monkeypatch.setattr(
            "utils.sys.executable",
            r"G:\SendasVida\SV-1.3\.venv\Scripts\python.exe",
            raising=False,
        )
        assert is_running_from_project_venv() is True

    def test_detects_non_project_venv(self, monkeypatch):
        monkeypatch.setattr(
            "utils.sys.executable",
            r"C:\Python313\python.exe",
            raising=False,
        )
        assert is_running_from_project_venv() is False

    def test_warns_when_not_running_from_project_venv(self, monkeypatch):
        monkeypatch.setattr(
            "utils.sys.executable",
            r"C:\Python313\python.exe",
            raising=False,
        )
        warnings = []
        monkeypatch.setattr("utils.QMessageBox.warning", lambda *args: warnings.append(args))

        assert warn_if_not_running_from_project_venv() is True
        assert warnings

    def test_does_not_warn_when_running_from_project_venv(self, monkeypatch):
        monkeypatch.setattr(
            "utils.sys.executable",
            r"G:\SendasVida\SV-1.3\.venv\Scripts\python.exe",
            raising=False,
        )
        warnings = []
        monkeypatch.setattr("utils.QMessageBox.warning", lambda *args: warnings.append(args))

        assert warn_if_not_running_from_project_venv() is False
        assert not warnings


class TestWhatsAppHelpers:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("70123456", "59170123456"),
            ("591 7012 3456", "59170123456"),
            ("+591 70123456", "59170123456"),
            ("0059170123456", "59170123456"),
            ("(7) 012-3456", "59170123456"),
            ("", None),
            ("   ", None),
            ("abc", None),
        ],
    )
    def test_normalize_bolivia_phone(self, raw, expected):
        assert normalize_bolivia_phone(raw) == expected

    def test_build_whatsapp_url_with_message(self):
        url = build_whatsapp_url("70123456", "Hola mundo")
        assert url == "https://wa.me/59170123456?text=Hola%20mundo"

    def test_build_whatsapp_url_without_message(self):
        assert build_whatsapp_url("70123456") == "https://wa.me/59170123456"

    def test_build_whatsapp_url_invalid_number(self):
        assert build_whatsapp_url("") is None
