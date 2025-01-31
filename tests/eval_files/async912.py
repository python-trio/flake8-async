# ASYNCIO_NO_ERROR
# ARG --enable=ASYNC100,ASYNC912
# asyncio is tested in async912_asyncio. Cancelscopes in anyio are named the same
# as in trio, so they're also tested with this file.

# ASYNC100 has autofixes, but ASYNC912 does not. This leaves us with the option
# of not testing both in the same file, or running with NOAUTOFIX.
# NOAUTOFIX

import contextlib
from typing import TypeVar

import trio


def bar() -> bool:
    return False


async def foo():
    # trivial cases where there is absolutely no `await` only triggers ASYNC100
    with trio.move_on_after(0.1):  # ASYNC100: 9, "trio", "move_on_after"
        ...
    with trio.move_on_at(0.1):  # ASYNC100: 9, "trio", "move_on_at"
        ...
    with trio.fail_after(0.1):  # ASYNC100: 9, "trio", "fail_after"
        ...
    with trio.fail_at(0.1):  # ASYNC100: 9, "trio", "fail_at"
        ...
    with trio.CancelScope(0.1):  # ASYNC100: 9, "trio", "CancelScope"
        ...

    # conditional cases trigger ASYNC912
    with trio.move_on_after(0.1):  # ASYNC912: 9
        if bar():
            await trio.lowlevel.checkpoint()
    with trio.move_on_at(0.1):  # ASYNC912: 9
        while bar():
            await trio.lowlevel.checkpoint()
    with trio.fail_after(0.1):  # ASYNC912: 9
        try:
            await trio.lowlevel.checkpoint()
        except:
            ...
    with trio.fail_at(0.1):  # ASYNC912: 9
        if bar():
            await trio.lowlevel.checkpoint()
    with trio.CancelScope(0.1):  # ASYNC912: 9
        if bar():
            await trio.lowlevel.checkpoint()
    # ASYNC912 generally shares the same logic as other 91x codes, check respective
    # eval files for more comprehensive tests.

    # check we don't trigger on all context managers
    with open(""):
        ...

    # don't error with guaranteed checkpoint
    with trio.move_on_after(0.1):
        await trio.lowlevel.checkpoint()
    with trio.move_on_after(0.1):
        if bar():
            await trio.lowlevel.checkpoint()
        else:
            await trio.lowlevel.checkpoint()

    # both scopes error in nested cases
    with trio.move_on_after(0.1):  # ASYNC912: 9
        with trio.move_on_after(0.1):  # ASYNC912: 13
            if bar():
                await trio.lowlevel.checkpoint()

    # We don't know which cancelscope will trigger first, so to avoid false
    # alarms on tricky-but-valid cases we don't raise any error for the outer one.
    with trio.move_on_after(0.1):
        with trio.move_on_after(0.1):
            await trio.lowlevel.checkpoint()

    with trio.move_on_after(0.1):
        await trio.lowlevel.checkpoint()
        with trio.move_on_after(0.1):
            await trio.lowlevel.checkpoint()

    with trio.move_on_after(0.1):
        with trio.move_on_after(0.1):
            await trio.lowlevel.checkpoint()
        await trio.lowlevel.checkpoint()

    # check correct line gives error
    # fmt: off
    with (
            # a
            # b
            trio.move_on_after(0.1)  # ASYNC912: 12
            # c
            ):
        if bar():
            await trio.lowlevel.checkpoint()

    with (
            open(""),
            trio.move_on_at(5),  # ASYNC912: 12
            open(""),
            ):
        if bar():
            await trio.lowlevel.checkpoint()
    # fmt: on

    # error on each call with multiple matching calls in the same with
    with (
        trio.move_on_after(0.1),  # ASYNC912: 8
        trio.fail_at(5),  # ASYNC912: 8
    ):
        if bar():
            await trio.lowlevel.checkpoint()

    # wrapped calls do not raise errors
    T = TypeVar("T")

    def customWrapper(a: T) -> T:
        return a

    with customWrapper(trio.fail_at(10)):
        ...
    with (res := trio.fail_at(10)):
        ...
    # but saving with `as` does
    with trio.fail_at(10) as res2:  # ASYNC912: 9
        if bar():
            await trio.lowlevel.checkpoint()


# This is handled by ASYNC913, which will raise an error about the loop.
async def livelocks():
    with trio.move_on_after(0.1):  # should error
        while True:
            try:
                await trio.sleep("1")  # type: ignore
            except TypeError:
                pass


def condition() -> bool:
    return True


async def livelocks_2():
    with trio.move_on_after(0.1):  # ASYNC912: 9
        while condition():
            try:
                await trio.sleep("1")  # type: ignore
            except TypeError:
                pass


# TODO: no-guaranteed-checkpoint-in-infinite-loop
# https://github.com/python-trio/flake8-async/issues/240
async def livelocks_3():
    with trio.move_on_after(0.1):  # should error
        while True:
            with contextlib.suppress(TypeError):
                await trio.sleep("1")  # type: ignore


async def livelocks_4():
    with trio.move_on_after(0.1):  # ASYNC912: 9
        while condition():
            with contextlib.suppress(TypeError):
                await trio.sleep("1")  # type: ignore


# raises an error...?
with trio.move_on_after(10):  # ASYNC100: 5, "trio", "move_on_after"
    ...


# completely sync function ... is this something we care about?
def sync_func():
    with trio.move_on_after(10):
        ...


async def check_yield_logic():
    # Does not raise any of async100 or async912, as the yield is treated
    # as a checkpoint because the parent context may checkpoint.
    with trio.move_on_after(1):
        yield
    with trio.move_on_after(1):
        if bar():
            await trio.lowlevel.checkpoint()
        yield


async def nursery_no_cancel_point():
    with trio.move_on_after(10):  # ASYNC912: 9
        async with trio.open_nursery():
            if bar():
                await trio.lowlevel.checkpoint()
