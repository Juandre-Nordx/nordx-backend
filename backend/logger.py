import logging
import sys

# Force stdout to be unbuffered so every log line is written immediately,
# even inside a container that may buffer output by default.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _FlushingStreamHandler(logging.StreamHandler):
    """StreamHandler that flushes after every emit so logs are never buffered."""

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


def _configure_root_logger() -> None:
    root = logging.getLogger()
    # Only configure once (guard against double-import in reload scenarios).
    if root.handlers:
        return

    root.setLevel(logging.INFO)

    handler = _FlushingStreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT))

    root.addHandler(handler)


_configure_root_logger()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

