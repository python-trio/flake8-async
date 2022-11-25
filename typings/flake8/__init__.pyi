"""
This type stub file was generated by pyright.
"""

import logging
import sys
from __future__ import annotations
from typing import Tuple, Dict

"""Top-level module for Flake8.

This module

- initializes logging for the command-line tool
- tracks the version of the package
- provides a way to configure logging for the command-line tool

.. autofunction:: flake8.configure_logging

"""
LOG: logging.Logger = ...
__version__: str = ...
__version_info__: Tuple[int, ...] = ...
_VERBOSITY_TO_LOG_LEVEL: Dict[int, int] = ...
LOG_FORMAT: str = ...

def configure_logging(
    verbosity: int, filename: str | None = ..., logformat: str = ...
) -> None:
    """Configure logging for flake8.

    :param verbosity:
        How verbose to be in logging information.
    :param filename:
        Name of the file to append log information to.
        If ``None`` this will log to ``sys.stderr``.
        If the name is "stdout" or "stderr" this will log to the appropriate
        stream.
    """
    ...