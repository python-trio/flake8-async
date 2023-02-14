"""Various visitors/error classes that are too small to warrant getting their own file."""

from __future__ import annotations

import ast
from typing import Any, cast

from .flake8triovisitor import Flake8TrioVisitor
from .helpers import (
    cancel_scope_names,
    disabled_by_default,
    error_class,
    get_matching_call,
    has_decorator,
)

# used in 100
checkpoint_node_types = (ast.Await, ast.AsyncFor, ast.AsyncWith)


@error_class
class Visitor100(Flake8TrioVisitor):
    error_codes = {
        "TRIO100": (
            "{0}.{1} context contains no checkpoints, remove the context or add"
            " `await {0}.lowlevel.checkpoint()`."
        ),
    }

    def visit_With(self, node: ast.With | ast.AsyncWith):
        for item in (i.context_expr for i in node.items):
            call = get_matching_call(item, *cancel_scope_names)
            if call and not any(
                isinstance(x, checkpoint_node_types) and x != node
                for x in ast.walk(node)
            ):
                # type checking has been done inside get_matching_call
                self.error(item, call[2], call[1])

    visit_AsyncWith = visit_With


@error_class
class Visitor101(Flake8TrioVisitor):
    error_codes = {
        "TRIO101": (
            "`yield` inside a nursery or cancel scope is only safe when implementing "
            "a context manager - otherwise, it breaks exception handling."
        ),
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._yield_is_error = False
        self._safe_decorator = False

    def visit_With(self, node: ast.With | ast.AsyncWith):
        self.save_state(node, "_yield_is_error", copy=True)
        for item in node.items:
            # if there's no safe decorator,
            # and it's not yet been determined that yield is error
            # and this withitem opens a cancelscope:
            # then yielding is unsafe
            if (
                not self._safe_decorator
                and not self._yield_is_error
                and get_matching_call(
                    item.context_expr, "open_nursery", *cancel_scope_names
                )
                is not None
            ):
                self._yield_is_error = True

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        self.save_state(node)
        self._yield_is_error = False
        self._safe_decorator = has_decorator(
            node.decorator_list, "contextmanager", "asynccontextmanager"
        )

    visit_AsyncWith = visit_With
    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Yield(self, node: ast.Yield):
        if self._yield_is_error:
            self.error(node)


@error_class
class Visitor106(Flake8TrioVisitor):
    error_codes = {
        "TRIO106": "{0} must be imported with `import {0}` for the linter to work.",
    }

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module in ("trio", "anyio"):
            self.error(node, node.module)

    def visit_Import(self, node: ast.Import):
        for name in node.names:
            if name.name in ("trio", "anyio") and name.asname is not None:
                self.error(node, name.name)


@error_class
class Visitor109(Flake8TrioVisitor):
    error_codes = {
        "TRIO109": (
            "Async function definition with a `timeout` parameter - use "
            "`{}.[fail/move_on]_[after/at]` instead."
        ),
    }

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # pending configuration or a more sophisticated check, ignore
        # all functions with a decorator
        if node.decorator_list:
            return

        args = node.args
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
            if arg.arg == "timeout":
                self.error(arg, self.library_str)


@error_class
class Visitor110(Flake8TrioVisitor):
    error_codes = {
        "TRIO110": (
            "`while <condition>: await {0}.sleep()` should be replaced by "
            "a `{0}.Event`."
        ),
    }

    def visit_While(self, node: ast.While):
        if (
            len(node.body) == 1
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Await)
            and get_matching_call(node.body[0].value.value, "sleep", "sleep_until")
        ):
            self.error(node, self.library_str)


@error_class
class Visitor112(Flake8TrioVisitor):
    error_codes = {
        "TRIO112": (
            "Redundant nursery {}, consider replacing with directly awaiting "
            "the function call."
        ),
    }

    # if with has a withitem `trio.open_nursery() as <X>`,
    # and the body is only a single expression <X>.start[_soon](),
    # and does not pass <X> as a parameter to the expression
    def visit_With(self, node: ast.With | ast.AsyncWith):
        # body is single expression
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Expr):
            return
        for item in node.items:
            # get variable name <X>
            if not isinstance(item.optional_vars, ast.Name):
                continue
            var_name = item.optional_vars.id

            # check for trio.open_nursery
            nursery = get_matching_call(item.context_expr, "open_nursery")

            # `isinstance(..., ast.Call)` is done in get_matching_call
            body_call = cast(ast.Call, node.body[0].value)

            if (
                nursery is not None
                and get_matching_call(body_call, "start", "start_soon", base=var_name)
                # check for presence of <X> as parameter
                and not any(
                    (isinstance(n, ast.Name) and n.id == var_name)
                    for n in self.walk(*body_call.args, *body_call.keywords)
                )
            ):
                self.error(item.context_expr, var_name)

    visit_AsyncWith = visit_With


# used in 113 and 900
def _get_identifier(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _get_identifier(node.func)
    return ""


# used in 113 and 114
STARTABLE_CALLS = (
    "run_process",
    "serve_ssl_over_tcp",
    "serve_tcp",
    "serve_listeners",
    "serve",
)


@error_class
class Visitor113(Flake8TrioVisitor):
    error_codes = {
        "TRIO113": (
            "Dangerous `.start_soon()`, function might not be executed before"
            " `__aenter__` exits. Consider replacing with `.start()`."
        ),
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.typed_calls["trio.open_nursery"] = "trio.Nursery"
        self.typed_calls["anyio.create_task_group"] = "anyio.TaskGroup"

        self.async_function = False
        self.asynccontextmanager = False
        self.aenter = False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.save_state(node, "aenter")

        self.aenter = node.name == "__aenter__" or any(
            _get_identifier(d) == "asynccontextmanager" for d in node.decorator_list
        )

    def visit_Yield(self, node: ast.Yield):
        self.aenter = False

    def visit_Call(self, node: ast.Call) -> None:
        def is_startable(n: ast.expr, *startable_list: str) -> bool:
            if isinstance(n, ast.Name):
                return n.id in startable_list
            if isinstance(n, ast.Attribute):
                return n.attr in startable_list
            if isinstance(n, ast.Call):
                return any(is_startable(nn, *startable_list) for nn in n.args)
            return False

        def is_nursery_call(node: ast.expr):
            if not isinstance(node, ast.Attribute) or node.attr != "start_soon":
                return False
            var = ast.unparse(node.value)
            return ("trio" in self.library and var.endswith("nursery")) or (
                self.variables.get(var, "")
                in (
                    "trio.Nursery",
                    "anyio.TaskGroup",
                )
            )

        if (
            self.aenter
            and is_nursery_call(node.func)
            and len(node.args) > 0
            and is_startable(
                node.args[0],
                *STARTABLE_CALLS,
                *self.options.startable_in_context_manager,
            )
        ):
            self.error(node)


# Checks that all async functions with a "task_status" parameter have a match in
# --startable-in-context-manager. Will only match against the last part of the option
# name, so may miss cases where functions are named the same in different modules/classes
# and option names are specified including the module name.
@error_class
class Visitor114(Flake8TrioVisitor):
    error_codes = {
        "TRIO114": (
            "Startable function {} not in --startable-in-context-manager parameter "
            "list, please add it so TRIO113 can catch errors using it."
        ),
    }

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if any(
            isinstance(n, ast.arg) and n.arg == "task_status"
            for n in self.walk(*node.args.args, *node.args.kwonlyargs)
        ) and not any(
            node.name == opt
            for opt in (*self.options.startable_in_context_manager, *STARTABLE_CALLS)
        ):
            self.error(node, node.name)


# Suggests replacing all `trio.sleep(0)` with the more suggestive
# `trio.lowlevel.checkpoint()`
@error_class
class Visitor115(Flake8TrioVisitor):
    error_codes = {
        "TRIO115": "Use `{0}.lowlevel.checkpoint()` instead of `{0}.sleep(0)`.",
    }

    def visit_Call(self, node: ast.Call):
        if (
            (m := get_matching_call(node, "sleep"))
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == 0
        ):
            # m[2] is set to node.func.value.id
            self.error(node, m[2])


@error_class
class Visitor116(Flake8TrioVisitor):
    error_codes = {
        "TRIO116": (
            "{0}.sleep() with >24 hour interval should usually be "
            "`{0}.sleep_forever()`."
        ),
    }

    def visit_Call(self, node: ast.Call):
        if (m := get_matching_call(node, "sleep")) and len(node.args) == 1:
            arg = node.args[0]
            if (
                # `trio.sleep(math.inf)`
                (isinstance(arg, ast.Attribute) and arg.attr == "inf")
                # `trio.sleep(inf)`
                or (isinstance(arg, ast.Name) and arg.id == "inf")
                # `trio.sleep(float("inf"))`
                or (
                    isinstance(arg, ast.Call)
                    and isinstance(arg.func, ast.Name)
                    and arg.func.id == "float"
                    and len(arg.args)
                    and isinstance(arg.args[0], ast.Constant)
                    and arg.args[0].value == "inf"
                )
                # `trio.sleep(1e999)` (constant value inf)
                # `trio.sleep(86401)`
                # `trio.sleep(86400.1)`
                or (
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, (int, float))
                    and arg.value > 86400
                )
            ):
                self.error(node, m[2])


DEPRECATED_ERRORS = ("MultiError", "NonBaseMultiError")


# anyio does not have MultiError, so this check is trio-only
@error_class
class Visitor117(Flake8TrioVisitor):
    error_codes = {
        "TRIO117": ("Reference to {}, prefer [exceptiongroup.]BaseExceptionGroup."),
    }

    # This should never actually happen given TRIO106
    def visit_Name(self, node: ast.Name):
        if node.id in DEPRECATED_ERRORS and "trio" in self.library:
            self.error(node, node.id)

    def visit_Attribute(self, node: ast.Attribute):
        if (n := ast.unparse(node)) in ("trio.MultiError", "trio.NonBaseMultiError"):
            self.error(node, n)


@error_class
@disabled_by_default
class Visitor900(Flake8TrioVisitor):
    error_codes = {
        "TRIO900": ("Async generator without `@asynccontextmanager` not allowed.")
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.unsafe_function: ast.AsyncFunctionDef | None = None

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef | ast.FunctionDef | ast.Lambda
    ):
        self.save_state(node, "unsafe_function")
        if isinstance(node, ast.AsyncFunctionDef) and not any(
            _get_identifier(d) in ("asynccontextmanager", "fixture")
            for d in node.decorator_list
        ):
            self.unsafe_function = node
        else:
            self.unsafe_function = None

    def visit_Yield(self, node: ast.Yield):
        if self.unsafe_function is not None:
            self.error(self.unsafe_function)
            self.unsafe_function = None

    visit_FunctionDef = visit_AsyncFunctionDef
    visit_Lambda = visit_AsyncFunctionDef
