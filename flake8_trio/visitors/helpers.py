"""Helper functions used in several visitor classes.

Also contains the decorator definitions used to register error classes.
"""

from __future__ import annotations

import ast
from fnmatch import fnmatch
from typing import TYPE_CHECKING, NamedTuple, TypeVar

import libcst as cst
import libcst.matchers as m

from ..base import Statement
from . import (
    ERROR_CLASSES,
    ERROR_CLASSES_CST,
    default_disabled_error_codes,
    utility_visitors,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from .flake8triovisitor import Flake8TrioVisitor, Flake8TrioVisitor_cst, HasLineCol

    T = TypeVar("T", bound=Flake8TrioVisitor)
    T_CST = TypeVar("T_CST", bound=Flake8TrioVisitor_cst)


def error_class(error_class: type[T]) -> type[T]:
    assert error_class.error_codes
    ERROR_CLASSES.add(error_class)
    return error_class


def error_class_cst(error_class: type[T_CST]) -> type[T_CST]:
    assert error_class.error_codes
    ERROR_CLASSES_CST.add(error_class)
    return error_class


def disabled_by_default(error_class: type[T]) -> type[T]:
    assert error_class.error_codes
    default_disabled_error_codes.extend(error_class.error_codes)
    return error_class


def utility_visitor(c: type[T]) -> type[T]:
    assert not hasattr(c, "error_codes")
    c.error_codes = {}
    utility_visitors.add(c)
    return c


def _get_identifier(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _get_identifier(node.func)
    return ""


# ignores module and only checks the unqualified name of the decorator
# used in 101, 113, 900 and 910/911
def has_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef, *names: str):
    return any(_get_identifier(dec) in names for dec in node.decorator_list)


# matches the fully qualified name against fnmatch pattern
# used to match decorators and methods to user-supplied patterns
# used in 910/911 and 200
def fnmatch_qualified_name(name_list: list[ast.expr], *patterns: str) -> str | None:
    for name in name_list:
        if isinstance(name, ast.Call):
            name = name.func
        qualified_name = ast.unparse(name)

        for pattern in patterns:
            # strip leading "@"s for when we're working with decorators
            if fnmatch(qualified_name, pattern.lstrip("@")):
                return pattern
    return None


# used in 103/104 and 910/911
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
        return hasattr(iterable.value, "__len__") and len(iterable.value) > 0

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
        except Exception:  # noqa: PIE786
            return False
    return False


# used in 102, 103 and 104
def critical_except(node: ast.ExceptHandler) -> Statement | None:
    def has_exception(node: ast.expr) -> str | None:
        name = ast.unparse(node)
        if name in (
            "BaseException",
            "trio.Cancelled",
            "anyio.get_cancelled_exc_class()",
            "get_cancelled_exc_class()",
        ):
            return name
        return None

    name: str | None = None
    posnode: HasLineCol = node

    # bare except
    if node.type is None:
        name = "bare except"

    # several exceptions
    elif isinstance(node.type, ast.Tuple):
        for element in node.type.elts:
            name = has_exception(element)
            if name is not None:
                posnode = element
                break
    # single exception, either a Name or an Attribute
    else:
        name = has_exception(node.type)
        posnode = node.type

    if name is not None:
        return Statement(name, posnode.lineno, posnode.col_offset)

    return None


# used in 100, 101 and 102
cancel_scope_names = (
    "fail_after",
    "fail_at",
    "move_on_after",
    "move_on_at",
    "CancelScope",
)


# convenience function used in a lot of visitors
# should probably return a named tuple
def get_matching_call(
    node: ast.AST, *names: str, base: Iterable[str] = ("trio", "anyio")
) -> tuple[ast.Call, str, str] | None:
    if isinstance(base, str):
        base = (base,)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in base
        and node.func.attr in names
    ):
        return node, node.func.attr, node.func.value.id
    return None


# ___ CST helpers ___
def oneof_names(*names: str):
    return m.OneOf(*map(m.Name, names))


CSTNode_T = TypeVar("CSTNode_T", bound=cst.CSTNode)


def list_contains(
    seq: Sequence[CSTNode_T], matcher: m.BaseMatcherNode
) -> Iterator[CSTNode_T]:
    yield from (item for item in seq if m.matches(item, matcher))


class AttributeCall(NamedTuple):
    node: cst.Call
    base: str
    function: str


def with_has_call(
    node: cst.With, *names: str, base: Iterable[str] = ("trio", "anyio")
) -> list[AttributeCall]:
    res_list: list[AttributeCall] = []
    for item in node.items:
        if res := m.extract(
            item.item,
            m.Call(
                func=m.Attribute(
                    value=m.SaveMatchedNode(m.Name(), name="library"),
                    attr=m.SaveMatchedNode(
                        oneof_names(*names),
                        name="function",
                    ),
                )
            ),
        ):
            assert isinstance(item.item, cst.Call)
            assert isinstance(res["library"], cst.Name)
            assert isinstance(res["function"], cst.Name)
            if res["library"].value not in base:
                continue
            res_list.append(
                AttributeCall(item.item, res["library"].value, res["function"].value)
            )
    return res_list


def func_has_decorator(func: cst.FunctionDef, *names: str) -> bool:
    return any(
        list_contains(
            func.decorators,
            m.Decorator(
                decorator=m.OneOf(
                    oneof_names(*names),
                    m.Attribute(attr=oneof_names(*names)),
                    m.Call(func=m.Attribute(attr=oneof_names(*names))),
                )
            ),
        )
    )
