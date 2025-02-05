"""Async function with no awaits could be sync.
It currently does not care if 910/911 would also be triggered."""

# ARG --enable=ASYNC124,ASYNC910,ASYNC911
# ARG --no-checkpoint-warning-decorator=custom_disabled_decorator

# 910/911 will also autofix async124, in the sense of adding a checkpoint. This is perhaps
# not what the user wants though, so this would be a case in favor of making 910/911 not
# trigger when async124 does.
# AUTOFIX # all errors get "fixed" except for foo_fix_no_subfix in async124_no_autofix.py
# ASYNCIO_NO_AUTOFIX
from typing import Any, overload
from pytest import fixture

custom_disabled_decorator: Any = ...


def condition() -> bool:
    return False


async def foo() -> Any:
    await foo()


async def foo_print():  # ASYNC124: 0  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    print("hello")


async def conditional_wait():  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    if condition():
        await foo()


async def foo_gen():  # ASYNC124: 0  # ASYNC911: 0, "exit", Statement("yield", lineno+1)
    yield  # ASYNC911: 4, "yield", Statement("function definition", lineno-1)


async def foo_async_with():
    async with foo_gen():
        ...


async def foo_async_for():
    async for i in foo_gen():
        ...


async def foo_nested():  # ASYNC124: 0  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    async def foo_nested_2():
        await foo()


async def foo_nested_sync():  # ASYNC124: 0  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    def foo_nested_sync_child():
        await foo()  # type: ignore[await-not-async]


# We don't want to trigger on empty/pass functions because of inheritance.
# Uses same logic as async91x.


async def foo_empty():
    "blah"
    ...


async def foo_empty_pass():
    "foo"
    pass


# this was previously silenced, but pytest now gives good errors on sync test + async
# fixture; so in the rare case that it has to be async the user will be able to debug it
async def test_async_fixture(  # ASYNC124: 0  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    my_async_fixture,
):
    assert my_async_fixture.setup_worked_correctly


# no params -> no async fixtures
async def test_no_fixture():  # ASYNC124: 0  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    print("blah")


# skip @overload. They should always be empty, but /shrug
@overload
async def foo_overload():
    print("blah")


async def foo_overload(): ...


# skip @[pytest.]fixture if they have any params, since they might depend on other
# async fixtures
@fixture
async def foo_fix(my_async_fixture):
    print("blah")


# @fixture with no params can be converted to sync
# see async124_no_autofix.py


async def default_value():
    def foo(arg=await foo()): ...


# only the expression in genexp's get checked
async def foo_async_gen():  # ASYNC124: 0
    return (  # ASYNC910: 4, "return", Statement("function definition", lineno-1)
        await a async for a in foo_gen()
    )


async def foo_async_gen_await():
    return (a for a in await foo_gen())


async def foo_async_for_comprehension():
    return [a async for a in foo_gen()]


class Foo:
    # async124 ignores class methods
    async def bar(  # ASYNC910: 4, "exit", Statement("function definition", lineno)
        self,
    ):
        async def bee():  # ASYNC124: 8  # ASYNC910: 8, "exit", Statement("function definition", lineno)
            print("blah")

    async def later_in_class(  # ASYNC910: 4, "exit", Statement("function definition", lineno)
        self,
    ):
        print()


async def after_class():  # ASYNC124: 0  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    print()


@custom_disabled_decorator
async def foo_has_custom_disabled_decorator():
    print()
