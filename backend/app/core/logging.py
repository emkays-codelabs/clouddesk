import json
import logging
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_workflow_id: ContextVar[str | None] = ContextVar("workflow_id", default=None)

_UNSET = object()


def current_request_id() -> str | None:
    """The request id bound by the request-id middleware, or None outside a request."""
    return _request_id.get()


_HANDLER_MARK = "_clouddesk_json_handler"

REDACTED = "***"
# Keys whose value is a secret: password, secret, api key, authorization, or a lone `token` word
# (`access_token`, `token`). A count such as `total_tokens` is a number, not a credential.
_SECRET_KEY = re.compile(
    r"passw(or)?d|secret|api[_-]?key|authorization|(^|[_\-])token($|[_\-])", re.IGNORECASE
)
# Every attribute a bare LogRecord has: anything else on a record came from `extra={...}`.
_STANDARD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}
_RESERVED_KEYS = frozenset(
    {"timestamp", "level", "logger", "message", "request_id", "workflow_id", "exception"}
)


def _redact(key: str, value: object) -> object:
    """The value to log for `key`: masked when the key looks secret, and inside a dict as well."""
    if _SECRET_KEY.search(key):
        return REDACTED
    if isinstance(value, dict):
        return {str(k): _redact(str(k), v) for k, v in value.items()}
    return value


@contextmanager
def log_context(
    *, request_id: str | None | object = _UNSET, workflow_id: str | None | object = _UNSET
) -> Iterator[None]:
    """Bind ids to every log line emitted inside the block; restore the previous values after."""
    tokens = []
    if request_id is not _UNSET:
        tokens.append((_request_id, _request_id.set(request_id)))  # type: ignore[arg-type]
    if workflow_id is not _UNSET:
        tokens.append((_workflow_id, _workflow_id.set(workflow_id)))  # type: ignore[arg-type]
    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)


class JsonFormatter(logging.Formatter):
    """One JSON object per line; request_id and workflow_id are always present (null when unset).

    The `extra={...}` fields of a record are added, redacted by key name, JSON-safe through
    `default=str`; they never override a reserved key.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id.get(),
            "workflow_id": _workflow_id.get(),
        }
        for key, value in record.__dict__.items():
            if key in _STANDARD_ATTRS:
                continue
            # An extra field can never replace a reserved key; it is kept under a prefixed one.
            payload[f"extra_{key}" if key in _RESERVED_KEYS else key] = _redact(key, value)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(level: int | str = logging.INFO) -> None:
    """Route all logging, uvicorn's included, through one JSON handler. Safe to call repeatedly."""
    root = logging.getLogger()
    root.handlers = [h for h in root.handlers if not getattr(h, _HANDLER_MARK, False)]

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    setattr(handler, _HANDLER_MARK, True)
    root.addHandler(handler)
    root.setLevel(level)

    # uvicorn installs its own plain-text handlers; hand its records to the root handler instead.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
