#!/usr/bin/env python
"""Tests for flake8-async package metadata."""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, TypeVar

from git.repo import Repo
from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Iterable

ROOT_PATH = Path(__file__).parent.parent
CHANGELOG = ROOT_PATH / "docs" / "changelog.rst"
USAGE = ROOT_PATH / "docs" / "usage.rst"
INIT_FILE = ROOT_PATH / "flake8_async" / "__init__.py"

ALLOW_FUTURE = "--allow-future-in-changelog" in sys.argv

T = TypeVar("T", bound="Version")


def today() -> datetime.date:
    return datetime.datetime.now(tz=datetime.timezone.utc).date()


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


def test_latest_release_is_not_in_the_future() -> None:
    # With CalVer, a typo'd year or month gives a version that quietly sorts
    # after every correct release (https://github.com/python-trio/flake8-async/issues/469),
    # so the newest changelog entry may never be dated later than today.
    latest = next(iter(get_releases()))
    now = today()
    assert 1 <= latest.month <= 12, f"{latest} does not have a valid month"
    assert (latest.year + 2000, latest.month) <= (
        now.year,
        now.month,
    ), f"latest release {latest} is dated in the future (today is {now:%Y-%m})"


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


def check_version_info_is_in_sync() -> None:
    """Assert that all places stating a version agree, before release.

    In pre-commit, update_version() auto-fixes these instead; but at release
    time nothing may be patched up on the fly, or the built package would not
    match the repository contents.
    """
    latest = next(iter(get_releases()))
    assert (
        latest == VERSION
    ), f"changelog head is {latest}, but __version__ is {VERSION}"
    m = re.search(r"^     rev: (\d+\.\d+\.\d+)$", USAGE.read_text(), flags=re.MULTILINE)
    assert m is not None, "pre-commit example not found in usage.rst"
    assert m.group(1) == str(VERSION), (
        f"pre-commit example in usage.rst pins rev {m.group(1)}, "
        f"but __version__ is {VERSION}"
    )


def ensure_tagged() -> None:
    last_version = next(iter(get_releases()))
    repo = Repo(ROOT_PATH)
    # Local tags can be missing in a shallow CI checkout, so ask the remote.
    if repo.git.ls_remote("origin", f"refs/tags/{last_version}"):
        return
    if last_version.patch == 1:
        # A new year.month series must match the date it is released (patch
        # releases keep the year.month of their series, so aren't checked).
        # One month of slack covers a release PR merged just after month end.
        now = today()
        months_ago = (now.year - 2000 - last_version.year) * 12 + (
            now.month - last_version.month
        )
        assert 0 <= months_ago <= 1, (
            f"refusing to tag {last_version}: today is {now:%Y-%m}, and with"
            " CalVer the version should match the date of release"
        )
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
    test_latest_release_is_not_in_the_future()

    if "--ensure-tag" in sys.argv:
        check_version_info_is_in_sync()
        ensure_tagged()
    else:
        update_version()
