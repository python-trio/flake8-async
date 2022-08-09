from typing import Any

import trio
import trio as noterror


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

    # nursery inside context manager
    async with trio.open_process() as bar:
        async with trio.open_nursery() as nursery:
            nursery.start(bar)  # safe
    with trio.open_process() as bar:
        async with trio.open_nursery() as nursery:
            nursery.start(bar)  # safe
    async with trio.open_process() as bar:
        with trio.open_nursery() as nursery:
            nursery.start(bar)  # safe
    with trio.open_process() as bar:
        with trio.open_nursery() as nursery:
            nursery.start(bar)  # safe

    # reset variables on nested function
    async with trio.open_nursery() as nursery:

        async def foo_1():
            nursery = noterror.something
            async with trio.open_process() as bar_2:
                nursery.start(bar_2)  # safe

        def foo_2():
            nursery = noterror.something
            with trio.open_process() as bar_2:
                nursery.start(bar_2)  # safe

    # specifically check for trio.open_nursery
    async with noterror.open_nursery() as nursery:
        async with trio.open("") as bar:
            nursery.start(bar)

    bar_1: Any = ""
    bar_2: Any = ""
    nursery_2: Any = ""

    async with trio.open_nursery() as nursery_1:
        nursery_1.start(bar_1)
        nursery_1.start(bar_2)
        nursery_2.start(bar_1)
        nursery_2.start(bar_2)
        async with trio.open_nursery() as nursery_2:
            nursery_1.start(bar_1)
            nursery_1.start(bar_2)
            nursery_2.start(bar_1)
            nursery_2.start(bar_2)
            with open("") as bar_1:
                nursery_1.start(bar_1)  # error: 32, line-1, line-11, "bar_1", "start"
                nursery_1.start(bar_2)
                nursery_2.start(bar_1)  # error: 32, line-3, line-8, "bar_1", "start"
                nursery_2.start(bar_2)
                async with trio.open("") as bar_2:
                    nursery_1.start(bar_1)  # error: 36, line-6, line-16, "bar_1", "start"
                    nursery_1.start(bar_2)  # error: 36, line-2, line-17, "bar_2", "start"
                    nursery_2.start(bar_1)  # error: 36, line-8, line-13, "bar_1", "start"
                    nursery_2.start(bar_2)  # error: 36, line-4, line-14, "bar_2", "start"
                nursery_1.start(bar_1)  # error: 32, line-10, line-20, "bar_1", "start"
                nursery_1.start(bar_2)
                nursery_2.start(bar_1)  # error: 32, line-12, line-17, "bar_1", "start"
                nursery_2.start(bar_2)
            nursery_1.start(bar_1)
            nursery_1.start(bar_2)
            nursery_2.start(bar_1)
            nursery_2.start(bar_2)
        nursery_1.start(bar_1)
        nursery_1.start(bar_2)
        nursery_2.start(bar_1)
        nursery_2.start(bar_2)

    async with trio.open_nursery() as nursery_1:
        nursery_1.start(bar_1)
        nursery_1.start(bar_2)
        nursery_2.start(bar_1)
        nursery_2.start(bar_2)
        with open("") as bar_1:
            nursery_1.start(bar_1)  # error: 28, line-1, line-6, "bar_1", "start"
            nursery_1.start(bar_2)
            nursery_2.start(bar_1)
            nursery_2.start(bar_2)
            async with trio.open_nursery() as nursery_2:
                nursery_1.start(bar_1)  # error: 32, line-6, line-11, "bar_1", "start"
                nursery_1.start(bar_2)
                nursery_2.start(bar_1)
                nursery_2.start(bar_2)
                async with trio.open("") as bar_2:
                    nursery_1.start(bar_1)  # error: 36, line-11, line-16, "bar_1", "start"
                    nursery_1.start(bar_2)  # error: 36, line-2, line-17, "bar_2", "start"
                    nursery_2.start(bar_1)
                    nursery_2.start(bar_2)  # error: 36, line-4, line-9, "bar_2", "start"
                nursery_1.start(bar_1)  # error: 32, line-15, line-20, "bar_1", "start"
                nursery_1.start(bar_2)
                nursery_2.start(bar_1)
                nursery_2.start(bar_2)
            nursery_1.start(bar_1)  # error: 28, line-19, line-24, "bar_1", "start"
            nursery_1.start(bar_2)
            nursery_2.start(bar_1)
            nursery_2.start(bar_2)
        nursery_1.start(bar_1)
        nursery_1.start(bar_2)
        nursery_2.start(bar_1)
        nursery_2.start(bar_2)

    async with trio.open_nursery() as nursery_1, trio.anything() as bar_1, trio.open_nursery() as nursery_2, trio.anything() as bar_2:
        nursery_1.start(bar_1)  # error: 24, line-1, line-1, "bar_1", "start"
        nursery_1.start(bar_2)  # error: 24, line-2, line-2, "bar_2", "start"
        nursery_2.start(bar_1)
        nursery_2.start(bar_2)  # error: 24, line-4, line-4, "bar_2", "start"

    async with trio.open_nursery() as nursery:
        async with trio.anything() as bar:
            nursery.start(noterror.bar)  # safe
            nursery.start(bar.anything)  # error: 26, line-2, line-3, "bar", "start"
            nursery.start(bar.anything.anything)  # error: 26, line-3, line-4, "bar", "start"

    # I think this is an error
    async with trio.open_nursery() as nursery:
        async with trio.open_nursery() as nursery_2:
            nursery.start(nursery_2)  # error: 26, line-1, line-2, "nursery_2", "start"
            nursery_2.start(nursery)

    # in theory safe-ish, but treated as error
    async with trio.open_nursery() as nursery:
        nursery = noterror.anything
        async with trio.anything() as bar:
            nursery.start_soon(bar)  # error: 31, line-1, line-3, "bar", "start_soon"

    async with trio.open_nursery() as nursery:
        async with trio.anything() as nursery:
            async with trio.anything() as bar:
                nursery.start_soon(bar)

    # weird calls
    # async nursery
    async with trio.open_nursery() as nursery:
        # async context manager
        async with trio.open_process() as bar:
            nursery.start(*bar)  # error: 27, line-1, line-3, "bar", "start"
            nursery.start(foo=[*bar])  # error: 32, line-2, line-4, "bar", "start"
            nursery.start(..., ..., *bar, ...)  # error: 37, line-3, line-5, "bar", "start"
            nursery.start_soon(*bar)  # error: 32, line-4, line-6, "bar", "start_soon"

    # async nursery
    async with trio.open_nursery() as nursery:
        # async context manager
        async with trio.open_process() as bar:
            nursery.start(**bar)  # error: 28, line-1, line-3, "bar", "start"
            nursery.start(foo={**bar})  # error: 33, line-2, line-4, "bar", "start"
            nursery.start(..., ..., **bar, foo=...)  # error: 38, line-3, line-5, "bar", "start"
            nursery.start_soon(**bar)  # error: 33, line-4, line-6, "bar", "start_soon"

    # async nursery
    async with trio.open_nursery() as nursery:
        # async context manager
        async with trio.open_process() as bar:
            nursery.start(
                ...,
                bar,  # error: 16, line-3, line-5, "bar", "start"
                ...,
                *bar,  # error: 17, line-5, line-7, "bar", "start"
                ...,
                **bar,  # error: 18, line-7, line-9, "bar", "start"
            )

    async with trio.open_nursery() as nursery:
        # async context manager
        async with trio.open_process() as bar:
            nursery.start(list((tuple([0]), (bar))))  # error: 45, line-1, line-3, "bar", "start"

            nursery.start("bar")
            nursery.start(lambda bar: bar+1)

            def myfun(nursery, bar):
                nursery.start(bar)

# fmt: on
