"""A highly opinionated flake8 plugin for Trio-related problems.

This can include anything from outright bugs, to pointless/dead code,
to likely performance issues, to minor points of idiom that might signal
a misunderstanding.

It may well be too noisy for anyone with different opinions, that's OK.

Pairs well with flake8-async and flake8-bugbear.
"""

import ast
import tokenize
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

# CalVer: YY.month.patch, e.g. first release of July 2022 == "22.7.1"
__version__ = "22.8.7"


Error_codes = {
    "TRIO100": "{} context contains no checkpoints, add `await trio.sleep(0)`",
    "TRIO101": (
        "yield inside a nursery or cancel scope is only safe when implementing "
        "a context manager - otherwise, it breaks exception handling"
    ),
    "TRIO102": (
        "await inside {0.name} on line {0.lineno} must have shielded cancel "
        "scope with a timeout"
    ),
    "TRIO103": "{} block with a code path that doesn't re-raise the error",
    "TRIO104": "Cancelled (and therefore BaseException) must be re-raised",
    "TRIO105": "trio async function {} must be immediately awaited",
    "TRIO106": "trio must be imported with `import trio` for the linter to work",
    "TRIO107": (
        "{0} from async function with no guaranteed checkpoint or exception "
        "since function definition on line {1.lineno}"
    ),
    "TRIO108": (
        "{0} from async iterable with no guaranteed checkpoint since {1.name} "
        "on line {1.lineno}"
    ),
    "TRIO109": (
        "Async function definition with a `timeout` parameter - use "
        "`trio.[fail/move_on]_[after/at]` instead"
    ),
    "TRIO110": "`while <condition>: await trio.sleep()` should be replaced by a `trio.Event`.",
    "TRIO111": (
        "variable {2} is usable within the context manager on line {0}, but that "
        "will close before nursery opened on line {1} - this is usually a bug.  "
        "Nurseries should generally be the inner-most context manager."
    ),
    "TRIO112": "Redundant nursery {}, consider replacing with directly awaiting the function call",
}


class Statement(NamedTuple):
    name: str
    lineno: int
    col_offset: int = -1

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, Statement)
            and self[:2] == other[:2]
            and (
                self.col_offset == other.col_offset
                or -1 in (self.col_offset, other.col_offset)
            )
        )


HasLineCol = Union[ast.expr, ast.stmt, ast.arg, ast.excepthandler, Statement]


def get_matching_call(
    node: ast.AST, *names: str, base: str = "trio"
) -> Optional[Tuple[ast.Call, str]]:
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == base
        and node.func.attr in names
    ):
        return node, node.func.attr
    return None


class Error:
    def __init__(self, error_code: str, lineno: int, col: int, *args: object):
        self.line = lineno
        self.col = col
        self.code = error_code
        self.args = args

    # for yielding to flake8
    def __iter__(self):
        yield self.line
        yield self.col
        yield f"{self.code}: " + Error_codes[self.code].format(*self.args)
        yield type(Plugin)

    def cmp(self):
        return self.line, self.col, self.code, self.args

    # for sorting in tests
    def __lt__(self, other: Any) -> bool:
        assert isinstance(other, Error)
        return self.cmp() < other.cmp()

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Error) and self.cmp() == other.cmp()


checkpoint_node_types = (ast.Await, ast.AsyncFor, ast.AsyncWith)
cancel_scope_names = (
    "fail_after",
    "fail_at",
    "move_on_after",
    "move_on_at",
    "CancelScope",
)
context_manager_names = (
    "contextmanager",
    "asynccontextmanager",
)


class Flake8TrioVisitor(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self._problems: List[Error] = []
        self.suppress_errors = False

    @classmethod
    def run(cls, tree: ast.AST) -> Iterable[Error]:
        visitor = cls()
        visitor.visit(tree)
        yield from visitor._problems

    def visit_nodes(
        self, *nodes: Union[ast.AST, Iterable[ast.AST]], generic: bool = False
    ):
        if generic:
            visit = self.generic_visit
        else:
            visit = self.visit
        for arg in nodes:
            if isinstance(arg, ast.AST):
                visit(arg)
            else:
                for node in arg:
                    visit(node)

    def error(self, error: str, node: HasLineCol, *args: object):
        if not self.suppress_errors:
            self._problems.append(Error(error, node.lineno, node.col_offset, *args))

    def get_state(self, *attrs: str, copy: bool = False) -> Dict[str, Any]:
        if not attrs:
            attrs = tuple(self.__dict__.keys())
        res: Dict[str, Any] = {}
        for attr in attrs:
            if attr == "_problems":
                continue
            value = getattr(self, attr)
            if copy and hasattr(value, "copy"):
                value = value.copy()
            res[attr] = value
        return res

    def set_state(self, attrs: Dict[str, Any], copy: bool = False):
        for attr, value in attrs.items():
            if copy and hasattr(value, "copy"):
                value = value.copy()
            setattr(self, attr, value)

    def walk(self, *body: ast.AST) -> Iterable[ast.AST]:
        for b in body:
            yield from ast.walk(b)


def has_decorator(decorator_list: List[ast.expr], *names: str):
    for dec in decorator_list:
        if (isinstance(dec, ast.Name) and dec.id in names) or (
            isinstance(dec, ast.Attribute) and dec.attr in names
        ):
            return True
    return False


# handles 100, 101, 106, 109, 110, 111, 112
class VisitorMiscChecks(Flake8TrioVisitor):
    class NurseryCall(NamedTuple):
        stack_index: int
        name: str

    class TrioContextManager(NamedTuple):
        lineno: int
        name: str
        is_nursery: bool

    def __init__(self):
        super().__init__()

        # 101
        self._yield_is_error = False
        self._safe_decorator = False

        # 111
        self._context_managers: List[VisitorMiscChecks.TrioContextManager] = []
        self._nursery_call: Optional[VisitorMiscChecks.NurseryCall] = None

        self.defaults = self.get_state(copy=True)

    # ---- 100, 101, 111, 112 ----
    def visit_With(self, node: Union[ast.With, ast.AsyncWith]):
        self.check_for_trio100(node)
        self.check_for_trio112(node)

        outer = self.get_state("_yield_is_error", "_context_managers", copy=True)

        for item in node.items:
            # 101
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

            # 111
            # if a withitem is saved in a variable,
            # push its line, variable, and whether it's a trio nursery
            # to the _context_managers stack,
            if isinstance(item.optional_vars, ast.Name):
                self._context_managers.append(
                    self.TrioContextManager(
                        item.context_expr.lineno,
                        item.optional_vars.id,
                        get_matching_call(item.context_expr, "open_nursery")
                        is not None,
                    )
                )

        self.generic_visit(node)
        self.set_state(outer)

    visit_AsyncWith = visit_With

    # ---- 100 ----
    def check_for_trio100(self, node: Union[ast.With, ast.AsyncWith]):
        # Context manager with no `await trio.X` call within
        for item in (i.context_expr for i in node.items):
            call = get_matching_call(item, *cancel_scope_names)
            if call and not any(
                isinstance(x, checkpoint_node_types) and x != node
                for x in ast.walk(node)
            ):
                self.error("TRIO100", item, f"trio.{call[1]}")

    # ---- 101 ----
    def visit_FunctionDef(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]):
        outer = self.get_state()
        self.set_state(self.defaults, copy=True)

        # check for @<context_manager_name> and @<library>.<context_manager_name>
        if has_decorator(node.decorator_list, *context_manager_names):
            self._safe_decorator = True

        self.generic_visit(node)

        self.set_state(outer)

    # ---- 101, 109 ----
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.check_for_trio109(node)
        self.visit_FunctionDef(node)

    def visit_Lambda(self, node: ast.Lambda):
        outer = self.get_state()
        self.set_state(self.defaults, copy=True)
        self.generic_visit(node)
        self.set_state(outer)

    # ---- 101 ----
    def visit_Yield(self, node: ast.Yield):
        if self._yield_is_error:
            self.error("TRIO101", node)

        self.generic_visit(node)

    # ---- 109 ----
    def check_for_trio109(self, node: ast.AsyncFunctionDef):
        # pending configuration or a more sophisticated check, ignore
        # all functions with a decorator
        if node.decorator_list:
            return

        args = node.args
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
            if arg.arg == "timeout":
                self.error("TRIO109", arg)

    # ---- 106 ----
    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "trio":
            self.error("TRIO106", node)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for name in node.names:
            if name.name == "trio" and name.asname is not None:
                self.error("TRIO106", node)
        self.generic_visit(node)

    # ---- 110 ----
    def visit_While(self, node: ast.While):
        self.check_for_trio110(node)
        self.generic_visit(node)

    def check_for_trio110(self, node: ast.While):
        if (
            len(node.body) == 1
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Await)
            and get_matching_call(node.body[0].value.value, "sleep", "sleep_until")
        ):
            self.error("TRIO110", node)

    # ---- 111 ----
    # if it's a <X>.start[_soon] call
    # and <X> is a nursery listed in self._context_managers:
    # Save <X>'s index in self._context_managers to guard against cm's higher in the
    # stack being passed as parameters to it. (and save <X> for the error message)
    def visit_Call(self, node: ast.Call):
        outer = self.get_state("_nursery_call")

        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.attr in ("start", "start_soon")
        ):
            self._nursery_call = None
            for i, cm in enumerate(self._context_managers):
                if node.func.value.id == cm.name:
                    # don't break upon finding a nursery in case there's multiple cm's
                    # on the stack with the same name
                    if cm.is_nursery:
                        self._nursery_call = self.NurseryCall(i, node.func.attr)
                    else:
                        self._nursery_call = None

        self.generic_visit(node)
        self.set_state(outer)

    # If we're inside a <X>.start[_soon] call (where <X> is a nursery),
    # and we're accessing a variable cm that's on the self._context_managers stack,
    # with a higher index than <X>:
    #   Raise error since the scope of cm may close before the function passed to the
    # nursery finishes.
    def visit_Name(self, node: ast.Name):
        self.generic_visit(node)
        if self._nursery_call is None:
            return

        for i, cm in enumerate(self._context_managers):
            if cm.name == node.id and i > self._nursery_call.stack_index:
                self.error(
                    "TRIO111",
                    node,
                    cm.lineno,
                    self._context_managers[self._nursery_call.stack_index].lineno,
                    node.id,
                    self._nursery_call.name,
                )

    # if with has a withitem `trio.open_nursery() as <X>`,
    # and the body is only a single expression <X>.start[_soon](),
    # and does not pass <X> as a parameter to the expression
    def check_for_trio112(self, node: Union[ast.With, ast.AsyncWith]):
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

            # isinstance(..., ast.Call) is done in get_matching_call
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
                self.error("TRIO112", item.context_expr, var_name)


# used in 102, 103 and 104
def critical_except(node: ast.ExceptHandler) -> Optional[Statement]:
    def has_exception(node: Optional[ast.expr]) -> str:
        if isinstance(node, ast.Name) and node.id == "BaseException":
            return "BaseException"
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "trio"
            and node.attr == "Cancelled"
        ):
            return "trio.Cancelled"
        return ""

    # bare except
    if node.type is None:
        return Statement("bare except", node.lineno, node.col_offset)
    # several exceptions
    if isinstance(node.type, ast.Tuple):
        for element in node.type.elts:
            name = has_exception(element)
            if name:
                return Statement(name, element.lineno, element.col_offset)
    # single exception, either a Name or an Attribute
    name = has_exception(node.type)
    if name:
        return Statement(name, node.type.lineno, node.type.col_offset)
    return None


class Visitor102(Flake8TrioVisitor):
    class TrioScope:
        def __init__(self, node: ast.Call, funcname: str):
            self.node = node
            self.funcname = funcname
            self.variable_name: Optional[str] = None
            self.shielded: bool = False
            self.has_timeout: bool = True

            # scope.shielded is assigned to in visit_Assign

            if self.funcname == "CancelScope":
                self.has_timeout = False
                for kw in node.keywords:
                    # Only accepts constant values
                    if kw.arg == "shield" and isinstance(kw.value, ast.Constant):
                        self.shielded = kw.value.value
                    # sets to True even if timeout is explicitly set to inf
                    if kw.arg == "deadline":
                        self.has_timeout = True

    def __init__(self):
        super().__init__()
        self._critical_scope: Optional[Statement] = None
        self._trio_context_managers: List[Visitor102.TrioScope] = []
        self._safe_decorator = False

    # if we're inside a finally, and not inside a context_manager, and we're not
    # inside a scope that doesn't have both a timeout and shield
    def visit_Await(
        self,
        node: Union[ast.Await, ast.AsyncFor, ast.AsyncWith],
        visit_children: bool = True,
    ):
        if (
            self._critical_scope is not None
            and not self._safe_decorator
            and not any(
                cm.has_timeout and cm.shielded for cm in self._trio_context_managers
            )
        ):
            self.error("TRIO102", node, self._critical_scope)
        if visit_children:
            self.generic_visit(node)

    visit_AsyncFor = visit_Await

    def visit_With(self, node: Union[ast.With, ast.AsyncWith]):
        has_context_manager = False

        # Check for a `with trio.<scope_creater>`
        for item in node.items:
            call = get_matching_call(
                item.context_expr, "open_nursery", *cancel_scope_names
            )
            if call is None:
                continue

            trio_scope = self.TrioScope(*call)
            # check if it's saved in a variable
            if isinstance(item.optional_vars, ast.Name):
                trio_scope.variable_name = item.optional_vars.id

            self._trio_context_managers.append(trio_scope)
            has_context_manager = True
            break

        self.generic_visit(node)

        if has_context_manager:
            self._trio_context_managers.pop()

    def visit_AsyncWith(self, node: ast.AsyncWith):
        self.visit_Await(node, visit_children=False)
        self.visit_With(node)

    def visit_FunctionDef(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]):
        outer = self.get_state("_safe_decorator")

        # check for @<context_manager_name> and @<library>.<context_manager_name>
        if has_decorator(node.decorator_list, *context_manager_names):
            self._safe_decorator = True

        self.generic_visit(node)

        self.set_state(outer)

    visit_AsyncFunctionDef = visit_FunctionDef

    def critical_visit(
        self,
        node: Union[ast.ExceptHandler, Iterable[ast.AST]],
        block: Statement,
        generic: bool = False,
    ):
        outer = self.get_state("_critical_scope", "_trio_context_managers")

        self._trio_context_managers = []
        self._critical_scope = block

        self.visit_nodes(node, generic=generic)
        self.set_state(outer)

    def visit_Try(self, node: ast.Try):
        # There's no visit_Finally, so we need to manually visit the Try fields.
        self.visit_nodes(node.body, node.handlers, node.orelse)
        self.critical_visit(
            node.finalbody, Statement("try/finally", node.lineno, node.col_offset)
        )

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        res = critical_except(node)
        if res is None:
            self.generic_visit(node)
        else:
            self.critical_visit(node, res, generic=True)

    def visit_Assign(self, node: ast.Assign):
        # checks for <scopename>.shield = [True/False]
        if self._trio_context_managers and len(node.targets) == 1:
            last_scope = self._trio_context_managers[-1]
            target = node.targets[0]
            if (
                last_scope.variable_name is not None
                and isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == last_scope.variable_name
                and target.attr == "shield"
                and isinstance(node.value, ast.Constant)
            ):
                last_scope.shielded = node.value.value
        self.generic_visit(node)


# Never have an except Cancelled or except BaseException block with a code path that
# doesn't re-raise the error
class Visitor103_104(Flake8TrioVisitor):
    def __init__(self):
        super().__init__()
        self.except_name: Optional[str] = ""
        self.unraised: bool = False
        self.unraised_break: bool = False
        self.unraised_continue: bool = False
        self.loop_depth = 0

    # If an `except` is bare, catches `BaseException`, or `trio.Cancelled`
    # set self.unraised, and if it's still set after visiting child nodes
    # then there might be a code path that doesn't re-raise.
    def visit_ExceptHandler(self, node: ast.ExceptHandler):

        outer = self.get_state()
        marker = critical_except(node)

        # we need to *not* unset self.unraised if this is non-critical, to still
        # warn about `return`s

        if marker is not None:
            # save name from `as <except_name>`
            self.except_name = node.name

            self.loop_depth = 0
            self.unraised = True

        # visit child nodes. Will unset self.unraised if all code paths `raise`
        self.generic_visit(node)

        if self.unraised and marker is not None:
            self.error("TRIO103", marker, marker.name)

        self.set_state(outer)

    def visit_Raise(self, node: ast.Raise):
        # if there's an unraised critical exception, the raise isn't bare,
        # and the name doesn't match, signal a problem.
        if (
            self.unraised
            and node.exc is not None
            and not (isinstance(node.exc, ast.Name) and node.exc.id == self.except_name)
        ):
            self.error("TRIO104", node)

        # treat it as safe regardless, to avoid unnecessary error messages.
        self.unraised = False

        self.generic_visit(node)

    def visit_Return(self, node: Union[ast.Return, ast.Yield]):
        if self.unraised:
            # Error: must re-raise
            self.error("TRIO104", node)
        self.generic_visit(node)

    visit_Yield = visit_Return

    # Treat Try's as fully covering only if `finally` always raises.
    def visit_Try(self, node: ast.Try):
        if not self.unraised:
            self.generic_visit(node)
            return

        # in theory it's okay if the try and all excepts re-raise,
        # and there is a bare except
        # but is a pain to parse and would require a special case for bare raises in
        # nested excepts.
        for n in (*node.body, *node.handlers, *node.orelse):
            self.visit(n)
            # re-set unraised to warn about returns in each block
            self.unraised = True

        # but it's fine if we raise in finally
        self.visit_nodes(node.finalbody)

    # Treat if's as fully covering if both `if` and `else` raise.
    # `elif` is parsed by the ast as a new if statement inside the else.
    def visit_If(self, node: ast.If):
        if not self.unraised:
            self.generic_visit(node)
            return

        body_raised = False
        self.visit_nodes(node.body)

        # does body always raise correctly
        body_raised = not self.unraised

        self.unraised = True
        self.visit_nodes(node.orelse)

        # if body didn't raise, or it's unraised after else, set unraise
        self.unraised = not body_raised or self.unraised

    # A loop is guaranteed to raise if:
    # condition always raises, or
    #   else always raises, and
    #   always raise before break
    # or body always raises (before break) and is guaranteed to run at least once
    def visit_For(self, node: Union[ast.For, ast.While]):
        if not self.unraised:
            self.generic_visit(node)
            return

        infinite_loop = False
        if isinstance(node, ast.While):
            try:
                infinite_loop = body_guaranteed_once = bool(ast.literal_eval(node.test))
            except Exception:
                body_guaranteed_once = False
            self.visit_nodes(node.test)
        else:
            body_guaranteed_once = iter_guaranteed_once(node.iter)
            self.visit_nodes(node.target)
            self.visit_nodes(node.iter)

        prebody = self.get_state("unraised_break", "unraised_continue")
        self.unraised_break = False
        self.unraised_continue = False

        self.loop_depth += 1
        self.visit_nodes(node.body)
        self.loop_depth -= 1

        # if body is not guaranteed to run, or can continue at unraised, reset
        if not (infinite_loop or (body_guaranteed_once and not self.unraised_continue)):
            self.unraised = True
        self.visit_nodes(node.orelse)

        # if we might break at an unraised point, set unraised
        self.unraised |= self.unraised_break
        self.set_state(prebody)

    visit_While = visit_For

    def visit_Break(self, node: ast.Break):
        if self.unraised and self.loop_depth == 0:
            self.error("TRIO104", node)
        self.unraised_break |= self.unraised
        self.generic_visit(node)

    def visit_Continue(self, node: ast.Continue):
        if self.unraised and self.loop_depth == 0:
            self.error("TRIO104", node)
        self.unraised_continue |= self.unraised
        self.generic_visit(node)


def iter_guaranteed_once(iterable: ast.expr) -> bool:
    # static container with an "elts" attribute
    if hasattr(iterable, "elts"):
        elts: Iterable[ast.expr] = iterable.elts  # type: ignore
        for elt in elts:
            assert isinstance(elt, ast.expr)
            # recurse starred expression
            if isinstance(elt, ast.Starred):
                if iter_guaranteed_once(elt.value):
                    return True
            else:
                return True
        return False
    if isinstance(iterable, ast.Constant):
        try:
            return len(iterable.value) > 0
        except Exception:
            return False
    if isinstance(iterable, ast.Dict):
        for key, val in zip(iterable.keys, iterable.values):
            # {**{...}, **{<...>}} is parsed as {None: {...}, None: {<...>}}
            if key is None and isinstance(val, ast.Dict):
                if iter_guaranteed_once(val):
                    return True
            else:
                return True
    # check for range() with literal parameters
    if (
        isinstance(iterable, ast.Call)
        and isinstance(iterable.func, ast.Name)
        and iterable.func.id == "range"
    ):
        try:
            return len(range(*[ast.literal_eval(a) for a in iterable.args])) > 0
        except Exception:
            return False
    return False


trio_async_functions = (
    "aclose_forcefully",
    "open_file",
    "open_ssl_over_tcp_listeners",
    "open_ssl_over_tcp_stream",
    "open_tcp_listeners",
    "open_tcp_stream",
    "open_unix_socket",
    "run_process",
    "serve_listeners",
    "serve_ssl_over_tcp",
    "serve_tcp",
    "sleep",
    "sleep_forever",
    "sleep_until",
)


class Visitor105(Flake8TrioVisitor):
    def __init__(self):
        super().__init__()
        self.node_stack: List[ast.AST] = []

    def visit(self, node: ast.AST):
        self.node_stack.append(node)
        super().visit(node)
        self.node_stack.pop()

    def visit_Call(self, node: ast.Call):
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "trio"
            and node.func.attr in trio_async_functions
            and (
                len(self.node_stack) < 2
                or not isinstance(self.node_stack[-2], ast.Await)
            )
        ):
            self.error("TRIO105", node, node.func.attr)
        self.generic_visit(node)


def empty_body(body: List[ast.stmt]) -> bool:
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


class Visitor107_108(Flake8TrioVisitor):
    def __init__(self):
        super().__init__()
        self.has_yield = False
        self.safe_decorator = False
        self.async_function = False

        self.uncheckpointed_statements: Set[Statement] = set()
        self.uncheckpointed_before_continue: Set[Statement] = set()
        self.uncheckpointed_before_break: Set[Statement] = set()

        self.default = self.get_state()

    def visit(self, node: ast.AST):
        if not self.async_function and not isinstance(node, ast.AsyncFunctionDef):
            self.generic_visit(node)
        else:
            super().visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # don't lint functions whose bodies solely consist of pass or ellipsis
        if has_decorator(node.decorator_list, "overload") or empty_body(node.body):
            # no reason to generic_visit an empty body
            return

        outer = self.get_state()
        self.set_state(self.default, copy=True)

        # disable checks in asynccontextmanagers by saying the function isn't async
        self.async_function = not has_decorator(
            node.decorator_list, "asynccontextmanager"
        )

        if self.async_function:
            self.uncheckpointed_statements = {
                Statement("function definition", node.lineno, node.col_offset)
            }

        self.generic_visit(node)

        if self.async_function:
            self.check_function_exit(node)

        self.set_state(outer)

    # error if function exits or returns with uncheckpointed statements
    def check_function_exit(self, node: Union[ast.Return, ast.AsyncFunctionDef]):
        for statement in self.uncheckpointed_statements:
            self.error(
                "TRIO108" if self.has_yield else "TRIO107",
                node,
                "return" if isinstance(node, ast.Return) else "exit",
                statement,
            )

    def visit_Return(self, node: ast.Return):
        self.generic_visit(node)
        self.check_function_exit(node)

        # avoid duplicate error messages
        self.uncheckpointed_statements = set()

    # disregard checkpoints in nested function definitions
    def visit_FunctionDef(self, node: ast.FunctionDef):
        outer = self.get_state()
        self.set_state(self.default, copy=True)
        self.generic_visit(node)
        self.set_state(outer)

    # checkpoint functions
    def visit_Await(self, node: Union[ast.Await, ast.Raise]):
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
        self.has_yield = True
        self.generic_visit(node)
        for statement in self.uncheckpointed_statements:
            self.error("TRIO108", node, "yield", statement)

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
        all_except_checkpoint: Set[Statement] = set()
        for handler in node.handlers:
            # enter with worst case of try
            self.uncheckpointed_statements = body_uncheckpointed_statements.copy()

            self.visit_nodes(handler)

            all_except_checkpoint.update(self.uncheckpointed_statements)

        # check else
        # if else runs it's after all of try, so restore state to back then
        self.uncheckpointed_statements = try_checkpoint
        self.visit_nodes(node.orelse)

        # checkpoint if else checkpoints, and all excepts checkpoint
        if all_except_checkpoint:
            self.uncheckpointed_statements.update(all_except_checkpoint)

        # if there's no finally, don't restore state from try
        if node.finalbody:
            # can enter from try, else, or any except
            self.uncheckpointed_statements.update(body_uncheckpointed_statements)
            self.visit_nodes(node.finalbody)

    # valid checkpoint if both body and orelse checkpoint
    def visit_If(self, node: Union[ast.If, ast.IfExp]):
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

    # Check for yields w/o checkpoint inbetween due to entering loop body the first time,
    # after completing all of loop body, and after any continues.
    # yield in else have same requirement
    # state after the loop same as above, and in addition the state at any break
    def visit_loop(self, node: Union[ast.While, ast.For, ast.AsyncFor]):
        # visit condition
        infinite_loop = False
        if isinstance(node, ast.While):
            try:
                infinite_loop = body_guaranteed_once = bool(ast.literal_eval(node.test))
            except Exception:
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
        self.uncheckpointed_before_continue.update(self.uncheckpointed_statements)

    def visit_Break(self, node: ast.Break):
        self.uncheckpointed_before_break.update(self.uncheckpointed_statements)

    # first node in a condition is always evaluated, but may shortcut at any point
    # after that so we track worst-case checkpoint (i.e. after yield)
    def visit_BoolOp(self, node: ast.BoolOp):
        self.visit(node.op)

        # first value always evaluated
        self.visit(node.values[0])

        worst_case_shortcut = self.uncheckpointed_statements.copy()

        for value in node.values[1:]:
            self.visit(value)
            worst_case_shortcut.update(self.uncheckpointed_statements)

        self.uncheckpointed_statements = worst_case_shortcut


class Plugin:
    name = __name__
    version = __version__

    def __init__(self, tree: ast.AST):
        self._tree = tree

    @classmethod
    def from_filename(cls, filename: str) -> "Plugin":
        with tokenize.open(filename) as f:
            source = f.read()
        return cls(ast.parse(source))

    def run(self) -> Iterable[Error]:
        for v in Flake8TrioVisitor.__subclasses__():
            yield from v.run(self._tree)
