"""Various visitors/error classes that are too small to warrant getting their own file."""

from __future__ import annotations

import ast
from collections import defaultdict
from typing import TYPE_CHECKING, Any, cast

from .flake8asyncvisitor import Flake8AsyncVisitor, Flake8AsyncVisitor_cst
from .helpers import (
    disabled_by_default,
    error_class,
    error_class_cst,
    get_matching_call,
    has_decorator,
    identifier_to_string,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    import libcst as cst

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
            "Redundant {1} {0}, consider replacing with directly awaiting "
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

            start_methods: tuple[str, ...] = ("start", "start_soon")
            # check for trio.open_nursery and anyio.create_task_group
            if get_matching_call(item.context_expr, "open_nursery", base="trio"):
                nursery_type = "nursery"

            elif get_matching_call(
                item.context_expr, "create_task_group", base="anyio"
            ):
                nursery_type = "task group"
            # check for asyncio.TaskGroup
            elif get_matching_call(item.context_expr, "TaskGroup", base="asyncio"):
                nursery_type = "task group"
                start_methods = ("create_task",)
            else:
                # incorrectly marked as not covered on py39
                continue  # pragma: no cover  # https://github.com/nedbat/coveragepy/issues/198

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
                self.error(item.context_expr, var_name, nursery_type)

    visit_AsyncWith = visit_With


# used in 113 and 114
STARTABLE_CALLS = ("serve",)
TRIO_STARTABLE_CALLS = (
    "run_process",
    "serve_ssl_over_tcp",
    "serve_tcp",
    "serve_listeners",
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
        # this is not entirely correct, it's trio.open_nursery.__aenter__()->trio.Nursery
        # but VisitorTypeTracker currently does not work like that.
        self.typed_calls["trio.open_nursery"] = "trio.Nursery"
        self.typed_calls["anyio.create_task_group"] = "anyio.TaskGroup"
        self.typed_calls["asyncio.TaskGroup"] = "asyncio.TaskGroup"

        self.async_function = False
        self.asynccontextmanager = False
        self.aenter = False

        self.potential_errors: dict[str, list[ast.Call]] = defaultdict(list)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.save_state(node, "aenter", "asynccontextmanager", "potential_errors")

        self.aenter = node.name == "__aenter__"
        self.asynccontextmanager = has_decorator(node, "asynccontextmanager")

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.save_state(node, "aenter", "asynccontextmanager", "potential_errors")
        # sync function should never be named __aenter__ or have @asynccontextmanager
        self.aenter = self.asynccontextmanager = False

    def visit_Yield(self, node: ast.Yield):
        for nodes in self.potential_errors.values():
            for n in nodes:
                self.error(n)
        self.potential_errors.clear()
        self.aenter = self.asynccontextmanager = False

    def visit_Call(self, node: ast.Call) -> None:
        def is_startable(n: ast.expr, *startable_list: str) -> bool:
            if isinstance(n, ast.Name):
                return n.id in startable_list
            if isinstance(n, ast.Attribute):
                return n.attr in startable_list and not (
                    n.attr in TRIO_STARTABLE_CALLS
                    and isinstance(n.value, ast.Name)
                    and n.value.id != "trio"
                )
            if isinstance(n, ast.Call):
                return any(is_startable(nn, *startable_list) for nn in n.args)
            return False

        def is_nursery_call(node: ast.expr) -> str | None:
            if not isinstance(node, ast.Attribute) or node.attr not in (
                "start_soon",
                "create_task",
            ):
                return None
            var = ast.unparse(node.value)
            if (
                ("trio" in self.library and var.endswith("nursery"))
                or ("anyio" in self.library and var.endswith("task_group"))
                or (
                    self.variables.get(var, "")
                    in (
                        "trio.Nursery",
                        "anyio.TaskGroup",
                        "asyncio.TaskGroup",
                    )
                )
            ):
                return var
            return None

        if (
            (var := is_nursery_call(node.func)) is not None
            and len(node.args) > 0
            and is_startable(
                node.args[0],
                *STARTABLE_CALLS,
                *TRIO_STARTABLE_CALLS,
                *self.options.startable_in_context_manager,
            )
        ):
            if self.aenter:
                self.error(node)
            elif self.asynccontextmanager:
                self.potential_errors[var].append(node)

    def visit_AsyncWith(self, node: ast.AsyncWith | ast.With):
        # Entirely skip any nurseries that doesn't have any yields in them.
        # This fixes an otherwise very thorny false alarm.
        # In the worst case this does mean we iterate over the body twice, but might
        # actually be a performance gain on average due to setting `novisit`
        if not any(isinstance(n, ast.Yield) for b in node.body for n in ast.walk(b)):
            self.novisit = True
            return

    # open_nursery/create_task_group only works with AsyncWith, but in case somebody
    # is doing something very weird we'll be conservative and possibly avoid
    # some potential false alarms
    visit_With = visit_AsyncWith


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
            for opt in (
                *self.options.startable_in_context_manager,
                *STARTABLE_CALLS,
                *TRIO_STARTABLE_CALLS,
            )
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
            self.error(node, m.base)


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
                self.error(node, m.base)


@error_class
class Visitor119(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC119": (
            "Yield in contextmanager in async generator might not trigger"
            " cleanup. Use `@asynccontextmanager` or refactor."
        )
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
            node,
            "asynccontextmanager",
            "fixture",
            *self.options.transform_async_generator_decorators,
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
class Visitor121(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC121": (
            "{0} in a {1} block behaves counterintuitively in several"
            " situations. Refactor to have the {0} outside."
        )
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.unsafe_stack: list[str] = []

    def visit_AsyncWith(self, node: ast.AsyncWith):
        self.save_state(node, "unsafe_stack", copy=True)

        for item in node.items:
            if get_matching_call(item.context_expr, "open_nursery", base="trio"):
                self.unsafe_stack.append("nursery")
            elif get_matching_call(
                item.context_expr, "create_task_group", base="anyio"
            ) or get_matching_call(item.context_expr, "TaskGroup", base="asyncio"):
                self.unsafe_stack.append("task group")

    def visit_While(self, node: ast.While | ast.For | ast.AsyncFor):
        self.save_state(node, "unsafe_stack", copy=True)
        self.unsafe_stack.append("loop")

    visit_For = visit_While
    visit_AsyncFor = visit_While

    def check_loop_flow(self, node: ast.Continue | ast.Break, statement: str) -> None:
        # self.unsafe_stack should never be empty, but no reason not to avoid a crash
        # for invalid code.
        if self.unsafe_stack and self.unsafe_stack[-1] != "loop":
            self.error(node, statement, self.unsafe_stack[-1])

    def visit_Continue(self, node: ast.Continue) -> None:
        self.check_loop_flow(node, "continue")

    def visit_Break(self, node: ast.Break) -> None:
        self.check_loop_flow(node, "break")

    def visit_Return(self, node: ast.Return) -> None:
        for unsafe_cm in "nursery", "task group":
            if unsafe_cm in self.unsafe_stack:
                self.error(node, "return", unsafe_cm)

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        self.save_state(node, "unsafe_stack", copy=True)
        self.unsafe_stack = []

    visit_AsyncFunctionDef = visit_FunctionDef


@error_class
class Visitor122(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC122": (
            "Separating initialization from entry of {} changed behavior in Trio"
            " 0.27, and was unintuitive before then. If you only support"
            " trio>=0.27 you should disable this check."
        )
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.in_withitem = False

    def visit_withitem(self, node: ast.withitem):
        self.save_state(node, "in_withitem")
        self.in_withitem = True

    def visit_Call(self, node: ast.Call):
        if not self.in_withitem and (
            match := get_matching_call(
                node, "fail_after", "move_on_after", base=("trio", "anyio")
            )
        ):
            self.error(node, str(match))


@error_class
class Visitor125(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC125": (
            "Using {} with a constant value is nonsensical, as the value is relative "
            "to the runner clock. Use ``fail_after(...)``, ``move_on_after(...)``, "
            "``CancelScope(relative_deadline=...)`` or calculate it relative to "
            "``{}.current_time()``."
        )
    }

    def visit_Call(self, node: ast.Call):
        def is_constant(value: ast.expr) -> bool:
            if isinstance(value, ast.Constant):
                return True
            if isinstance(value, ast.BinOp):
                return is_constant(value.left) and is_constant(value.right)
            return False

        match = get_matching_call(
            node, "fail_at", "move_on_at", "CancelScope", base=("trio", "anyio")
        )
        if match is None:
            return

        if match.name in ("fail_at", "move_on_at") and len(node.args) == 1:
            value = node.args[0]
        else:
            for kw in node.keywords:
                if kw.arg == "deadline":
                    value = kw.value
                    break
            else:
                return
        if is_constant(value):
            self.error(
                value,
                str(match),
                match.base,
            )


@error_class_cst
class Visitor300(Flake8AsyncVisitor_cst):
    error_codes: Mapping[str, str] = {
        "ASYNC300": "asyncio.create_task() called without saving the result"
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.safe_to_create_task: bool = False

    def visit_Assign(self, node: cst.CSTNode):
        self.save_state(node, "safe_to_create_task")
        self.safe_to_create_task = True

    def visit_CompIf(self, node: cst.CSTNode):
        self.save_state(node, "safe_to_create_task")
        self.safe_to_create_task = False

    def visit_Call(self, node: cst.Call):
        if (
            identifier_to_string(node.func) == "asyncio.create_task"
            and not self.safe_to_create_task
        ):
            self.error(node)
        self.visit_Assign(node)

    visit_NamedExpr = visit_Assign
    visit_AugAssign = visit_Assign
    visit_IfExp_test = visit_CompIf

    # because this is a Flake8AsyncVisitor_cst, we need to manually call restore_state
    def leave_Assign(
        self, original_node: cst.CSTNode, updated_node: cst.CSTNode
    ) -> Any:
        self.restore_state(original_node)
        return updated_node

    leave_Call = leave_Assign
    leave_CompIf = leave_Assign
    leave_NamedExpr = leave_Assign
    leave_AugAssign = leave_Assign

    def leave_IfExp_test(self, node: cst.IfExp):
        self.restore_state(node)


@error_class
@disabled_by_default
class Visitor900(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = {
        "ASYNC900": (
            "Async generator not allowed, unless transformed "
            "by a known decorator (one of: {})."
        )
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.unsafe_function: ast.AsyncFunctionDef | None = None
        self.transform_decorators = [
            "contextlib.asynccontextmanager",
            "pytest.fixture",
            *self.options.transform_async_generator_decorators,
        ]
        # only recommend if using trio
        if "trio" in self.library:
            self.transform_decorators.insert(0, "trio.as_safe_channel")

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef | ast.FunctionDef | ast.Lambda
    ):
        self.save_state(node, "unsafe_function")
        if isinstance(node, ast.AsyncFunctionDef) and not has_decorator(
            node, *(d.split(".")[-1] for d in self.transform_decorators)
        ):
            self.unsafe_function = node
        else:
            self.unsafe_function = None

    def visit_Yield(self, node: ast.Yield):
        if self.unsafe_function is not None:
            self.error(self.unsafe_function, ", ".join(self.transform_decorators))
            self.unsafe_function = None

    visit_FunctionDef = visit_AsyncFunctionDef
    visit_Lambda = visit_AsyncFunctionDef
