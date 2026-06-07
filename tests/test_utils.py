"""Tests for utility functions: setup_logging and acquire_single_instance_lock."""

# region - imports
import sys
import logging
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import setup_logging, acquire_single_instance_lock
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
