"""Contains Flake8AsyncRunner.

The runner is what's run by the Plugin, and handles traversing
the AST and letting all registered ERROR_CLASSES do their visit'ing on them.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import libcst as cst

from .base import Error, Options
from .visitors import (
    ERROR_CLASSES,
    ERROR_CLASSES_CST,
    utility_visitors,
    utility_visitors_cst,
)
from .visitors.visitor_utility import NoqaHandler

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from libcst import Module

    from .visitors.flake8asyncvisitor import Flake8AsyncVisitor, Flake8AsyncVisitor_cst


@dataclass
class SharedState:
    options: Options
    problems: list[Error] = field(default_factory=list[Error])
    noqas: dict[int, set[str]] = field(default_factory=dict[int, set[str]])
    library: tuple[str, ...] = ()
    typed_calls: dict[str, str] = field(default_factory=dict[str, str])
    variables: dict[str, str] = field(default_factory=dict[str, str])


class __CommonRunner:
    """Common functionality used in both runners."""

    def __init__(self, options: Options):
        super().__init__()
        self.state = SharedState(options)

    def selected(self, error_codes: Mapping[str, str]) -> bool:
        enabled_or_autofix = (
            self.state.options.enabled_codes | self.state.options.autofix_codes
        )
        return bool(set(error_codes) & enabled_or_autofix)


class Flake8AsyncRunner(ast.NodeVisitor, __CommonRunner):
    def __init__(self, options: Options):
        super().__init__(options)
        # utility visitors that need to run before the error-checking visitors
        self.utility_visitors = {v(self.state) for v in utility_visitors}

        self.visitors = {
            v(self.state) for v in ERROR_CLASSES if self.selected(v.error_codes)
        }

    @classmethod
    def run(cls, tree: ast.AST, options: Options) -> Iterable[Error]:
        runner = cls(options)
        runner.visit(tree)
        yield from runner.state.problems

    def visit(self, node: ast.AST):
        """Visit a node."""
        # tracks the subclasses that, from this node on, iterated through it's subfields
        # we need to remember it so we can restore it at the end of the function.
        novisit: set[Flake8AsyncVisitor] = set()

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


class Flake8AsyncRunner_cst(__CommonRunner):
    def __init__(self, options: Options, module: Module):
        super().__init__(options)
        self.options = options
        self.noqas: dict[int, set[str]] = {}

        utility_visitors = utility_visitors_cst.copy()
        if self.options.disable_noqa:
            utility_visitors.remove(NoqaHandler)

        # Could possibly enable/disable utility visitors here, if visitors declared
        # dependencies
        self.utility_visitors: tuple[Flake8AsyncVisitor_cst, ...] = tuple(
            v(self.state) for v in utility_visitors
        )

        # sort the error classes to get predictable behaviour when multiple autofixers
        # are enabled
        sorted_error_classes_cst = sorted(ERROR_CLASSES_CST, key=lambda x: x.__name__)
        self.visitors: tuple[Flake8AsyncVisitor_cst, ...] = tuple(
            v(self.state)
            for v in sorted_error_classes_cst
            if self.selected(v.error_codes)
        )
        self.module = module

    def run(self) -> Iterable[Error]:
        for v in (*self.utility_visitors, *self.visitors):
            self.module = cst.MetadataWrapper(self.module).visit(v)

        yield from self.state.problems

        # expose the noqa's parsed by the last visitor, so they can be used to filter
        # ast problems
        if not self.options.disable_noqa:
            self.noqas = v.noqas  # type: ignore[reportUnboundVariable]
