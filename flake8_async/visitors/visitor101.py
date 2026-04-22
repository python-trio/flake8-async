"""Contains visitor for ASYNC101.

`yield` inside a nursery or cancel scope is only safe when implementing a context manager
- otherwise, it breaks exception handling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .flake8asyncvisitor import Flake8AsyncVisitor_cst
from .helpers import (
    calls_any_of,
    cancel_scope_names,
    error_class_cst,
    func_has_decorator,
)

# Qualified names of context managers that open a nursery / task group / cancel
# scope. `yield`ing inside any of these breaks exception handling unless the
# enclosing function is itself a context manager (see ASYNC101 docs).
_CANCEL_SCOPE_CMS: tuple[str, ...] = (
    # nursery/taskgroup
    "trio.open_nursery",
    "anyio.create_task_group",
    "asyncio.TaskGroup",
    # stdlib cancel scopes
    "asyncio.timeout",
    "asyncio.timeout_at",
    # trio/anyio share the same cancel-scope spelling
    *(f"{lib}.{name}" for lib in ("trio", "anyio") for name in cancel_scope_names),
    # 3rd-party CMs with internal cancel scopes / nurseries. See issue #350.
    "trio_websocket.open_websocket",
    "trio_websocket.open_websocket_url",
    "trio_websocket.serve_websocket",
    "trio_asyncio.open_loop",
    "trio_parallel.open_worker_context",
    "trio_util.move_on_when",
    "trio_util.run_and_cancelling",
    "qtrio.open_emissions_nursery",
    "qtrio.enter_emissions_channel",
    "anyio.from_thread.BlockingPortal",
    "anyio.from_thread.start_blocking_portal",
    "asgi_lifespan.LifespanManager",
    "apscheduler.AsyncScheduler",
    "mcp.client.streamable_http.streamablehttp_client",
    "mcp.client.sse.sse_client",
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    import libcst as cst


@error_class_cst
class Visitor101(Flake8AsyncVisitor_cst):
    error_codes: Mapping[str, str] = {
        "ASYNC101": (
            "`yield` inside a nursery or cancel scope is only safe when implementing "
            "a context manager - otherwise, it breaks exception handling."
        ),
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._yield_is_error = False
        self._safe_decorator = False

    def visit_With(self, node: cst.With):
        self.save_state(node, "_yield_is_error", copy=True)
        # if there's no safe decorator,
        # and it's not yet been determined that yield is error
        # and this withitem opens a nursery/taskgroup/cancelscope:
        # then yielding is unsafe
        self._yield_is_error = (
            not self._safe_decorator
            and not self._yield_is_error
            and calls_any_of(node, *_CANCEL_SCOPE_CMS)
        )

    def leave_With(
        self, original_node: cst.BaseStatement, updated_node: cst.BaseStatement
    ) -> cst.BaseStatement:
        self.restore_state(original_node)
        return updated_node

    leave_FunctionDef = leave_With

    def visit_FunctionDef(self, node: cst.FunctionDef):
        self.save_state(node, "_yield_is_error", "_safe_decorator")
        self._yield_is_error = False
        self._safe_decorator = func_has_decorator(
            node,
            "contextmanager",
            "asynccontextmanager",
            "fixture",
            *self.options.transform_async_generator_decorators,
        )

    # trigger on leaving yield so any comments are parsed for noqas
    def visit_Yield(self, node: cst.Yield):
        if self._yield_is_error:
            self.error(node)
