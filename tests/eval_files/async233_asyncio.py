# ARG --enable=ASYNC233
# NOTRIO # see async233.py
# NOANYIO # see async233.py
# BASE_LIBRARY asyncio
from pathlib import Path


async def foo(path: Path):
    path.read_text()  # ASYNC233_asyncio: 4, 'path.read_text'
    Path("foo").write_text("content")  # ASYNC233_asyncio: 4, "Path('foo').write_text"


def foo_sync(path: Path):
    path.read_text()
