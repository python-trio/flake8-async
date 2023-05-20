#!/usr/bin/env python
"""Tests for flake8-trio package metadata."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

from .test_flake8_trio import ERROR_CODES

ROOT_PATH = Path(__file__).parent.parent
CHANGELOG = ROOT_PATH / "CHANGELOG.md"
README = CHANGELOG.parent / "README.md"

# 107 & 108 are removed (but still mentioned in changelog & readme)
# TRIOxxx_* are fake codes to get different error messages for the same code
IGNORED_CODES_REGEX = r"TRIO107|TRIO108|TRIO\d\d\d_.*"


def test_messages_documented():
    documented_errors: dict[str, set[str]] = {}
    for path in (CHANGELOG, README):
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        filename = path.name
        documented_errors[filename] = set()
        for line in lines:
            for error_msg in re.findall(r"TRIO\d\d\d", line):
                documented_errors[filename].add(error_msg)

    documented_errors["flake8_trio.py"] = set(ERROR_CODES)

    # get tested error codes from file names and from `INCLUDE` lines
    documented_errors["eval_files"] = set()
    p = Path(__file__).parent / "eval_files"
    for file_path in p.iterdir():
        if not file_path.is_file():
            continue

        if m := re.search(r"trio\d\d\d", str(file_path)):
            documented_errors["eval_files"].add(m.group().upper())

        with open(file_path) as file:
            for line in file:
                if line.startswith("# ARG --enable"):
                    for m in re.findall(r"trio\d\d\d", line, re.IGNORECASE):
                        # pyright types m as `Any` (as it is in typeshed)
                        # mypy types it as Optional[Match[str]]
                        # but afaict it should be something like str|Tuple[str,...]
                        # depending on whether there's a group in the pattern or not.
                        # (or bytes, if both inputs are bytes)
                        documented_errors["eval_files"].add(cast("str", m))
                    break

    for errset in documented_errors.values():
        errset.difference_update(
            [c for c in errset if re.fullmatch(IGNORED_CODES_REGEX, c)]
        )

    unique_errors: dict[str, set[str]] = {}
    missing_errors: dict[str, set[str]] = {}
    for key, codes in documented_errors.items():
        unique_errors[key] = codes.copy()
        missing_errors[key] = set()

        for other_key, other_codes in documented_errors.items():
            if key == other_key:
                continue
            unique_errors[key].difference_update(other_codes)
            missing_errors[key].update(other_codes - codes)

    assert unique_errors == missing_errors
