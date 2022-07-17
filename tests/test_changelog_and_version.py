"""Tests for flake8-trio package metadata."""
import re
from pathlib import Path
from typing import NamedTuple, Optional

import flake8_trio


class Version(NamedTuple):
    year: int
    month: int
    day: int

    @classmethod
    def from_string(cls, string):
        return cls(*map(int, string.split(".")))


def get_latest_release() -> Optional[Version]:
    valid_pattern = re.compile(r"^## (\d\d\.\d?\d\.\d?\d)$")
    with open(Path(__file__).parent.parent / "CHANGELOG.md") as f:
        for aline in f.readlines():
            version_match = valid_pattern.match(aline)
            if version_match:
                return Version.from_string(version_match.group(1))

    return None


def test_last_release_against_changelog():
    """Ensure we have the latest version covered in CHANGELOG.md"""
    assert get_latest_release() == Version.from_string(flake8_trio.__version__)
