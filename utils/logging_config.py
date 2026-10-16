"""Structured logging configuration with automatic secret masking."""
import logging
import re
import sys
from typing import Optional


class SecretMaskingFilter(logging.Filter):
    """Filter that masks API keys, secrets, and authorization tokens."""

    API_KEY_PATTERNS = [
        re.compile(r"AIza[0-9A-Za-z\-_]{35}"),  # Standard Google API Key pattern
        re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{8,})['\"]?"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            masked_msg = record.msg
            for pattern in self.API_KEY_PATTERNS:
                masked_msg = pattern.sub("[REDACTED_SECRET]", masked_msg)
            record.msg = masked_msg
        return True


def get_logger(name: str = "ai_quiz_platform", level: int = logging.INFO) -> logging.Logger:
    """Get a configured logger instance with formatting and secret masking."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)

        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        handler.addFilter(SecretMaskingFilter())

        logger.addHandler(handler)
        logger.propagate = False

    return logger
