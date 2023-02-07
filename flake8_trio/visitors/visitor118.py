"""Visitor for TRIO118.

Don't assign the value of `anyio.get_cancelled_exc_class()` to a variable, since
that breaks linter checks and multi-backend programs.
"""


from __future__ import annotations

import ast
import re

from .flake8triovisitor import Flake8TrioVisitor
from .helpers import error_class


@error_class
class Visitor118(Flake8TrioVisitor):
    error_codes = {
        "TRIO118": (
            "Don't assign the value of `anyio.get_cancelled_exc_class()` to a variable,"
            " since that breaks linter checks and multi-backend programs."
        )
    }

    def visit_Assign(self, node: ast.Assign | ast.AnnAssign):
        if node.value is None:
            return
        name = ast.unparse(node.value)
        if re.fullmatch(r"(anyio.)?get_cancelled_exc_class(\(\))?", name):
            self.error(node.value)

    visit_AnnAssign = visit_Assign

    # redundant check with TRIO106
    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "anyio":
            for alias in node.names:
                if alias.name == "get_cancelled_exc_class" and alias.asname is not None:
                    # alias doesn't have a lineno in 3.9
                    self.error(node)
                    return
