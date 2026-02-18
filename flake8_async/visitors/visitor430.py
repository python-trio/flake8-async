"""Visitor to check for pytest.raises(ExceptionGroup) usage.

ASYNC430: Suggests using pytest.RaisesGroup instead of pytest.raises(ExceptionGroup).
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any

from .flake8asyncvisitor import Flake8AsyncVisitor
from .helpers import error_class

if TYPE_CHECKING:
    from collections.abc import Mapping


@error_class
class Visitor430(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC430": (
            "Using `pytest.raises(ExceptionGroup)` is discouraged, consider using "
            "`pytest.RaisesGroup` instead."
        )
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.imports_pytest: bool = False
        self.imports_exceptiongroup: bool = False
        self.async_function = False

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef | ast.FunctionDef | ast.Lambda
    ):
        self.save_state(node, "async_function")
        self.async_function = isinstance(node, ast.AsyncFunctionDef)

    visit_FunctionDef = visit_AsyncFunctionDef
    visit_Lambda = visit_AsyncFunctionDef

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "pytest":
                self.imports_pytest = True

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "pytest":
            self.imports_pytest = True
        elif node.module == "builtins" or node.module is None:
            # Check for `from builtins import ExceptionGroup`
            for alias in node.names:
                if alias.name in ("ExceptionGroup", "BaseExceptionGroup"):
                    self.imports_exceptiongroup = True

    def visit_Call(self, node: ast.Call) -> None:
        if not self.async_function:
            return

        func_name = ast.unparse(node.func)

        # Check for pytest.raises(ExceptionGroup) or pytest.raises(BaseExceptionGroup)
        if not (
            func_name == "pytest.raises"
            or (self.imports_pytest and func_name == "raises")
        ):
            return

        # Check first argument (exception type)
        if not node.args:
            return

        first_arg = node.args[0]
        if isinstance(first_arg, ast.Name) and first_arg.id in (
            "ExceptionGroup",
            "BaseExceptionGroup",
        ):
            self.error(node)
        elif isinstance(first_arg, ast.Attribute) and first_arg.attr in (
            "ExceptionGroup",
            "BaseExceptionGroup",
        ):
            # Handle pytest.raises(pytest.ExceptionGroup) or similar
            self.error(node)
