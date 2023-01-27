"""Check that all visitors are imported.

Checks that all flake8_trio/visitor*.py files are imported in flake8_trio/visitor/__init__
so their decorators are run.
"""

from __future__ import annotations

import re
from pathlib import Path


def test_all_visitors_imported():
    visitor_dir = Path(__file__).parent.parent / "flake8_trio" / "visitors"
    visitor_files = {
        f.stem for f in visitor_dir.iterdir() if f.stem.startswith("visitor")
    }
    visited_files = set()
    with open(visitor_dir / "__init__.py") as f:
        for line in f:
            if m := re.match(r"from \. import (?P<module>\w*)", line):
                visited_files.add(m.group("module"))
    assert visitor_files == visited_files
