# ARG --enable=ASYNC233
# NOASYNCIO # see async233_asyncio.py
import pathlib
from pathlib import Path
from pathlib import PosixPath as UnixPath

import trio


async def foo(path: Path, other_path: pathlib.Path):
    path.open()  # ASYNC233: 4, 'path.open', "trio"
    path.read_text()  # ASYNC233: 4, 'path.read_text', "trio"
    path.read_bytes()  # ASYNC233: 4, 'path.read_bytes', "trio"
    path.write_text("content")  # ASYNC233: 4, 'path.write_text', "trio"
    path.write_bytes(b"content")  # ASYNC233: 4, 'path.write_bytes', "trio"
    path.touch()  # ASYNC233: 4, 'path.touch', "trio"

    other_path.read_text()  # ASYNC233: 4, 'other_path.read_text', "trio"
    Path("foo").read_text()  # ASYNC233: 4, "Path('foo').read_text", "trio"
    pathlib.Path(
        "foo"
    ).read_bytes()  # ASYNC233: 4, "pathlib.Path('foo').read_bytes", "trio"
    pathlib.Path.cwd().write_text(
        "content"
    )  # ASYNC233: 4, 'pathlib.Path.cwd().write_text', "trio"
    UnixPath("foo").touch()  # ASYNC233: 4, "UnixPath('foo').touch", "trio"

    assigned = Path("foo")
    assigned.write_bytes(b"content")  # ASYNC233: 4, 'assigned.write_bytes', "trio"

    await path.read_text()
    await trio.wrap_file(path.open())
    path.with_suffix(".txt")


def foo_sync(path: Path):
    path.read_text()
