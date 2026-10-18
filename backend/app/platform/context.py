"""Immutable, task-local authority. No default tenant or implicit service bypass."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RequestContext:
    user_id: str | None
    workspace_id: str
    access_role: str
    business_role: str | None = None
    worker: bool = False

    def __post_init__(self):
        UUID(self.workspace_id)
        if self.user_id is not None:
            UUID(self.user_id)
        if self.access_role not in {"admin", "operator", "viewer", "worker"}:
            raise ValueError("Invalid access role")
        if self.worker != (self.access_role == "worker"):
            raise ValueError("Invalid worker authority")


_context: ContextVar[RequestContext | None] = ContextVar("dation_workspace", default=None)
_infrastructure: ContextVar[bool] = ContextVar("dation_worker_infrastructure", default=False)


def current() -> RequestContext:
    value = _context.get()
    if value is None:
        raise RuntimeError("A verified workspace context is required.")
    return value


@contextmanager
def bind(value: RequestContext):
    token = _context.set(value)
    try:
        yield value
    finally:
        _context.reset(token)


@contextmanager
def worker_infrastructure():
    """Only the standalone worker's global claim/report/reconciliation loop."""
    token = _infrastructure.set(True)
    try:
        yield
    finally:
        _infrastructure.reset(token)


def is_infrastructure():
    return _infrastructure.get() and _context.get() is None


def job_context(job):
    # Read authority from the persisted row, never from request_json supplied by a browser.
    return RequestContext(None, job["workspace_id"], "worker", worker=True)
