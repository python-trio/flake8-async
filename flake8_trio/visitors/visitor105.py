"""TRIO105: library async function must be immediately awaited."""

from __future__ import annotations

import ast

from .flake8triovisitor import Flake8TrioVisitor
from .helpers import error_class, is_nursery_call

# used in 105
trio_async_funcs = (
    "aclose_forcefully",
    "open_file",
    "open_ssl_over_tcp_listeners",
    "open_ssl_over_tcp_stream",
    "open_tcp_listeners",
    "open_tcp_stream",
    "open_unix_socket",
    "run_process",
    "serve_listeners",
    "serve_ssl_over_tcp",
    "serve_tcp",
    "sleep",
    "sleep_forever",
    "sleep_until",
)


@error_class
class Visitor105(Flake8TrioVisitor):
    error_codes = {
        "TRIO105": "{1} async function {0} must be immediately awaited.",
    }

    def visit_Call(self, node: ast.Call):
        if "trio" not in self.library:
            return
        if (
            not getattr(node, "awaited", False)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and (
                (node.func.value.id == "trio" and node.func.attr in trio_async_funcs)
                or is_nursery_call(node.func, "start")
            )
        ):
            self.error(node, node.func.attr, node.func.value.id)
