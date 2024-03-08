# type: ignore
# ARG --enable=ASYNC230,ASYNC231
# NOASYNCIO # see async23x_asyncio.py
import io
import os

import trio


async def foo():
    open("")  # ASYNC230: 4, 'open', "trio"
    io.open_code("")  # ASYNC230: 4, 'io.open_code', "trio"
    os.fdopen(0)  # ASYNC231: 4, 'os.fdopen', "trio"

    # sync call is awaited, so it can't be sync
    await open("")

    # wrapped calls are always okay
    await trio.wrap_file(open(""))
    await trio.wrap_file(os.fdopen(0))

    # with uses the same code & logic
    with os.fdopen(0):  # ASYNC231: 9, 'os.fdopen', "trio"
        ...
    with open(""):  # ASYNC230: 9, 'open', "trio"
        ...
    with open("") as f:  # ASYNC230: 9, 'open', "trio"
        ...
    with foo(), open(""):  # ASYNC230: 16, 'open', "trio"
        ...
    async with open(""):  # ASYNC230: 15, 'open', "trio"
        ...
    async with trio.wrap_file(open("")):
        ...

    # test io.open
    # pyupgrade removes the unnecessary `io.`
    # https://github.com/asottile/pyupgrade#open-alias
    # and afaict neither respects fmt:off nor #noqa - so I don't know how to test it
    open("")  # ASYNC230: 4, 'open', "trio"


def foo_sync():
    open("")
