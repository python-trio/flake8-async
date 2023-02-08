"""Contains Flake8TrioRunner.

The runner is what's run by the Plugin, and handles traversing
the AST and letting all registered ERROR_CLASSES do their visit'ing on them.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .visitors import ERROR_CLASSES, utility_visitors

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Iterable

    from .base import Error
    from .visitors.flake8triovisitor import Flake8TrioVisitor


@dataclass
class SharedState:
    options: Namespace
    problems: list[Error] = field(default_factory=list)
    library: tuple[str, ...] = field(default_factory=tuple)
    typed_calls: dict[str, str] = field(default_factory=dict)
    variables: dict[str, str] = field(default_factory=dict)


class Flake8TrioRunner(ast.NodeVisitor):
    def __init__(self, options: Namespace):
        super().__init__()
        self.state = SharedState(options)

        # utility visitors that need to run before the error-checking visitors
        self.utility_visitors = {v(self.state) for v in utility_visitors}

        self.visitors = {
            v(self.state) for v in ERROR_CLASSES if self.selected(v.error_codes)
        }

    def selected(self, error_codes: dict[str, str]) -> bool:
        return any(
            re.match(self.state.options.enable_visitor_codes_regex, code)
            for code in error_codes
        )

    @classmethod
    def run(cls, tree: ast.AST, options: Namespace) -> Iterable[Error]:
        runner = cls(options)
        runner.visit(tree)
        yield from runner.state.problems

    def visit(self, node: ast.AST):
        """Visit a node."""
        # tracks the subclasses that, from this node on, iterated through it's subfields
        # we need to remember it so we can restore it at the end of the function.
        novisit: set[Flake8TrioVisitor] = set()

        method = "visit_" + node.__class__.__name__

        for subclass in *self.utility_visitors, *self.visitors:
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
        for subclass in *self.utility_visitors, *self.visitors:
            subclass.set_state(subclass.outer.pop(node, {}))
