"""A highly opinionated flake8 plugin for Trio-related problems.

This can include anything from outright bugs, to pointless/dead code,
to likely performance issues, to minor points of idiom that might signal
a misunderstanding.

It may well be too noisy for anyone with different opinions, that's OK.

Pairs well with flake8-async and flake8-bugbear.
"""

import ast
import tokenize
from typing import Any, Generator, List, Optional, Set, Tuple, Type, Union

# CalVer: YY.month.patch, e.g. first release of July 2022 == "22.7.1"
__version__ = "22.7.3"


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


class TrioScope:
    def __init__(self, node: ast.Call, funcname: str, packagename: str):
        self.node = node
        self.funcname = funcname
        self.packagename = packagename
        self.variable_name: Optional[str] = None
        self.shielded: bool = False
        self.timeout: bool = False

        if self.funcname == "CancelScope":
            for kw in node.keywords:
                # Only accepts constant values
                if kw.arg == "shield" and isinstance(kw.value, ast.Constant):
                    self.shielded = kw.value.value
                # sets to True even if timeout is explicitly set to inf
                if kw.arg == "deadline":
                    self.timeout = True
        else:
            self.timeout = True

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


class Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.problems: List[Error] = []
        self.safe_yields: Set[ast.Yield] = set()
        self._yield_is_error = False
        self._context_manager = False
        self._inside_finally: Optional[ast.Try] = None
        self._scope: Optional[TrioScope] = None

    def visit_generic_with(self, node: Union[ast.With, ast.AsyncWith]):
        self.check_for_trio100(node)

        outer_yie = self._yield_is_error
        outer_scope = self._scope

        # Check for a `with trio.<scope_creater>`
        trio_scope = next(
            (
                get_trio_scope(item, "open_nursery", *cancel_scope_names)
                for item in (i.context_expr for i in node.items)
            ),
            None,
        )
        if trio_scope is not None:
            if not self._context_manager:
                self._yield_is_error = True

            # Check for `with [...] as <varname>`
            trio_scope.variable_name = next(
                (
                    item.optional_vars.id
                    for item in node.items
                    if isinstance(item.optional_vars, ast.Name)
                ),
                None,
            )
            self._scope = trio_scope
        self.generic_visit(node)

        # reset scope and yield_is_error
        self._yield_is_error = outer_yie
        self._scope = outer_scope

    def visit_Assign(self, node: ast.Assign) -> None:
        # checks for <scopename>.shield = [True/False]
        if (
            self._scope
            and self._scope.variable_name is not None
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Attribute)
            and isinstance(node.targets[0].value, ast.Name)
            and node.targets[0].value.id == self._scope.variable_name
            and node.targets[0].attr == "shield"
            and isinstance(node.value, ast.Constant)
        ):
            self._scope.shielded = node.value.value
        self.generic_visit(node)

    def visit_Await(self, node: ast.Await) -> None:
        # if we're inside a finally, and not inside a context_manager, and we're either not in a scope, or in a scope that doesn't have both a timeout and shield
        if (
            self._inside_finally is not None
            and not self._context_manager
            and (
                self._scope is None
                or (
                    self._scope is not None
                    and not (self._scope.timeout and self._scope.shielded)
                )
            )
        ):
            self.problems.append(make_error(TRIO102, node.lineno, node.col_offset))
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.visit_generic_with(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.visit_generic_with(node)

    def visit_generic_FunctionDef(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ):
        outer_cm = self._context_manager
        outer_yie = self._yield_is_error
        self._yield_is_error = False

        # check for @<context_manager_name> and @<library>.<context_manager_name>
        if any(
            (isinstance(d, ast.Name) and d.id in context_manager_names)
            or (isinstance(d, ast.Attribute) and d.attr in context_manager_names)
            for d in node.decorator_list
        ):
            self._context_manager = True
        self.generic_visit(node)
        self._context_manager = outer_cm
        self._yield_is_error = outer_yie

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.visit_generic_FunctionDef(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_generic_FunctionDef(node)

    def visit_Yield(self, node: ast.Yield) -> None:
        if self._yield_is_error:
            self.problems.append(make_error(TRIO101, node.lineno, node.col_offset))

        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        # There's no visit_Finally, so we need to manually visit the Try fields.
        # It's important to do self.visit instead of self.generic_visit since
        # the nodes in the fields might be registered elsewhere in this class.
        for item in (*node.body, *node.handlers, *node.orelse):
            self.visit(item)

        outer = self._inside_finally
        self._inside_finally = node
        for item in node.finalbody:
            self.visit(item)
        self._inside_finally = outer

    def check_for_trio100(self, node: Union[ast.With, ast.AsyncWith]) -> None:
        # Context manager with no `await` call within
        for item in (i.context_expr for i in node.items):
            call = get_trio_scope(item, *cancel_scope_names)
            if call and not any(
                isinstance(x, checkpoint_node_types) for x in ast.walk(node)
            ):
                self.problems.append(
                    make_error(TRIO100, item.lineno, item.col_offset, call)
                )


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
        visitor = Visitor()
        visitor.visit(self._tree)
        yield from visitor.problems


TRIO100 = "TRIO100: {} context contains no checkpoints, add `await trio.sleep(0)`"
TRIO101 = "TRIO101: yield inside a nursery or cancel scope is only safe when implementing a context manager - otherwise, it breaks exception handling"
TRIO102 = "TRIO102: await in finally without a cancel scope and shielding"
