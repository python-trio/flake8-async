"""Checks for exceptions raised on invalid code."""

import ast

import libcst as cst
import pytest

from flake8_async.visitors.helpers import iter_guaranteed_once, iter_guaranteed_once_cst


def _raises_on_code_cst(source: str):
    expression = cst.parse_expression(source)
    with pytest.raises(RuntimeError, match="Invalid literal values.*"):
        iter_guaranteed_once_cst(expression)


def test_iter_guaranteed_once_cst():
    _raises_on_code_cst("range(1, 10, 0)")
    _raises_on_code_cst("range(5, 2, 3, 4)")


def _raises_on_code_ast(source: str):
    expression = ast.parse(source).body[0]
    assert isinstance(expression, ast.Expr)
    call = expression.value
    assert isinstance(call, ast.Call)
    with pytest.raises(RuntimeError, match="Invalid literal values.*"):
        iter_guaranteed_once(call)


def test_iter_guaranteed_once():
    _raises_on_code_ast("range(1, 10, 0)")
    _raises_on_code_ast("range(5, 2, 3, 4)")
