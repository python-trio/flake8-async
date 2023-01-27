# ARG --no-checkpoint-warning-decorator=asynccontextmanager,other_context_manager


async def foo1():  # TRIO900: 0
    yield
    yield


@asynccontextmanager
async def foo2():
    yield


@asynccontextmanager
async def foo3():
    async def bar():  # TRIO900: 4
        yield

    yield


def foo4():
    yield


# no-checkpoint-warning-decorator now ignored
@other_context_manager
async def foo5():  # TRIO900: 0
    yield
