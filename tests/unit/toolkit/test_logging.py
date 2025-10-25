"""Tests for toolkit logging configuration."""

from phantom.toolkit.logging import configure_logging, get_logger


class TestConfigureLogging:
    def test_configure_json_format_does_not_raise(self):
        configure_logging(level="INFO", format="json")

    def test_configure_console_format_does_not_raise(self):
        configure_logging(level="DEBUG", format="console")

    def test_configure_warning_level_does_not_raise(self):
        # basicConfig is a no-op once handlers exist, so we only verify
        # configure_logging itself succeeds without error at each level.
        configure_logging(level="WARNING", format="console")

    def test_configure_without_timestamps(self):
        configure_logging(
            level="INFO",
            format="json",
            include_timestamps=False,
        )


class TestGetLogger:
    def test_returns_bound_logger(self):
        logger = get_logger("phantom.test")
        assert logger is not None

    def test_loggers_with_different_names_are_distinct(self):
        logger_a = get_logger("module.a")
        logger_b = get_logger("module.b")
        assert logger_a is not logger_b
