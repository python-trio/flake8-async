"""Contains Visitor91X and Visitor124.

Visitor91X contains checks for
* ASYNC100 cancel-scope-no-checkpoint
* ASYNC910 async-function-no-checkpoint
* ASYNC911 async-generator-no-checkpoint
* ASYNC912 cancel-scope-no-guaranteed-checkpoint
* ASYNC913 indefinite-loop-no-guaranteed-checkpoint

Visitor124 contains
* ASYNC124 async-function-could-be-sync
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

import libcst as cst
import libcst.matchers as m
from libcst.metadata import CodeRange, PositionProvider

from ..base import Statement
from .flake8asyncvisitor import Flake8AsyncVisitor_cst
from .helpers import (
    MatchingCall,
    cancel_scope_names,
    disable_codes_by_default,
    error_class_cst,
    flatten_preserving_comments,
    fnmatch_qualified_name_cst,
    func_has_decorator,
    get_matching_call_cst,
    identifier_to_string,
    iter_guaranteed_once_cst,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


class ArtificialStatement(Statement):
    """Statement that should not trigger 910/911 on function exit.

    Used by loops and `with` statements.
    """


# Statement injected at the start of loops to track missed checkpoints.
ARTIFICIAL_STATEMENT = ArtificialStatement("artificial", -1)
# There's no particular reason why loops use a globally instanced statement, but
# `with` does not - mostly just an artifact of them being implemented at different times.


def func_empty_body(node: cst.FunctionDef) -> bool:
    """Check if function body consist of `pass`, `...`, and/or (doc)string literals."""
    empty_statement = m.Pass() | m.Expr(m.Ellipsis() | m.SimpleString())

    return m.matches(
        node.body,
        m.OneOf(
            # newline + indented statements
            m.IndentedBlock(
                [m.ZeroOrMore(m.SimpleStatementLine([m.ZeroOrMore(empty_statement)]))]
            ),
            # same-line statement[s]
            m.SimpleStatementSuite(body=[m.ZeroOrMore(empty_statement)]),
        ),
    )


# this could've been implemented as part of visitor91x, but /shrug
@error_class_cst
class Visitor124(Flake8AsyncVisitor_cst):
    error_codes: Mapping[str, str] = {
        "ASYNC124": (
            "Async function with no `await` could be sync."
            " Async functions are more expensive to call."
        )
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.has_await = False
        self.in_class = False

    def visit_ClassDef(self, node: cst.ClassDef):
        self.save_state(node, "in_class", copy=False)
        self.in_class = True

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        self.restore_state(original_node)
        return updated_node

    # await in sync defs are not valid, but handling this will make ASYNC124
    # correctly pop up in parent func as if the child function was async
    def visit_FunctionDef(self, node: cst.FunctionDef):
        # default values are evaluated in parent scope
        # this visitor has no autofixes, so we can throw away return value
        _ = node.params.visit(self)

        self.save_state(node, "has_await", "in_class", copy=False)

        # ignore class methods
        self.has_await = self.in_class

        # but not nested functions
        self.in_class = False

        _ = node.body.visit(self)

        # we've manually visited subnodes (that we care about).
        return False

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if (
            original_node.asynchronous is not None
            and not self.has_await
            and not func_empty_body(original_node)
            and not func_has_decorator(original_node, "overload")
            # skip functions with @fixture and params since they may be relying
            # on async fixtures.
            and not (
                original_node.params.params
                and func_has_decorator(original_node, "fixture")
            )
            # ignore functions with no_checkpoint_warning_decorators
            and not fnmatch_qualified_name_cst(
                original_node.decorators, *self.options.no_checkpoint_warning_decorators
            )
        ):
            self.error(original_node)
        self.restore_state(original_node)
        return updated_node

    def visit_Await(self, node: cst.Await):
        self.has_await = True

    def visit_With(self, node: cst.With | cst.For | cst.CompFor):
        if node.asynchronous is not None:
            self.has_await = True

    visit_For = visit_With
    visit_CompFor = visit_With

    # The generator target will be immediately evaluated, but the other
    # elements will not be evaluated at the point of defining the GenExp.
    # To consume those needs an explicit syntactic checkpoint
    def visit_GeneratorExp(self, node: cst.GeneratorExp):
        node.for_in.iter.visit(self)
        return False


@dataclass
class LoopState:
    infinite_loop: bool = False
    body_guaranteed_once: bool = False
    has_break: bool = False

    uncheckpointed_before_continue: set[Statement] = field(
        default_factory=set[Statement]
    )
    uncheckpointed_before_break: set[Statement] = field(default_factory=set[Statement])
    # pyright emits reportUnknownVariableType, requiring the generic to default_factory
    # to be specified.
    # But for these we require a union, and `|` doesn't work on py39, and uses of
    # `Union` gets autofixed by ruff.
    # So.... let's just ignore the error for now
    artificial_errors: set[  # pyright: ignore[reportUnknownVariableType]
        cst.Return | cst.Yield
    ] = field(default_factory=set)
    nodes_needing_checkpoints: list[  # pyright: ignore[reportUnknownVariableType]
        cst.Return | cst.Yield | ArtificialStatement
    ] = field(default_factory=list)

    def copy(self):
        return LoopState(
            infinite_loop=self.infinite_loop,
            body_guaranteed_once=self.body_guaranteed_once,
            has_break=self.has_break,
            uncheckpointed_before_continue=self.uncheckpointed_before_continue.copy(),
            uncheckpointed_before_break=self.uncheckpointed_before_break.copy(),
            artificial_errors=self.artificial_errors.copy(),
            nodes_needing_checkpoints=self.nodes_needing_checkpoints.copy(),
        )


@dataclass
class TryState:
    body_uncheckpointed_statements: set[Statement] = field(
        default_factory=set[Statement]
    )
    try_checkpoint: set[Statement] = field(default_factory=set[Statement])
    except_uncheckpointed_statements: set[Statement] = field(
        default_factory=set[Statement]
    )
    added: set[Statement] = field(default_factory=set[Statement])

    def copy(self):
        return TryState(
            body_uncheckpointed_statements=self.body_uncheckpointed_statements.copy(),
            try_checkpoint=self.try_checkpoint.copy(),
            except_uncheckpointed_statements=self.except_uncheckpointed_statements.copy(),
            added=self.added.copy(),
        )


@dataclass
class MatchState:
    # TryState, LoopState, and MatchState all do fairly similar things. It would be nice
    # to harmonize them and share logic.
    base_uncheckpointed_statements: set[Statement] = field(
        default_factory=set[Statement]
    )
    case_uncheckpointed_statements: set[Statement] = field(
        default_factory=set[Statement]
    )
    has_fallback: bool = False

    def copy(self):
        return MatchState(
            base_uncheckpointed_statements=self.base_uncheckpointed_statements.copy(),
            case_uncheckpointed_statements=self.case_uncheckpointed_statements.copy(),
            has_fallback=self.has_fallback,
        )


def checkpoint_statement(library: str) -> cst.SimpleStatementLine:
    # logic before this should stop code from wanting to insert the non-existing
    # asyncio.lowlevel.checkpoint
    assert library != "asyncio"
    return cst.SimpleStatementLine(
        [cst.Expr(cst.parse_expression(f"await {library}.lowlevel.checkpoint()"))]
    )


class CommonVisitors(cst.CSTTransformer, ABC):
    """Base class for InsertCheckpointsInLoopBody and Visitor91X.

    Contains the transform methods used to actually insert the checkpoints, as well
    as making sure that the library used will get imported. Adding the library import
    is done in Visitor91X.
    """

    def __init__(self):
        super().__init__()
        self.noautofix: bool = False
        self.add_statement: cst.SimpleStatementLine | None = None

        # used for inserting import if there's none
        self.explicitly_imported_library: dict[str, bool] = {
            "trio": False,
            "anyio": False,
        }
        self.add_import: set[str] = set()

        self.__booldepth = 0

    @property
    @abstractmethod
    def library(self) -> tuple[str, ...]: ...

    @abstractmethod
    def should_autofix(self, node: cst.CSTNode, code: str | None = None) -> bool: ...

    # instead of trying to exclude yields found in all the weird places from
    # setting self.add_statement, we instead clear it upon each new line.
    # Several of them *could* be handled, e.g. `if ...: yield`, but
    # that's uncommon enough we don't care about it.
    def visit_SimpleStatementLine(self, node: cst.SimpleStatementLine):
        super().visit_SimpleStatementLine(node)
        self.add_statement = None

    # insert checkpoint before yield with a flattensentinel, if indicated
    def leave_SimpleStatementLine(
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.SimpleStatementLine | cst.FlattenSentinel[cst.SimpleStatementLine]:
        _ = super().leave_SimpleStatementLine(original_node, updated_node)

        # possible TODO: generate an error if transforming+visiting is done in a
        # single pass and emit-error-on-transform can be enabled/disabled. The error can't
        # be generated in the yield/return since it doesn't know if it will be autofixed.
        if self.add_statement is None:
            return updated_node

        # methods setting self.add_statement should have called self.should_autofix
        assert self.should_autofix(original_node)
        curr_add_statement = self.add_statement
        self.add_statement = None

        # multiple statements on a single line is not handled
        if len(updated_node.body) > 1:
            return updated_node

        self.ensure_imported_library()
        return cst.FlattenSentinel([curr_add_statement, updated_node])

    def visit_BooleanOperation(self, node: cst.BooleanOperation):
        self.__booldepth += 1
        self.noautofix = True

    def leave_BooleanOperation(
        self, original_node: cst.BooleanOperation, updated_node: cst.BooleanOperation
    ):
        assert self.__booldepth
        self.__booldepth -= 1
        if not self.__booldepth:
            self.noautofix = False
        return updated_node

    def ensure_imported_library(self) -> None:
        """Mark library for import.

        Check that the library we'd use to insert checkpoints
        is imported - if not, mark it to be inserted later.
        """
        assert self.library
        if not self.explicitly_imported_library[self.library[0]]:
            self.add_import.add(self.library[0])


class InsertCheckpointsInLoopBody(CommonVisitors):
    """Insert checkpoints in loop bodies.

    This inserts checkpoints that it was not known on the first pass whether a
    checkpoint would be necessary, i.e. no uncheckpointed statements as we started to
    parse the loop, but then there's uncheckpointed statements on continue or as loop
    body finishes.
    Called from `leave_While` and `leave_For` in Visitor91X.
    """

    def __init__(
        self,
        nodes_needing_checkpoint: Sequence[cst.Yield | cst.Return],
        library: tuple[str, ...],
        explicitly_imported: dict[str, bool],
    ):
        super().__init__()
        self.explicitly_imported_library = explicitly_imported
        self.nodes_needing_checkpoint = nodes_needing_checkpoint
        self.__library = library

    @property
    def library(self) -> tuple[str, ...]:
        return self.__library if self.__library else ("trio",)

    def should_autofix(self, node: cst.CSTNode, code: str | None = None) -> bool:
        return not self.noautofix

    def leave_Yield(
        self,
        original_node: cst.Yield,
        updated_node: cst.Yield,
    ) -> cst.Yield:
        # Needs to be passed *original* node, since updated node is a copy
        # which loses identity equality
        if original_node in self.nodes_needing_checkpoint and self.should_autofix(
            original_node
        ):
            self.add_statement = checkpoint_statement(self.library[0])
        return updated_node

    # returns handled same as yield, but ofc needs to ignore types
    leave_Return = leave_Yield  # type: ignore


disable_codes_by_default("ASYNC910", "ASYNC911", "ASYNC912", "ASYNC913")


@dataclass
class ContextManager:
    has_checkpoint: bool | None = None
    call: MatchingCall[cst.Call] | None = None
    line: int | None = None
    column: int | None = None


@error_class_cst
class Visitor91X(Flake8AsyncVisitor_cst, CommonVisitors):
    error_codes: Mapping[str, str] = {
        "ASYNC910": (
            "{0} from async function with no guaranteed checkpoint or exception "
            "since function definition on line {1.lineno}."
        ),
        "ASYNC911": (
            "{0} from async iterable with no guaranteed checkpoint since {1.name} "
            "on line {1.lineno}."
        ),
        "ASYNC912": (
            "CancelScope with no guaranteed cancel point. This makes it potentially "
            "impossible to cancel."
        ),
        "ASYNC913": "Indefinite loop with no guaranteed cancel points.",
        "ASYNC100": (
            "{0}.{1} context contains no checkpoints, remove the context or add"
            " `await {0}.lowlevel.checkpoint()`."
        ),
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.has_yield = False
        self.async_function = False
        self.uncheckpointed_statements: set[Statement] = set()
        self.comp_unknown = False

        self.loop_state = LoopState()
        self.try_state = TryState()
        self.match_state = MatchState()

        # ASYNC100
        self.has_checkpoint_stack: list[ContextManager] = []
        self.taskgroup_has_start_soon: dict[str, bool] = {}

        # --exception-suppress-context-manager
        self.suppress_imported_as: list[str] = []

        # used to transfer new body between visit_FunctionDef and leave_FunctionDef
        self.new_body: cst.BaseSuite | None = None

    def should_autofix(self, node: cst.CSTNode, code: str | None = None) -> bool:
        if code is None:
            code = "ASYNC911" if self.has_yield else "ASYNC910"

        return (
            not self.noautofix
            and super().should_autofix(node, code)
            and self.library != ("asyncio",)
        )

    def checkpoint_cancel_point(self) -> None:
        for cm in reversed(self.has_checkpoint_stack):
            if cm.has_checkpoint:
                # Everything further down in the stack is already True.
                break
            cm.has_checkpoint = True
        # don't need to look for any .start_soon() calls
        self.taskgroup_has_start_soon.clear()

    def checkpoint_schedule_point(self) -> None:
        # ASYNC912&ASYNC913 only cares about cancel points, so don't remove
        # them if we only do a schedule point
        self.uncheckpointed_statements = {
            s
            for s in self.uncheckpointed_statements
            if isinstance(s, ArtificialStatement)
        }

    def checkpoint(self) -> None:
        self.uncheckpointed_statements = set()
        self.checkpoint_cancel_point()

    def checkpoint_statement(self) -> cst.SimpleStatementLine:
        return checkpoint_statement(self.library[0])

    def visit_Call(self, node: cst.Call) -> None:
        # [Nursery/TaskGroup].start_soon introduces a cancel point
        if (
            isinstance(node.func, cst.Attribute)
            and isinstance(node.func.value, cst.Name)
            and node.func.attr.value == "start_soon"
            and node.func.value.value in self.taskgroup_has_start_soon
        ):
            self.taskgroup_has_start_soon[node.func.value.value] = True

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        # Semi-crude approach to handle `from contextlib import suppress`.
        # It does not handle the identifier being overridden, or assigned
        # to other idefintifers. Function scoping is handled though.
        # The "proper" way would be to add a cst version of
        # visitor_utility.VisitorTypeTracker, and expand that to handle imports.
        if isinstance(node.module, cst.Name) and node.module.value == "contextlib":
            # handle `from contextlib import *`
            if isinstance(node.names, cst.ImportStar):
                self.suppress_imported_as.append("suppress")
                return
            for alias in node.names:
                if alias.name.value == "suppress":
                    if alias.asname is not None:
                        # `libcst.AsName` is incorrectly typed
                        # https://github.com/Instagram/LibCST/issues/503
                        assert isinstance(alias.asname.name, cst.Name)
                        self.suppress_imported_as.append(alias.asname.name.value)
                    else:
                        self.suppress_imported_as.append("suppress")
                    return

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        # `await` in default values happen in parent scope
        # we also know we don't ever modify parameters so we can ignore the return value
        _ = node.params.visit(self)

        # don't lint functions whose bodies solely consist of pass or ellipsis
        # @overload functions are also guaranteed to be empty
        # we also ignore pytest fixtures
        if func_has_decorator(node, "overload", "fixture") or func_empty_body(node):
            return False  # subnodes can be ignored

        self.save_state(
            node,
            "has_yield",
            "async_function",
            "uncheckpointed_statements",
            # comp_unknown does not need to be saved
            "loop_state",
            "try_state",
            "has_checkpoint_stack",
            # node_dict is cleaned up and don't need to be saved
            "taskgroup_has_start_soon",
            "suppress_imported_as",  # a copy is saved, but state is not reset
            copy=True,
        )
        self.uncheckpointed_statements = set()
        self.has_checkpoint_stack = []
        self.has_yield = False
        self.loop_state = LoopState()
        # try_state is reset upon entering try
        self.taskgroup_has_start_soon = {}

        self.async_function = (
            node.asynchronous is not None
            and not fnmatch_qualified_name_cst(
                node.decorators, *self.options.no_checkpoint_warning_decorators
            )
        )
        # only visit subnodes if there is an async function defined inside
        # this should improve performance on codebases with many sync functions
        if not self.async_function and not any(
            m.findall(node, m.FunctionDef(asynchronous=m.Asynchronous()))
        ):
            return False

        pos = self.get_metadata(PositionProvider, node).start  # type: ignore
        self.uncheckpointed_statements = {
            Statement("function definition", pos.line, pos.column)  # type: ignore
        }

        # visit body
        # we're not gonna get FlattenSentinel or RemovalSentinel
        self.new_body = cast("cst.BaseSuite", node.body.visit(self))

        # we know that leave_FunctionDef for this FunctionDef will run immediately after
        # this function exits so we don't need to worry about save_state for new_body
        return False

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if (
            self.new_body is not None
            and self.async_function
            # updated_node does not have a position, so we must send original_node
            and self.check_function_exit(original_node)
            and self.should_autofix(original_node)
            and isinstance(self.new_body, cst.IndentedBlock)
        ):
            # insert checkpoint at the end of body
            new_body_block = list(self.new_body.body)
            new_body_block.append(self.checkpoint_statement())
            self.new_body = self.new_body.with_changes(body=new_body_block)

            self.ensure_imported_library()

        if self.new_body is not None:
            updated_node = updated_node.with_changes(body=self.new_body)
        self.restore_state(original_node)
        # reset self.new_body
        self.new_body = None
        return updated_node

    # error if function exit/return/yields with uncheckpointed statements
    # returns a bool indicating if any real (i.e. not artificial) errors were raised
    # so caller can insert checkpoint before statement (if yield/return) or at end
    # of body (functiondef)
    def check_function_exit(
        self,
        original_node: cst.FunctionDef | cst.Return | cst.Yield,
    ) -> bool:
        if not self.uncheckpointed_statements:
            return False

        # Artificial statement is injected in visit_While_body to make sure errors
        # are raised on multiple loops, if e.g. the end of a loop is uncheckpointed.
        if ARTIFICIAL_STATEMENT in self.uncheckpointed_statements:
            # function can't end in the middle of a loop body, where artificial
            # statements are injected
            assert not isinstance(original_node, cst.FunctionDef)

            # Add it to artificial errors, so loop logic can later turn it into
            # a real error if needed.
            self.loop_state.artificial_errors.add(original_node)

            # Add this as a node potentially needing checkpoints only if it
            # missing checkpoints solely depends on whether the artificial statement is
            # "real"
            if len(self.uncheckpointed_statements) == 1 and self.should_autofix(
                original_node
            ):
                self.loop_state.nodes_needing_checkpoints.append(original_node)
                return False

        any_errors = False
        # raise the actual errors
        for statement in self.uncheckpointed_statements:
            if isinstance(statement, ArtificialStatement):
                continue
            any_errors |= self.error_91x(original_node, statement)

        return any_errors

    def leave_Return(
        self, original_node: cst.Return, updated_node: cst.Return
    ) -> cst.Return:
        if not self.async_function:
            return updated_node
        if self.check_function_exit(original_node) and self.should_autofix(
            original_node
        ):
            self.add_statement = self.checkpoint_statement()
        # avoid duplicate error messages
        # but don't see it as a cancel point for ASYNC100
        self.checkpoint_schedule_point()

        # return original node to avoid problems with identity equality
        assert original_node.deep_equals(updated_node)
        return original_node

    def error_91x(
        self,
        node: cst.Return | cst.FunctionDef | cst.Yield,
        statement: Statement,
    ) -> bool:
        assert not isinstance(statement, ArtificialStatement), statement

        if isinstance(node, cst.FunctionDef):
            msg = "exit"
        else:
            msg = node.__class__.__name__.lower()

        return self.error(
            node,
            msg,
            statement,
            error_code="ASYNC911" if self.has_yield else "ASYNC910",
        )

    def leave_Await(
        self, original_node: cst.Await, updated_node: cst.Await
    ) -> cst.Await:
        # the expression being awaited is not checkpointed
        # so only set checkpoint after the await node

        # all nodes are now checkpointed
        self.checkpoint()
        return updated_node

    # raising exception means we don't need to checkpoint so we can treat it as one
    # can't use TypeVar due to libcst's built-in type checking not supporting it
    leave_Raise = leave_Await  # type: ignore

    def _is_exception_suppressing_context_manager(self, node: cst.With) -> bool:
        return (
            fnmatch_qualified_name_cst(
                (x.item for x in node.items if isinstance(x.item, cst.Call)),
                "contextlib.suppress",
                *self.suppress_imported_as,
                *self.options.exception_suppress_context_managers,
            )
            is not None
        )

    def _checkpoint_with(self, node: cst.With, entry: bool):
        """Conditionally checkpoints entry/exit of With.

        If the `with` only contains calls to open_nursery/create_task_group, it's a
        schedule point but not a cancellation point, so we treat it as a checkpoint
        for async91x but not for async100.

        Saves the name of the taskgroup/nursery if entry is set
        """
        if not getattr(node, "asynchronous", None):
            return

        for item in node.items:
            if isinstance(item.item, cst.Call) and identifier_to_string(
                item.item.func
            ) in (
                "trio.open_nursery",
                "anyio.create_task_group",
            ):
                if item.asname is not None and isinstance(item.asname.name, cst.Name):
                    # save the nursery/taskgroup to see if it has a `.start_soon`
                    if entry:
                        self.taskgroup_has_start_soon[item.asname.name.value] = False
                    elif self.taskgroup_has_start_soon.pop(
                        item.asname.name.value, False
                    ):
                        self.checkpoint()
                        return
            else:
                self.checkpoint()
                break
        else:
            # only taskgroup/nursery calls
            self.checkpoint_schedule_point()

    # Async context managers can reasonably checkpoint on either or both of entry and
    # exit.  Given that we can't tell which, we assume "both" to avoid raising a
    # missing-checkpoint warning when there might in fact be one (i.e. a false alarm).
    def visit_With_body(self, node: cst.With):
        self.save_state(node, "taskgroup_has_start_soon", copy=True)

        is_suppressing = False

        # if this might suppress exceptions, we cannot treat anything inside it as
        # checkpointing.
        if self._is_exception_suppressing_context_manager(node):
            self.save_state(node, "uncheckpointed_statements", copy=True)

        for withitem in node.items:
            self.has_checkpoint_stack.append(ContextManager())
            if get_matching_call_cst(
                withitem.item, "open_nursery", "create_task_group"
            ):
                if withitem.asname is not None and isinstance(
                    withitem.asname.name, cst.Name
                ):
                    self.taskgroup_has_start_soon[withitem.asname.name.value] = False
                self.checkpoint_schedule_point()
                # Technically somebody could set open_nursery or create_task_group as
                # suppressing context managers, but we're not add logic for that.
                continue

            if bool(getattr(node, "asynchronous", False)):
                self.checkpoint()

            # not a clean function call
            if not isinstance(withitem.item, cst.Call) or not isinstance(
                withitem.item.func, (cst.Name, cst.Attribute)
            ):
                continue

            if (
                fnmatch_qualified_name_cst(
                    (withitem.item.func,),
                    "contextlib.suppress",
                    *self.suppress_imported_as,
                    *self.options.exception_suppress_context_managers,
                )
                is not None
            ):
                # Don't re-update state if there's several suppressing cm's.
                if not is_suppressing:
                    self.save_state(node, "uncheckpointed_statements", copy=True)
                    is_suppressing = True
                continue

            if res := (
                get_matching_call_cst(withitem.item, *cancel_scope_names)
                or get_matching_call_cst(
                    withitem.item,
                    "timeout",
                    "timeout_at",
                    base="asyncio",
                )
            ):
                # typing issue: https://github.com/Instagram/LibCST/issues/1107
                pos = cst.ensure_type(
                    self.get_metadata(PositionProvider, withitem),
                    CodeRange,
                ).start
                self.uncheckpointed_statements.add(
                    ArtificialStatement("withitem", pos.line, pos.column)
                )

                cm = self.has_checkpoint_stack[-1]
                cm.line = pos.line
                cm.column = pos.column
                cm.call = res
                cm.has_checkpoint = False

    def leave_With(self, original_node: cst.With, updated_node: cst.With):
        withitems = list(updated_node.items)
        for i in reversed(range(len(updated_node.items))):
            cm = self.has_checkpoint_stack.pop()
            # ASYNC100
            if cm.has_checkpoint is False:
                res = cm.call
                assert res is not None
                # bypass 910 & 911's should_autofix logic, which excludes asyncio
                if self.error(
                    res.node, res.base, res.name, error_code="ASYNC100"
                ) and super().should_autofix(res.node, code="ASYNC100"):
                    if len(withitems) == 1:
                        # Remove this With node, bypassing later logic.
                        return flatten_preserving_comments(updated_node)
                    if i == len(withitems) - 1:
                        # preserve trailing comma, or remove comma if there was none
                        withitems[-2] = withitems[-2].with_changes(
                            comma=withitems[-1].comma
                        )
                    withitems.pop(i)

            # ASYNC912
            elif cm.call is not None:
                assert cm.line is not None
                assert cm.column is not None
                s = ArtificialStatement("withitem", cm.line, cm.column)
                if s in self.uncheckpointed_statements:
                    self.uncheckpointed_statements.remove(s)
                    self.error(cm.call.node, error_code="ASYNC912")

        # if exception-suppressing, restore all uncheckpointed statements from
        # before the `with`.
        if self._is_exception_suppressing_context_manager(original_node):
            prev_checkpoints = self.uncheckpointed_statements
            self.restore_state(original_node)
            self.uncheckpointed_statements.update(prev_checkpoints)

        self._checkpoint_with(original_node, entry=False)

        return updated_node.with_changes(items=withitems)

    # error if no checkpoint since earlier yield or function entry
    def leave_Yield(
        self, original_node: cst.Yield, updated_node: cst.Yield
    ) -> cst.Yield:
        if not self.async_function:
            return updated_node
        self.has_yield = True

        # Treat as a checkpoint for ASYNC100, since the context we yield to
        # may checkpoint.
        self.checkpoint_cancel_point()

        if self.check_function_exit(original_node) and self.should_autofix(
            original_node
        ):
            self.add_statement = self.checkpoint_statement()

        # mark as requiring checkpoint after
        pos = self.get_metadata(PositionProvider, original_node).start  # type: ignore
        self.uncheckpointed_statements = {
            Statement("yield", pos.line, pos.column)  # type: ignore
        }
        # return original to avoid problems with identity equality
        assert original_node.deep_equals(updated_node)
        return original_node

    # valid checkpoint if there's valid checkpoints (or raise) in:
    # (try or else) and all excepts, or in finally
    #
    # try can jump into any except or into the finally* at any point during it's
    # execution so we need to make sure except & finally can handle worst-case
    # * unless there's a bare except / except BaseException - not implemented.
    def visit_Try(self, node: cst.Try | cst.TryStar):
        if not self.async_function:
            return
        self.save_state(node, "try_state", copy=True)
        # except & finally guaranteed to enter with checkpoint if checkpointed
        # before try and no yield in try body.
        self.try_state.body_uncheckpointed_statements = (
            self.uncheckpointed_statements.copy()
        )
        # yields inside `try` can always be uncheckpointed
        for inner_node in m.findall(node.body, m.Yield()):
            pos = self.get_metadata(PositionProvider, inner_node).start  # type: ignore
            self.try_state.body_uncheckpointed_statements.add(
                Statement("yield", pos.line, pos.column)  # type: ignore
            )

    def leave_Try_body(self, node: cst.Try | cst.TryStar):
        # save state at end of try for entering else
        self.try_state.try_checkpoint = self.uncheckpointed_statements

        # check that all except handlers checkpoint (await or most likely raise)
        self.try_state.except_uncheckpointed_statements = set()

    def visit_ExceptHandler(self, node: cst.ExceptHandler | cst.ExceptStarHandler):
        # enter with worst case of try
        self.uncheckpointed_statements = (
            self.try_state.body_uncheckpointed_statements.copy()
        )

    def leave_ExceptHandler(
        self,
        original_node: cst.ExceptHandler | cst.ExceptStarHandler,
        updated_node: cst.ExceptHandler | cst.ExceptStarHandler,
    ) -> Any:  # not worth creating a TypeVar to handle correctly
        self.try_state.except_uncheckpointed_statements.update(
            self.uncheckpointed_statements
        )
        return updated_node

    def visit_Try_orelse(self, node: cst.Try | cst.TryStar):
        # check else
        # if else runs it's after all of try, so restore state to back then
        self.uncheckpointed_statements = self.try_state.try_checkpoint

    def leave_Try_orelse(self, node: cst.Try | cst.TryStar):
        # checkpoint if else checkpoints, and all excepts checkpoint
        self.uncheckpointed_statements.update(
            self.try_state.except_uncheckpointed_statements
        )

    def visit_Try_finalbody(self, node: cst.Try | cst.TryStar):
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

    def leave_Try_finalbody(self, node: cst.Try | cst.TryStar):
        if node.finalbody:
            self.uncheckpointed_statements.difference_update(self.try_state.added)

    def leave_Try(
        self, original_node: cst.Try | cst.TryStar, updated_node: cst.Try | cst.TryStar
    ) -> cst.Try | cst.TryStar:
        self.restore_state(original_node)
        return updated_node

    visit_TryStar = visit_Try
    leave_TryStar = leave_Try
    leave_TryStar_body = leave_Try_body
    visit_TryStar_orelse = visit_Try_orelse
    leave_TryStar_orelse = leave_Try_orelse
    visit_TryStar_finalbody = visit_Try_finalbody
    leave_TryStar_finalbody = leave_Try_finalbody
    visit_ExceptStarHandler = visit_ExceptHandler
    leave_ExceptStarHandler = leave_ExceptHandler

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
        return False  # libcst shouldn't visit subnodes again

    def leave_Match_subject(self, node: cst.Match) -> None:
        # We start the match logic after parsing the subject, instead of visit_Match,
        # since the subject is always executed and might checkpoint.
        if not self.async_function:
            return
        self.save_state(node, "match_state", copy=True)
        self.match_state = MatchState(
            base_uncheckpointed_statements=self.uncheckpointed_statements.copy()
        )

    def visit_MatchCase(self, node: cst.MatchCase) -> None:
        # enter each case from the state after parsing the subject
        self.uncheckpointed_statements = self.match_state.base_uncheckpointed_statements

    def leave_MatchCase_guard(self, node: cst.MatchCase) -> None:
        # `case _:` is no pattern and no guard, which means we know body is executed.
        # But we also know that `case _ if <guard>:` is guaranteed to execute the guard,
        # so for later logic we can treat them the same *if* there's no pattern and that
        # guard checkpoints.
        if (
            isinstance(node.pattern, cst.MatchAs)
            and node.pattern.pattern is None
            and (node.guard is None or not self.uncheckpointed_statements)
        ):
            self.match_state.has_fallback = True

    def leave_MatchCase(
        self, original_node: cst.MatchCase, updated_node: cst.MatchCase
    ) -> cst.MatchCase:
        # collect the state at the end of each case
        self.match_state.case_uncheckpointed_statements.update(
            self.uncheckpointed_statements
        )
        return updated_node

    def leave_Match(
        self, original_node: cst.Match, updated_node: cst.Match
    ) -> cst.Match:
        # leave the Match with the worst-case of all branches
        self.uncheckpointed_statements = self.match_state.case_uncheckpointed_statements
        # if no fallback, also add the state at entering the match (after parsing subject)
        if not self.match_state.has_fallback:
            self.uncheckpointed_statements.update(
                self.match_state.base_uncheckpointed_statements
            )

        self.restore_state(original_node)
        return updated_node

    def visit_While(self, node: cst.While | cst.For):
        self.save_state(
            node,
            "loop_state",
            copy=True,
        )
        self.loop_state = LoopState()
        self.loop_state.infinite_loop = self.loop_state.body_guaranteed_once = False

    visit_For = visit_While

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
            self.loop_state.infinite_loop = self.loop_state.body_guaranteed_once = True

    def visit_For_iter(self, node: cst.For):
        self.loop_state.body_guaranteed_once = iter_guaranteed_once_cst(node.iter)

    def visit_While_body(self, node: cst.For | cst.While):
        if not self.async_function:
            return

        self.save_state(
            node,
            "uncheckpointed_statements",
            # reference is overwritten below so don't need to copy
            copy=False,
        )

        # inject an artificial uncheckpointed statement that won't raise an error,
        # but will be marked if an error would be generated. We can then generate
        # appropriate errors if the loop doesn't checkpoint

        if getattr(node, "asynchronous", None):
            self.checkpoint()
        else:
            self.uncheckpointed_statements = {ARTIFICIAL_STATEMENT}

        self.loop_state.uncheckpointed_before_continue = set()
        self.loop_state.uncheckpointed_before_break = set()

    visit_For_body = visit_While_body

    def leave_While_body(self, node: cst.For | cst.While):
        if not self.async_function:
            return

        # if there's errors due to the artificial statement
        # raise a real error for each statement in outer[uncheckpointed_statements],
        # uncheckpointed_before_continue, and checkpoints at the end of the loop
        any_error = False
        for err_node in self.loop_state.artificial_errors:
            for stmt in (
                self.outer[node]["uncheckpointed_statements"]
                | self.uncheckpointed_statements
                | self.loop_state.uncheckpointed_before_continue
            ):
                if isinstance(stmt, ArtificialStatement):
                    continue
                any_error |= self.error_91x(err_node, stmt)

        # if there's no errors from artificial statements, we don't need to insert
        # the potential checkpoints
        if not any_error:
            self.loop_state.nodes_needing_checkpoints = []

        if (
            self.loop_state.infinite_loop
            and not self.loop_state.has_break
            and ARTIFICIAL_STATEMENT in self.uncheckpointed_statements
            and self.error(node, error_code="ASYNC913")
        ):
            # We can override nodes_needing_checkpoints, as that's solely for checkpoints
            # that error because of the artificial statement injected at the start of
            # the loop. When inserting a checkpoint at the start of the loop, those
            # will be remedied
            self.loop_state.nodes_needing_checkpoints = [ARTIFICIAL_STATEMENT]

        # replace artificial statements in else with prebody uncheckpointed statements
        # non-artificial stmts before continue/break/at body end will already be in them
        for stmts in (
            self.loop_state.uncheckpointed_before_continue,
            self.loop_state.uncheckpointed_before_break,
            self.uncheckpointed_statements,
        ):
            if ARTIFICIAL_STATEMENT in stmts:
                stmts.remove(ARTIFICIAL_STATEMENT)
                stmts.update(self.outer[node]["uncheckpointed_statements"])

        # AsyncFor guarantees checkpoint on running out of iterable
        # so reset checkpoint state at end of loop. (but not state at break)
        if getattr(node, "asynchronous", None):
            self.checkpoint()
        else:
            # enter orelse with worst case:
            # loop body might execute fully before entering orelse
            # (current state of self.uncheckpointed_statements)
            # or not at all
            if not self.loop_state.body_guaranteed_once:
                self.uncheckpointed_statements.update(
                    self.outer[node]["uncheckpointed_statements"]
                )
            # or at a continue, unless it's an infinite loop
            if not self.loop_state.infinite_loop:
                self.uncheckpointed_statements.update(
                    self.loop_state.uncheckpointed_before_continue
                )

    leave_For_body = leave_While_body

    def leave_While_orelse(self, node: cst.For | cst.While):
        if not self.async_function:
            return
        # if this is an infinite loop, with no break in it, don't raise
        # alarms about the state after it.
        if self.loop_state.infinite_loop and not self.loop_state.has_break:
            self.uncheckpointed_statements = set()
        else:
            # We may exit from:
            # orelse (covering: no body, body until continue, and all body)
            # `break`
            self.uncheckpointed_statements.update(
                self.loop_state.uncheckpointed_before_break
            )

        # reset break & continue in case of nested loops
        self.outer[node]["uncheckpointed_statements"] = self.uncheckpointed_statements

    leave_For_orelse = leave_While_orelse

    def leave_While(
        self, original_node: cst.For | cst.While, updated_node: cst.For | cst.While
    ) -> (
        cst.While
        | cst.For
        | cst.FlattenSentinel[cst.For | cst.While]
        | cst.RemovalSentinel
    ):
        # don't bother autofixing same-line loops
        if isinstance(updated_node.body, cst.SimpleStatementSuite):
            self.restore_state(original_node)
            return updated_node

        # ASYNC913, indefinite loop with no guaranteed checkpoint
        if self.loop_state.nodes_needing_checkpoints == [ARTIFICIAL_STATEMENT]:
            if self.should_autofix(original_node, code="ASYNC913"):
                # insert checkpoint at start of body
                new_body = list(updated_node.body.body)
                new_body.insert(0, self.checkpoint_statement())
                indentedblock = updated_node.body.with_changes(body=new_body)
                updated_node = updated_node.with_changes(body=indentedblock)

                self.ensure_imported_library()
        elif self.loop_state.nodes_needing_checkpoints:
            assert ARTIFICIAL_STATEMENT not in self.loop_state.nodes_needing_checkpoints
            transformer = InsertCheckpointsInLoopBody(
                cast(
                    "list[cst.Yield | cst.Return]",
                    self.loop_state.nodes_needing_checkpoints,
                ),
                self.library,
                self.explicitly_imported_library,
            )
            # type of updated_node expanded to the return type
            updated_node = updated_node.visit(transformer)  # type: ignore

            # include any necessary import added
            self.add_import.update(transformer.add_import)

        self.restore_state(original_node)
        return updated_node

    leave_For = leave_While

    # save state in case of continue/break at a point not guaranteed to checkpoint
    def visit_Continue(self, node: cst.Continue):
        if not self.async_function:
            return
        self.loop_state.uncheckpointed_before_continue.update(
            self.uncheckpointed_statements
        )

    def visit_Break(self, node: cst.Break):
        self.loop_state.has_break = True
        if not self.async_function:
            return
        self.loop_state.uncheckpointed_before_break.update(
            self.uncheckpointed_statements
        )

    # we visit BooleanOperation_left as usual, but ignore checkpoints in the
    # right-hand side while still adding any yields in it.
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
            self.checkpoint()
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

    # The generator target will be immediately evaluated, but the other
    # elements will not be evaluated at the point of defining the GenExp.
    # To consume those needs an explicit syntactic checkpoint
    def visit_GeneratorExp(self, node: cst.GeneratorExp):
        node.for_in.iter.visit(self)
        return False

    def visit_Import(self, node: cst.Import):
        """Register explicitly imported library.

        This is *slightly* different enough from what the utility visitor does
        that it's added here, but the functionality is maybe better placed in there.
        """
        for alias in node.names:
            if m.matches(
                alias, m.ImportAlias(name=m.Name("trio") | m.Name("anyio"), asname=None)
            ):
                assert isinstance(alias.name.value, str)
                self.explicitly_imported_library[alias.name.value] = True

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module):
        """Add needed library import, if any, to the module."""
        if not self.add_import:
            return updated_node

        # make sure we insert the import after docstring[s], comments at the beginning of
        # the file, and after other imports (especially important to be after __future__)
        new_body = list(updated_node.body)
        index = 0
        while m.matches(
            new_body[index],
            m.SimpleStatementLine(
                [m.ImportFrom() | m.Import() | m.Expr(m.SimpleString())]
            ),
        ):
            index += 1
        # trivial to insert multiple imports - but it should not happen with current
        # implementation
        assert len(self.add_import) == 1
        new_body.insert(index, cst.parse_statement(f"import {self.library[0]}"))
        return updated_node.with_changes(body=new_body)
