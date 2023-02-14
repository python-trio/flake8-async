"""Utility visitors for tracking shared state and modifying the tree."""

from __future__ import annotations

import ast

from .flake8triovisitor import Flake8TrioVisitor
from .helpers import utility_visitor


@utility_visitor
class VisitorTypeTracker(Flake8TrioVisitor):
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
        if not isinstance(node.target, ast.Name):
            return
        target = node.target.id
        typename = ast.unparse(node.annotation)
        self.variables[target] = typename

    def visit_Assign(self, node: ast.Assign):
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            return

        # `f = open(...)`
        if isinstance(node.value, ast.Call) and (
            vartype := self.typed_calls.get(ast.unparse(node.value.func), None)
        ):
            self.variables[node.targets[0].id] = vartype

        # f = ff (and ff is a variable with known type)
        elif isinstance(node.value, ast.Name) and (
            value := self.variables.get(node.value.id, None)
        ):
            self.variables[node.targets[0].id] = value

    def visit_With(self, node: ast.With | ast.AsyncWith):
        if len(node.items) != 1:
            return
        item = node.items[0]
        if (
            isinstance(item.context_expr, ast.Call)
            and isinstance(item.optional_vars, ast.Name)
            and (
                vartype := self.typed_calls.get(
                    ast.unparse(item.context_expr.func), None
                )
            )
        ):
            self.variables[item.optional_vars.id] = vartype

    visit_AsyncWith = visit_With


@utility_visitor
class VisitorAwaitModifier(Flake8TrioVisitor):
    def visit_Await(self, node: ast.Await):
        if isinstance(node.value, ast.Call):
            # add attribute to indicate it's awaited
            setattr(node.value, "awaited", True)  # noqa: B010


@utility_visitor
class VisitorLibraryHandler(Flake8TrioVisitor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # check whether library we're working towards has been explicitly
        # specified with --anyio, otherwise assume Trio - but we update if we
        # see imports
        if self.options.anyio:
            self.add_library("anyio")

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.name
            if name in ("trio", "anyio") and alias.asname is None:
                self.add_library(name)
