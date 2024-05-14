#!/usr/bin/env python
"""Tests for flake8-async package metadata."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

from .test_flake8_async import ERROR_CODES

ROOT_PATH = Path(__file__).parent.parent
CHANGELOG = ROOT_PATH / "docs" / "changelog.rst"
RULES_DOC = ROOT_PATH / "docs" / "rules.rst"

# 107, 108 & 117 are removed (but still mentioned in changelog & readme)
# ASYNCxxx_* are fake codes to get different error messages for the same code
IGNORED_CODES_REGEX = r"(TRIO|ASYNC)(107|108|117)|ASYNC\d\d\d_.*"


# temp function for eval files
# less sure what to do with the changelog
def rename_trio_to_async(s: str) -> str:
    return re.sub("TRIO", "ASYNC", s)


def test_messages_documented():
    documented_errors: dict[str, set[str]] = {}
    for path in (CHANGELOG, RULES_DOC):
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        filename = path.name
        documented_errors[filename] = set()
        for line in lines:
            for error_msg in re.findall(r"TRIO\d\d\d|ASYNC\d\d\d", line):
                documented_errors[filename].add(rename_trio_to_async(error_msg))

    documented_errors["flake8_async.py"] = set(ERROR_CODES)

    # get tested error codes from file names and from `# ARG --enable` lines
    documented_errors["eval_files"] = set()
    p = Path(__file__).parent / "eval_files"
    for file_path in p.iterdir():
        if not file_path.is_file():
            continue

        # only look in the stem (final part of the path), so as not to get tripped
        # up by [git worktree] directories with an exception code in the name
        if m := re.search(r"^async\d\d\d", str(file_path.stem)):
            documented_errors["eval_files"].add(m.group().upper())

        with open(file_path) as file:
            for line in file:
                if line.startswith("# ARG --enable"):
                    for m in re.findall(r"async\d\d\d", line, re.IGNORECASE):
                        # pyright types m as `Any` (as it is in typeshed)
                        # mypy types it as Optional[Match[str]]
                        # but afaict it should be something like str|Tuple[str,...]
                        # depending on whether there's a group in the pattern or not.
                        # (or bytes, if both inputs are bytes)
                        # see https://github.com/python/typeshed/issues/263
                        documented_errors["eval_files"].add(cast("str", m))
                    break

    # ignore codes that aren't actually codes, and removed codes
    for errset in documented_errors.values():
        errset.difference_update(
            [c for c in errset if re.fullmatch(IGNORED_CODES_REGEX, c)]
        )

    # error is only listed in one file
    unique_errors: dict[str, set[str]] = {}
    # error is mentioned in other files but not in this one
    missing_errors: dict[str, set[str]] = {}
    for key, codes in documented_errors.items():
        unique_errors[key] = codes.copy()
        missing_errors[key] = set()

        for other_key, other_codes in documented_errors.items():
            if key == other_key:
                continue
            unique_errors[key].difference_update(other_codes)
            missing_errors[key].update(other_codes - codes)

    # both of these should be dicts with empty sets
    assert unique_errors == missing_errors
