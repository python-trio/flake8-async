# type: ignore
# ARG --enable=ASYNC230,ASYNC231
# NOTRIO # see async23x.py
# NOANYIO # see async23x.py
# BASE_LIBRARY asyncio
import io
import os

import asyncio


async def foo():
    open("")  # ASYNC230_asyncio: 4, 'open'
    io.open_code("")  # ASYNC230_asyncio: 4, 'io.open_code'
    os.fdopen(0)  # ASYNC231_asyncio: 4, 'os.fdopen'

    # sync call is awaited, so it can't be sync
    await open("")

    # asyncio.wrap_file does not exist, so check that it doesn't trigger the
    # protection that e.g. `trio.wrap_file` would give.
    # In theory we could support detecting equivalent `wrap_file`s from other libraries
    await asyncio.wrap_file(open(""))  # ASYNC230_asyncio: 28, 'open'
    await asyncio.wrap_file(os.fdopen(0))  # ASYNC231_asyncio: 28, 'os.fdopen'

    # with uses the same code & logic
    with os.fdopen(0):  # ASYNC231_asyncio: 9, 'os.fdopen'
        ...
    with open(""):  # ASYNC230_asyncio: 9, 'open'
        ...
    with open("") as f:  # ASYNC230_asyncio: 9, 'open'
        ...
    with foo(), open(""):  # ASYNC230_asyncio: 16, 'open'
        ...
    async with open(""):  # ASYNC230_asyncio: 15, 'open'
        ...
    async with asyncio.wrap_file(open("")):  # ASYNC230_asyncio: 33, 'open'
        ...

    # test io.open
    # pyupgrade removes the unnecessary `io.`
    # https://github.com/asottile/pyupgrade#open-alias
    # and afaict neither respects fmt:off nor #noqa - so I don't know how to test it
    open("")  # ASYNC230_asyncio: 4, 'open'


def foo_sync():
    open("")
