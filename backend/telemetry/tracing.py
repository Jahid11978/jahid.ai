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
        return cls(trace_id=uuid4().hex)

    @classmethod
    def current(cls) -> "TraceContext":
        return cls(_current_trace.get() or uuid4().hex)


@contextmanager
def trace(trace_id: str | None = None):
    context = TraceContext(trace_id or TraceContext.create().trace_id)
    token = _current_trace.set(context.trace_id)
    try:
        yield context
    finally:
        _current_trace.reset(token)
