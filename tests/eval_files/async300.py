# BASE_LIBRARY asyncio
# TRIO_NO_ERROR
# ANYIO_NO_ERROR

from typing import Any

import asyncio


def handle_things(*args: object): ...


class TaskStorer:
    def __init__(self):
        self.tasks: set[Any] = set()

    def __ior__(self, obj: object):
        self.tasks.add(obj)

    def __iadd__(self, obj: object):
        self.tasks.add(obj)


async def foo():
    args: Any
    asyncio.create_task(*args)  # ASYNC300: 4

    k = asyncio.create_task(*args)

    mylist = []
    mylist.append(asyncio.create_task(*args))

    handle_things(asyncio.create_task(*args))

    (l := asyncio.create_task(*args))

    mylist = [asyncio.create_task(*args)]

    task_storer = TaskStorer()
    task_storer |= asyncio.create_task(*args)
    task_storer += asyncio.create_task(*args)

    mylist = [asyncio.create_task(*args) for i in range(10)]

    # non-call usage is fine
    asyncio.create_task
    asyncio.create_task = args

    # more or less esoteric ways of not saving the value

    [asyncio.create_task(*args)]  # ASYNC300: 5

    (asyncio.create_task(*args) for i in range(10))  # ASYNC300: 5

    args = 1 if asyncio.create_task(*args) else 2  # ASYNC300: 16

    args = (i for i in range(10) if asyncio.create_task(*args))  # ASYNC300: 36

    # not supported, it can't be used as a context manager
    with asyncio.create_task(*args) as k:  # type: ignore[attr-defined]  # ASYNC300: 9
        ...

    # import aliasing is not supported (this would raise ASYNC106 bad-async-library-import)
    from asyncio import create_task

    create_task(*args)

    # nor is assigning it
    boo = asyncio.create_task
    boo(*args)

    # or any lambda thing
    my_lambda = lambda: asyncio.create_task(*args)
    my_lambda(*args)

    # don't crash

    args.nodes[args].append(args)
    args[1].nodes()
    args[1].abc.nodes()
