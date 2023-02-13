# type: ignore
# ARG --enable-visitor-codes-regex=(TRIO230)|(TRIO231)
import io
import os

import trio


async def foo():
    open("")  # TRIO230: 4, 'open', "trio"
    io.open_code("")  # TRIO230: 4, 'io.open_code', "trio"
    os.fdopen(0)  # TRIO231: 4, 'os.fdopen', "trio"

    # sync call is awaited, so it can't be sync
    await open("")

    # wrapped calls are always okay
    await trio.wrap_file(open(""))
    await trio.wrap_file(os.fdopen(0))

    # with uses the same code & logic
    with os.fdopen(0):  # TRIO231: 9, 'os.fdopen', "trio"
        ...
    with open(""):  # TRIO230: 9, 'open', "trio"
        ...
    with open("") as f:  # TRIO230: 9, 'open', "trio"
        ...
    with foo(), open(""):  # TRIO230: 16, 'open', "trio"
        ...
    async with open(""):  # TRIO230: 15, 'open', "trio"
        ...
    async with trio.wrap_file(open("")):
        ...

    # test io.open
    # pyupgrade removes the unnecessary `io.`
    # https://github.com/asottile/pyupgrade#open-alias
    # and afaict neither respects fmt:off nor #noqa - so I don't know how to test it
    open("")  # TRIO230: 4, 'open', "trio"


def foo_sync():
    open("")
