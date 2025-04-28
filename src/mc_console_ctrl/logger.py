"""Structured JSON logging configuration.

This module provides a structured logging setup with JSON formatting and queue-based
handling for thread-safe logging. It includes custom formatters and filters for
managing log levels and output formatting.

Example:
    ```python
    import logging
    from logger import setup_logging

    logger = logging.getLogger(__name__)
    setup_logging()

    logger.info("Application started", extra={"version": "1.0.0"})
    ```
"""

import atexit
import datetime as dt
import json
import logging
import logging.config
import logging.handlers
import pathlib
from dataclasses import dataclass
from typing import Optional
from typing_extensions import override

# Built-in attributes of LogRecord that should not be included in extra fields
LOG_RECORD_BUILTIN_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}

# Global queue listener instance
_queue_listener: Optional[logging.handlers.QueueListener] = None


def setup_logging(config_path: Optional[pathlib.Path] = None) -> None:
    """Set up logging configuration for the application.

    Args:
        config_path: Optional path to a JSON logging configuration file.
                    If not provided, looks for logging_config.json in the same directory as this module.

    Raises:
        FileNotFoundError: If logging_config.json is not found
        json.JSONDecodeError: If the config file is not valid JSON
        ValueError: If the configuration is invalid
    """
    global _queue_listener

    if config_path is None:
        module_dir = pathlib.Path(__file__).parent
        config_path = module_dir / "logging_config.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Logging configuration file not found: {config_path}. "
            "Please ensure logging_config.json exists in the module directory."
        )

    try:
        with open(config_path) as f_in:
            config = json.load(f_in)

        # Register our formatter class in the config
        if "formatters" in config:
            for formatter in config["formatters"].values():
                if isinstance(formatter, dict) and formatter.get("()", "").endswith(
                    "StructuredJSONFormatter"
                ):
                    formatter["()"] = f"{__name__}.StructuredJSONFormatter"

                # Ensure log directory exists if file handlers are configured
        for handler in config.get("handlers", {}).values():
            filename = handler.get("filename")
            if filename:
                log_path = pathlib.Path(filename).parent
                log_path.mkdir(parents=True, exist_ok=True)

        logging.config.dictConfig(config)

        # Set up queue handler if configured
        queue_handler = logging.getHandlerByName("queue_handler")
        if isinstance(queue_handler, logging.handlers.QueueHandler):
            _queue_listener = getattr(queue_handler, "listener", None)
            if _queue_listener is not None:
                _queue_listener.start()
                atexit.register(_queue_listener.stop)

    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid logging configuration in {config_path}: {str(e)}", e.doc, e.pos
        ) from e
    except ValueError as e:
        raise ValueError(
            f"Invalid logging configuration in {config_path}: {str(e)}"
        ) from e


@dataclass
class FormatterKeys:
    """Configuration for JSON log formatter keys mapping."""

    timestamp: str = "created"
    level: str = "levelname"
    logger: str = "name"
    message: str = "message"
    file: str = "filename"
    line: str = "lineno"


class StructuredJSONFormatter(logging.Formatter):
    def __init__(
        self,
        *,
        fmt_keys: dict[str, str] | None = None,
    ):
        super().__init__()
        self.fmt_keys = fmt_keys if fmt_keys is not None else {}

    @override
    def format(self, record: logging.LogRecord) -> str:
        message = self._prepare_log_dict(record)
        return json.dumps(message, default=str)

    def _prepare_log_dict(self, record: logging.LogRecord):
        always_fields = {
            "message": record.getMessage(),
            "timestamp": dt.datetime.fromtimestamp(
                record.created, tz=dt.timezone.utc
            ).isoformat(),
        }
        if record.exc_info is not None:
            always_fields["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info is not None:
            always_fields["stack_info"] = self.formatStack(record.stack_info)

        message = {
            key: msg_val
            if (msg_val := always_fields.pop(val, None)) is not None
            else getattr(record, val)
            for key, val in self.fmt_keys.items()
        }
        message.update(always_fields)

        for key, val in record.__dict__.items():
            if key not in LOG_RECORD_BUILTIN_ATTRS:
                message[key] = val

        return message


class NonErrorFilter(logging.Filter):
    """Filter that only allows non-error log records (INFO and below)."""

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= logging.INFO
