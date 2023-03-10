"""Contains Visitor91X.

910 looks for async functions without guaranteed checkpoints (or exceptions), and 911 does
the same except for async iterables - while also requiring that they checkpoint between
each yield.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import libcst as cst
import libcst.matchers as m
from libcst.metadata import PositionProvider

from ..base import Statement
from .flake8triovisitor import Flake8TrioVisitor_cst
from .helpers import (
    disabled_by_default,
    error_class_cst,
    fnmatch_qualified_name_cst,
    func_has_decorator,
    iter_guaranteed_once_cst,
)

ARTIFICIAL_STATEMENT = Statement("artificial", -1)


def func_empty_body(node: cst.FunctionDef) -> bool:
    # Does the function body consist solely of `pass`, `...`, and (doc)string literals?
    empty_statement = m.Pass() | m.Expr(m.Ellipsis() | m.SimpleString())
    return m.matches(
        node.body,
        m.IndentedBlock(
            [m.ZeroOrMore(m.SimpleStatementLine([m.ZeroOrMore(empty_statement)]))]
        ),
    )


@dataclass
class LoopState:
    infinite_loop: bool = False
    body_guaranteed_once: bool = False
    has_break: bool = False

    uncheckpointed_before_continue: set[Statement] = field(default_factory=set)
    uncheckpointed_before_break: set[Statement] = field(default_factory=set)
    artificial_errors: set[cst.Return | cst.FunctionDef | cst.Yield] = field(
        default_factory=set
    )

    def copy(self):
        return LoopState(
            infinite_loop=self.infinite_loop,
            body_guaranteed_once=self.body_guaranteed_once,
            has_break=self.has_break,
            uncheckpointed_before_continue=self.uncheckpointed_before_continue.copy(),
            uncheckpointed_before_break=self.uncheckpointed_before_break.copy(),
            artificial_errors=self.artificial_errors.copy(),
        )


@dataclass
class TryState:
    body_uncheckpointed_statements: set[Statement] = field(default_factory=set)
    try_checkpoint: set[Statement] = field(default_factory=set)
    except_uncheckpointed_statements: set[Statement] = field(default_factory=set)
    added: set[Statement] = field(default_factory=set)

    def copy(self):
        return TryState(
            body_uncheckpointed_statements=self.body_uncheckpointed_statements.copy(),
            try_checkpoint=self.try_checkpoint.copy(),
            except_uncheckpointed_statements=self.except_uncheckpointed_statements.copy(),
            added=self.added.copy(),
        )


@error_class_cst
@disabled_by_default
class Visitor91X(Flake8TrioVisitor_cst):
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
        self.comp_unknown = False

        self.loop_state = LoopState()
        self.try_state = TryState()

    @property
    def infinite_loop(self) -> bool:
        return self.loop_state.infinite_loop

    @infinite_loop.setter
    def infinite_loop(self, value: bool):
        self.loop_state.infinite_loop = value

    @property
    def body_guaranteed_once(self) -> bool:
        return self.loop_state.body_guaranteed_once

    @body_guaranteed_once.setter
    def body_guaranteed_once(self, value: bool):
        self.loop_state.body_guaranteed_once = value

    @property
    def has_break(self) -> bool:
        return self.loop_state.has_break

    @has_break.setter
    def has_break(self, value: bool):
        self.loop_state.has_break = value

    @property
    def uncheckpointed_before_continue(self) -> set[Statement]:
        return self.loop_state.uncheckpointed_before_continue

    @uncheckpointed_before_continue.setter
    def uncheckpointed_before_continue(self, value: set[Statement]):
        self.loop_state.uncheckpointed_before_continue = value

    @property
    def uncheckpointed_before_break(self) -> set[Statement]:
        return self.loop_state.uncheckpointed_before_break

    @uncheckpointed_before_break.setter
    def uncheckpointed_before_break(self, value: set[Statement]):
        self.loop_state.uncheckpointed_before_break = value

    @property
    def artificial_errors(self) -> set[cst.Return | cst.FunctionDef | cst.Yield]:
        return self.loop_state.artificial_errors

    @artificial_errors.setter
    def artificial_errors(self, value: set[cst.Return | cst.FunctionDef | cst.Yield]):
        self.loop_state.artificial_errors = value  # pragma: no cover

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        # don't lint functions whose bodies solely consist of pass or ellipsis
        if func_has_decorator(node, "overload", "fixture") or func_empty_body(node):
            return

        self.save_state(
            node,
            "has_yield",
            "safe_decorator",
            "async_function",
            "uncheckpointed_statements",
            "loop_state",
            "try_state",
            copy=True,
        )
        self.uncheckpointed_statements = set()
        self.has_yield = self.safe_decorator = False
        self.loop_state = LoopState()

        self.async_function = (
            node.asynchronous is not None
            and not fnmatch_qualified_name_cst(
                node.decorators, *self.options.no_checkpoint_warning_decorators
            )
        )
        if not self.async_function:
            return

        pos = self.get_metadata(PositionProvider, node).start
        self.uncheckpointed_statements = {
            Statement("function definition", pos.line, pos.column)
        }

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if self.async_function:
            # updated_node does not have a Position, so we must send original_node
            self.check_function_exit(original_node)
        self.restore_state(original_node)
        return updated_node

    # error if function exits or returns with uncheckpointed statements
    def check_function_exit(self, node: cst.Return | cst.FunctionDef):
        for statement in self.uncheckpointed_statements:
            self.error_91x(node, statement)

    def leave_Return(
        self, original_node: cst.Return, updated_node: cst.Return
    ) -> cst.Return:
        if not self.async_function:
            return updated_node
        self.check_function_exit(original_node)
        # avoid duplicate error messages
        self.uncheckpointed_statements = set()

        return updated_node

    def error_91x(
        self, node: cst.Return | cst.FunctionDef | cst.Yield, statement: Statement
    ):
        # artificial statement is injected in visit_While_body to make sure errors
        # are raised on multiple loops, if e.g. the end of a loop is uncheckpointed.
        # Here we add it to artificial errors, so loop logic can later turn it into
        # a real error if needed.
        if statement == ARTIFICIAL_STATEMENT:
            self.loop_state.artificial_errors.add(node)
            return
        if isinstance(node, cst.FunctionDef):
            msg = "exit"
        else:
            msg = node.__class__.__name__.lower()

        self.error(
            node,
            msg,
            statement,
            error_code="TRIO911" if self.has_yield else "TRIO910",
        )

    def leave_Await(
        self, original_node: cst.Await, updated_node: cst.Await
    ) -> cst.Await:
        # the expression being awaited is not checkpointed
        # so only set checkpoint after the await node

        # all nodes are now checkpointed
        self.uncheckpointed_statements = set()
        return updated_node

    # raising exception means we don't need to checkpoint so we can treat it as one
    # can't use TypeVar due to libcst's built-in type checking not supporting it
    leave_Raise = leave_Await  # type: ignore

    # Async context managers can reasonably checkpoint on either or both of entry and
    # exit.  Given that we can't tell which, we assume "both" to avoid raising a
    # missing-checkpoint warning when there might in fact be one (i.e. a false alarm).
    def visit_With_body(self, node: cst.With):
        if getattr(node, "asynchronous", None):
            self.uncheckpointed_statements = set()

    leave_With_body = visit_With_body

    # error if no checkpoint since earlier yield or function entry
    def leave_Yield(
        self, original_node: cst.Yield, updated_node: cst.Yield
    ) -> cst.Yield:
        if not self.async_function:
            return updated_node
        self.has_yield = True
        for statement in self.uncheckpointed_statements:
            self.error_91x(original_node, statement)

        # mark as requiring checkpoint after
        pos = self.get_metadata(PositionProvider, original_node).start
        self.uncheckpointed_statements = {Statement("yield", pos.line, pos.column)}
        return updated_node

    # valid checkpoint if there's valid checkpoints (or raise) in:
    # (try or else) and all excepts, or in finally
    #
    # try can jump into any except or into the finally* at any point during it's
    # execution so we need to make sure except & finally can handle worst-case
    # * unless there's a bare except / except BaseException - not implemented.
    def visit_Try(self, node: cst.Try):
        if not self.async_function:
            return
        self.save_state(node, "try_state")
        # except & finally guaranteed to enter with checkpoint if checkpointed
        # before try and no yield in try body.
        self.try_state.body_uncheckpointed_statements = (
            self.uncheckpointed_statements.copy()
        )
        for inner_node in m.findall(node.body, m.Yield()):
            pos = self.get_metadata(PositionProvider, inner_node).start
            self.try_state.body_uncheckpointed_statements.add(
                Statement("yield", pos.line, pos.column)
            )

    def leave_Try_body(self, node: cst.Try):
        # save state at end of try for entering else
        self.try_state.try_checkpoint = self.uncheckpointed_statements

        # check that all except handlers checkpoint (await or most likely raise)
        self.try_state.except_uncheckpointed_statements = set()

    def visit_ExceptHandler(self, node: cst.ExceptHandler):
        # enter with worst case of try
        self.uncheckpointed_statements = (
            self.try_state.body_uncheckpointed_statements.copy()
        )

    def leave_ExceptHandler(
        self, original_node: cst.ExceptHandler, updated_node: cst.ExceptHandler
    ) -> cst.ExceptHandler:
        self.try_state.except_uncheckpointed_statements.update(
            self.uncheckpointed_statements
        )
        return updated_node

    def visit_Try_orelse(self, node: cst.Try):
        # check else
        # if else runs it's after all of try, so restore state to back then
        self.uncheckpointed_statements = self.try_state.try_checkpoint

    def leave_Try_orelse(self, node: cst.Try):
        # checkpoint if else checkpoints, and all excepts checkpoint
        self.uncheckpointed_statements.update(
            self.try_state.except_uncheckpointed_statements
        )

    def visit_Try_finalbody(self, node: cst.Try):
        if node.finalbody:
            self.try_state.added = (
                self.try_state.body_uncheckpointed_statements.difference(
                    self.uncheckpointed_statements
                )
            )
            # if there's no bare except or except BaseException, we can jump into
            # finally from any point in try. But the exception will be reraised after
            # finally, so track what we add so it can be removed later.
            # (This is for catching return or yield in the finally, which is usually
            # very bad)
            if not any(
                h.type is None
                or (isinstance(h.type, cst.Name) and h.type.value == "BaseException")
                for h in node.handlers
            ):
                self.uncheckpointed_statements.update(self.try_state.added)

    def leave_Try_finalbody(self, node: cst.Try):
        if node.finalbody:
            self.uncheckpointed_statements.difference_update(self.try_state.added)

    def leave_Try(self, original_node: cst.Try, updated_node: cst.Try) -> cst.Try:
        self.restore_state(original_node)
        return updated_node

    def leave_If_test(self, node: cst.If | cst.IfExp) -> None:
        if not self.async_function:
            return
        self.save_state(node, "uncheckpointed_statements", copy=True)

    def leave_If_body(self, node: cst.If | cst.IfExp) -> None:
        if not self.async_function:
            return

        # restore state to after test, saving current state instead
        (
            self.uncheckpointed_statements,
            self.outer[node]["uncheckpointed_statements"],
        ) = (
            self.outer[node]["uncheckpointed_statements"],
            self.uncheckpointed_statements,
        )

    def leave_If(self, original_node: cst.If, updated_node: cst.If) -> cst.If:
        if self.async_function:
            # merge current state with post-body state
            self.uncheckpointed_statements.update(
                self.outer[original_node]["uncheckpointed_statements"]
            )
        return updated_node

    # libcst calls attributes in the order they appear in the code, so we manually
    # rejig the order here
    def visit_IfExp(self, node: cst.IfExp) -> bool:
        _ = node.test.visit(self)
        self.leave_If_test(node)
        _ = node.body.visit(self)
        self.leave_If_body(node)
        _ = node.orelse.visit(self)
        self.leave_If(node, node)  # type: ignore
        return False

    def visit_While(self, node: cst.While | cst.For):
        self.save_state(
            node,
            "loop_state",
            copy=True,
        )
        self.loop_state = LoopState()
        self.infinite_loop = self.body_guaranteed_once = False

    # Check for yields w/o checkpoint in between due to entering loop body the first time,
    # after completing all of loop body, and after any continues.
    # yield in else have same requirement
    # state after the loop same as above, and in addition the state at any break
    def visit_While_test(self, node: cst.While):
        # save state in case of nested loops
        # One could plausibly just check for True here
        if (m.matches(node.test, m.Name("True"))) or (
            getattr(node.test, "evaluated_value", False)
        ):
            self.infinite_loop = self.body_guaranteed_once = True

    def visit_For_iter(self, node: cst.For):
        self.body_guaranteed_once = iter_guaranteed_once_cst(node.iter)

    def visit_While_body(self, node: cst.While | cst.For):
        if not self.async_function:
            return

        self.save_state(
            node,
            "uncheckpointed_statements",
        )

        # inject an artificial uncheckpointed statement that won't raise an error,
        # but will be marked if an error would be generated. We can then generate
        # appropriate errors if the loop doesn't checkpoint

        if getattr(node, "asynchronous", None):
            self.uncheckpointed_statements = set()
        else:
            self.uncheckpointed_statements = {ARTIFICIAL_STATEMENT}

        self.uncheckpointed_before_continue = set()
        self.uncheckpointed_before_break = set()

    visit_For_body = visit_While_body

    def leave_While_body(self, node: cst.While | cst.For):
        if not self.async_function:
            return
        # if there's errors due to the artificial statement
        # raise a real error for each statement in outer[uncheckpointed_statements],
        # uncheckpointed_before_continue, and uncheckpointed_before_break
        new_uncheckpointed_statements = (
            self.outer[node]["uncheckpointed_statements"]
            | self.uncheckpointed_statements
        )
        for err_node in self.artificial_errors:
            for stmt in (
                new_uncheckpointed_statements | self.uncheckpointed_before_continue
            ):
                self.error_91x(err_node, stmt)

        # replace artificial in break with prebody uncheckpointed statements
        for stmts in (
            self.uncheckpointed_before_continue,
            self.uncheckpointed_before_break,
            self.uncheckpointed_statements,
        ):
            if ARTIFICIAL_STATEMENT in stmts:
                stmts.remove(ARTIFICIAL_STATEMENT)
                stmts.update(self.outer[node]["uncheckpointed_statements"])

        # AsyncFor guarantees checkpoint on running out of iterable
        # so reset checkpoint state at end of loop. (but not state at break)
        if getattr(node, "asynchronous", None):
            self.uncheckpointed_statements = set()
        else:
            # enter orelse with worst case:
            # loop body might execute fully before entering orelse
            # (current state of self.uncheckpointed_statements)
            # or not at all
            if not self.body_guaranteed_once:
                self.uncheckpointed_statements.update(
                    self.outer[node]["uncheckpointed_statements"]
                )
            # or at a continue, unless it's an infinite loop
            if not self.infinite_loop:
                self.uncheckpointed_statements.update(
                    self.uncheckpointed_before_continue
                )

    leave_For_body = leave_While_body

    def leave_While_orelse(self, node: cst.While | cst.For):
        if not self.async_function:
            return
        # if this is an infinite loop, with no break in it, don't raise
        # alarms about the state after it.
        if self.infinite_loop and not self.has_break:
            self.uncheckpointed_statements = set()
        else:
            # We may exit from:
            # orelse (covering: no body, body until continue, and all body)
            # break
            self.uncheckpointed_statements.update(self.uncheckpointed_before_break)

        # reset break & continue in case of nested loops
        self.outer[node]["uncheckpointed_statements"] = self.uncheckpointed_statements
        self.restore_state(node)

    leave_For_orelse = leave_While_orelse

    # save state in case of continue/break at a point not guaranteed to checkpoint
    def visit_Continue(self, node: cst.Continue):
        if not self.async_function:
            return
        self.uncheckpointed_before_continue.update(self.uncheckpointed_statements)

    def visit_Break(self, node: cst.Break):
        self.has_break = True
        if not self.async_function:
            return
        self.uncheckpointed_before_break.update(self.uncheckpointed_statements)

    # first node in a condition is always evaluated, but may shortcut at any point
    # after that so we track worst-case checkpoint (i.e. after yield)
    def visit_BooleanOperation_right(self, node: cst.BooleanOperation):
        if not self.async_function:
            return
        self.save_state(node, "uncheckpointed_statements", copy=True)

    def leave_BooleanOperation_right(self, node: cst.BooleanOperation):
        if not self.async_function:
            return
        self.uncheckpointed_statements.update(
            self.outer[node]["uncheckpointed_statements"]
        )

    # comprehensions are simpler than loops, since they cannot contain yields
    # or many other complicated statements, but their subfields are not in the order
    # they're logically executed, so we manually visit each field in execution order,
    # as long as the effect of the statement is not known. Once we know the comprehension
    # will checkpoint, we stop visiting, or once we are no longer guaranteed to execute
    # code deeper in the comprehension.
    # Functions return `False` so libcst doesn't iterate subnodes [again].
    def visit_ListComp(self, node: cst.DictComp | cst.SetComp | cst.ListComp):
        if not self.async_function or not self.uncheckpointed_statements:
            return False

        outer = self.comp_unknown
        self.comp_unknown = True

        # visit `for` and `if`s
        node.for_in.visit(self)

        # if still unknown, visit the expression
        if self.comp_unknown and self.uncheckpointed_statements:
            if isinstance(node, cst.DictComp):
                node.key.visit(self)
                node.value.visit(self)
            else:
                node.elt.visit(self)

        self.comp_unknown = outer
        return False

    visit_SetComp = visit_ListComp
    visit_DictComp = visit_ListComp

    def visit_CompFor(self, node: cst.CompFor):
        # should only ever be visited manually, when inside an async function
        assert self.async_function

        if not self.uncheckpointed_statements:
            return False

        # if async comprehension, checkpoint
        if node.asynchronous:
            self.uncheckpointed_statements = set()
            self.comp_unknown = False
            return False

        # visit the iter call, which might have await's
        node.iter.visit(self)

        # stop checking if the loop is not guaranteed to execute
        if not iter_guaranteed_once_cst(node.iter):
            self.comp_unknown = False

        # only the first `if` is guaranteed to execute
        # and if there's any, don't check inner loop
        elif node.ifs:
            self.comp_unknown = False
            node.ifs[0].visit(self)
        elif node.inner_for_in:
            # visit nested loops (and ifs), if any
            node.inner_for_in.visit(self)

        return False

    # We don't have any logic on if generators are guaranteed to unroll, so always
    # ignore their content
    def visit_GeneratorExp(self, node: cst.GeneratorExp):
        return False
