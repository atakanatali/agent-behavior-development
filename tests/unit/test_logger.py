"""Unit tests for orchestify.utils.logger module."""
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

# Clear logger cache before importing
import orchestify.utils.logger as logger_module


class TestGetLogger:
    def setup_method(self):
        """Clear logger cache before each test."""
        logger_module._loggers.clear()

    def test_get_logger_returns_logger(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        logger = logger_module.get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_get_logger_caches(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        l1 = logger_module.get_logger("cached_test")
        l2 = logger_module.get_logger("cached_test")
        assert l1 is l2

    def test_get_logger_debug_level(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        logger = logger_module.get_logger("debug_test")
        assert logger.level == logging.DEBUG

    def test_get_logger_creates_log_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        logger_module.get_logger("dir_test")
        assert (tmp_path / ".orchestify" / "logs").exists()

    def test_get_logger_has_handlers(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        logger = logger_module.get_logger("handler_test")
        assert len(logger.handlers) >= 2  # file + console


class TestGetFileLogger:
    def test_creates_file_logger(self, tmp_path):
        log_file = tmp_path / "test.log"
        logger = logger_module.get_file_logger("file_test", log_file)
        assert isinstance(logger, logging.Logger)

    def test_creates_parent_dir(self, tmp_path):
        log_file = tmp_path / "subdir" / "test.log"
        logger_module.get_file_logger("dir_file_test", log_file)
        assert log_file.parent.exists()

    def test_writes_to_file(self, tmp_path):
        log_file = tmp_path / "write_test.log"
        logger = logger_module.get_file_logger("write_test", log_file)
        logger.setLevel(logging.DEBUG)
        logger.info("Test message")
        # Flush handlers
        for handler in logger.handlers:
            handler.flush()
        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content
