"""TRIO105: library async function must be immediately awaited."""

from __future__ import annotations

import ast

from .flake8triovisitor import Flake8TrioVisitor
from .helpers import error_class

# used in 105
trio_async_funcs = (
    "trio.aclose_forcefully",
    "trio.open_file",
    "trio.open_ssl_over_tcp_listeners",
    "trio.open_ssl_over_tcp_stream",
    "trio.open_tcp_listeners",
    "trio.open_tcp_stream",
    "trio.open_unix_socket",
    "trio.run_process",
    "trio.serve_listeners",
    "trio.serve_ssl_over_tcp",
    "trio.serve_tcp",
    "trio.sleep",
    "trio.sleep_forever",
    "trio.sleep_until",
    "trio.lowlevel.cancel_shielded_checkpoint",
    "trio.lowlevel.checkpoint",
    "trio.lowlevel.checkpoint_if_cancelled",
    "trio.lowlevel.open_process",
    "trio.lowlevel.permanently_detach_coroutine_object",
    "trio.lowlevel.reattach_detached_coroutine_object",
    "trio.lowlevel.temporarily_detach_coroutine_object",
    "trio.lowlevel.wait_readable",
    "trio.lowlevel.wait_task_rescheduled",
    "trio.lowlevel.wait_writable",
)


@error_class
class Visitor105(Flake8TrioVisitor):
    error_codes = {
        "TRIO105": "{0} async {1} must be immediately awaited.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.typed_calls["trio.open_nursery"] = "trio.Nursery"

    def visit_Call(self, node: ast.Call):
        if getattr(node, "awaited", False) or "trio" not in self.library:
            return

        if (name := ast.unparse(node.func)) in trio_async_funcs:
            self.error(node, name, "function")
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "start":
            var = ast.unparse(node.func.value)

            if self.variables.get(var, "") == "trio.Nursery" or var.endswith("nursery"):
                self.error(node, "trio.Nursery.start", "method")
