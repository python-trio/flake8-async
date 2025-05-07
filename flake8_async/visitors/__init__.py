# pyright: reportUnusedImport=false
"""Submodule for all error classes/visitors.

Exports ERROR_CLASSES and default_disabled_error_codes to be used by others, and populates
them by importing all files with visitor classes (which needs to manually maintained).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .flake8asyncvisitor import Flake8AsyncVisitor, Flake8AsyncVisitor_cst

__all__ = [
    "ERROR_CLASSES",
    "ERROR_CLASSES_CST",
    "default_disabled_error_codes",
    "utility_visitors",
    "utility_visitors_cst",
]
ERROR_CLASSES: set[type[Flake8AsyncVisitor]] = set()
ERROR_CLASSES_CST: set[type[Flake8AsyncVisitor_cst]] = set()
default_disabled_error_codes: list[str] = []
utility_visitors: set[type[Flake8AsyncVisitor]] = set()
utility_visitors_cst: set[type[Flake8AsyncVisitor_cst]] = set()

# Import all files with visitors so their decorators run, filling the above containers
# This has to be done at the end to avoid circular imports
from . import (
    visitor2xx,
    visitor4xx,
    visitor91x,
    visitor101,
    visitor102_120,
    visitor103_104,
    visitor105,
    visitor111,
    visitor118,
    visitor123,
    visitor_utility,
    visitors,
)
