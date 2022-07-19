"""A highly opinionated flake8 plugin for Trio-related problems.

This can include anything from outright bugs, to pointless/dead code,
to likely performance issues, to minor points of idiom that might signal
a misunderstanding.

It may well be too noisy for anyone with different opinions, that's OK.

Pairs well with flake8-async and flake8-bugbear.
"""

import ast
import tokenize
from typing import Any, Generator, List, Optional, Tuple, Type, Union

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

    def visit_With(self, node: ast.With) -> None:
        self.check_for_trio100(node)
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.check_for_trio100(node)
        self.generic_visit(node)

    def check_for_trio100(self, node: Union[ast.With, ast.AsyncWith]) -> None:
        # Context manager with no `await` call within
        for item in (i.context_expr for i in node.items):
            call = is_trio_call(item, "fail_after", "move_on_after")
            if call and not any(isinstance(x, ast.Await) for x in ast.walk(node)):
                self.problems.append(
                    make_error(TRIO100, item.lineno, item.col_offset, call)
                )


class Plugin:
    name = __name__
    version = __version__

    def __init__(
        self, tree: Optional[ast.AST] = None, filename: Optional[str] = None
    ) -> None:
        if tree is None:
            assert filename is not None
            self._tree = self.load_file(filename)
        else:
            self._tree = tree

    def load_file(self, filename: str) -> ast.AST:
        with tokenize.open(filename) as f:
            return ast.parse(f.read())

    def run(self) -> Generator[Tuple[int, int, str, Type[Any]], None, None]:
        visitor = Visitor()
        visitor.visit(self._tree)
        yield from visitor.problems


TRIO100 = "TRIO100: {} context contains no checkpoints, add `await trio.sleep(0)`"
