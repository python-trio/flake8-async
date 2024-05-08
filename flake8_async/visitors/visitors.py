"""Various visitors/error classes that are too small to warrant getting their own file."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, cast

from .flake8asyncvisitor import Flake8AsyncVisitor
from .helpers import disabled_by_default, error_class, get_matching_call, has_decorator

if TYPE_CHECKING:
    from collections.abc import Mapping

LIBRARIES = ("trio", "anyio", "asyncio")


@error_class
class Visitor106(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC106": "{0} must be imported with `import {0}` for the linter to work.",
    }

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module in LIBRARIES:
            self.error(node, node.module)

    def visit_Import(self, node: ast.Import):
        for name in node.names:
            if name.name in LIBRARIES and name.asname is not None:
                self.error(node, name.name)


@error_class
class Visitor109(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC109": (
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
class Visitor110(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC110": (
            "`while <condition>: await {0}.sleep()` should be replaced by "
            "a `{0}.Event`."
        ),
    }

    def visit_While(self, node: ast.While):
        if (
            len(node.body) == 1
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Await)
            and (
                get_matching_call(node.body[0].value.value, "sleep", "sleep_until")
                or (
                    # get_matching_call doesn't (currently) support checking for trio.x.y
                    isinstance(call := node.body[0].value.value, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "checkpoint"
                    and isinstance(call.func.value, ast.Attribute)
                    and call.func.value.attr == "lowlevel"
                    and isinstance(call.func.value.value, ast.Name)
                    and call.func.value.value.id in ("trio", "anyio")
                )
            )
        ):
            self.error(node, self.library_str)


@error_class
class Visitor112(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC112": (
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

            # check for trio.open_nursery and anyio.create_task_group
            nursery = get_matching_call(
                item.context_expr, "open_nursery", base="trio"
            ) or get_matching_call(item.context_expr, "create_task_group", base="anyio")
            start_methods: tuple[str, ...] = ("start", "start_soon")
            if nursery is None:
                # check for asyncio.TaskGroup
                nursery = get_matching_call(
                    item.context_expr, "TaskGroup", base="asyncio"
                )
                if nursery is None:
                    continue
                start_methods = ("create_task",)

            body_call = node.body[0].value
            if isinstance(body_call, ast.Await):
                body_call = body_call.value

            # `isinstance(..., ast.Call)` is done in get_matching_call
            body_call = cast("ast.Call", body_call)

            if (
                get_matching_call(body_call, *start_methods, base=var_name)
                # check for presence of <X> as parameter
                and not any(
                    (isinstance(n, ast.Name) and n.id == var_name)
                    for n in self.walk(*body_call.args, *body_call.keywords)
                )
            ):
                self.error(item.context_expr, var_name)

    visit_AsyncWith = visit_With


# used in 113 and 114
STARTABLE_CALLS = (
    "run_process",
    "serve_ssl_over_tcp",
    "serve_tcp",
    "serve_listeners",
    "serve",
)


@error_class
class Visitor113(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC113": (
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

        self.aenter = node.name == "__aenter__" or has_decorator(
            node, "asynccontextmanager"
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
                    "asyncio.TaskGroup",
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
class Visitor114(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC114": (
            "Startable function {} not in --startable-in-context-manager parameter "
            "list, please add it so ASYNC113 can catch errors using it."
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


# Suggests replacing all `[trio|anyio].sleep(0)` with the more suggestive
# `trio.lowlevel.checkpoint()`
@error_class
class Visitor115(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC115": "Use `{0}.lowlevel.checkpoint()` instead of `{0}.sleep(0)`.",
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
class Visitor116(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC116": (
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


@error_class
class Visitor119(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC119": "Yield in contextmanager in async generator might not trigger"
        " cleanup. Use `@asynccontextmanager` or refactor."
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.unsafe_function: bool = False
        self.contextmanager: bool = False

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef | ast.FunctionDef | ast.Lambda
    ):
        self.save_state(node, "unsafe_function", "contextmanager")
        self.contextmanager = False
        if isinstance(node, ast.AsyncFunctionDef) and not has_decorator(
            node, "asynccontextmanager"
        ):
            self.unsafe_function = True
        else:
            self.unsafe_function = False

    def visit_With(self, node: ast.With | ast.AsyncWith):
        self.save_state(node, "contextmanager")
        self.contextmanager = True

    def visit_Yield(self, node: ast.Yield):
        if self.unsafe_function and self.contextmanager:
            self.error(node)

    visit_AsyncWith = visit_With
    visit_FunctionDef = visit_AsyncFunctionDef
    # it's not possible to yield or open context managers in lambda's, so this
    # one isn't strictly needed afaik.
    visit_Lambda = visit_AsyncFunctionDef


@error_class
@disabled_by_default
class Visitor900(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC900": "Async generator without `@asynccontextmanager` not allowed."
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.unsafe_function: ast.AsyncFunctionDef | None = None

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef | ast.FunctionDef | ast.Lambda
    ):
        self.save_state(node, "unsafe_function")
        if isinstance(node, ast.AsyncFunctionDef) and not has_decorator(
            node, "asynccontextmanager", "fixture"
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
