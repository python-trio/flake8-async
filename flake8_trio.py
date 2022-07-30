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
    Collection,
    Generator,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

# CalVer: YY.month.patch, e.g. first release of July 2022 == "22.7.1"
__version__ = "22.7.4"


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
    def __init__(self) -> None:
        super().__init__()
        self.problems: List[Error] = []

    @classmethod
    def run(cls, tree: ast.AST) -> Generator[Error, None, None]:
        visitor = cls()
        visitor.visit(tree)
        yield from visitor.problems

    def visit_nodes(self, nodes: Union[ast.expr, Iterable[ast.AST]]) -> None:
        if isinstance(nodes, ast.expr):
            self.visit(nodes)
        else:
            for node in nodes:
                self.visit(node)

    def error(self, error: str, lineno: int, col: int, *args: Any, **kwargs: Any):
        self.problems.append(make_error(error, lineno, col, *args, **kwargs))


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
        # if self.packagename is None:
        # return self.funcname
        return f"{self.packagename}.{self.funcname}"


def get_trio_scope(node: ast.AST, *names: str) -> Optional[TrioScope]:
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "trio"
        and node.func.attr in names
    ):
        # return "trio." + node.func.attr
        return TrioScope(node, node.func.attr, node.func.value.id)
    return None


def has_decorator(decorator_list: List[ast.expr], names: Collection[str]):
    for dec in decorator_list:
        if (isinstance(dec, ast.Name) and dec.id in names) or (
            isinstance(dec, ast.Attribute) and dec.attr in names
        ):
            return True
    return False


# handles 100, 101 and 106
class VisitorMiscChecks(Flake8TrioVisitor):
    def __init__(self) -> None:
        super().__init__()
        self._yield_is_error = False
        self._context_manager = False

    def visit_With(self, node: Union[ast.With, ast.AsyncWith]) -> None:
        self.check_for_trio100(node)

        outer_yie = self._yield_is_error

        # Check for a `with trio.<scope_creater>`
        if not self._context_manager:
            for item in (i.context_expr for i in node.items):
                if (
                    get_trio_scope(item, "open_nursery", *cancel_scope_names)
                    is not None
                ):
                    self._yield_is_error = True
                    break

        self.generic_visit(node)

        # reset yield_is_error
        self._yield_is_error = outer_yie

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.visit_With(node)

    def visit_FunctionDef(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> None:
        outer_cm = self._context_manager
        outer_yie = self._yield_is_error
        self._yield_is_error = False

        # check for @<context_manager_name> and @<library>.<context_manager_name>
        if has_decorator(node.decorator_list, context_manager_names):
            self._context_manager = True

        self.generic_visit(node)

        self._context_manager = outer_cm
        self._yield_is_error = outer_yie

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_Yield(self, node: ast.Yield) -> None:
        if self._yield_is_error:
            self.problems.append(make_error(TRIO101, node.lineno, node.col_offset))

        self.generic_visit(node)

    def check_for_trio100(self, node: Union[ast.With, ast.AsyncWith]) -> None:
        # Context manager with no `await` call within
        for item in (i.context_expr for i in node.items):
            call = get_trio_scope(item, *cancel_scope_names)
            if call and not any(
                isinstance(x, checkpoint_node_types) and x != node
                for x in ast.walk(node)
            ):
                self.problems.append(
                    make_error(TRIO100, item.lineno, item.col_offset, call)
                )

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "trio":
            self.problems.append(make_error(TRIO106, node.lineno, node.col_offset))
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for name in node.names:
            if name.name == "trio" and name.asname is not None:
                self.problems.append(make_error(TRIO106, node.lineno, node.col_offset))


class Visitor102(Flake8TrioVisitor):
    def __init__(self) -> None:
        super().__init__()
        self._inside_finally: bool = False
        self._scopes: List[TrioScope] = []
        self._context_manager = False

    def visit_Assign(self, node: ast.Assign) -> None:
        # checks for <scopename>.shield = [True/False]
        if self._scopes and len(node.targets) == 1:
            last_scope = self._scopes[-1]
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

    def visit_Await(self, node: ast.Await) -> None:
        self.check_for_trio102(node)
        self.generic_visit(node)

    def visit_With(self, node: Union[ast.With, ast.AsyncWith]) -> None:
        trio_scope = None

        # Check for a `with trio.<scope_creater>`
        for item in node.items:
            trio_scope = get_trio_scope(
                item.context_expr, "open_nursery", *cancel_scope_names
            )
            if trio_scope is not None:
                # check if it's saved in a variable
                if isinstance(item.optional_vars, ast.Name):
                    trio_scope.variable_name = item.optional_vars.id
                break

        if trio_scope is not None:
            self._scopes.append(trio_scope)

        self.generic_visit(node)

        if trio_scope is not None:
            self._scopes.pop()

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.check_for_trio102(node)
        self.visit_With(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.check_for_trio102(node)
        self.generic_visit(node)

    def visit_FunctionDef(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> None:
        outer_cm = self._context_manager

        # check for @<context_manager_name> and @<library>.<context_manager_name>
        if has_decorator(node.decorator_list, context_manager_names):
            self._context_manager = True

        self.generic_visit(node)
        self._context_manager = outer_cm

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_Try(self, node: ast.Try) -> None:
        # There's no visit_Finally, so we need to manually visit the Try fields.
        # It's important to do self.visit instead of self.generic_visit since
        # the nodes in the fields might be registered elsewhere in this class.
        for item in (*node.body, *node.handlers, *node.orelse):
            self.visit(item)

        outer = self._inside_finally
        outer_scopes = self._scopes

        self._scopes = []
        self._inside_finally = True

        for item in node.finalbody:
            self.visit(item)

        self._scopes = outer_scopes
        self._inside_finally = outer

    def check_for_trio102(self, node: Union[ast.Await, ast.AsyncFor, ast.AsyncWith]):
        # if we're inside a finally, and not inside a context_manager, and we're not
        # inside a scope that doesn't have both a timeout and shield
        if (
            self._inside_finally
            and not self._context_manager
            and not any(scope.has_timeout and scope.shielded for scope in self._scopes)
        ):
            self.problems.append(make_error(TRIO102, node.lineno, node.col_offset))


# Never have an except Cancelled or except BaseException block with a code path that
# doesn't re-raise the error
class Visitor103_104(Flake8TrioVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.except_name: Optional[str] = ""
        self.unraised: bool = False
        self.loop_depth = 0

    # If an `except` is bare, catches `BaseException`, or `trio.Cancelled`
    # set self.unraised, and if it's still set after visiting child nodes
    # then there might be a code path that doesn't re-raise.
    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        def has_exception(node: Optional[ast.expr]):
            return (isinstance(node, ast.Name) and node.id == "BaseException") or (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "trio"
                and node.attr == "Cancelled"
            )

        outer = (self.unraised, self.except_name, self.loop_depth)
        marker = None

        # we need to not unset self.unraised if this is non-critical to still
        # warn about `return`s

        # bare except
        if node.type is None:
            self.unraised = True
            marker = (node.lineno, node.col_offset)
        # several exceptions
        elif isinstance(node.type, ast.Tuple):
            for element in node.type.elts:
                if has_exception(element):
                    self.unraised = True
                    marker = element.lineno, element.col_offset
                    break
        # single exception, either a Name or an Attribute
        elif has_exception(node.type):
            self.unraised = True
            marker = node.type.lineno, node.type.col_offset

        if marker is not None:
            # save name `as <except_name>`
            self.except_name = node.name
            self.loop_depth = 0

        # visit child nodes. Will unset self.unraised if all code paths `raise`
        self.generic_visit(node)

        if self.unraised and marker is not None:
            self.problems.append(make_error(TRIO103, *marker))

        (self.unraised, self.except_name, self.loop_depth) = outer

    def visit_Raise(self, node: ast.Raise):
        # if there's an unraised critical exception, the raise isn't bare,
        # and the name doesn't match, signal a problem.
        if (
            self.unraised
            and node.exc is not None
            and not (isinstance(node.exc, ast.Name) and node.exc.id == self.except_name)
        ):
            self.problems.append(make_error(TRIO104, node.lineno, node.col_offset))

        # treat it as safe regardless, to avoid unnecessary error messages.
        self.unraised = False

        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        if self.unraised:
            # Error: must re-raise
            self.problems.append(make_error(TRIO104, node.lineno, node.col_offset))
        self.generic_visit(node)

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
        outer_unraised = self.unraised
        self.loop_depth += 1
        for n in node.body:
            self.visit(n)
        self.loop_depth -= 1
        for n in node.orelse:
            self.visit(n)
        self.unraised = outer_unraised

    visit_While = visit_For

    def visit_Break(self, node: Union[ast.Break, ast.Continue]):
        if self.unraised and self.loop_depth == 0:
            self.problems.append(make_error(TRIO104, node.lineno, node.col_offset))
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
    def __init__(self) -> None:
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
            self.problems.append(
                make_error(TRIO105, node.lineno, node.col_offset, node.func.attr)
            )
        self.generic_visit(node)


class Visitor300_301(Flake8TrioVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.all_await = True

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        outer = self.all_await

        self.all_await = False
        self.generic_visit(node)

        if not self.all_await:
            self.error(TRIO300, node.lineno, node.col_offset)

        self.all_await = outer

    def visit_Return(self, node: ast.Return):
        self.generic_visit(node)
        if not self.all_await:
            self.error(TRIO301, node.lineno, node.col_offset)
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

    # ignore checkpoints in try, excepts and orelse
    def visit_Try(self, node: ast.Try):
        outer = self.all_await

        self.visit_nodes(node.body)
        self.visit_nodes(node.handlers)
        self.visit_nodes(node.orelse)

        self.all_await = outer

        self.visit_nodes(node.finalbody)

    # valid checkpoint if both body and orelse have checkpoints
    def visit_If(self, node: Union[ast.If, ast.IfExp]):
        if self.all_await:
            self.generic_visit(node)
            return

        # ignore checkpoints in condition
        self.visit_nodes(node.test)
        self.all_await = False

        self.visit_nodes(node.body)
        body_await = self.all_await
        self.all_await = False

        self.visit_nodes(node.orelse)
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

    def __init__(self, tree: ast.AST) -> None:
        self._tree = tree

    @classmethod
    def from_filename(cls, filename: str) -> "Plugin":
        with tokenize.open(filename) as f:
            source = f.read()
        return cls(ast.parse(source))

    def run(self) -> Generator[Tuple[int, int, str, Type[Any]], None, None]:
        for v in Flake8TrioVisitor.__subclasses__():
            yield from v.run(self._tree)


TRIO100 = "TRIO100: {} context contains no checkpoints, add `await trio.sleep(0)`"
TRIO101 = "TRIO101: yield inside a nursery or cancel scope is only safe when implementing a context manager - otherwise, it breaks exception handling"
TRIO102 = "TRIO102: it's unsafe to await inside `finally:` unless you use a shielded cancel scope with a timeout"
TRIO103 = "TRIO103: except Cancelled or except BaseException block with a code path that doesn't re-raise the error"
TRIO104 = "TRIO104: Cancelled (and therefore BaseException) must be re-raised"
TRIO105 = "TRIO105: Trio async function {} must be immediately awaited"
TRIO106 = "TRIO106: trio must be imported with `import trio` for the linter to work"
TRIO300 = "TRIO300: Async functions must have at least one checkpoint on every code path, unless an exception is raised"
TRIO301 = "TRIO301: Early return from async function must have at least one checkpoint on every code path before it."
