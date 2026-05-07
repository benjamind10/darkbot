"""In-memory rolling log buffer for Discord display."""

import collections
import logging


class RollingLogHandler(logging.Handler):
    """Stores the last N formatted log entries in memory."""

    def __init__(self, maxlen: int = 500):
        super().__init__()
        self._entries: collections.deque[str] = collections.deque(maxlen=maxlen)
        self.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._entries.append(self.format(record))
        except Exception:
            self.handleError(record)

    def get_entries(self, n: int) -> list[str]:
        entries = list(self._entries)
        return entries[-n:] if n < len(entries) else entries
