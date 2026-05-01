"""Canonical-qualname resolution for ast / cst nodes.

Kept in its own module to avoid circular imports between
``flake8asyncvisitor`` (which exposes ``canonical_name`` on the base classes)
and ``helpers`` (which accepts an ``imports`` mapping for matcher functions).
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import libcst as cst

if TYPE_CHECKING:
    from collections.abc import Mapping


# Resolve a Name/Attribute/Call node to a dotted qualname via `imports`
# (local-name -> canonical dotted qualname). The root Name falls back to its own
# identifier, so `trio.open_nursery()` resolves to "trio.open_nursery" even when
# nothing was imported. Returns None for shapes we can't resolve (subscripts,
# Calls nested inside an Attribute chain like `foo("x").bar`, etc.).
def resolve_canonical_ast(node: ast.AST, imports: Mapping[str, str]) -> str | None:
    # A Call only collapses to its callee at the *outermost* position. Inside
    # an Attribute chain (e.g. `foo("x").bar`), the call's return value is what
    # `.bar` is bound on, and we can't determine that statically — so don't
    # silently elide the call into a dotted name like "foo.bar".
    if isinstance(node, ast.Call):
        return resolve_canonical_ast(node.func, imports)
    return _resolve_attr_chain_ast(node, imports)


def _resolve_attr_chain_ast(node: ast.AST, imports: Mapping[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return imports.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        prefix = _resolve_attr_chain_ast(node.value, imports)
        return None if prefix is None else f"{prefix}.{node.attr}"
    return None


def resolve_canonical_cst(node: cst.CSTNode, imports: Mapping[str, str]) -> str | None:
    if isinstance(node, cst.Call):
        return resolve_canonical_cst(node.func, imports)
    return _resolve_attr_chain_cst(node, imports)


def _resolve_attr_chain_cst(
    node: cst.CSTNode, imports: Mapping[str, str]
) -> str | None:
    if isinstance(node, cst.Name):
        return imports.get(node.value, node.value)
    if isinstance(node, cst.Attribute):
        prefix = _resolve_attr_chain_cst(node.value, imports)
        return None if prefix is None else f"{prefix}.{node.attr.value}"
    return None
