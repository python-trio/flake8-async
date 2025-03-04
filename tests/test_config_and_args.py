"""Various tests for testing argument and config parsing."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from flake8_async import Plugin, main

from .test_flake8_async import initialize_options

try:
    import flake8
except ImportError:
    flake8 = None  # type: ignore[assignment]

EXAMPLE_PY_TEXT = """import trio
with trio.move_on_after(10):
    ...
"""
EXAMPLE_PY_AUTOFIXED_TEXT = "import trio\n...\n"
EXAMPLE_PY_ERROR = (
    "./example.py:2:6: ASYNC100 trio.move_on_after context contains no checkpoints,"
    " remove the context or add `await trio.lowlevel.checkpoint()`.\n"
)


def write_examplepy(tmp_path: Path, text: str = EXAMPLE_PY_TEXT) -> None:
    assert tmp_path.joinpath("example.py").write_text(text)


def assert_autofixed(tmp_path: Path, text: str = EXAMPLE_PY_AUTOFIXED_TEXT) -> None:
    assert tmp_path.joinpath("example.py").read_text() == text


def assert_unchanged(tmp_path: Path, text: str = EXAMPLE_PY_TEXT) -> None:
    assert tmp_path.joinpath("example.py").read_text() == text


def monkeypatch_argv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    argv: list[Path | str] | None = None,
) -> None:
    if argv is None:
        argv = [tmp_path / "flake8-async", "./example.py"]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", argv)


def test_run_flake8_async(tmp_path: Path):
    write_examplepy(tmp_path)
    res = subprocess.run(
        [
            "flake8-async",
            "./example.py",
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert res.returncode == 1
    assert not res.stderr
    assert res.stdout == EXAMPLE_PY_ERROR.encode("ascii")


def test_systemexit_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch_argv(monkeypatch, tmp_path)

    tmp_path.joinpath("example.py").write_text("")

    with pytest.raises(SystemExit) as exc_info:
        from flake8_async import __main__  # noqa: F401

    assert exc_info.value.code == 0
    out, err = capsys.readouterr()
    assert not out
    assert not err


def test_systemexit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    write_examplepy(tmp_path)
    monkeypatch_argv(monkeypatch, tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        from flake8_async import __main__  # noqa: F401

    assert exc_info.value.code == 1
    out, err = capsys.readouterr()
    assert out == EXAMPLE_PY_ERROR
    assert not err


def test_run_in_git_repo(tmp_path: Path):
    write_examplepy(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "add", "example.py"], cwd=tmp_path, check=True)
    res = subprocess.run(
        [
            "flake8-async",
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert res.returncode == 1
    assert not res.stderr
    assert res.stdout == EXAMPLE_PY_ERROR.encode("ascii")


def test_run_no_git_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch_argv(monkeypatch, tmp_path, [tmp_path / "flake8-async"])
    assert main() == 1
    out, err = capsys.readouterr()
    assert err == "Doesn't seem to be a git repo; pass filenames to format.\n"
    assert not out


def test_run_100_autofix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    write_examplepy(tmp_path)
    monkeypatch_argv(
        monkeypatch,
        tmp_path,
        [tmp_path / "flake8-async", "--autofix=ASYNC", "./example.py"],
    )
    assert main() == 1

    out, err = capsys.readouterr()
    assert out == EXAMPLE_PY_ERROR
    assert not err
    assert_autofixed(tmp_path)


def test_114_raises_on_invalid_parameter(capsys: pytest.CaptureFixture[str]):
    plugin = Plugin(ast.AST(), [])
    # argparse will reraise ArgumentTypeError as SystemExit
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
            initialize_options(plugin, args=[f"--async200-blocking-calls={arg}"])
        out, err = capsys.readouterr()
        assert not out, out
        assert all(word in err for word in (str(i), arg, "->"))


@pytest.mark.skipif(flake8 is None, reason="flake8 is not installed")
def test_anyio_from_config(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    assert tmp_path.joinpath(".flake8").write_text(
        """
[flake8]
anyio = True
select = ASYNC220
"""
    )

    from flake8_async.visitors.visitor2xx import Visitor22X

    err_msg = Visitor22X.error_codes["ASYNC220"].format(
        "subprocess.Popen",
        "[anyio/trio]",
    )
    err_file = Path(__file__).parent / "eval_files" / "anyio_trio.py"

    # find the line with the expected error
    for lineno, line in enumerate(  # noqa: B007 # lineno not used in loop body
        err_file.read_text().split("\n"), start=1
    ):
        if "# ASYNC220: " in line:
            break
    else:
        raise AssertionError("could not find error in file")

    # construct the full error message
    expected = f"{err_file}:{lineno}:5: ASYNC220 {err_msg}\n"
    from flake8.main.cli import main

    returnvalue = main(
        argv=[
            str(err_file),
            "--config",
            str(tmp_path / ".flake8"),
        ]
    )
    out, err = capsys.readouterr()
    assert not err
    assert expected == out
    assert returnvalue == 1


# `code` parameter temporarily introduced to test deprecation of trio200-blocking-calls
def _test_async200_from_config_common(tmp_path: Path, code: str = "async200") -> str:
    assert tmp_path.joinpath(".flake8").write_text(
        f"""
[flake8]
{code}-blocking-calls =
  other -> async,
  sync_fns.* -> the_async_equivalent,
select = ASYNC200
extend-ignore = E
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
        "./example.py:5:5: ASYNC200 User-configured blocking sync call sync_fns.* "
        "in async function, consider replacing with the_async_equivalent.\n"
    )


@pytest.mark.skipif(flake8 is None, reason="flake8 is not installed")
def test_200_from_config_flake8_internals(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    # abuse flake8 internals to avoid having to use subprocess
    # which breaks breakpoints and hinders debugging
    # TODO: fixture (?) to change working directory

    EXAMPLE_PY_TEXT = _test_async200_from_config_common(tmp_path)
    # replace ./ with tmp_path/
    err_msg = str(tmp_path) + EXAMPLE_PY_TEXT[1:]

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


@pytest.mark.skipif(flake8 is None, reason="flake8 is not installed")
def test_200_from_config_subprocess(tmp_path: Path):
    err_msg = _test_async200_from_config_common(tmp_path)
    res = subprocess.run(["flake8"], cwd=tmp_path, capture_output=True, check=False)
    assert res.returncode == 1
    assert not res.stderr
    assert res.stdout == err_msg.encode("ascii")


@pytest.mark.skipif(flake8 is None, reason="flake8 is not installed")
def test_async200_from_config_subprocess(tmp_path: Path):
    err_msg = _test_async200_from_config_common(tmp_path, code="trio200")
    res = subprocess.run(["flake8"], cwd=tmp_path, capture_output=True, check=False)
    assert res.returncode == 1
    assert res.stderr.endswith(
        b"UserWarning: trio200-blocking-calls has been deprecated in favor of "
        b"async200-blocking-calls\n  warnings.warn(\n"
    )
    assert res.stdout == err_msg.encode("ascii")


def test_trio200_warning(tmp_path: Path):
    fpath = tmp_path / "foo.py"
    fpath.touch()
    res = subprocess.run(
        ["flake8-async", "--trio200-blocking-calls=foo->bar", "foo.py"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        encoding="utf8",
    )
    assert res.returncode == 0
    assert res.stderr.endswith(
        "UserWarning: trio200-blocking-calls has been deprecated in favor of "
        "async200-blocking-calls\n  warnings.warn(\n"
    )
    assert not res.stdout


@pytest.mark.skipif(flake8 is None, reason="flake8 is not installed")
def test_async200_from_config_subprocess_cli_ignore(tmp_path: Path):
    _ = _test_async200_from_config_common(tmp_path)
    res = subprocess.run(
        ["flake8", "--ignore=ASYNC200"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        encoding="utf8",
    )
    assert not res.stderr
    assert not res.stdout
    assert res.returncode == 0


def test_900_default_off():
    res = subprocess.run(
        ["flake8-async", "tests/eval_files/async900.py"],
        capture_output=True,
        check=False,
        encoding="utf8",
    )
    assert res.returncode == 1
    assert not res.stderr
    assert "ASYNC124" in res.stdout
    assert "ASYNC900" not in res.stdout


@pytest.mark.skipif(flake8 is None, reason="flake8 is not installed")
def test_900_default_off_flake8(capsys: pytest.CaptureFixture[str]):
    from flake8.main.cli import main

    returnvalue = main(
        argv=[
            "tests/eval_files/async900.py",
        ]
    )
    out, err = capsys.readouterr()
    assert returnvalue == 1
    assert not err
    assert "E501" in out
    assert "ASYNC900" not in out


def test_910_can_be_selected(tmp_path: Path):
    """Check if flake8 allows us to --select our 5-letter code.

    But we can run with --enable regardless.
    """
    myfile = tmp_path.joinpath("foo.py")
    myfile.write_text("""async def foo():\n    print()""")

    binary = "flake8-async" if flake8 is None else "flake8"
    select_enable = "enable" if flake8 is None else "select"

    res = subprocess.run(
        [binary, f"--{select_enable}=ASYNC910", "foo.py"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        encoding="utf8",
    )

    assert not res.stderr
    assert res.stdout == (
        "foo.py:1:1: ASYNC910 exit from async function with no guaranteed"
        " checkpoint or exception since function definition on line 1.\n"
    )
    assert res.returncode == 1


def test_enable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    write_examplepy(tmp_path)

    argv: list[Path | str] = [tmp_path / "flake8-async", "./example.py"]
    monkeypatch_argv(monkeypatch, tmp_path, argv)

    def _helper(*args: str, error: bool = False, autofix: bool = False) -> None:
        argv.extend(args)
        main()
        out, err = capsys.readouterr()
        if error:
            assert out == EXAMPLE_PY_ERROR
        else:
            assert not out
        if autofix:
            assert_autofixed(tmp_path)
            write_examplepy(tmp_path)
        else:
            assert_unchanged(tmp_path)
        assert not err
        for _ in args:
            argv.pop()

    # default enable
    _helper(error=True)

    # explicit enable
    _helper("--enable=ASYNC100", error=True)

    # explicit enable other
    _helper("--enable=ASYNC101")

    # make sure commas don't enable others
    _helper("--enable=ASYNC101,")
    _helper("--enable=,")
    _helper("--enable=ASYNC101,,ASYNC102")

    # disable
    _helper("--disable=ASYNC100")

    # disable enabled code
    _helper("--disable=ASYNC100", "--enable=ASYNC100")

    # don't enable, but autofix
    _helper(
        "--enable=''",
        "--autofix=ASYNC100",
        error=True,  # TODO: should be False
        autofix=True,
    )

    _helper(
        "--enable=''",
        "--autofix=ASYNC100",
        "--error-on-autofix",
        error=True,
        autofix=True,
    )


@pytest.mark.skipif(flake8 is None, reason="flake8 is not installed")
def test_flake8_plugin_with_autofix_fails(tmp_path: Path):
    write_examplepy(tmp_path)
    res = subprocess.run(
        [
            "flake8",
            "./example.py",
            "--autofix=ASYNC",
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert res.returncode == 1
    assert not res.stdout
    assert res.stderr == b"Cannot autofix when run as a flake8 plugin.\n"


NOQA_TEXT = """import trio
with trio.move_on_after(10): ... # noqa
"""
NOQA_TEXT_AST = """import trio as foo # noqa"""


def test_noqa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    write_examplepy(tmp_path, text=NOQA_TEXT)
    monkeypatch_argv(monkeypatch, tmp_path)
    assert main() == 0


def test_disable_noqa_cst(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    write_examplepy(tmp_path, text=NOQA_TEXT)
    monkeypatch_argv(
        monkeypatch,
        tmp_path,
        [tmp_path / "flake8-async", "./example.py", "--disable-noqa"],
    )
    assert main() == 1
    out, err = capsys.readouterr()
    assert not err
    assert (
        out == "./example.py:2:6: ASYNC100 trio.move_on_after context contains no"
        " checkpoints, remove the context or add `await"
        " trio.lowlevel.checkpoint()`.\n"
    )


def test_disable_noqa_ast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    write_examplepy(tmp_path, text=NOQA_TEXT_AST)
    monkeypatch_argv(
        monkeypatch,
        tmp_path,
        [tmp_path / "flake8-async", "./example.py", "--disable-noqa"],
    )
    assert main() == 1
    out, err = capsys.readouterr()
    assert not err
    assert (
        out
        == "./example.py:1:1: ASYNC106 trio must be imported with `import trio` for the"
        " linter to work.\n"
    )


@pytest.mark.skipif(flake8 is None, reason="flake8 is not installed")
def test_config_select_error_code(tmp_path: Path) -> None:
    # this ... seems to work? I'm confused
    assert tmp_path.joinpath(".flake8").write_text(
        """
[flake8]
select = ASYNC100
extend-select = ASYNC100
"""
    )
    res = subprocess.run(
        ["flake8", "--help"], cwd=tmp_path, capture_output=True, check=False
    )
    assert not res.stderr
    assert res.returncode == 0


# flake8>=6 enforces three-letter error codes in config
@pytest.mark.skipif(flake8 is None, reason="flake8 is not installed")
def test_config_ignore_error_code(tmp_path: Path) -> None:
    assert tmp_path.joinpath(".flake8").write_text(
        """
[flake8]
ignore = ASYNC100
"""
    )
    res = subprocess.run(
        ["flake8", "--help"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        encoding="utf8",
    )
    assert (
        "Error code 'ASYNC100' supplied to 'ignore' option does not match" in res.stderr
    )
    assert res.returncode == 1


# flake8>=6 enforces three-letter error codes in config
@pytest.mark.skipif(flake8 is None, reason="flake8 is not installed")
def test_config_extend_ignore_error_code(tmp_path: Path) -> None:
    assert tmp_path.joinpath(".flake8").write_text(
        """
[flake8]
extend-ignore = ASYNC100
"""
    )
    res = subprocess.run(
        ["flake8", "--help"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        encoding="utf8",
    )
    assert (
        "Error code 'ASYNC100' supplied to 'extend-ignore' option does not match"
        in res.stderr
    )
    assert res.returncode == 1


@pytest.mark.skipif(flake8 is None, reason="flake8 is not installed")
# but make sure we can disable selected codes
def test_config_disable_error_code(tmp_path: Path) -> None:
    # select ASYNC200 and create file that induces ASYNC200
    _test_async200_from_config_common(tmp_path)
    # disable ASYNC200
    with open(tmp_path.joinpath(".flake8"), "a", encoding="utf-8") as file:
        file.write("disable = ASYNC200")

    # it now returns no errors
    res = subprocess.run(["flake8"], cwd=tmp_path, capture_output=True, check=True)
    assert not res.stdout
    assert not res.stderr
    assert res.returncode == 0
