"""Contains Flake8TrioRunner.

The runner is what's run by the Plugin, and handles traversing
the AST and letting all registered ERROR_CLASSES do their visit'ing on them.
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from .visitors import ERROR_CLASSES

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Iterable

    from .base import Error
    from .visitors.flake8triovisitor import Flake8TrioVisitor


class Flake8TrioRunner(ast.NodeVisitor):
    def __init__(self, options: Namespace):
        super().__init__()
        self._problems: list[Error] = []
        self.options = options

        self.visitors = {
            v(options, self._problems)
            for v in ERROR_CLASSES
            if self.selected(v.error_codes)
        }

    def selected(self, error_codes: dict[str, str]) -> bool:
        return any(
            re.match(self.options.enable_visitor_codes_regex, code)
            for code in error_codes
        )

    @classmethod
    def run(cls, tree: ast.AST, options: Namespace) -> Iterable[Error]:
        runner = cls(options)
        runner.visit(tree)
        yield from runner._problems

    def visit(self, node: ast.AST):
        """Visit a node."""
        # don't bother visiting if no visitors are enabled, or all enabled visitors
        # in parent nodes have marked novisit
        if not self.visitors:
            return

        # tracks the subclasses that, from this node on, iterated through it's subfields
        # we need to remember it so we can restore it at the end of the function.
        novisit: set[Flake8TrioVisitor] = set()

        method = "visit_" + node.__class__.__name__

        if m := getattr(self, method, None):
            m(node)

        for subclass in self.visitors:
            # check if subclass has defined a visitor for this type
            class_method = getattr(subclass, method, None)
            if class_method is None:
                continue

            # call it
            class_method(node)

            # it will set `.novisit` if it has itself handled iterating through subfields
            # so we add it to our novisit set
            if subclass.novisit:
                novisit.add(subclass)

        # Remove all subclasses that iterated through subfields from our list of
        # visitors, so we don't visit them twice.
        self.visitors.difference_update(novisit)

        # iterate through subfields using NodeVisitor
        self.generic_visit(node)

        # reset the novisit flag for the classes in novisit
        for subclass in novisit:
            subclass.novisit = False

        # and add them back to our visitors
        self.visitors.update(novisit)

        # restore any outer state that was saved in the visitor method
        for subclass in self.visitors:
            subclass.set_state(subclass.outer.pop(node, {}))

    def visit_Await(self, node: ast.Await):
        if isinstance(node.value, ast.Call):
            # add attribute to indicate it's awaited
            setattr(node.value, "awaited", True)  # noqa: B010
