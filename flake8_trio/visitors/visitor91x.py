"""Contains Visitor91X.

910 looks for async functions without guaranteed checkpoints (or exceptions), and 911 does
the same except for async iterables - while also requiring that they checkpoint between
each yield.
"""

from __future__ import annotations

import ast
from typing import Any

from ..base import Statement
from .flake8triovisitor import Flake8TrioVisitor
from .helpers import (
    disabled_by_default,
    error_class,
    fnmatch_qualified_name,
    has_decorator,
    iter_guaranteed_once,
)


# used in 910/911
def empty_body(body: list[ast.stmt]) -> bool:
    # Does the function body consist solely of `pass`, `...`, and (doc)string literals?
    return all(
        isinstance(stmt, ast.Pass)
        or (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and (stmt.value.value is Ellipsis or isinstance(stmt.value.value, str))
        )
        for stmt in body
    )


@error_class
@disabled_by_default
class Visitor91X(Flake8TrioVisitor):
    error_codes = {
        "TRIO910": (
            "{0} from async function with no guaranteed checkpoint or exception "
            "since function definition on line {1.lineno}."
        ),
        "TRIO911": (
            "{0} from async iterable with no guaranteed checkpoint since {1.name} "
            "on line {1.lineno}."
        ),
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.has_yield = False
        self.safe_decorator = False
        self.async_function = False

        self.uncheckpointed_statements: set[Statement] = set()
        self.uncheckpointed_before_continue: set[Statement] = set()
        self.uncheckpointed_before_break: set[Statement] = set()

        self.default = self.get_state()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # don't lint functions whose bodies solely consist of pass or ellipsis
        if has_decorator(node.decorator_list, "overload") or empty_body(node.body):
            return

        self.save_state(node)
        self.set_state(self.default, copy=True)

        # disable checks in asynccontextmanagers by saying the function isn't async
        self.async_function = not fnmatch_qualified_name(
            node.decorator_list, *self.options.no_checkpoint_warning_decorators
        )
        if not self.async_function:
            return

        self.uncheckpointed_statements = {
            Statement("function definition", node.lineno, node.col_offset)
        }

        self.generic_visit(node)

        self.check_function_exit(node)

    # error if function exits or returns with uncheckpointed statements
    def check_function_exit(self, node: ast.Return | ast.AsyncFunctionDef):
        for statement in self.uncheckpointed_statements:
            self.error(
                node,
                "return" if isinstance(node, ast.Return) else "exit",
                statement,
                error_code="TRIO911" if self.has_yield else "TRIO910",
            )

    def visit_Return(self, node: ast.Return):
        if not self.async_function:
            return
        self.generic_visit(node)
        self.check_function_exit(node)

        # avoid duplicate error messages
        self.uncheckpointed_statements = set()

    # disregard checkpoints in nested function definitions
    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.save_state(node)
        self.set_state(self.default, copy=True)

    # checkpoint functions
    def visit_Await(self, node: ast.Await | ast.Raise):
        # the expression being awaited is not checkpointed
        # so only set checkpoint after the await node
        self.generic_visit(node)

        # all nodes are now checkpointed
        self.uncheckpointed_statements = set()

    # raising exception means we don't need to checkpoint so we can treat it as one
    visit_Raise = visit_Await

    # Async context managers can reasonably checkpoint on either or both of entry and
    # exit.  Given that we can't tell which, we assume "both" to avoid raising a
    # missing-checkpoint warning when there might in fact be one (i.e. a false alarm).
    def visit_AsyncWith(self, node: ast.AsyncWith):
        self.visit_nodes(node.items)

        self.uncheckpointed_statements = set()
        self.visit_nodes(node.body)

        self.uncheckpointed_statements = set()

    # error if no checkpoint since earlier yield or function entry
    def visit_Yield(self, node: ast.Yield):
        if not self.async_function:
            return
        self.has_yield = True
        self.generic_visit(node)
        for statement in self.uncheckpointed_statements:
            self.error(
                node,
                "yield",
                statement,
                error_code="TRIO911",
            )

        # mark as requiring checkpoint after
        self.uncheckpointed_statements = {
            Statement("yield", node.lineno, node.col_offset)
        }

    # valid checkpoint if there's valid checkpoints (or raise) in:
    # (try or else) and all excepts, or in finally
    #
    # try can jump into any except or into the finally* at any point during it's
    # execution so we need to make sure except & finally can handle worst-case
    # * unless there's a bare except / except BaseException - not implemented.
    def visit_Try(self, node: ast.Try):
        if not self.async_function:
            return
        # except & finally guaranteed to enter with checkpoint if checkpointed
        # before try and no yield in try body.
        body_uncheckpointed_statements = self.uncheckpointed_statements.copy()
        for inner_node in self.walk(*node.body):
            if isinstance(inner_node, ast.Yield):
                body_uncheckpointed_statements.add(
                    Statement("yield", inner_node.lineno, inner_node.col_offset)
                )

        # check try body
        self.visit_nodes(node.body)

        # save state at end of try for entering else
        try_checkpoint = self.uncheckpointed_statements

        # check that all except handlers checkpoint (await or most likely raise)
        except_uncheckpointed_statements: set[Statement] = set()

        for handler in node.handlers:
            # enter with worst case of try
            self.uncheckpointed_statements = body_uncheckpointed_statements.copy()

            self.visit_nodes(handler)

            except_uncheckpointed_statements.update(self.uncheckpointed_statements)

        # check else
        # if else runs it's after all of try, so restore state to back then
        self.uncheckpointed_statements = try_checkpoint
        self.visit_nodes(node.orelse)

        # checkpoint if else checkpoints, and all excepts checkpoint
        self.uncheckpointed_statements.update(except_uncheckpointed_statements)

        if node.finalbody:
            added = body_uncheckpointed_statements.difference(
                self.uncheckpointed_statements
            )
            # if there's no bare except or except BaseException, we can jump into
            # finally from any point in try. But the exception will be reraised after
            # finally, so track what we add so it can be removed later.
            # (This is for catching return or yield in the finally, which is usually
            # very bad)
            if not any(
                h.type is None
                or (isinstance(h.type, ast.Name) and h.type.id == "BaseException")
                for h in node.handlers
            ):
                self.uncheckpointed_statements.update(added)

            self.visit_nodes(node.finalbody)
            self.uncheckpointed_statements.difference_update(added)

    # valid checkpoint if both body and orelse checkpoint
    def visit_If(self, node: ast.If | ast.IfExp):
        if not self.async_function:
            return
        # visit condition
        self.visit_nodes(node.test)
        outer = self.uncheckpointed_statements.copy()

        # visit body
        self.visit_nodes(node.body)
        body_outer = self.uncheckpointed_statements

        # reset to after condition and visit orelse
        self.uncheckpointed_statements = outer
        self.visit_nodes(node.orelse)

        # union of both branches is the new set of unhandled entries
        self.uncheckpointed_statements.update(body_outer)

    # inline if
    visit_IfExp = visit_If

    # Check for yields w/o checkpoint in between due to entering loop body the first time,
    # after completing all of loop body, and after any continues.
    # yield in else have same requirement
    # state after the loop same as above, and in addition the state at any break
    def visit_loop(self, node: ast.While | ast.For | ast.AsyncFor):
        if not self.async_function:
            return
        # visit condition

        # the following block is duplicated in Visitor103_104
        infinite_loop = False
        if isinstance(node, ast.While):
            try:
                infinite_loop = body_guaranteed_once = bool(ast.literal_eval(node.test))
            except Exception:  # noqa: PIE786
                body_guaranteed_once = False
            self.visit_nodes(node.test)
        else:
            self.visit_nodes(node.target)
            self.visit_nodes(node.iter)
            body_guaranteed_once = iter_guaranteed_once(node.iter)

        # save state in case of nested loops
        outer = self.get_state(
            "uncheckpointed_before_continue",
            "uncheckpointed_before_break",
            "suppress_errors",
        )

        self.uncheckpointed_before_continue = set()

        # AsyncFor guaranteed checkpoint at every iteration
        if isinstance(node, ast.AsyncFor):
            self.uncheckpointed_statements = set()

        pre_body_uncheckpointed_statements = self.uncheckpointed_statements

        # check for all possible uncheckpointed statements before entering start of loop
        # due to `continue` or multiple iterations
        if not isinstance(node, ast.AsyncFor):
            # reset uncheckpointed_statements to not clear it if awaited
            self.uncheckpointed_statements = set()

            # avoid duplicate errors
            self.suppress_errors = True

            # set self.uncheckpointed_before_continue and uncheckpointed at end of loop
            self.visit_nodes(node.body)

            self.suppress_errors = outer["suppress_errors"]

            self.uncheckpointed_statements.update(self.uncheckpointed_before_continue)

        # add uncheckpointed on first iter
        self.uncheckpointed_statements.update(pre_body_uncheckpointed_statements)

        # visit body
        self.uncheckpointed_before_break = set()
        self.visit_nodes(node.body)

        # AsyncFor guarantees checkpoint on running out of iterable
        # so reset checkpoint state at end of loop. (but not state at break)
        if isinstance(node, ast.AsyncFor):
            self.uncheckpointed_statements = set()
        else:
            # enter orelse with worst case:
            # loop body might execute fully before entering orelse
            # (current state of self.uncheckpointed_statements)
            # or not at all
            if not body_guaranteed_once:
                self.uncheckpointed_statements.update(
                    pre_body_uncheckpointed_statements
                )
            # or at a continue, unless it's an infinite loop
            if not infinite_loop:
                self.uncheckpointed_statements.update(
                    self.uncheckpointed_before_continue
                )

        # visit orelse
        self.visit_nodes(node.orelse)

        # if this is an infinite loop, with no break in it, don't raise
        # alarms about the state after it.
        if infinite_loop and not any(
            isinstance(n, ast.Break) for n in self.walk(*node.body)
        ):
            self.uncheckpointed_statements = set()
        else:
            # We may exit from:
            # orelse (covering: no body, body until continue, and all body)
            # break
            self.uncheckpointed_statements.update(self.uncheckpointed_before_break)

        # reset break & continue in case of nested loops
        self.set_state(outer)

    visit_While = visit_loop
    visit_For = visit_loop
    visit_AsyncFor = visit_loop

    # save state in case of continue/break at a point not guaranteed to checkpoint
    def visit_Continue(self, node: ast.Continue):
        if not self.async_function:
            return
        self.uncheckpointed_before_continue.update(self.uncheckpointed_statements)

    def visit_Break(self, node: ast.Break):
        if not self.async_function:
            return
        self.uncheckpointed_before_break.update(self.uncheckpointed_statements)

    # first node in a condition is always evaluated, but may shortcut at any point
    # after that so we track worst-case checkpoint (i.e. after yield)
    def visit_BoolOp(self, node: ast.BoolOp):
        if not self.async_function:
            return
        self.visit(node.op)

        # first value always evaluated
        self.visit(node.values[0])

        worst_case_shortcut = self.uncheckpointed_statements.copy()

        for value in node.values[1:]:
            self.visit(value)
            worst_case_shortcut.update(self.uncheckpointed_statements)

        self.uncheckpointed_statements = worst_case_shortcut
