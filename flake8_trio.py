"""A highly opinionated flake8 plugin for Trio-related problems.

This can include anything from outright bugs, to pointless/dead code,
to likely performance issues, to minor points of idiom that might signal
a misunderstanding.

It may well be too noisy for anyone with different opinions, that's OK.

Pairs well with flake8-async and flake8-bugbear.
"""

import ast
import importlib.metadata
from typing import Optional, Type, Any, Generator

# CalVer: YY.month.patch, e.g. first release of July 2022 == "22.7.1"
__version__ = "22.7.1"

TRIO100 = "TRIO100: {} context contains no checkpoints, add `await trio.sleep(0)`"


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
        self.problems: list[tuple[int, int]] = []

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            call = is_trio_call(item.context_expr, "fail_after", "move_on_after")
            if call and not any(isinstance(x, ast.Await) for x in ast.walk(node)):
                self.problems.append(
                    (item.lineno, item.col_offset, TRIO100.format(call))
                )

        # Don't forget to visit the child nodes for other errors!
        self.generic_visit(node)


class Plugin:
    name = __name__
    version = __version__

    def __init__(self, tree: ast.AST) -> None:
        self._tree = tree

    def run(self) -> Generator[tuple[int, int, str, Type[Any]], None, None]:
        visitor = Visitor()
        visitor.visit(self._tree)
        for line, col, message in visitor.problems:
            yield line, col, message, type(self)
