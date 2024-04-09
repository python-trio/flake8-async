# AUTOFIX
# NOASYNCIO - does not trigger on ASYNC100
# ARG --enable=ASYNC100,ASYNC911,ASYNC910
from typing import Any

import trio


def foo() -> bool:
    return False


# fmt: off
async def foo_no_noqa():
    with trio.fail_after(5):  # ASYNC100: 9, 'trio', 'fail_after'
        if foo():
            return  # ASYNC910: 12, "return", Statement("function definition", lineno-3)
    await trio.lowlevel.checkpoint()


async def foo_noqa_bare():
    with trio.fail_after(5):  # noqa
        if foo():
            return  # noqa
    await trio.lowlevel.checkpoint()


async def foo_noqa_100():
    with trio.fail_after(5):  # noqa: ASYNC100
        if foo():
            return  # ASYNC910: 12, "return", Statement("function definition", lineno-3)
    await trio.lowlevel.checkpoint()


async def foo_noqa_911():
    with trio.fail_after(5):  # ASYNC100: 9, 'trio', 'fail_after'
        if foo():
            return  # noqa: ASYNC910
    await trio.lowlevel.checkpoint()


async def foo_noqa_100_911():
    with trio.fail_after(5):  # noqa: ASYNC100, ASYNC911
        if foo():
            return  # noqa: ASYNC910
    await trio.lowlevel.checkpoint()


async def foo_noqa_100_911_500():
    with trio.fail_after(5):  # noqa: ASYNC100, ASYNC911 , ASYNC500,,,
        if foo():
            return  # noqa: ASYNC100, ASYNC910 , ASYNC500,,,
    await trio.lowlevel.checkpoint()
# fmt: on

# check that noqas work after line numbers have been modified in a different visitor

# this will remove one line
with trio.fail_after(5):  # ASYNC100: 5, 'trio', 'fail_after'
    ...


async def foo_changed_lineno():
    yield  # noqa: ASYNC911
    await trio.lowlevel.checkpoint()


# this will add two lines
async def foo_changing_lineno():  # ASYNC911: 0, "exit", Statement("yield", lineno+1)
    yield  # ASYNC911: 4, "yield", Statement("function definition", lineno-1)


with trio.fail_after(5):  # noqa: ASYNC100
    ...
