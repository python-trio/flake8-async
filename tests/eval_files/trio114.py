import trio

# ARG --startable-in-context-manager=foo


async def foo(task_status):
    ...


async def bar(task_status):  # error: 0, "bar"
    async def barbar(task_status):  # error: 4, "barbar"
        ...

    def sync_bar():
        async def barbar(task_status):  # error: 8, "barbar"
            ...


async def foo2(task_status=trio.TASK_STATUS_IGNORED):  # error: 0, "foo2"
    ...


async def foo3(*, task_status):  # error: 0, "foo3"
    ...


# don't error on pos-only parameter
async def foo4(task_status, /):
    ...


async def foo5(*task_status):
    ...


async def foo6(**task_status):
    ...


def sync():
    async def sync_async(task_status):  # error: 4, "sync_async"
        ...
