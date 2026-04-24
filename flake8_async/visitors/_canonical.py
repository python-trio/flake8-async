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
# nothing was imported. Returns None for shapes we can't resolve (subscripts, etc.).
def resolve_canonical_ast(node: ast.AST, imports: Mapping[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return imports.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        prefix = resolve_canonical_ast(node.value, imports)
        return None if prefix is None else f"{prefix}.{node.attr}"
    if isinstance(node, ast.Call):
        return resolve_canonical_ast(node.func, imports)
    return None


def resolve_canonical_cst(
    node: cst.CSTNode, imports: Mapping[str, str]
) -> str | None:
    if isinstance(node, cst.Name):
        return imports.get(node.value, node.value)
    if isinstance(node, cst.Attribute):
        prefix = resolve_canonical_cst(node.value, imports)
        return None if prefix is None else f"{prefix}.{node.attr.value}"
    if isinstance(node, cst.Call):
        return resolve_canonical_cst(node.func, imports)
    return None
