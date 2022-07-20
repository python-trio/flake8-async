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
__version__ = "22.7.1"


Error = Tuple[int, int, str, Type[Any]]
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


def is_trio_call(node: ast.AST, *names: str) -> Optional[str]:
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "trio"
        and node.func.attr in names
    ):
        return "trio." + node.func.attr
    return None


class Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.problems: List[Error] = []
        self.safe_yields: Set[ast.Yield] = set()
        self._yield_is_error = False
        self._context_manager = False

    def visit_generic_with(self, node: Union[ast.With, ast.AsyncWith]):
        self.check_for_trio100(node)

        outer = self._yield_is_error
        if not self._context_manager and any(
            is_trio_call(item, "open_nursery", *cancel_scope_names)
            for item in (i.context_expr for i in node.items)
        ):
            self._yield_is_error = True

        self.generic_visit(node)
        self._yield_is_error = outer

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

    def check_for_trio100(self, node: Union[ast.With, ast.AsyncWith]) -> None:
        # Context manager with no `await` call within
        for item in (i.context_expr for i in node.items):
            call = is_trio_call(item, *cancel_scope_names)
            if call and not any(isinstance(x, ast.Await) for x in ast.walk(node)):
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
