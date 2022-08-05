"""A highly opinionated flake8 plugin for Trio-related problems.

This can include anything from outright bugs, to pointless/dead code,
to likely performance issues, to minor points of idiom that might signal
a misunderstanding.

It may well be too noisy for anyone with different opinions, that's OK.

Pairs well with flake8-async and flake8-bugbear.
"""

import ast
import tokenize
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type, Union

# CalVer: YY.month.patch, e.g. first release of July 2022 == "22.7.1"
__version__ = "22.8.1"

Error = Tuple[int, int, str, Type[Any]]


checkpoint_node_types = (ast.Await, ast.AsyncFor, ast.AsyncWith)
cancel_scope_names = (
    "fail_after",
    "fail_at",
    "move_on_after",
    "move_at",
    "CancelScope",
)
context_manager_names = (
    "contextmanager",
    "asynccontextmanager",
)


def make_error(error: str, lineno: int, col: int, *args: Any, **kwargs: Any) -> Error:
    return (lineno, col, error.format(*args, **kwargs), type(Plugin))


class Flake8TrioVisitor(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self._problems: List[Error] = []

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

    def error(self, error: str, lineno: int, col: int, *args: Any, **kwargs: Any):
        self._problems.append(make_error(error, lineno, col, *args, **kwargs))

    def get_state(self, *attrs: str) -> Dict[str, Any]:
        if not attrs:
            attrs = tuple(self.__dict__.keys())
        return {attr: getattr(self, attr) for attr in attrs if attr != "_problems"}

    def set_state(self, attrs: Dict[str, Any]):
        for attr, value in attrs.items():
            setattr(self, attr, value)


class TrioScope:
    def __init__(self, node: ast.Call, funcname: str, packagename: str):
        self.node = node
        self.funcname = funcname
        self.packagename = packagename
        self.variable_name: Optional[str] = None
        self.shielded: bool = False
        self.has_timeout: bool = False

        if self.funcname == "CancelScope":
            for kw in node.keywords:
                # Only accepts constant values
                if kw.arg == "shield" and isinstance(kw.value, ast.Constant):
                    self.shielded = kw.value.value
                # sets to True even if timeout is explicitly set to inf
                if kw.arg == "deadline":
                    self.has_timeout = True
        else:
            self.has_timeout = True

    def __str__(self):
        # Not supporting other ways of importing trio
        return f"{self.packagename}.{self.funcname}"


def get_trio_scope(node: ast.AST, *names: str) -> Optional[TrioScope]:
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "trio"
        and node.func.attr in names
    ):
        return TrioScope(node, node.func.attr, node.func.value.id)
    return None


def has_decorator(decorator_list: List[ast.expr], *names: str):
    for dec in decorator_list:
        if (isinstance(dec, ast.Name) and dec.id in names) or (
            isinstance(dec, ast.Attribute) and dec.attr in names
        ):
            return True
    return False


# handles 100, 101 and 106
class VisitorMiscChecks(Flake8TrioVisitor):
    def __init__(self):
        super().__init__()
        self._yield_is_error = False
        self._safe_decorator = False

    def visit_With(self, node: Union[ast.With, ast.AsyncWith]):
        self.check_for_trio100(node)

        outer = self.get_state("_yield_is_error")

        # Check for a `with trio.<scope_creater>`
        if not self._safe_decorator:
            for item in (i.context_expr for i in node.items):
                if (
                    get_trio_scope(item, "open_nursery", *cancel_scope_names)
                    is not None
                ):
                    self._yield_is_error = True
                    break

        self.generic_visit(node)

        # reset yield_is_error
        self.set_state(outer)

    def visit_AsyncWith(self, node: ast.AsyncWith):
        self.visit_With(node)

    def visit_FunctionDef(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]):
        outer = self.get_state()
        self._yield_is_error = False
        self._inside_loop = False

        # check for @<context_manager_name> and @<library>.<context_manager_name>
        if has_decorator(node.decorator_list, *context_manager_names):
            self._safe_decorator = True

        self.generic_visit(node)

        self.set_state(outer)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.check_109(node.args)
        self.visit_FunctionDef(node)

    def visit_Yield(self, node: ast.Yield):
        if self._yield_is_error:
            self.error(TRIO101, node.lineno, node.col_offset)

        self.generic_visit(node)

    def check_for_trio100(self, node: Union[ast.With, ast.AsyncWith]):
        # Context manager with no `await` call within
        for item in (i.context_expr for i in node.items):
            call = get_trio_scope(item, *cancel_scope_names)
            if call and not any(
                isinstance(x, checkpoint_node_types) and x != node
                for x in ast.walk(node)
            ):
                self.error(TRIO100, item.lineno, item.col_offset, call)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "trio":
            self.error(TRIO106, node.lineno, node.col_offset)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for name in node.names:
            if name.name == "trio" and name.asname is not None:
                self.error(TRIO106, node.lineno, node.col_offset)

    def check_109(self, args: ast.arguments):
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
            if arg.arg == "timeout":
                self.error(TRIO109, arg.lineno, arg.col_offset)

    def visit_While(self, node: ast.While):
        self.check_for_110(node)
        self.generic_visit(node)

    def check_for_110(self, node: ast.While):
        if (
            len(node.body) == 1
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Await)
            and get_trio_scope(node.body[0].value.value, "sleep", "sleep_until")
        ):
            self.error(TRIO110, node.lineno, node.col_offset)


def critical_except(node: ast.ExceptHandler) -> Optional[Tuple[int, int, str]]:
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
        return node.lineno, node.col_offset, "bare except"
    # several exceptions
    elif isinstance(node.type, ast.Tuple):
        for element in node.type.elts:
            name = has_exception(element)
            if name:
                return element.lineno, element.col_offset, name
    # single exception, either a Name or an Attribute
    else:
        name = has_exception(node.type)
        if name:
            return node.type.lineno, node.type.col_offset, name
    return None


class Visitor102(Flake8TrioVisitor):
    def __init__(self):
        super().__init__()
        self._critical_scope: Optional[Tuple[int, int, str]] = None
        self._trio_context_managers: List[TrioScope] = []
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
            self.error(TRIO102, node.lineno, node.col_offset, *self._critical_scope)
        if visit_children:
            self.generic_visit(node)

    visit_AsyncFor = visit_Await

    def visit_With(self, node: Union[ast.With, ast.AsyncWith]):
        has_context_manager = False

        # Check for a `with trio.<scope_creater>`
        for item in node.items:
            trio_scope = get_trio_scope(
                item.context_expr, "open_nursery", *cancel_scope_names
            )
            if trio_scope is None:
                continue

            self._trio_context_managers.append(trio_scope)
            has_context_manager = True
            # check if it's saved in a variable
            if isinstance(item.optional_vars, ast.Name):
                trio_scope.variable_name = item.optional_vars.id
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
        block: Tuple[int, int, str],
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
            node.finalbody, (node.lineno, node.col_offset, "try/finally")
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
            self.error(TRIO103, *marker)

        self.set_state(outer)

    def visit_Raise(self, node: ast.Raise):
        # if there's an unraised critical exception, the raise isn't bare,
        # and the name doesn't match, signal a problem.
        if (
            self.unraised
            and node.exc is not None
            and not (isinstance(node.exc, ast.Name) and node.exc.id == self.except_name)
        ):
            self.error(TRIO104, node.lineno, node.col_offset)

        # treat it as safe regardless, to avoid unnecessary error messages.
        self.unraised = False

        self.generic_visit(node)

    def visit_Return(self, node: Union[ast.Return, ast.Yield]):
        if self.unraised:
            # Error: must re-raise
            self.error(TRIO104, node.lineno, node.col_offset)
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
        for n in node.finalbody:
            self.visit(n)

    # Treat if's as fully covering if both `if` and `else` raise.
    # `elif` is parsed by the ast as a new if statement inside the else.
    def visit_If(self, node: ast.If):
        if not self.unraised:
            self.generic_visit(node)
            return

        body_raised = False
        for n in node.body:
            self.visit(n)

        # does body always raise correctly
        body_raised = not self.unraised

        self.unraised = True
        for n in node.orelse:
            self.visit(n)

        # if body didn't raise, or it's unraised after else, set unraise
        self.unraised = not body_raised or self.unraised

    # It's hard to check for full coverage of `raise`s inside loops, so
    # we completely disregard them when checking coverage by resetting the
    # effects of them afterwards
    def visit_For(self, node: Union[ast.For, ast.While]):
        outer = self.get_state("unraised")

        self.loop_depth += 1
        for n in node.body:
            self.visit(n)
        self.loop_depth -= 1
        for n in node.orelse:
            self.visit(n)

        self.set_state(outer)

    visit_While = visit_For

    def visit_Break(self, node: Union[ast.Break, ast.Continue]):
        if self.unraised and self.loop_depth == 0:
            self.error(TRIO104, node.lineno, node.col_offset)
        self.generic_visit(node)

    visit_Continue = visit_Break


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
            self.error(TRIO105, node.lineno, node.col_offset, node.func.attr)
        self.generic_visit(node)


class Visitor107_108(Flake8TrioVisitor):
    def __init__(self):
        super().__init__()
        self.all_await = True

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        outer = self.all_await

        # do not require checkpointing if overloading
        self.all_await = has_decorator(node.decorator_list, "overload")
        self.generic_visit(node)

        if not self.all_await:
            self.error(TRIO107, node.lineno, node.col_offset)

        self.all_await = outer

    def visit_Return(self, node: ast.Return):
        self.generic_visit(node)
        if not self.all_await:
            self.error(TRIO108, node.lineno, node.col_offset)
        # avoid duplicate error messages
        self.all_await = True

    # disregard raise's in nested functions
    def visit_FunctionDef(self, node: ast.FunctionDef):
        outer = self.all_await
        self.generic_visit(node)
        self.all_await = outer

    # checkpoint functions
    def visit_Await(
        self, node: Union[ast.Await, ast.AsyncFor, ast.AsyncWith, ast.Raise]
    ):
        self.generic_visit(node)
        self.all_await = True

    visit_AsyncFor = visit_Await
    visit_AsyncWith = visit_Await

    # raising exception means we don't need to checkpoint so we can treat it as one
    visit_Raise = visit_Await

    # valid checkpoint if there's valid checkpoints (or raise) in at least one of:
    # (try or else) and all excepts
    # finally
    def visit_Try(self, node: ast.Try):
        if self.all_await:
            self.generic_visit(node)
            return

        # check try body
        self.visit_nodes(node.body)
        body_await = self.all_await
        self.all_await = False

        # check that all except handlers checkpoint (await or most likely raise)
        all_except_await = True
        for handler in node.handlers:
            self.visit_nodes(handler)
            all_except_await &= self.all_await
            self.all_await = False

        # check else
        self.visit_nodes(node.orelse)

        # (try or else) and all excepts
        self.all_await = (body_await or self.all_await) and all_except_await

        # finally can check on it's own
        self.visit_nodes(node.finalbody)

    # valid checkpoint if both body and orelse have checkpoints
    def visit_If(self, node: Union[ast.If, ast.IfExp]):
        if self.all_await:
            self.generic_visit(node)
            return

        # ignore checkpoints in condition
        self.visit_nodes(node.test)
        self.all_await = False

        # check body
        self.visit_nodes(node.body)
        body_await = self.all_await
        self.all_await = False

        self.visit_nodes(node.orelse)

        # checkpoint if both body and else
        self.all_await = body_await and self.all_await

    # inline if
    visit_IfExp = visit_If

    # ignore checkpoints in loops due to continue/break shenanigans
    def visit_While(self, node: Union[ast.While, ast.For]):
        outer = self.all_await
        self.generic_visit(node)
        self.all_await = outer

    visit_For = visit_While


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


TRIO100 = "TRIO100: {} context contains no checkpoints, add `await trio.sleep(0)`"
TRIO101 = "TRIO101: yield inside a nursery or cancel scope is only safe when implementing a context manager - otherwise, it breaks exception handling"
TRIO102 = "TRIO102: await inside {2} on line {0} must have shielded cancel scope with a timeout"
TRIO103 = "TRIO103: {} block with a code path that doesn't re-raise the error"
TRIO104 = "TRIO104: Cancelled (and therefore BaseException) must be re-raised"
TRIO105 = "TRIO105: trio async function {} must be immediately awaited"
TRIO106 = "TRIO106: trio must be imported with `import trio` for the linter to work"
TRIO107 = "TRIO107: Async functions must have at least one checkpoint on every code path, unless an exception is raised"
TRIO108 = "TRIO108: Early return from async function must have at least one checkpoint on every code path before it."
TRIO109 = "TRIO109: Async function definition with a `timeout` parameter - use `trio.[fail/move_on]_[after/at]` instead"
TRIO110 = "TRIO110: `while <condition>: await trio.sleep()` should be replaced by a `trio.Event`."
