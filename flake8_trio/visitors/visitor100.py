"""Contains visitor for TRIO100.

A `with trio.fail_after(...):` or `with trio.move_on_after(...):`
context does not contain any `await` statements.  This makes it pointless, as
the timeout can only be triggered by a checkpoint.
Checkpoints on Await, Async For and Async With
"""
# if future annotations are imported then shed will reformat away the Union use
from typing import Any, Union

import libcst as cst
import libcst.matchers as m

from .flake8triovisitor import Flake8TrioVisitor_cst
from .helpers import AttributeCall, error_class_cst, with_has_call


@error_class_cst
class Visitor100_libcst(Flake8TrioVisitor_cst):
    error_codes = {
        "TRIO100": (
            "{0}.{1} context contains no checkpoints, remove the context or add"
            " `await {0}.lowlevel.checkpoint()`."
        ),
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.has_checkpoint_stack: list[bool] = []
        self.node_dict: dict[cst.With, list[AttributeCall]] = {}

    def visit_With(self, node: cst.With) -> None:
        if m.matches(node, m.With(asynchronous=m.Asynchronous())):
            self.checkpoint_node(node)
        if res := with_has_call(
            node, "fail_after", "fail_at", "move_on_after", "move_on_at", "CancelScope"
        ):
            self.node_dict[node] = res

            self.has_checkpoint_stack.append(False)
        else:
            self.has_checkpoint_stack.append(True)

    def leave_With(self, original_node: cst.With, updated_node: cst.With) -> cst.With:
        if not self.has_checkpoint_stack.pop():
            for res in self.node_dict[original_node]:
                self.error(res.node, res.base, res.function)
        # if: autofixing is enabled for this code
        # then: remove the with and pop out it's body
        return updated_node

    @m.visit(m.Await() | m.For(asynchronous=m.Asynchronous()))
    # can't use m.call_if_inside(m.With), since it matches parents *or* the node itself
    # need to use Union due to https://github.com/Instagram/LibCST/issues/870
    def checkpoint_node(self, node: Union[cst.Await, cst.For, cst.With]):
        if self.has_checkpoint_stack:
            self.has_checkpoint_stack[-1] = True

    def visit_FunctionDef(self, node: cst.FunctionDef):
        self.save_state(node, "has_checkpoint_stack", copy=True)
        self.has_checkpoint_stack = []

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        self.set_state(self.outer.pop(original_node, {}))
        return updated_node
