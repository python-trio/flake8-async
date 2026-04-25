"""Visitor for ASYNC118.

Don't assign the value of `anyio.get_cancelled_exc_class()` to a variable, since
that breaks linter checks and multi-backend programs.
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from .flake8asyncvisitor import Flake8AsyncVisitor
from .helpers import error_class

if TYPE_CHECKING:
    from collections.abc import Mapping


@error_class
class Visitor118(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC118": (
            "Don't assign the value of `anyio.get_cancelled_exc_class()` to a variable,"
            " since that breaks linter checks and multi-backend programs."
        )
    }

    def visit_Assign(self, node: ast.Assign | ast.AnnAssign):
        value = node.value
        if value is None:
            return
        target = value.func if isinstance(value, ast.Call) else value
        if self.canonical_name(target) == "anyio.get_cancelled_exc_class":
            self.error(value)
            return
        # Fallback for code where anyio isn't importable (e.g. stubs or partial
        # configs) but the name is still spelled out literally.
        if re.fullmatch(r"(anyio.)?get_cancelled_exc_class(\(\))?", ast.unparse(value)):
            self.error(value)

    visit_AnnAssign = visit_Assign

    # redundant check with ASYNC106
    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "anyio":
            for alias in node.names:
                if alias.name == "get_cancelled_exc_class" and alias.asname is not None:
                    # alias doesn't have a lineno in 3.9
                    self.error(node)
                    return
