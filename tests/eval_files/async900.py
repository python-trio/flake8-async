# type: ignore
# ARG --no-checkpoint-warning-decorator=asynccontextmanager,other_context_manager
# transform-async-generator-decorators set further down

# trio will also recommend trio.as_safe_channel, see async900_trio
# NOTRIO
from contextlib import asynccontextmanager


async def foo1():  # ASYNC900: 0, 'contextlib.asynccontextmanager, pytest.fixture, this_is_like_a_context_manager'
    yield
    yield


@asynccontextmanager
async def foo2():
    yield


@asynccontextmanager
async def foo3():
    async def bar():  # ASYNC900: 4, 'contextlib.asynccontextmanager, pytest.fixture, this_is_like_a_context_manager'
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
async def foo5():  # ASYNC900: 0, 'contextlib.asynccontextmanager, pytest.fixture, this_is_like_a_context_manager'
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


# ARG --transform-async-generator-decorators=this_is_like_a_context_manager


@this_is_like_a_context_manager()  # OK because of the config, issue #277
async def some_generator():
    while True:
        yield
