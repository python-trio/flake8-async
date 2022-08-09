from typing import Any

import trio
import trio as noterror


async def foo():
    async with trio.open_nursery():
        ...

    # async nursery
    async with trio.open_nursery() as nursery:
        # async context manager
        async with trio.open_process() as bar:
            nursery.start(bar)  # error: 12, line-1, line-3
            nursery.start(foo=bar)  # error: 12, line-2, line-4
            nursery.start(..., ..., bar, ...)  # error: 12, line-3, line-5

            nursery.start_soon(bar)  # error: 12, line-5, line-7

        # sync context manager
        with open("") as bar:
            nursery.start(bar)  # error: 12, line-1, line-11
            nursery.start(foo=bar)  # error: 12, line-2, line-12
            nursery.start(..., ..., bar, ...)  # error: 12, line-3, line-13

            nursery.start_soon(bar)  # error: 12, line-5, line-15

    # sync nursery
    with trio.open_nursery() as nursery:
        # async context manager
        async with trio.open_process() as bar:
            nursery.start(bar)  # error: 12, line-1, line-3
            nursery.start(foo=bar)  # error: 12, line-2, line-4
            nursery.start(..., ..., bar, ...)  # error: 12, line-3, line-5

            nursery.start_soon(bar)  # error: 12, line-5, line-7

        # sync context manager
        with open("") as bar:
            nursery.start(bar)  # error: 12, line-1, line-11
            nursery.start(foo=bar)  # error: 12, line-2, line-12
            nursery.start(..., ..., bar, ...)  # error: 12, line-3, line-13

            nursery.start_soon(bar)  # error: 12, line-5, line-15

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
                nursery_1.start(bar_1)  # error: 16, line-1, line-11
                nursery_1.start(bar_2)
                nursery_2.start(bar_1)  # error: 16, line-3, line-8
                nursery_2.start(bar_2)
                async with trio.open("") as bar_2:
                    nursery_1.start(bar_1)  # error: 20, line-6, line-16
                    nursery_1.start(bar_2)  # error: 20, line-2, line-17
                    nursery_2.start(bar_1)  # error: 20, line-8, line-13
                    nursery_2.start(bar_2)  # error: 20, line-4, line-14
                nursery_1.start(bar_1)  # error: 16, line-10, line-20
                nursery_1.start(bar_2)
                nursery_2.start(bar_1)  # error: 16, line-12, line-17
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
            nursery_1.start(bar_1)  # error: 12, line-1, line-6
            nursery_1.start(bar_2)
            nursery_2.start(bar_1)
            nursery_2.start(bar_2)
            async with trio.open_nursery() as nursery_2:
                nursery_1.start(bar_1)  # error: 16, line-6, line-11
                nursery_1.start(bar_2)
                nursery_2.start(bar_1)
                nursery_2.start(bar_2)
                async with trio.open("") as bar_2:
                    nursery_1.start(bar_1)  # error: 20, line-11, line-16
                    nursery_1.start(bar_2)  # error: 20, line-2, line-17
                    nursery_2.start(bar_1)
                    nursery_2.start(bar_2)  # error: 20, line-4, line-9
                nursery_1.start(bar_1)  # error: 16, line-15, line-20
                nursery_1.start(bar_2)
                nursery_2.start(bar_1)
                nursery_2.start(bar_2)
            nursery_1.start(bar_1)  # error: 12, line-19, line-24
            nursery_1.start(bar_2)
            nursery_2.start(bar_1)
            nursery_2.start(bar_2)
        nursery_1.start(bar_1)
        nursery_1.start(bar_2)
        nursery_2.start(bar_1)
        nursery_2.start(bar_2)

    async with trio.open_nursery() as nursery_1, trio.anything() as bar_1, trio.open_nursery() as nursery_2, trio.anything() as bar_2:
        nursery_1.start(bar_1)  # error: 8, line-1, line-1
        nursery_1.start(bar_2)  # error: 8, line-2, line-2
        nursery_2.start(bar_1)
        nursery_2.start(bar_2)  # error: 8, line-4, line-4

    async with trio.open_nursery() as nursery:
        async with trio.anything() as bar:
            nursery.start(noterror.bar)  # safe
            nursery.start(bar.anything)  # error: 12, line-2, line-3
            nursery.start(bar.anything.anything)  # error: 12, line-3, line-4

    # I think this is an error
    async with trio.open_nursery() as nursery:
        async with trio.open_nursery() as nursery_2:
            nursery.start(nursery_2)  # error: 12, line-1, line-2

    # in theory safe
    async with trio.open_nursery() as nursery:
        nursery = noterror.anything
        async with trio.anything() as bar:
            nursery.start_soon(bar)  # error: 12, line-1, line-3

    async with trio.open_nursery() as nursery:
        async with trio.anything() as nursery:
            async with trio.anything() as bar:
                nursery.start_soon(bar)
