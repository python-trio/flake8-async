"""Check that all visitors are imported.

Checks that all flake8_async/visitor*.py files are imported in
flake8_async/visitor/__init__.py so their decorators are run.
"""

from __future__ import annotations

import re
from pathlib import Path


def test_all_visitors_imported():
    visitor_dir = Path(__file__).parent.parent / "flake8_async" / "visitors"
    visitor_files = {
        f.stem for f in visitor_dir.iterdir() if f.stem.startswith("visitor")
    }
    visited_files: set[str] = set()
    in_import: bool | None = None
    with open(visitor_dir / "__init__.py") as f:
        for line in f:
            if m := re.fullmatch(r"from \. import \(\n", line):
                in_import = True
            elif in_import and (m := re.fullmatch(r" *(?P<module>\w*),\n", line)):
                visited_files.add(m.group("module"))
            elif in_import and re.fullmatch(r"\)\n", line):
                in_import = False

    # check that parsing succeeded
    assert in_import is False

    assert visitor_files == visited_files
