"""Tests for flake8-trio package metadata."""
import re
import unittest
from pathlib import Path
from typing import Dict, Iterable, NamedTuple, Set

import flake8_trio


class Version(NamedTuple):
    year: int
    month: int
    patch: int

    @classmethod
    def from_string(cls, string):
        return cls(*map(int, string.split(".")))


def get_releases() -> Iterable[Version]:
    valid_pattern = re.compile(r"^## (\d\d\.\d?\d\.\d?\d)$")
    with open(Path(__file__).parent.parent / "CHANGELOG.md") as f:
        lines = f.readlines()
    for aline in lines:
        version_match = valid_pattern.match(aline)
        if version_match:
            yield Version.from_string(version_match.group(1))


def test_last_release_against_changelog():
    """Ensure we have the latest version covered in CHANGELOG.md"""
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


class test_messages_documented(unittest.TestCase):
    def runTest(self):
        documented_errors: Dict[str, Set[str]] = {}
        for filename in (
            "CHANGELOG.md",
            "README.md",
            "flake8_trio.py",
            "tests/test_flake8_trio.py",
        ):
            with open(Path(__file__).parent.parent / filename) as f:
                lines = f.readlines()
            documented_errors[filename] = set()
            for line in lines:
                for error_msg in re.findall(r"TRIO\d\d\d", line):
                    documented_errors[filename].add(error_msg)

        file_items = list(documented_errors.items())
        first = file_items.pop()
        for file, documented in file_items:
            self.assertSetEqual(first[1], documented, msg=(first[0], file))
