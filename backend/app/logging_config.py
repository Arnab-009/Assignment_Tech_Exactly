"""Centralised logging configuration."""
from __future__ import annotations

import logging
import sys

_NOISY_LOGGERS = (
    "httpx",
    "httpcore",
    "googleapiclient.discovery_cache",
    "google_genai",
    "google.genai",
    "urllib3",
)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once, writing structured-ish lines to stdout."""
    resolved = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=resolved,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
