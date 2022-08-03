import typing
from typing import Any, Union, overload

import trio

_ = ""


async def foo() -> Any:
    await foo()


async def foo2():  # error: 0, function
    ...


async def foo_yield_1(delay, to):  # safe
    await foo()
    yield 5
    await foo()


async def foo_yield_2():  # safe
    yield  # TRIO108: 4
    yield  # TRIO108: 4
    await foo()


async def foo_yield_3():  # error: 0, iterable
    await foo()
    yield


async def foo_yield_4():  # safe
    yield  # TRIO108: 4
    await (yield)  # TRIO108: 11


# If
async def foo_if_1():  # error: 0, function
    if _:
        await foo()


async def foo_if_2():
    if _:
        await foo()
    else:
        await foo()


async def foo_if_3():
    await foo()
    if _:
        ...


async def foo_if_4():  # now safe
    if await foo():
        ...


async def foo_if_5():  # error: 0, iterable
    if ...:
        yield


async def foo_if_6():  # error: 0, iterable
    if ...:
        ...
    else:
        yield


async def foo_if_7():
    yield
    if ...:
        yield  # TRIO108: 8
        await foo()
    else:
        yield  # TRIO108: 8
        await foo()


async def foo_if_8():  # error: 0, iterable
    yield
    if ...:
        await foo()


async def foo_if_9():  # error: 0, iterable
    yield
    if ...:
        ...
    else:
        await foo()


async def foo_if_10():  # safe
    yield
    if ...:
        await foo()
    else:
        await foo()


async def foo_if_11():  # safe
    await foo()
    if ...:
        ...
    else:
        ...


# IfExp
async def foo_ifexp_1():  # safe
    print(await foo() if _ else await foo())


async def foo_ifexp_2():  # error: 0, function
    print(_ if False and await foo() else await foo())


# loops
async def foo_while_1():  # error: 0, function
    while _:
        await foo()


async def foo_while_2():  # now safe
    while _:
        await foo()
    else:
        await foo()


async def foo_while_3():  # safe
    await foo()
    while _:
        ...


async def foo_while_4():  # error: 0, iterable
    yield  # TRIO108: 4
    while ...:
        if ...:
            break
    else:
        await foo()  # might not run


async def foo_while_5():  # error: 0, iterable
    yield  # TRIO108: 4
    while ...:
        await foo()  # might not run


async def foo_while_6():  # error: 0, iterable
    await foo()
    while ...:
        yield  # TRIO108: 8


# no checkpoint after yield if else is entered
async def foo_while_7():  # error: 0, iterable
    while ...:
        await foo()
        yield
    else:
        yield  # TRIO108: 8


# no checkpoint after yield if else is entered
async def foo_while_8():  # error: 0, iterable
    while ...:
        yield  # TRIO108: 8
        await foo()
    else:
        # might not enter loop body
        yield  # TRIO108: 8


# might not enter the loop body, and therefore not checkpoint
async def foo_while_9():  # error: 0, iterable
    while ...:
        yield  # TRIO108: 8
        await foo()


# Might not checkpoint after yield
async def foo_while_10():  # error: 0, iterable
    await foo()
    while ...:
        yield  # TRIO108: 8
        if ...:
            continue
        await foo()


async def foo_while_11():  # error: 0, iterable
    await foo()
    while ...:
        yield  # safe
        if ...:
            break
        await foo()


# check nested error is only printed once
async def foo_while_12():
    while ...:
        yield  # TRIO108: 8

        async def foo_nested_error():  # error: 8, iterable
            yield

    await foo()


# might execute loop body once, and continue the first time
# and therefore not checkpoint after yield
async def foo_while_13():  # error: 0, iterable
    await foo()
    while ...:
        yield  # TRIO108: 8
        if ...:
            continue
        await foo()
        while ...:
            yield  # safe
            await foo()


async def foo_while_14():  # error: 0, iterable
    await foo()
    while ...:
        yield
        if ...:
            break
        await foo()
        while ...:
            yield  # safe
            await foo()
        yield  # safe
        await foo()


# for
async def foo_for():  # error: 0, iterable
    await foo()
    for i in "":
        yield  # TRIO108: 8


async def foo_for_1():  # error: 0, function
    for _ in "":
        await foo()


async def foo_for_2():  # now safe
    for _ in "":
        await foo()
    else:
        await foo()


# nested function definition
async def foo_func_1():
    await foo()

    async def foo_func_2():  # error: 4, function
        ...


async def foo_func_3():  # error: 0, function
    async def foo_func_4():
        await foo()


async def foo_func_5():  # error: 0, function
    def foo_func_6():  # safe
        async def foo_func_7():  # error: 8, function
            ...


async def foo_func_8():  # error: 0, function
    def foo_func_9():
        raise


# normal function
def foo_normal_func_1():
    return


def foo_normal_func_2():
    ...


def foo_normal_func_3():
    yield


# overload decorator
@overload
async def foo_overload_1(_: bytes):
    ...


@typing.overload
async def foo_overload_1(_: str):
    ...


async def foo_overload_1(_: Union[bytes, str]):
    await foo()


# conditions
async def foo_condition_1():  # safe
    if await foo():
        ...


async def foo_condition_2():  # error: 0, function
    if False and await foo():
        ...


async def foo_condition_3():  # error: 0, function
    if ... and await foo():
        ...


async def foo_condition_4():  # safe
    while await foo():
        ...


async def foo_condition_5():  # safe
    for i in await foo():
        ...


async def foo_condition_6():  # in theory error, but not worth parsing
    for i in (None, await foo()):
        break


async def foo_while_break_1():  # safe
    while ...:
        await foo()
        break
    else:
        await foo()


async def foo_while_break_2():  # error: 0, function
    while ...:
        break
    else:
        await foo()


async def foo_while_break_3():  # error: 0, function
    while ...:
        await foo()
        break
    else:
        ...


async def foo_while_break_4():  # error: 0, function
    while ...:
        break
    else:
        ...


async def foo_while_break_5():  # error: 0, iterable
    while ...:
        await foo()
        if ...:
            break
        yield
        break


async def foo_while_continue_1():  # safe
    while ...:
        await foo()
        continue
    else:
        await foo()


async def foo_while_continue_2():  # safe
    while ...:
        continue
    else:
        await foo()


async def foo_while_continue_3():  # error: 0, function
    while ...:
        await foo()
        continue
    else:
        ...


async def foo_while_continue_4():  # error: 0, function
    while ...:
        continue
    else:
        ...


async def foo_async_for_1():
    async for _ in trio.trick_pyright:
        ...


# async with
# async with guarantees checkpoint on at least one of entry or exit
async def foo_async_with():  # error: 0, iterable
    yield  # TRIO108: 4
    async with trio.fail_after(5):
        yield  # TRIO108: 8


async def foo_async_with_2():  # error: 0, iterable
    async with (
        yield
    ):  # error, with'd expression evaluated before checkpoint, iterable
        # not guaranteed that async with checkpoints on entry (or is that only for trio?)
        yield  # TRIO108: 8


# if fail_after checkpoints on entry, will not checkpoint after yield
async def foo_async_with_3():  # error: 0, iterable
    async with trio.fail_after(5):
        yield  # TRIO108: 8


async def foo_async_with_4():  # safe
    async with trio.fail_after(5):
        ...


# async for
async def foo_async_for():  # error: 0, iterable
    yield  # TRIO108: 4
    async for i in (yield):  # TRIO108: 20
        yield  # safe
    else:
        yield  # safe


# await anext(iter) is not called on break
async def foo_async_for_2():  # error: 0, iterable
    async for i in trio.trick_pyright:
        yield
        break


async def foo_async_for_3():  # safe
    async for i in trio.trick_pyright:
        yield


async def foo_async_for_4():  # safe
    async for i in trio.trick_pyright:
        yield
        continue


# try
# safe only if (try or else) and all except bodies either await or raise
# if foo() raises a ValueError it's not checkpointed
async def foo_try_1():  # error: 0, function
    try:
        await foo()
    except ValueError:
        ...
    except:
        raise
    else:
        await foo()


async def foo_try_2():  # safe
    try:
        ...
    except ValueError:
        ...
    except:
        raise
    finally:
        await foo()


async def foo_try_3():  # safe
    try:
        await foo()
    except ValueError:
        await foo()
    except:
        raise


# raise
async def foo_raise_1():  # safe
    raise ValueError()


async def foo_raise_2():  # safe
    if _:
        await foo()
    else:
        raise ValueError()


async def foo_try_4():  # safe
    try:
        ...
    except ValueError:
        raise
    except:
        raise
    else:
        await foo()


async def foo_try_5():  # error: 0, iterable
    try:
        await foo()
        yield
    except:
        pass


async def foo_try_6():  # safe
    try:
        yield
    finally:
        await foo()


# no checkpoint after yield in else
async def foo_try_7():  # error: 0, iterable
    try:
        await foo()
    except:
        await foo()
    else:
        yield


async def foo_try_8():  # safe
    await foo()
    try:
        pass
    except:
        pass
    else:
        pass


async def foo_try_9():  # error: 0, function
    try:
        pass
    except:
        pass
    else:
        pass


async def foo_try_10():  # safe
    try:
        await foo()
    except:
        await foo()
    else:
        pass


# no checkpoint after yield in ValueError
async def foo_try_11():  # error: 0, iterable
    yield
    try:
        await foo()
    except ValueError:
        # try might not have checkpointed
        yield  # TRIO108: 8
    except:
        await foo()
    else:
        pass


async def foo_try_12():  # error: 0, iterable
    try:
        yield
    except:
        await foo()


async def foo_try_13():  # error: 0, iterable
    try:
        ...
    except:
        await foo()
    else:
        yield


async def foo_try_14():  # error: 0, iterable
    try:
        yield
    except:
        await foo()
    else:
        yield  # TRIO108: 8


async def foo_try_15():  # safe
    try:
        yield
    except:
        yield  # TRIO108: 8
    finally:
        await foo()


async def foo_try_16():  # error: 0, iterable
    yield
    try:
        ...
    except:
        ...
    else:
        await foo()


async def foo_try_17():
    try:
        yield
        await foo()
    finally:
        # try might crash before checkpoint
        yield  # TRIO108: 8
        await foo()


async def foo_yield_return_1():
    yield
    return


async def foo_yield_return_2():
    await foo()
    yield
    return


async def foo_yield_return_3():
    await foo()
    yield
    await foo()
    return
