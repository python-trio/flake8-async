import trio
import trio as noterror


async def foo():
    async with trio.open_nursery():
        async with trio.open_process():  # error: 19, 6
            ...

    async with trio.open_process():
        async with trio.open_nursery():
            ...

    async with trio.open_nursery():

        async def bar():
            async with trio.open_process():  # safe
                ...

    async with trio.open_nursery():
        with trio.anything():  # safe (not async)
            ...

    async with trio.open_nursery():
        async with noterror.booboo():  # safe
            ...

    async with trio.open_nursery():
        async with trio.anything.anything.anything():  # ??? - currently safe
            ...

    async with trio.open_nursery():
        async with trio.open_nursery():  # safe
            ...
        async with trio.anything():  # error: 19, 32
            ...

    async with trio.anything():
        async with trio.open_nursery():  # safe
            async with trio.open_nursery():  # safe
                async with trio.anything():  # error: 27, 40
                    async with trio.anything():  # error: 31, 40
                        ...

    async with noterror.booboo(), trio.open_nursery():
        async with noterror.booboo(), trio.anything():  # error: 38, 45
            ...

    async with trio.open_nursery(), trio.anything():  # error: 36, 49
        ...

    async with trio.anything(), trio.open_nursery():  # safe
        ...

    async with trio.open_nursery(), trio.anything(), trio.open_nursery():  # error: 36, 55
        ...
