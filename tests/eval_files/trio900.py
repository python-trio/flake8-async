# type: ignore
# ARG --no-checkpoint-warning-decorator=asynccontextmanager,other_context_manager
from contextlib import asynccontextmanager


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


@pytest.fixture
async def async_fixtures_are_basically_context_managers():
    yield


@pytest.fixture(scope="function")  # args don't matter
async def async_fixtures_can_take_arguments():
    yield


# no-checkpoint-warning-decorator now ignored
@other_context_manager
async def foo5():  # TRIO900: 0
    yield


# issue 133
async def this_is_not_an_async_generator():
    @asynccontextmanager
    async def cm():
        yield

    async with cm():
        pass


async def another_non_generator():
    def foo():
        yield
