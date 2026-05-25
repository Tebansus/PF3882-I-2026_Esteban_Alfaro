"""Cross-cutting correlation-ID propagation for the EasyPass microservices.

The goal of Homework 5 is to add correlation IDs **in the least invasive way
possible**. Business logic (route handlers, GraphQL resolvers, the functions
that call other services) is left completely untouched. Everything here is
cross-cutting (the Python equivalent of AOP) and is enabled with three lines of
wiring at service start-up:

    from correlation import (
        CorrelationIdMiddleware, configure_logging, install_requests_propagation,
    )
    configure_logging()              # log lines carry the correlation ID
    install_requests_propagation()   # outgoing HTTP calls carry the header
    app.add_middleware(CorrelationIdMiddleware)   # inbound capture + echo

How it works:

* **Inbound** — a pure ASGI middleware reads the ``X-Correlation-ID`` request
  header (or generates one if absent), stores it in a ``ContextVar``, and echoes
  it back on the response.
* **Outbound** — ``requests.Session.request`` is wrapped once so every downstream
  HTTP call automatically carries the current correlation ID. No call site is
  modified (AOP-style interception).
* **Logging** — a logging filter injects the current correlation ID into every
  log record, so a single client request is traceable across all services.
"""

from __future__ import annotations

import logging
import os
import uuid
from contextvars import ContextVar

CORRELATION_ID_HEADER = "X-Correlation-ID"
_HEADER_KEY = CORRELATION_ID_HEADER.lower().encode()

# Holds the correlation ID for the duration of a request. ContextVars are
# isolated per task/thread and copied into FastAPI's threadpool workers, so the
# value set by the middleware is visible to sync route handlers and the
# downstream HTTP calls they make.
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")

logger = logging.getLogger("correlation")


def get_correlation_id() -> str:
    """Return the correlation ID bound to the current request (or '-')."""
    return _correlation_id.get()


def new_correlation_id() -> str:
    return f"gen-{uuid.uuid4()}"


class CorrelationIdMiddleware:
    """Pure ASGI middleware: capture/generate the correlation ID and echo it.

    Implemented as raw ASGI (rather than BaseHTTPMiddleware) so the ContextVar
    is set in the *same* task that runs the application, guaranteeing it is
    visible to the route handler and any downstream calls.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope["headers"]).get(_HEADER_KEY)
        correlation_id = incoming.decode() if incoming else new_correlation_id()
        token = _correlation_id.set(correlation_id)

        logger.info(
            "inbound %s %s",
            scope.get("method", "?"),
            scope.get("path", "?"),
        )

        async def send_with_header(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append((CORRELATION_ID_HEADER.encode(), correlation_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            _correlation_id.reset(token)


class _CorrelationIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_id.get()
        return True


def configure_logging(service_name: str | None = None) -> None:
    """Route all logging through a formatter that includes the correlation ID."""
    service_name = service_name or os.getenv("SERVICE_NAME", "service")

    handler = logging.StreamHandler()
    handler.addFilter(_CorrelationIdLogFilter())
    handler.setFormatter(
        logging.Formatter(
            f"%(asctime)s | {service_name} | correlation_id=%(correlation_id)s "
            "| %(levelname)s | %(message)s"
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def install_requests_propagation() -> None:
    """Wrap ``requests.Session.request`` so outgoing calls carry the header.

    Idempotent and safe to call even if ``requests`` is not installed.
    """
    try:
        import requests
    except ImportError:
        return

    original = requests.Session.request
    if getattr(original, "_correlation_patched", False):
        return

    def request_with_correlation(self, method, url, *args, **kwargs):
        headers = kwargs.get("headers") or {}
        headers.setdefault(CORRELATION_ID_HEADER, _correlation_id.get())
        kwargs["headers"] = headers
        logger.info("outbound %s %s", method, url)
        return original(self, method, url, *args, **kwargs)

    request_with_correlation._correlation_patched = True
    requests.Session.request = request_with_correlation
