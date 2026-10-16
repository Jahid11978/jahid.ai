from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from uuid import uuid4

_current_trace: ContextVar[str | None] = ContextVar("jahid_trace_id", default=None)


@dataclass(frozen=True)
class TraceContext:
    trace_id: str

    @classmethod
    def create(cls) -> "TraceContext":
        """Return a context with a new UUID-based trace ID."""
        return cls(trace_id=uuid4().hex)

    @classmethod
    def current(cls) -> "TraceContext":
        """Return the active ID, or a new unbound ID if none is active."""
        return cls(_current_trace.get() or uuid4().hex)


@contextmanager
def trace(trace_id: str | None = None):
    """Yield a context whose trace ID is active for the managed block.

    Generate an ID when ``trace_id`` is empty or ``None``. Restore the previous
    ID on exit, including when an exception propagates from the block.
    """
    context = TraceContext(trace_id or TraceContext.create().trace_id)
    token = _current_trace.set(context.trace_id)
    try:
        yield context
    finally:
        _current_trace.reset(token)
