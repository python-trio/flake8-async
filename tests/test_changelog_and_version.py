"""Tests for flake8-trio package metadata."""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import flake8_trio

from .test_flake8_trio import ERROR_CODES

if TYPE_CHECKING:
    from collections.abc import Iterable

root_path = Path(__file__).parent.parent


class Version(NamedTuple):
    year: int
    month: int
    patch: int

    @classmethod
    def from_string(cls, string):
        return cls(*map(int, string.split(".")))


def get_releases() -> Iterable[Version]:
    valid_pattern = re.compile(r"^## (\d\d\.\d?\d\.\d?\d)$")
    with open(root_path / "CHANGELOG.md", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        version_match = valid_pattern.match(line)
        if version_match:
            yield Version.from_string(version_match.group(1))


def test_last_release_against_changelog():
    """Ensure we have the latest version covered in 'CHANGELOG.md'."""
    latest_release, *_ = get_releases()
    assert latest_release == Version.from_string(flake8_trio.__version__)


def test_version_increments_are_correct():
    versions = list(get_releases())
    for prev, current in zip(versions[1:], versions):
        assert prev < current  # remember that `versions` is newest-first
        msg = f"{current=} does not follow {prev=}"
        # for CalVer, we either increment the patch version by one, or
        # increment the time-based parts and set the patch version to one.
        if current.patch == 1:
            assert prev[:2] < current[:2], msg
        else:
            assert current == prev._replace(patch=prev.patch + 1), msg


IGNORED_CODES_REGEX = r"TRIO107|TRIO108|TRIO\d\d\d_.*"


class test_messages_documented(unittest.TestCase):
    def runTest(self):
        documented_errors: dict[str, set[str]] = {}
        for filename in (
            "CHANGELOG.md",
            "README.md",
        ):
            with open(root_path / filename, encoding="utf-8") as f:
                lines = f.readlines()
            documented_errors[filename] = set()
            for line in lines:
                for error_msg in re.findall(r"TRIO\d\d\d", line):
                    documented_errors[filename].add(error_msg)

        documented_errors["flake8_trio.py"] = set(ERROR_CODES)
        # check files for @error_class

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
                    if line.startswith("# ARG --enable-visitor-codes-regex"):
                        for m in re.findall(r"trio\d\d\d", line, re.IGNORECASE):
                            # pyright types m as `Any` (as it is in typeshed)
                            # mypy types it as Optional[Match[str]]
                            # but afaict it should be something like str|Tuple[str,...]
                            # depending on whether there's a group in the pattern or not.
                            # (or bytes, if both inputs are bytes)
                            assert isinstance(m, str)
                            documented_errors["eval_files"].add(m)
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
