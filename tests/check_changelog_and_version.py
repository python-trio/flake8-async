#!/usr/bin/env python
"""Tests for flake8-async package metadata."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, TypeVar

from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Iterable

ROOT_PATH = Path(__file__).parent.parent
CHANGELOG = ROOT_PATH / "docs" / "changelog.rst"
USAGE = ROOT_PATH / "docs" / "usage.rst"
INIT_FILE = ROOT_PATH / "flake8_async" / "__init__.py"

ALLOW_FUTURE = "--allow-future-in-changelog" in sys.argv

T = TypeVar("T", bound="Version")


class Version(NamedTuple):
    year: int
    month: int
    patch: int

    @classmethod
    def from_string(cls, string: str) -> Self:
        return cls(*map(int, string.split(".")))

    def __str__(self) -> str:
        return ".".join(map(str, self))


for line in INIT_FILE.read_text().splitlines():
    if m := re.match(r'__version__ = "(\d*\.\d*\.\d*)"', line):
        VERSION = Version.from_string(m.groups()[0])
        break
else:
    raise RuntimeError("No version detected.")


def get_releases() -> Iterable[Version]:
    valid_pattern = re.compile(r"^(\d\d\.\d?\d\.\d?\d)$")
    header_pattern = re.compile(r"^=+$")
    last_line_was_date = False
    last_line: str | None = None
    with open(CHANGELOG, encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        version_match = valid_pattern.match(line)
        if last_line_was_date:
            assert header_pattern.match(line)
            last_line_was_date = False
        elif version_match:
            yield Version.from_string(version_match.group(1))
            last_line_was_date = True
        # only allow `Future\n=====` when run in pre-commit
        elif header_pattern.match(line):
            assert ALLOW_FUTURE, "FUTURE header with no --allow-future-in-changelog. "
            assert last_line is not None
            assert last_line.lower().strip() == "future"
        last_line = line


def test_last_release_against_changelog() -> None:
    """Ensure we have the latest version covered in 'changelog.rst'.

    If changelog version is greater, the __init__ gets bumped in update_version().
    """
    latest_release = next(iter(get_releases()))
    assert latest_release >= VERSION, f"{latest_release}, {VERSION}"


def test_version_increments_are_correct() -> None:
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


def ensure_tagged() -> None:
    from git.repo import Repo

    last_version = next(iter(get_releases()))
    repo = Repo(ROOT_PATH)
    if str(last_version) not in iter(map(str, repo.tags)):
        # create_tag is partially unknown in pyright, which kinda looks like
        # https://github.com/gitpython-developers/GitPython/issues/1473
        # which should be resolved?
        repo.create_tag(str(last_version))  # type: ignore
        repo.remotes.origin.push(str(last_version))


def update_version() -> None:
    # If we've added a new version to the changelog, update __version__ to match
    last_version = next(iter(get_releases()))
    if last_version != VERSION:
        INIT_FILE = ROOT_PATH / "flake8_async" / "__init__.py"
        subs = (f'__version__ = "{VERSION}"', f'__version__ = "{last_version}"')
        INIT_FILE.write_text(INIT_FILE.read_text().replace(*subs))
        print("updated VERSION in __init__.py")

    # Similarly, update the pre-commit config example in the README
    current = USAGE.read_text()
    wanted = re.sub(
        pattern=r"^     rev: (\d+\.\d+\.\d+)$",
        repl=f"     rev: {last_version}",
        string=current,
        flags=re.MULTILINE,
    )
    if last_version != VERSION:
        assert current != wanted, "version changed but regex didn't substitute"
    if current != wanted:
        USAGE.write_text(wanted)
        print("updated rev in pre-commit example")


if __name__ == "__main__":
    test_last_release_against_changelog()
    test_version_increments_are_correct()

    update_version()
    if "--ensure-tag" in sys.argv:
        ensure_tagged()
