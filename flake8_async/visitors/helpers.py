"""Helper functions used in several visitor classes.

Also contains the decorator definitions used to register error classes.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from fnmatch import fnmatch
from typing import TYPE_CHECKING, Generic, TypeVar, Union

import libcst as cst
import libcst.matchers as m
from libcst.helpers import ensure_type, get_full_name_for_node_or_raise

from ..base import Statement
from . import (
    ERROR_CLASSES,
    ERROR_CLASSES_CST,
    default_disabled_error_codes,
    utility_visitors,
    utility_visitors_cst,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from .flake8asyncvisitor import (
        Flake8AsyncVisitor,
        Flake8AsyncVisitor_cst,
        HasLineCol,
    )

    T = TypeVar("T", bound=Flake8AsyncVisitor)
    T_CST = TypeVar("T_CST", bound=Flake8AsyncVisitor_cst)
    T_EITHER = TypeVar(
        "T_EITHER", bound=Union[Flake8AsyncVisitor, Flake8AsyncVisitor_cst]
    )

T_Call = TypeVar("T_Call", bound=Union[cst.Call, ast.Call])


def error_class(error_class: type[T]) -> type[T]:
    assert error_class.error_codes
    ERROR_CLASSES.add(error_class)
    return error_class


def error_class_cst(error_class: type[T_CST]) -> type[T_CST]:
    assert error_class.error_codes
    ERROR_CLASSES_CST.add(error_class)
    return error_class


def disabled_by_default(error_class: type[T_EITHER]) -> type[T_EITHER]:
    """Default-disables all error codes in a class."""
    assert error_class.error_codes  # type: ignore[attr-defined]
    default_disabled_error_codes.extend(
        error_class.error_codes  # type: ignore[attr-defined]
    )
    return error_class


def disable_codes_by_default(*codes: str) -> None:
    """Default-disables only specified codes."""
    default_disabled_error_codes.extend(codes)


def utility_visitor(c: type[T]) -> type[T]:
    assert not hasattr(c, "error_codes")
    c.error_codes = {}
    utility_visitors.add(c)
    return c


def utility_visitor_cst(c: type[T_CST]) -> type[T_CST]:
    assert not hasattr(c, "error_codes")
    c.error_codes = {}
    utility_visitors_cst.add(c)
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
# used in 113. cst version used in 101, 900 and 910/911
# matches @name, @foo.name, @name(...), and @foo.name(...)
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


def fnmatch_qualified_name_cst(
    name_list: Iterable[cst.Decorator | cst.Call | cst.Attribute | cst.Name],
    *patterns: str,
) -> str | None:
    for name in name_list:
        qualified_name = get_full_name_for_node_or_raise(name)

        for pattern in patterns:
            # strip leading "@"s for when we're working with decorators
            if fnmatch(qualified_name, pattern.lstrip("@")):
                return pattern
    return None


# used in 103/104
def iter_guaranteed_once(iterable: ast.expr) -> bool:
    # static container with an "elts" attribute
    if isinstance(iterable, (ast.List, ast.Tuple, ast.Set)):
        for elt in iterable.elts:
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
            # (where None is the value None, and not an ast node representing None)
            if key is None and isinstance(val, ast.Dict):
                if iter_guaranteed_once(val):
                    return True
            else:
                return True
        return False

    # check for range() with literal parameters
    if (
        isinstance(iterable, ast.Call)
        and isinstance(iterable.func, ast.Name)
        and iterable.func.id == "range"
    ):
        try:
            values = [ast.literal_eval(a) for a in iterable.args]
        except Exception:
            # parameters aren't literal
            return False

        try:
            evaluated_range = range(*values)
        except (ValueError, TypeError):
            str_values = ", ".join(map(str, values))
            raise RuntimeError(
                f"Invalid literal values to range function: `range({str_values})`"
            )

        try:
            return len(evaluated_range) > 0
        # if the length is > sys.maxsize
        except OverflowError:
            return True
    return False


# used in 91X
def iter_guaranteed_once_cst(iterable: cst.BaseExpression) -> bool:
    # static container with an "elts" attribute
    if isinstance(iterable, (cst.Tuple, cst.List, cst.Dict, cst.Set)):
        for elt in iterable.elements:
            # recurse starred expression
            if isinstance(elt, (cst.StarredElement, cst.StarredDictElement)):
                if iter_guaranteed_once_cst(elt.value):
                    return True
            else:
                # a non-starred non-empty container is guaranteed to iter
                return True
        return False

    if isinstance(iterable, cst.SimpleString):
        return len(iterable.raw_value) > 0

    # check for range() with literal parameters
    if m.matches(
        iterable,
        m.Call(
            func=m.Name("range"),
        ),
    ):
        values: list[int] = []
        for arg_arg in ensure_type(iterable, cst.Call).args:
            arg = arg_arg.value
            if isinstance(arg, cst.UnaryOperation):
                if not isinstance(arg.expression, cst.Integer):
                    return False
                value = arg.expression.evaluated_value
                if isinstance(arg.operator, cst.Minus):
                    value = -value
                elif isinstance(arg.operator, cst.BitInvert):
                    value = ~value
            elif isinstance(arg, cst.Integer):
                value = arg.evaluated_value
            else:
                return False
            values.append(value)
        try:
            evaluated_range = range(*values)
        except (ValueError, TypeError):
            str_values = ", ".join(map(str, values))
            raise RuntimeError(
                f"Invalid literal values to range function: `range({str_values})`"
            )
        try:
            return len(evaluated_range) > 0
        # if the length is > sys.maxsize
        except OverflowError:
            return True

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
            "asyncio.exceptions.CancelledError",
            "exceptions.CancelledError",
            "CancelledError",
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


@dataclass
class MatchingCall(Generic[T_Call]):
    node: T_Call
    name: str
    base: str

    def __str__(self) -> str:
        return self.base + "." + self.name


# convenience function used in a lot of visitors
def get_matching_call(
    node: ast.AST, *names: str, base: Iterable[str] = ("trio", "anyio")
) -> MatchingCall[ast.Call] | None:
    if isinstance(base, str):
        base = (base,)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in base
        and node.func.attr in names
    ):
        return MatchingCall(node, node.func.attr, node.func.value.id)
    return None


# ___ CST helpers ___
def get_matching_call_cst(
    node: cst.CSTNode, *names: str, base: Iterable[str] = ("trio", "anyio")
) -> MatchingCall[cst.Call] | None:
    if isinstance(base, str):
        base = (base,)
    if (
        isinstance(node, cst.Call)
        and isinstance(node.func, cst.Attribute)
        and node.func.attr.value in names
        and isinstance(node.func.value, (cst.Name, cst.Attribute))
    ):
        attr_base = identifier_to_string(node.func.value)
        if attr_base is not None and attr_base in base:
            return MatchingCall(node, node.func.attr.value, attr_base)
    return None


def oneof_names(*names: str):
    return m.OneOf(*map(m.Name, names))


CSTNode_T = TypeVar("CSTNode_T", bound=cst.CSTNode)


def list_contains(
    seq: Sequence[CSTNode_T], matcher: m.BaseMatcherNode
) -> Iterator[CSTNode_T]:
    yield from (item for item in seq if m.matches(item, matcher))


# the custom __or__ in libcst breaks pyright type checking. It's possible to use
# `Union` as a workaround ... except pyupgrade will automatically replace that.
# So we have to resort to specifying one of the base classes.
# See https://github.com/Instagram/LibCST/issues/1143
def build_cst_matcher(attr: str) -> m.BaseExpression:
    """Build a cst matcher structure with attributes&names matching a string `a.b.c`."""
    if "." not in attr:
        return m.Name(value=attr)
    body, tail = attr.rsplit(".")
    return m.Attribute(value=build_cst_matcher(body), attr=m.Name(value=tail))


def identifier_to_string(node: cst.CSTNode) -> str | None:
    """Convert a simple identifier to a string.

    If the node is composed of anything but cst.Name + cst.Attribute it returns None.
    """
    if isinstance(node, cst.Name):
        return node.value
    if (
        isinstance(node, cst.Attribute)
        and (lhs := identifier_to_string(node.value)) is not None
    ):
        return lhs + "." + node.attr.value

    return None


def with_has_call(
    node: cst.With, *names: str, base: Iterable[str] | str = ("trio", "anyio")
) -> list[MatchingCall[cst.Call]]:
    """Check if a with statement has a matching call, returning a list with matches.

    `names` specify the names of functions to match, `base` specifies the
    library/module(s) the function must be in.
    The list elements in the return value are named tuples with the matched node,
    base and function.

    Examples_

    `with_has_call(node, "bar", base="foo")` matches foo.bar.
    `with_has_call(node, "bar", "bee", base=("foo", "a.b.c")` matches
      `foo.bar`, `foo.bee`, `a.b.c.bar`, and `a.b.c.bee`.

    """
    if isinstance(base, str):
        base = (base,)

    # build matcher, using SaveMatchedNode to save the base and the function name.
    matcher = m.Call(
        func=m.Attribute(
            value=m.SaveMatchedNode(
                m.OneOf(*(build_cst_matcher(b) for b in base)), name="base"
            ),
            attr=m.SaveMatchedNode(
                oneof_names(*names),
                name="function",
            ),
        )
    )

    res_list: list[MatchingCall[cst.Call]] = []
    for item in node.items:
        if res := m.extract(item.item, matcher):
            assert isinstance(item.item, cst.Call)
            assert isinstance(res["base"], (cst.Name, cst.Attribute))
            assert isinstance(res["function"], cst.Name)
            base_string = identifier_to_string(res["base"])
            assert base_string is not None, "subscripts should never get matched"
            res_list.append(
                MatchingCall(
                    node=item.item, base=base_string, name=res["function"].value
                )
            )
    return res_list


def func_has_decorator(func: cst.FunctionDef, *names: str) -> bool:
    return any(
        list_contains(
            func.decorators,
            m.Decorator(
                decorator=m.OneOf(
                    # @name
                    oneof_names(*names),
                    # @foo.name
                    m.Attribute(attr=oneof_names(*names)),
                    # @name(...)
                    m.Call(func=oneof_names(*names)),
                    # @foo.name(...)
                    m.Call(func=m.Attribute(attr=oneof_names(*names))),
                )
            ),
        )
    )


def get_comments(node: cst.CSTNode | Iterable[cst.CSTNode]) -> Iterator[cst.EmptyLine]:
    if isinstance(node, (cst.CSTNode, cst.MaybeSentinel)):
        yield from (
            cst.EmptyLine(comment=ensure_type(c, cst.Comment))
            for c in m.findall(node, m.Comment())
        )
    else:
        for n in node:
            yield from get_comments(n)


# used in ASYNC100
def flatten_preserving_comments(node: cst.BaseCompoundStatement):
    # add leading lines (comments and empty lines) for the node to be removed
    new_leading_lines = list(node.leading_lines)

    # add other comments belonging to the node as empty lines with comments
    for attr in "lpar", "items", "rpar":
        # pragma, since this is currently only used to flatten `With` statements
        if comment_nodes := getattr(node, attr, None):  # pragma: no cover
            new_leading_lines.extend(get_comments(comment_nodes))

    # node.body is a BaseSuite, whose subclasses are SimpleStatementSuite
    # and IndentedBlock
    if isinstance(node.body, cst.SimpleStatementSuite):
        # `with ...: pass;pass;pass` -> pass;pass;pass
        return cst.SimpleStatementLine(
            node.body.body,
            leading_lines=new_leading_lines,
            trailing_whitespace=node.body.trailing_whitespace,
        )

    assert isinstance(node.body, cst.IndentedBlock)
    nodes = list(node.body.body)

    # nodes[0] is a BaseStatement, whose subclasses are SimpleStatementLine
    # and BaseCompoundStatement - both of which has leading_lines
    assert isinstance(nodes[0], (cst.SimpleStatementLine, cst.BaseCompoundStatement))

    # add body header comment - i.e. comments on the same/last line of the statement
    if node.body.header and node.body.header.comment:
        new_leading_lines.append(
            cst.EmptyLine(indent=True, comment=node.body.header.comment)
        )
    # add the leading lines of the first node
    new_leading_lines.extend(nodes[0].leading_lines)
    # update the first node with all the above constructed lines
    nodes[0] = nodes[0].with_changes(leading_lines=new_leading_lines)

    # if there's comments in the footer of the indented block, add a pass
    # statement with the comments as leading lines
    if node.body.footer:
        nodes.append(
            cst.SimpleStatementLine(
                [cst.Pass()],
                node.body.footer,
            )
        )
    return cst.FlattenSentinel(nodes)
