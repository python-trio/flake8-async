"""Submodule for all error classes/visitors.

Exports ERROR_CLASSES and default_disabled_error_codes to be used by others, and populates
them by importing all files with visitor classes (which needs to manually maintained).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .flake8triovisitor import Flake8TrioVisitor

__all__ = ["ERROR_CLASSES", "default_disabled_error_codes"]
ERROR_CLASSES: set[type[Flake8TrioVisitor]] = set()
default_disabled_error_codes: list[str] = []

# Import all visitors so their decorators run, filling the above containers
# This has to be done at the end to avoid circular imports
from . import visitor2xx  # isort: skip
from . import visitor102  # isort: skip
from . import visitor103_104  # isort: skip
from . import visitor107_108  # isort: skip
from . import visitor111  # isort: skip
from . import visitors  # isort: skip
