import contextlib
import contextlib as anything
import typing
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Union, overload

import trio

_ = ""

# INCLUDE TRIO107


async def foo() -> Any:
    await foo()


async def foo_yield_1():
    await foo()
    yield 5
    await foo()


async def foo_yield_2():
    yield  # error: 4, "yield", Statement("function definition", lineno-1)
    yield  # error: 4, "yield", Statement("yield", lineno-1)
    await foo()


async def foo_yield_3():  # error: 0, "exit", Statement("yield", lineno+2)
    await foo()
    yield


async def foo_yield_4():  # error: 0, "exit", Statement("yield", lineno+3)
    yield  # error: 4, "yield", Statement("function definition", lineno-1)
    await (yield)  # error: 11, "yield", Statement("yield", lineno-1)
    yield  # safe


async def foo_yield_return_1():
    yield  # error: 4, "yield", Statement("function definition", lineno-1)
    return  # error: 4, "return", Statement("yield", lineno-1)


async def foo_yield_return_2():
    await foo()
    yield
    return  # error: 4, "return", Statement("yield", lineno-1)


async def foo_yield_return_3():
    await foo()
    yield
    await foo()
    return


# async with
# async with guarantees checkpoint on at least one of entry or exit
async def foo_async_with():  # error: 0, "exit", Statement("yield", lineno+2)
    async with trio.fail_after(5):
        yield  # error: 8, "yield", Statement("function definition", lineno-2)


# fmt: off
async def foo_async_with_2():  # error: 0, "exit", Statement("yield", lineno+4)
    # with'd expression evaluated before checkpoint
    async with (yield):  # error: 16, "yield", Statement("function definition", lineno-2)
        # not guaranteed that async with checkpoints on entry (or is that only for trio?)
        yield  # error: 8, "yield", Statement("yield", lineno-2)
# fmt: on


async def foo_async_with_3():  # error: 0, "exit", Statement("yield", lineno+3)
    async with trio.fail_after(5):
        ...
    yield  # safe


async def foo_async_with_4():  # error: 0, "exit", Statement("yield", lineno+4)
    async with trio.fail_after(5):
        yield  # error: 8, "yield", Statement("function definition", lineno-2)
        await foo()
    yield


async def foo_async_with_5():  # error: 0, "exit", Statement("yield", lineno+3)
    async with trio.fail_after(5):
        yield  # error: 8, "yield", Statement("function definition", lineno-2)
    yield  # error: 4, "yield", Statement("yield", lineno-1)


# async for
async def foo_async_for():  # error: 0, "exit", Statement("yield", lineno+6)
    async for i in (
        yield  # error: 8, "yield", Statement("function definition", lineno-2)
    ):
        yield  # safe
    else:
        yield  # safe


# await anext(iter) is not called on break
async def foo_async_for_2():  # error: 0, "exit", Statement("yield", lineno+5)
    async for i in trio.trick_pyright:
        yield
        if ...:
            break
    yield  # error: 4, "yield", Statement("yield", lineno-3)


async def foo_async_for_3():  # safe
    async for i in trio.trick_pyright:
        yield


async def foo_async_for_4():  # safe
    async for i in trio.trick_pyright:
        yield
        continue


# await anext(iter) is not called on break
async def foo_async_for_6():  # error: 0, "exit", Statement("yield", lineno+2)
    async for i in trio.trick_pyright:
        yield
        break


# for
async def foo_for():  # error: 0, "exit", Statement("yield", lineno+3)
    await foo()
    for i in "":
        yield  # error: 8, "yield", Statement("yield", lineno)


async def foo_for_1():  # error: 0, "exit", Statement("function definition", lineno)
    for _ in "":
        await foo()
        yield


# while
async def foo_while_0():  # error: 0, "exit", Statement("yield", lineno+7)
    while ...:
        await foo()
        if ...:
            break  # if it breaks, have checkpointed
    else:
        await foo()  # runs if 0-iter
    yield  # safe


async def foo_while_1():  # error: 0, "exit", Statement("yield", lineno+7)
    while ...:
        if ...:
            break
        await foo()  # might not run
    else:
        await foo()  # might not run
    yield  # error: 4, "yield", Statement("function definition", lineno-7)


async def foo_while_2():  # error: 0, "exit", Statement("yield", lineno+5)
    while ...:
        await foo()
    else:
        await foo()  # will always run
    yield  # safe


async def foo_while_3():  # error: 0, "exit", Statement("yield", lineno+3)
    await foo()
    while ...:
        yield  # error: 8, "yield", Statement("yield", lineno)


# no checkpoint after yield if else is entered
async def foo_while_4():  # error: 0, "exit", Statement("yield", lineno+6)
    await foo()
    while ...:
        await foo()
        yield
    else:
        yield  # error: 8, "yield", Statement("yield", lineno-2)


# no checkpoint after yield if else is entered
async def foo_while_5():  # error: 0, "exit", Statement("yield", lineno+6)
    while ...:
        yield  # error: 8, "yield", Statement("function definition", lineno-2)
        await foo()
    else:
        # might not enter loop body
        yield  # error: 8, "yield", Statement("function definition", lineno-6)


# Might not checkpoint after yield
async def foo_while_6():  # error: 0, "exit", Statement("yield", lineno+3)
    await foo()
    while ...:
        yield  # error: 8, "yield", Statement("yield", lineno)
        if ...:
            continue
        await foo()


async def foo_while_7():  # error: 0, "exit", Statement("yield", lineno+3)
    await foo()
    while ...:
        yield  # safe
        if ...:
            break
        await foo()


# check nested error is only printed once
async def foo_while_9():
    await foo()
    while ...:
        yield  # error: 8, "yield", Statement("yield", lineno)

        async def foo_nested_error():  # error: 8, "exit", Statement("yield", lineno+1)# error: 8, "exit", Statement("yield", lineno+1)
            yield  # error: 12, "yield", Statement("function definition", lineno-1)# error: 12, "yield", Statement("function definition", lineno-1)

    await foo()


# might execute loop body once, and continue the first time
# and therefore not checkpoint after yield
async def foo_while_11():  # error: 0, "exit", Statement("yield", lineno+3)
    await foo()
    while ...:
        yield  # error: 8, "yield", Statement("yield", lineno)
        if ...:
            continue
        await foo()
        while ...:
            yield  # safe
            await foo()


async def foo_while_12():  # error: 0, "exit", Statement("yield", lineno+12)
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
    yield  # error: 4, "yield", Statement("yield", lineno-9)


async def foo_while_13():  # error: 0, "exit", Statement("yield", lineno+11)
    await foo()
    while ...:
        yield
        if ...:
            break
        await foo()
        yield
        await foo()
        if ...:
            break
    yield  # error: 4, "yield", Statement("yield", lineno-8)


# try
async def foo_try_1():  # error: 0, "exit", Statement("yield", lineno+2)
    try:
        yield  # error: 8, "yield", Statement("function definition", lineno-2)
    except:
        pass


# no checkpoint after yield in ValueError
async def foo_try_2():  # error: 0, "exit", Statement("yield", lineno+5)
    try:
        await foo()
    except ValueError:
        # try might not have checkpointed
        yield  # error: 8, "yield", Statement("function definition", lineno-5)
    except:
        await foo()
    else:
        pass


async def foo_try_3():  # error: 0, "exit", Statement("yield", lineno+6)
    try:
        ...
    except:
        await foo()
    else:
        yield  # error: 8, "yield", Statement("function definition", lineno-6)


async def foo_try_4():  # safe
    try:
        ...
    except:
        yield  # error: 8, "yield", Statement("function definition", lineno-4)
    finally:
        await foo()


async def foo_try_5():
    try:
        await foo()
    finally:
        # try might crash before checkpoint
        yield  # error: 8, "yield", Statement("function definition", lineno-5)
        await foo()


async def foo_try_6():  # error: 0, "exit", Statement("yield", lineno+5)
    try:
        await foo()
    except ValueError:
        pass
    yield  # error: 4, "yield", Statement("function definition", lineno-5)


async def foo_try_7():  # error: 0, "exit", Statement("yield", lineno+16)
    await foo()
    try:
        yield
        await foo()
    except ValueError:
        await foo()
        yield
        await foo()
    except SyntaxError:
        yield  # error: 8, "yield", Statement("yield", lineno-7)
        await foo()
    finally:
        pass
    # If the try raises an exception without checkpointing, and it's not caught
    # by any of the excepts, jumping straight to the finally.
    yield  # error: 4, "yield", Statement("yield", lineno-13)


# raise
async def foo_raise_1():  # safe
    raise ValueError()


async def foo_raise_2():  # safe
    if _:
        await foo()
    else:
        raise ValueError()


async def foo_try_8():  # safe
    await foo()
    try:
        pass
    except:
        pass
    else:
        pass


## safe only if (try or else) and all except bodies either await or raise
## if foo() raises a ValueError it's not checkpointed
# Should raise multiple errors
async def foo_try_18():  # error: 0, "exit", Statement("yield", lineno+3)
    try:
        await foo()
        yield
        await foo()
    except ValueError:
        ...
    except:
        raise
    else:
        await foo()


async def foo_try_19():  # safe
    try:
        ...
    except ValueError:
        ...
    except:
        raise
    finally:
        await foo()


async def foo_try_20():  # safe
    try:
        await foo()
    except ValueError:
        await foo()
    except:
        raise


async def foo_try_21():  # safe
    try:
        ...
    except ValueError:
        raise
    except:
        raise
    else:
        await foo()


async def foo_try_22():  # error: 0, "exit", Statement("yield", lineno+3)
    try:
        await foo()
        yield
        await foo()
    except:
        pass


# no checkpoint after yield in else
async def foo_try_24():  # error: 0, "exit", Statement("yield", lineno+6)
    try:
        await foo()
    except:
        await foo()
    else:
        yield


# if
async def foo_if_1():
    if ...:
        yield  # error: 8, "yield", Statement("function definition", lineno-2)
        await foo()
    else:
        yield  # error: 8, "yield", Statement("function definition", lineno-5)
        await foo()


async def foo_if_2():  # error: 0, "exit", Statement("yield", lineno+6)
    await foo()
    if ...:
        ...
    else:
        yield
    yield  # error: 4, "yield", Statement("yield", lineno-1)


async def foo_if_3():  # error: 0, "exit", Statement("yield", lineno+6)
    await foo()
    if ...:
        yield
    else:
        ...
    yield  # error: 4, "yield", Statement("yield", lineno-3)


async def foo_if_4():  # error: 0, "exit", Statement("yield", lineno+7)
    await foo()
    yield
    if ...:
        await foo()
    else:
        ...
    yield  # error: 4, "yield", Statement("yield", lineno-5)


async def foo_if_5():  # error: 0, "exit", Statement("yield", lineno+8)
    await foo()
    if ...:
        yield
        await foo()
    else:
        yield
        ...
    yield  # error: 4, "yield", Statement("yield", lineno-2)


async def foo_if_6():  # error: 0, "exit", Statement("yield", lineno+8)
    await foo()
    if ...:
        yield
    else:
        yield
        await foo()
        ...
    yield  # error: 4, "yield", Statement("yield", lineno-5)


# If

# should raise multiple
async def foo_if_11():  # error: 0, "exit", Statement("yield", lineno+2)
    if ...:
        yield  # error: 8, "yield", Statement("function definition", lineno-2)


async def foo_if_12():  # error: 0, "exit", Statement("function definition", lineno)
    if ...:
        ...
    else:
        yield  # error: 8, "yield", Statement("function definition", lineno-4)


async def foo_if_13():
    if ...:
        yield  # error: 8, "yield", Statement("function definition", lineno-2)
        await foo()
    else:
        yield  # error: 8, "yield", Statement("function definition", lineno-5)
        await foo()


async def foo_if_14():  # error: 0, "exit", Statement("function definition", lineno)
    if ...:
        await foo()
        yield
        await foo()


async def foo_if_15():  # error: 0, "exit", Statement("function definition", lineno)
    if ...:
        ...
    else:
        await foo()
        yield
        await foo()


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


# IfExp
async def foo_ifexp_1():  # safe
    print(await foo() if _ else await foo())


# should raise multiple
async def foo_ifexp_2():  # error: 0, "exit", Statement("yield", lineno+2)
    print(
        (yield)  # error: 9, "yield", Statement("function definition", lineno-2)
        if False and await foo()
        else await foo()
    )


# nested function definition
async def foo_func_1():
    await foo()

    async def foo_func_2():  # error: 4, "exit", Statement("yield", lineno+1)
        yield  # error: 8, "yield", Statement("function definition", lineno-1)


async def foo_func_3():  # error: 0, "exit", Statement("yield", lineno+2)
    await foo()
    yield

    async def foo_func_4():
        await foo()


async def foo_func_5():  # error: 0, "exit", Statement("yield", lineno+2)
    await foo()
    yield

    def foo_func_6():  # safe
        yield

        async def foo_func_7():
            await foo()
            ...


async def foo_while_break_5():  # error: 0, "exit", Statement("yield", lineno+5)
    while ...:
        await foo()
        if ...:
            break
        yield
        break


async def foo_async_for_1():
    async for _ in trio.trick_pyright:
        ...


# async def foo_multiple_1():  # error: 0, "exit", Statement("yield", lineno+2) # error: 0, "exit", Statement("function definition", lineno)
#    if ...:
#        yield  # error: 8, "yield", Statement("function definition", lineno-2)


@asynccontextmanager
async def foo_cm_1():  # error: 0, "exit", Statement("yield", lineno+2)
    if ...:
        yield  # error: 8, "yield", Statement("function definition", lineno-2)


@contextlib.asynccontextmanager
async def foo_cm_2():  # error: 0, "exit", Statement("yield", lineno+2)
    if ...:
        yield  # error: 8, "yield", Statement("function definition", lineno-2)


@anything.asynccontextmanager
async def foo_cm_3():  # error: 0, "exit", Statement("yield", lineno+2)
    if ...:
        yield  # error: 8, "yield", Statement("function definition", lineno-2)


@contextmanager
def foo_cm_4():
    if ...:
        yield


@contextlib.contextmanager
def foo_cm_5():
    if ...:
        yield


@anything.contextmanager
def foo_cm_6():
    if ...:
        yield
