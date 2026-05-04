import os
import sys

from loguru import logger


def setup_logging() -> None:
    """Configure loguru sinks and level."""
    logger.remove()
    level = os.getenv("LOG_LEVEL", "INFO")
    logger.add(sys.stderr, level=level, backtrace=False, diagnose=False)
