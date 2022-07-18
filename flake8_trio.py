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

    def visit_With(self, node: ast.With) -> None:
        self.check_for_trio100(node)
        self.check_for_trio101(node)
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.check_for_trio100(node)
        self.check_for_trio101(node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.trio101_mark_yields_safe(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.trio101_mark_yields_safe(node)
        self.generic_visit(node)

    def check_for_trio100(self, node: Union[ast.With, ast.AsyncWith]) -> None:
        # Context manager with no `await` call within
        for item in (i.context_expr for i in node.items):
            call = is_trio_call(item, "fail_after", "move_on_after")
            if call and not any(isinstance(x, ast.Await) for x in ast.walk(node)):
                self.problems.append(
                    make_error(TRIO100, item.lineno, item.col_offset, call)
                )

    def trio101_mark_yields_safe(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> None:
        if any(
            isinstance(d, ast.Name)
            and d.id in ("contextmanager", "asynccontextmanager")
            for d in node.decorator_list
        ):
            self.safe_yields.update(
                {x for x in ast.walk(node) if isinstance(x, ast.Yield)}
            )

    def check_for_trio101(self, node: Union[ast.With, ast.AsyncWith]) -> None:
        for item in (i.context_expr for i in node.items):
            call = is_trio_call(
                item,
                "open_nursery",
                "fail_after",
                "fail_at",
                "move_on_after",
                "move_at",
            )
            if call and any(
                isinstance(x, ast.Yield) and x not in self.safe_yields
                for x in ast.walk(node)
            ):
                self.problems.append(
                    make_error(TRIO101, item.lineno, item.col_offset, call)
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
TRIO101 = "TRIO101: {} never yield inside a nursery or cancel scope"
