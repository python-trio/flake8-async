"""Async function with no awaits could be sync.
It currently does not care if 910/911 would also be triggered."""

# ARG --enable=ASYNC124,ASYNC910,ASYNC911

# 910/911 will also autofix async124, in the sense of adding a checkpoint. This is perhaps
# not what the user wants though, so this would be a case in favor of making 910/911 not
# trigger when async124 does.
# AUTOFIX
# ASYNCIO_NO_AUTOFIX
from typing import Any
import trio


def condition() -> bool:
    return False


async def foo() -> Any:
    await foo()


async def foo_print():  # ASYNC124: 0  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    print("hello")
    await trio.lowlevel.checkpoint()


async def conditional_wait():  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    if condition():
        await foo()
    await trio.lowlevel.checkpoint()


async def foo_gen():  # ASYNC124: 0  # ASYNC911: 0, "exit", Statement("yield", lineno+1)
    await trio.lowlevel.checkpoint()
    yield  # ASYNC911: 4, "yield", Statement("function definition", lineno-1)
    await trio.lowlevel.checkpoint()


async def foo_async_with():
    async with foo_gen():
        ...


async def foo_async_for():
    async for i in foo_gen():
        ...


async def foo_nested():  # ASYNC124: 0  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    async def foo_nested_2():
        await foo()
    await trio.lowlevel.checkpoint()


async def foo_nested_sync():  # ASYNC124: 0  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    def foo_nested_sync_child():
        await foo()  # type: ignore[await-not-async]
    await trio.lowlevel.checkpoint()


# We don't want to trigger on empty/pass functions because of inheritance.
# Uses same logic as async91x.


async def foo_empty():
    "blah"
    ...


async def foo_empty_pass():
    "foo"
    pass


# we could consider filtering out functions named `test_.*` to not give false alarms on
# tests that use async fixtures.
# For ruff and for running through flake8 we could expect users to use per-file-ignores,
# but running as standalone we don't currently support that. (though probs wouldn't be
# too bad to add support).
# See e.g. https://github.com/agronholm/anyio/issues/803 for why one might want an async
# test without awaits.


async def test_async_fixture(my_anyio_fixture):  # ASYNC124: 0  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    assert my_anyio_fixture.setup_worked_correctly
    await trio.lowlevel.checkpoint()
