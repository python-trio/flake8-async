"""Various tests for testing argument and config parsing."""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from flake8_trio import Plugin

from .test_flake8_trio import initialize_options


def _common_error_setup(tmp_path: Path) -> str:
    assert tmp_path.joinpath("example.py").write_text(
        """import trio
with trio.move_on_after(10):
    ...
"""
    )
    return (
        "./example.py:2:6: TRIO100 trio.move_on_after context contains no checkpoints,"
        " remove the context or add `await trio.lowlevel.checkpoint()`.\n"
    )


def test_run_flake8_trio(tmp_path: Path):
    err_msg = _common_error_setup(tmp_path)
    res = subprocess.run(
        [
            "flake8_trio",
            "./example.py",
        ],
        cwd=tmp_path,
        capture_output=True,
    )
    assert not res.stderr
    assert res.stdout == err_msg.encode("ascii")


def test_run_in_git_repo(tmp_path: Path):
    err_msg = _common_error_setup(tmp_path)
    assert subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    assert subprocess.run(["git", "add", "example.py"], cwd=tmp_path)
    res = subprocess.run(
        [
            "flake8_trio",
        ],
        cwd=tmp_path,
        capture_output=True,
    )
    assert not res.stderr
    assert res.stdout == err_msg.encode("ascii")


def test_run_no_git_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", [tmp_path / "flake8_trio"])
    with pytest.raises(SystemExit):
        from flake8_trio import __main__  # noqa
    out, err = capsys.readouterr()
    assert err == "Doesn't seem to be a git repo; pass filenames to format.\n"
    assert not out


def test_run_100_autofix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    err_msg = _common_error_setup(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv", [tmp_path / "flake8_trio", "--autofix", "./example.py"]
    )
    from flake8_trio import __main__  # noqa

    out, err = capsys.readouterr()
    assert out == err_msg
    assert not err
    assert tmp_path.joinpath("example.py").read_text() == "import trio\n...\n"


def test_114_raises_on_invalid_parameter(capsys: pytest.CaptureFixture[str]):
    plugin = Plugin(ast.AST(), [])
    # flake8 will reraise ArgumentError as SystemExit
    for arg in "blah.foo", "foo*", "*":
        with pytest.raises(SystemExit):
            initialize_options(plugin, args=[f"--startable-in-context-manager={arg}"])
        out, err = capsys.readouterr()
        assert not out
        assert f"{arg!r} is not a valid method identifier" in err


def test_200_options(capsys: pytest.CaptureFixture[str]):
    plugin = Plugin(ast.AST(), [])
    for i, arg in (0, "foo"), (2, "foo->->bar"), (2, "foo->bar->fee"):
        with pytest.raises(SystemExit):
            initialize_options(plugin, args=[f"--trio200-blocking-calls={arg}"])
        out, err = capsys.readouterr()
        assert not out, out
        assert all(word in err for word in (str(i), arg, "->"))


def test_anyio_from_config(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    assert tmp_path.joinpath(".flake8").write_text(
        """
[flake8]
anyio = True
select = TRIO220
"""
    )

    from flake8_trio.visitors.visitor2xx import Visitor22X

    err_msg = Visitor22X.error_codes["TRIO220"].format(
        "subprocess.Popen",
        "[anyio|trio]",
    )
    err_file = str(Path(__file__).parent / "eval_files" / "anyio_trio.py")
    expected = f"{err_file}:10:5: TRIO220 {err_msg}\n"
    from flake8.main.cli import main

    returnvalue = main(
        argv=[
            err_file,
            "--config",
            str(tmp_path / ".flake8"),
        ]
    )
    out, err = capsys.readouterr()
    assert not err
    assert expected == out
    assert returnvalue == 1


def _test_trio200_from_config_common(tmp_path: Path) -> str:
    assert tmp_path.joinpath(".flake8").write_text(
        """
[flake8]
trio200-blocking-calls =
  other -> async,
  sync_fns.* -> the_async_equivalent,
select = TRIO200
"""
    )
    assert tmp_path.joinpath("example.py").write_text(
        """
import sync_fns

async def foo():
    sync_fns.takes_a_long_time()
"""
    )
    return (
        "./example.py:5:5: TRIO200 User-configured blocking sync call sync_fns.* "
        "in async function, consider replacing with the_async_equivalent.\n"
    )


def test_200_from_config_flake8_internals(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    # abuse flake8 internals to avoid having to use subprocess
    # which breaks breakpoints and hinders debugging
    # TODO: fixture (?) to change working directory

    err_msg = _test_trio200_from_config_common(tmp_path)
    # replace ./ with tmp_path/
    err_msg = str(tmp_path) + err_msg[1:]

    from flake8.main.cli import main

    returnvalue = main(
        argv=[
            str(tmp_path / "example.py"),
            "--append-config",
            str(tmp_path / ".flake8"),
        ]
    )
    out, err = capsys.readouterr()
    assert returnvalue == 1
    assert not err
    assert err_msg == out


def test_200_from_config_subprocess(tmp_path: Path):
    err_msg = _test_trio200_from_config_common(tmp_path)
    res = subprocess.run(["flake8"], cwd=tmp_path, capture_output=True)
    assert not res.stderr
    assert res.stdout == err_msg.encode("ascii")


def test_900_default_off(capsys: pytest.CaptureFixture[str]):
    from flake8.main.cli import main

    returnvalue = main(
        argv=[
            "tests/trio900.py",
        ]
    )
    out, err = capsys.readouterr()
    assert returnvalue == 1
    assert not err
    assert "TRIO900" not in out
