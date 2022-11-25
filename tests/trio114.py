import trio


async def foo(task_status):  # error: 0, "foo"
    ...


async def bar(task_status):  # error: 0, "bar"
    ...


async def foo2(task_status=trio.TASK_STATUS_IGNORED):  # error: 0, "foo2"
    ...


async def foo3(*, task_status):  # error: 0, "foo3"
    ...


async def foo4(task_status, /):  # error: 0, "foo4"
    ...


async def foo5(*task_status):
    ...


async def foo6(**task_status):
    ...
