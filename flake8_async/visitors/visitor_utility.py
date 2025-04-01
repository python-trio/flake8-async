"""Utility visitors for tracking shared state and modifying the tree."""

from __future__ import annotations

import ast
import functools
import re
from typing import TYPE_CHECKING, Any, cast

import libcst.matchers as m
from libcst.metadata import PositionProvider

from .flake8asyncvisitor import Flake8AsyncVisitor, Flake8AsyncVisitor_cst
from .helpers import utility_visitor, utility_visitor_cst

if TYPE_CHECKING:
    from re import Match

    import libcst as cst
    from libcst.metadata import CodeRange


@utility_visitor
class VisitorTypeTracker(Flake8AsyncVisitor):
    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef | ast.FunctionDef | ast.Lambda
    ):
        def or_none(node: ast.AST | None):
            if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.BitOr):
                return None
            if isinstance(node.left, ast.Constant) and node.left.value is None:
                return node.right
            if isinstance(node.right, ast.Constant) and node.right.value is None:
                return node.left
            return None

        self.save_state(node, "variables", copy=True)

        args = node.args
        for arg in *args.args, *args.posonlyargs, *args.kwonlyargs:
            annotation = arg.annotation

            if (
                isinstance(annotation, ast.Subscript)
                and isinstance(annotation.value, ast.Name)
                and annotation.value.id == "Optional"
            ):
                annotation = annotation.slice
            elif res := or_none(annotation):
                annotation = res

            if isinstance(annotation, (ast.Name, ast.Attribute, ast.Constant)):
                annotation_type = ast.unparse(annotation)
            else:
                annotation_type = "Any"

            self.variables[arg.arg] = annotation_type

    visit_FunctionDef = visit_AsyncFunctionDef
    visit_Lambda = visit_AsyncFunctionDef

    # Does not handle class members, or attributes in general
    def visit_ClassDef(self, node: ast.ClassDef):
        self.save_state(node, "variables", copy=True)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if not isinstance(node.target, (ast.Name, ast.Attribute)):
            # target can technically be a subscript
            return  # pragma: no cover
        target = ast.unparse(node.target)
        typename = ast.unparse(node.annotation)
        self.variables[target] = typename

    def visit_Assign(self, node: ast.Assign):
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            return

        # `f = open(...)`
        if isinstance(node.value, ast.Call) and (
            vartype := self.typed_calls.get(ast.unparse(node.value.func))
        ):
            self.variables[node.targets[0].id] = vartype

        # f = ff (and ff is a variable with known type)
        elif isinstance(node.value, ast.Name) and (
            value := self.variables.get(node.value.id)
        ):
            self.variables[node.targets[0].id] = value

    def visit_With(self, node: ast.With | ast.AsyncWith):
        # TODO: it's actually the return type of
        # `ast.unparse(item.context_expr.func).__[a]enter__()` that should be used
        if len(node.items) != 1:
            return
        item = node.items[0]
        if (
            isinstance(item.context_expr, ast.Call)
            and isinstance(item.optional_vars, ast.Name)
            and (vartype := self.typed_calls.get(ast.unparse(item.context_expr.func)))
        ):
            self.variables[item.optional_vars.id] = vartype

    visit_AsyncWith = visit_With


@utility_visitor
class VisitorAwaitModifier(Flake8AsyncVisitor):
    def visit_Await(self, node: ast.Await):
        if isinstance(node.value, ast.Call):
            # add attribute to indicate it's awaited
            setattr(node.value, "awaited", True)  # noqa: B010


@utility_visitor
class VisitorLibraryHandler(Flake8AsyncVisitor):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        # check whether library we're working towards has been explicitly
        # specified with --anyio, otherwise assume Trio - but we update if we
        # see imports
        if self.options.anyio:
            self.add_library("anyio")
        if self.options.asyncio:
            self.add_library("asyncio")

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.name
            if name in ("trio", "anyio", "asyncio") and alias.asname is None:
                self.add_library(name)


@utility_visitor_cst
class VisitorLibraryHandler_cst(Flake8AsyncVisitor_cst):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        # check whether library we're working towards has been explicitly
        # specified with --anyio, otherwise assume Trio - but we update if we
        # see imports
        if self.options.anyio:
            self.add_library("anyio")
        if self.options.asyncio:
            self.add_library("asyncio")

    def visit_Import(self, node: cst.Import):
        for alias in node.names:
            if m.matches(
                alias,
                m.ImportAlias(
                    name=m.Name("trio") | m.Name("anyio") | m.Name("asyncio"),
                    asname=None,
                ),
            ):
                assert isinstance(alias.name.value, str)
                self.add_library(alias.name.value)


# taken from
# https://github.com/PyCQA/flake8/blob/d016204366a22d382b5b56dc14b6cbff28ce929e/src/flake8/defaults.py#L27
NOQA_INLINE_REGEXP = re.compile(
    # We're looking for items that look like this:
    # ``# nxqa``
    # ``# nxqa: E123``
    # ``# nxqa: E123,W451,F921``
    # ``# nxqa:E123,W451,F921``
    # ``# NxQA: E123,W451,F921``
    # ``# NXQA: E123,W451,F921``
    # ``# NXQA:E123,W451,F921``
    # (o/O replaced with x/X to avoid the wrath of flake8-noqa/RUF100)
    # We do not want to capture the ``: `` that follows ``noqa``
    # We do not care about the casing of ``noqa``
    # We want a comma-separated list of errors
    # upstream links to an old version on regex101
    # https://regex101.com/r/4XUuax/5 full explanation of the regex
    r"# noqa(?::[\s]?(?P<codes>([A-Z]+[0-9]+(?:[,\s]+)?)+))?",
    re.IGNORECASE,
)


@functools.lru_cache(maxsize=512)
def _find_noqa(physical_line: str) -> Match[str] | None:
    return NOQA_INLINE_REGEXP.search(physical_line)


@utility_visitor_cst
class NoqaHandler(Flake8AsyncVisitor_cst):
    def visit_Comment(self, node: cst.Comment):
        noqa_match = _find_noqa(node.value)
        if noqa_match is None:
            return False

        codes_str = noqa_match.groupdict()["codes"]

        # see https://github.com/Instagram/LibCST/issues/1107
        metadata = cast("CodeRange", self.get_metadata(PositionProvider, node))
        pos = metadata.start

        codes: set[str]

        # blanket noqa
        if codes_str is None:
            # this also includes a non-blanket noqa with a list of invalid codes
            # so one should maybe instead specifically look for no `:`
            codes = set()
        else:
            # split string on ",", strip of whitespace, and save in set if non-empty
            codes = {
                item_strip
                for item in codes_str.split(",")
                if (item_strip := item.strip())
            }

            # TODO: Check that code exists
        self.noqas[pos.line] = codes
        return False
