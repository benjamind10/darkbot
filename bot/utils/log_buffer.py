"""In-memory rolling log buffer for Discord display."""

import collections
import logging
import re

# Ordered list of (compiled_pattern, replacement) applied before storing entries.
# Secrets are redacted at write time so they never enter the buffer.
_REDACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Discord bot token  (base64(user_id).base64(ts).base64(hmac))
    (re.compile(r"[MNO][A-Za-z0-9]{23}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27}"), "[REDACTED]"),
    # OpenAI / Anthropic-style keys:  sk-... or sk-proj-...
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), "[REDACTED]"),
    # Bearer <token>  (Authorization header value)
    (re.compile(r"(Bearer\s+)\S+", re.IGNORECASE), r"\1[REDACTED]"),
    # Authorization: <any-value>  or  Authorization=<any-value>  (to end of line)
    (re.compile(r"(Authorization\s*[:=]\s*)\S[^\n]*", re.IGNORECASE), r"\1[REDACTED]"),
    # Sensitive key=value or key: value pairs
    (
        re.compile(
            r"\b(password|passwd|secret|api[_-]?key|client[_-]?secret|auth[_-]?token|access[_-]?token)\s*[=:]\s*\S+",
            re.IGNORECASE,
        ),
        r"\1=[REDACTED]",
    ),
    # Connection URLs with embedded credentials:  scheme://user:pass@host
    (re.compile(r"(\w+://[^:@\s]+:)[^@\s]+(@)"), r"\1[REDACTED]\2"),
]


def _sanitize(text: str) -> str:
    for pattern, replacement in _REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RollingLogHandler(logging.Handler):
    """Stores the last N sanitized log entries in memory."""

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
            self._entries.append(_sanitize(self.format(record)))
        except Exception:
            self.handleError(record)

    def get_entries(self, n: int) -> list[str]:
        entries = list(self._entries)
        return entries[-n:] if n < len(entries) else entries
