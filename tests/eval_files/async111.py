# type: ignore
# ASYNC111: Variable, from context manager opened inside nursery, passed to start[_soon] might be invalidly accessed while in use, due to context manager closing before the nursery. This is usually a bug, and nurseries should generally be the inner-most context manager.
# It's possible there's an equivalent asyncio construction/gotcha, but methods are differently named, so this file will not raise any errors
# nurseries are named taskgroups in asyncio/anyio
# ASYNCIO_NO_ERROR
from typing import Any

import trio
import trio as noterror

# shed/black breaks up a *ton* of lines since adding more detailed error messages, so
# disable formatting to avoid having to adjust a ton of line references
# fmt: off
async def foo():
    async with trio.open_nursery():
        ...

    # async nursery
    async with trio.open_nursery() as nursery:
        # async context manager
        async with trio.open_process() as bar:
            nursery.start(bar)  # error: 26, line-1, line-3, "bar", "start"
            nursery.start(foo=bar)  # error: 30, line-2, line-4, "bar", "start"
            nursery.start(..., ..., bar, ...)  # error: 36, line-3, line-5, "bar", "start"

            nursery.start_soon(bar)  # error: 31, line-5, line-7, "bar", "start_soon"

        # sync context manager
        with open("") as bar:
            nursery.start(bar)  # error: 26, line-1, line-11, "bar", "start"
            nursery.start(foo=bar)  # error: 30, line-2, line-12, "bar", "start"
            nursery.start(..., ..., bar, ...)  # error: 36, line-3, line-13, "bar", "start"

            nursery.start_soon(bar)  # error: 31, line-5, line-15, "bar", "start_soon"

    # sync nursery
    with trio.open_nursery() as nursery:
        # async context manager
        async with trio.open_process() as bar:
            nursery.start(bar)  # error: 26, line-1, line-3, "bar", "start"
            nursery.start(foo=bar)  # error: 30, line-2, line-4, "bar", "start"
            nursery.start(..., ..., bar, ...)  # error: 36, line-3, line-5, "bar", "start"

            nursery.start_soon(bar)  # error: 31, line-5, line-7, "bar", "start_soon"

        # sync context manager
        with open("") as bar:
            nursery.start(bar)  # error: 26, line-1, line-11, "bar", "start"
            nursery.start(foo=bar)  # error: 30, line-2, line-12, "bar", "start"
            nursery.start(..., ..., bar, ...)  # error: 36, line-3, line-13, "bar", "start"

            nursery.start_soon(bar)  # error: 31, line-5, line-15, "bar", "start_soon"

    # check all safe async/sync permutations
    async with trio.open_process() as bar:
        async with trio.open_nursery() as nursery:
            nursery.start(bar)  # safe
    async with trio.open_process() as bar:
        with trio.open_nursery() as nursery:
            nursery.start(bar)  # safe
    with trio.open_process() as bar:
        async with trio.open_nursery() as nursery:
            nursery.start(bar)  # safe
    with trio.open_process() as bar:
        with trio.open_nursery() as nursery:
            nursery.start(bar)  # safe

# reset variables on nested function
with trio.open_nursery() as nursery:
    def foo_1():
        nursery = noterror.something
        with trio.open_process() as bar_2:
            nursery.start(bar_2)  # safe

    async def foo_2():
        nursery = noterror.something
        async with trio.open_process() as bar_2:
            nursery.start(bar_2)  # safe

# specifically check for *trio*.open_nursery
with noterror.open_nursery() as nursery:
    with trio.open("") as bar:
        nursery.start(bar)

# specifically check for trio.*open_nursery*
with trio.open_nurse() as nursery:
    with trio.open("") as bar:
        nursery.start(bar)


bar_1: Any = ""
bar_2: Any = ""
nursery_2: Any = ""
with trio.open_nursery() as nursery_1:
    nursery_1.start(bar_1)
    nursery_1.start(bar_2)
    nursery_2.start(bar_1)
    nursery_2.start(bar_2)
    with trio.open_nursery() as nursery_2:
        nursery_1.start(bar_1)
        nursery_1.start(bar_2)
        nursery_2.start(bar_1)
        nursery_2.start(bar_2)
        with open("") as bar_1:
            nursery_1.start(bar_1)  # error: 28, line-1, line-11, "bar_1", "start"
            nursery_1.start(bar_2)
            nursery_2.start(bar_1)  # error: 28, line-3, line-8, "bar_1", "start"
            nursery_2.start(bar_2)
            with trio.open("") as bar_2:
                nursery_1.start(bar_1)  # error: 32, line-6, line-16, "bar_1", "start"
                nursery_1.start(bar_2)  # error: 32, line-2, line-17, "bar_2", "start"
                nursery_2.start(bar_1)  # error: 32, line-8, line-13, "bar_1", "start"
                nursery_2.start(bar_2)  # error: 32, line-4, line-14, "bar_2", "start"
            nursery_1.start(bar_1)  # error: 28, line-10, line-20, "bar_1", "start"
            nursery_1.start(bar_2)
            nursery_2.start(bar_1)  # error: 28, line-12, line-17, "bar_1", "start"
            nursery_2.start(bar_2)
        nursery_1.start(bar_1)
        nursery_1.start(bar_2)
        nursery_2.start(bar_1)
        nursery_2.start(bar_2)
    nursery_1.start(bar_1)
    nursery_1.start(bar_2)
    nursery_2.start(bar_1)
    nursery_2.start(bar_2)

# same as above, except second and third scope swapped
with trio.open_nursery() as nursery_1:
    nursery_1.start(bar_1)
    nursery_1.start(bar_2)
    nursery_2.start(bar_1)
    nursery_2.start(bar_2)
    with open("") as bar_1:
        nursery_1.start(bar_1)  # error: 24, line-1, line-6, "bar_1", "start"
        nursery_1.start(bar_2)
        nursery_2.start(bar_1)
        nursery_2.start(bar_2)
        with trio.open_nursery() as nursery_2:
            nursery_1.start(bar_1)  # error: 28, line-6, line-11, "bar_1", "start"
            nursery_1.start(bar_2)
            nursery_2.start(bar_1)
            nursery_2.start(bar_2)
            with trio.open("") as bar_2:
                nursery_1.start(bar_1)  # error: 32, line-11, line-16, "bar_1", "start"
                nursery_1.start(bar_2)  # error: 32, line-2, line-17, "bar_2", "start"
                nursery_2.start(bar_1)
                nursery_2.start(bar_2)  # error: 32, line-4, line-9, "bar_2", "start"
            nursery_1.start(bar_1)  # error: 28, line-15, line-20, "bar_1", "start"
            nursery_1.start(bar_2)
            nursery_2.start(bar_1)
            nursery_2.start(bar_2)
        nursery_1.start(bar_1)  # error: 24, line-19, line-24, "bar_1", "start"
        nursery_1.start(bar_2)
        nursery_2.start(bar_1)
        nursery_2.start(bar_2)
    nursery_1.start(bar_1)
    nursery_1.start(bar_2)
    nursery_2.start(bar_1)
    nursery_2.start(bar_2)

# multiple withitems
with trio.open_nursery() as nursery_1, trio.anything() as bar_1, trio.open_nursery() as nursery_2, trio.anything() as bar_2:
    nursery_1.start(bar_1)  # error: 20, line-1, line-1, "bar_1", "start"
    nursery_1.start(bar_2)  # error: 20, line-2, line-2, "bar_2", "start"
    nursery_2.start(bar_1)
    nursery_2.start(bar_2)  # error: 20, line-4, line-4, "bar_2", "start"

# attribute/name parameter modifications
with trio.open_nursery() as nursery:
    with trio.anything() as bar:
        nursery.start(noterror.bar)  # safe
        nursery.start(bar.anything)  # error: 22, line-2, line-3, "bar", "start"
        nursery.start(bar.anything.anything)  # error: 22, line-3, line-4, "bar", "start"

# nursery passed as parameter
with trio.open_nursery() as nursery:
    with trio.open_nursery() as nursery_2:
        nursery.start(nursery_2)  # error: 22, line-1, line-2, "nursery_2", "start"
        nursery_2.start(nursery)

# in theory safe-ish, but treated as error and likely an error with typechecking
with trio.open_nursery() as nursery:
    nursery = noterror.anything
    with trio.anything() as bar:
        nursery.start_soon(bar)  # error: 27, line-1, line-3, "bar", "start_soon"

# context manager with same variable name overrides nursery
with trio.open_nursery() as nursery:
    with trio.anything() as nursery:
        with trio.anything() as bar:
            nursery.start_soon(bar)

# list unpack
with trio.open_nursery() as nursery:
    with trio.open_process() as bar:
        nursery.start(*bar)  # error: 23, line-1, line-2, "bar", "start"
        nursery.start(foo=[*bar])  # error: 28, line-2, line-3, "bar", "start"
        nursery.start(..., ..., *bar, ...)  # error: 33, line-3, line-4, "bar", "start"
        nursery.start_soon(*bar)  # error: 28, line-4, line-5, "bar", "start_soon"

# dict unpack
with trio.open_nursery() as nursery:
    with trio.open_process() as bar:
        nursery.start(**bar)  # error: 24, line-1, line-2, "bar", "start"
        nursery.start(foo={**bar})  # error: 29, line-2, line-3, "bar", "start"
        nursery.start(..., ..., **bar, foo=...)  # error: 34, line-3, line-4, "bar", "start"
        nursery.start_soon(**bar)  # error: 29, line-4, line-5, "bar", "start_soon"

# multi-line call with multiple errors
with trio.open_nursery() as nursery:
    with trio.open_process() as bar:
        nursery.start(
            ...,
            bar,  # error: 12, line-3, line-4, "bar", "start"
            ...,
            *bar,  # error: 13, line-5, line-6, "bar", "start"
            ...,
            **bar,  # error: 14, line-7, line-8, "bar", "start"
        )

# variable nested deep inside parameter list
with trio.open_nursery() as nursery:
    with trio.open_process() as bar:
        nursery.start(list((tuple([0]), (bar))))  # error: 41, line-1, line-2, "bar", "start"
        from functools import partial
        nursery.start(partial(noterror.bar, foo=bar))  # error: 48, line-3, line-4, "bar", "start"

# tricky cases
with trio.open_nursery() as nursery:
    with trio.open_process() as bar:
        nursery.start("bar")
        nursery.start(lambda bar: bar+1)

        def myfun(nursery, bar):
            nursery.start(bar)

# nursery overridden by non-expression context manager
b = trio.open()
with trio.open_nursery() as nursery:
    with b as nursery:
        with open("") as f:
            nursery.start(f)

# fmt: on

# visitor does not care to keep track of the type of nursery/taskgroup, so we
# raise errors on .create_task() even if it doesn't exist in trio.
with trio.open_nursery() as nursery:
    with open("") as f:
        nursery.create_task(f)  # error: 28, line-1, line-2, "f", "create_task"
