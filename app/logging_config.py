"""
Structured logging setup (structlog), configured once at import time and
reused everywhere via get_logger(__name__). Output is JSON lines to stdout
— the same shape of thing Pino gives the Node/TypeScript projects, so log
aggregation tooling doesn't need a special case for this service.

Log level is controlled by LOG_LEVEL (default INFO). Set LOG_FORMAT=console
for human-readable colored output during local development.
"""
from __future__ import annotations

import logging
import os
import sys

import structlog

_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
_LOG_FORMAT = os.environ.get("LOG_FORMAT", "json").lower()

logging.basicConfig(format="%(message)s", stream=sys.stdout, level=_LOG_LEVEL)

_shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
]

structlog.configure(
    processors=_shared_processors
    + [
        structlog.processors.JSONRenderer()
        if _LOG_FORMAT == "json"
        else structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(_LOG_LEVEL)),
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)


def get_logger(name: str):
    return structlog.get_logger(name)
