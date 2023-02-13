# type: ignore
import typing
from typing import Any, overload

import trio

_ = ""


def __() -> Any:
    ...


# ARG --enable-visitor-codes-regex=(TRIO910)|(TRIO911)


# function whose body solely consists of pass, ellipsis, or string constants is safe
async def foo_empty_1():
    ...


async def foo_empty_2():
    pass


async def foo_empty_3():
    """comment"""


async def foo_empty_4():
    ...
    """comment"""
    ...
    """comment2"""


async def foo() -> Any:
    await foo()


async def foo1():  # error: 0, "exit", Statement("function definition", lineno)
    __()


# If
async def foo_if_1():  # error: 0, "exit", Statement("function definition", lineno)
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


async def foo_if_4():  # safe
    await foo()
    if ...:
        ...
    else:
        ...


# IfExp
async def foo_ifexp_1():  # safe
    print(await foo() if _ else await foo())


async def foo_ifexp_2():  # error: 0, "exit", Statement("function definition", lineno)
    print(_ if False and await foo() else await foo())


# nested function definition
async def foo_func_1():
    await foo()

    async def foo_func_2():  # error: 4, "exit", Statement("function definition", lineno)
        __()


async def foo_func_3():  # error: 0, "exit", Statement("function definition", lineno)
    async def foo_func_4():
        await foo()


async def foo_func_5():  # error: 0, "exit", Statement("function definition", lineno)
    def foo_func_6():  # safe
        async def foo_func_7():  # error: 8, "exit", Statement("function definition", lineno)
            __()


async def foo_func_8():  # error: 0, "exit", Statement("function definition", lineno)
    def foo_func_9():
        raise


# normal function
def foo_normal_func_1():
    return


def foo_normal_func_2():
    ...


# overload decorator
@overload
async def foo_overload_1(_: bytes):
    ...


@typing.overload
async def foo_overload_1(_: str):
    ...


async def foo_overload_1(_: bytes | str):
    await foo()


# conditions
async def foo_condition_1():  # safe
    if await foo():
        ...


async def foo_condition_2():  # error: 0, "exit", Statement("function definition", lineno)
    if False and await foo():
        ...


async def foo_condition_3():  # error: 0, "exit", Statement("function definition", lineno)
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


# loops
async def foo_while_1():  # error: 0, "exit", Statement("function definition", lineno)
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


# for
async def foo_for_1():  # error: 0, "exit", Statement("function definition", lineno)
    for _ in "":
        await foo()


async def foo_for_2():  # now safe
    for _ in "":
        await foo()
    else:
        await foo()


async def foo_while_break_1():  # safe
    while foo():
        await foo()
        break
    else:
        await foo()


async def foo_while_break_2():  # error: 0, "exit", Statement("function definition", lineno)
    while foo():
        break
    else:
        await foo()


async def foo_while_break_3():  # error: 0, "exit", Statement("function definition", lineno)
    while foo():
        await foo()
        break
    else:
        ...


async def foo_while_break_4():  # error: 0, "exit", Statement("function definition", lineno)
    while foo():
        break
    else:
        ...


async def foo_while_continue_1():  # safe
    while foo():
        await foo()
        continue
    else:
        await foo()


async def foo_while_continue_2():  # safe
    while foo():
        continue
    else:
        await foo()


async def foo_while_continue_3():  # error: 0, "exit", Statement("function definition", lineno)
    while foo():
        await foo()
        continue
    else:
        ...


async def foo_while_continue_4():  # error: 0, "exit", Statement("function definition", lineno)
    while foo():
        continue
    else:
        ...


async def foo_async_for_1():
    async for _ in trio.trick_pyright:
        ...


# async with
# async with guarantees checkpoint on at least one of entry or exit
async def foo_async_with():
    async with trio.trick_pyright:
        ...


# raise
async def foo_raise_1():  # safe
    raise ValueError()


async def foo_raise_2():  # safe
    if _:
        await foo()
    else:
        raise ValueError()


# try
# safe only if (try or else) and all except bodies either await or raise
# if foo() raises a ValueError it's not checkpointed
async def foo_try_1():  # error: 0, "exit", Statement("function definition", lineno)
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


async def foo_try_4():  # safe
    try:
        ...
    except ValueError:
        raise
    except:
        raise
    else:
        await foo()


async def foo_try_5():  # safe
    await foo()
    try:
        pass
    except:
        pass
    else:
        pass


async def foo_try_6():  # error: 0, "exit", Statement("function definition", lineno)
    try:
        pass
    except:
        pass
    else:
        pass


async def foo_try_7():  # safe
    try:
        await foo()
    except:
        await foo()
    else:
        pass


# https://github.com/Zac-HD/flake8-trio/issues/45
async def to_queue(iter_func, queue):
    async with iter_func() as it:
        async for x in it:
            queue.put(x)


async def to_queue2(iter_func, queue):
    try:
        async with iter_func() as it:
            async for x in it:
                queue.put(x)
    finally:
        queue.put(None)


# safe, exception is propagated out
async def try_checkpoint_empty_finally():
    try:
        await trio.sleep(0)
    finally:
        ...


# unsafe, exception is suppressed
async def try_exception_suppressed():  # error: 0, 'exit', Statement('function definition', lineno)
    try:
        await trio.sleep(0)
    except:
        ...


# safe
async def try_bare_except_reraises():
    try:
        await trio.sleep(0)
    except:
        raise
    finally:
        ...


async def return_in_finally_bare_except_checkpoint():
    try:
        await trio.sleep(0)
    except:
        await trio.sleep(0)
    finally:
        return


async def return_in_finally_bare_except_empty():
    try:
        await trio.sleep(0)
    except:
        ...
    finally:
        return  # error: 8, 'return', Statement('function definition', lineno-6)


# early return
async def foo_return_1():
    return  # error: 4, "return", Statement("function definition", lineno-1)


async def foo_return_2():  # safe
    if _:
        return  # error: 8, "return", Statement("function definition", lineno-2)
    await foo()


async def foo_return_3():  # error: 0, "exit", Statement("function definition", lineno)
    if _:
        await foo()
        return  # safe


# loop over non-empty static collection
async def foo_loop_static():
    for i in [1, 2, 3]:
        await foo()


# also handle range with constants
async def foo_range_1():
    for i in range(5):
        await foo()


async def foo_range_2():
    for i in range(5, 10):
        await foo()


async def foo_range_3():
    for i in range(10, 5, -1):
        await foo()


async def foo_range_4():  # error: 0, "exit", Statement("function definition", lineno)
    for i in range(10, 5):
        await foo()


# error on complex parameters
async def foo_range_5():  # error: 0, "exit", Statement("function definition", lineno)
    for i in range(2 - 2):
        await foo()


# https://github.com/Zac-HD/flake8-trio/issues/47
async def f():
    while True:
        if ...:
            await trio.sleep(0)
            return
        # If you delete this loop, no warning.
        while foo():
            await __()


async def f1():
    while True:
        if ...:
            await trio.sleep(0)
            return


async def f2():
    while True:
        await trio.sleep(0)
        return


# code coverage
def foo_sync():
    # try in sync function
    try:
        pass
    except:
        pass

    # continue/break in sync function
    while True:
        if ...:
            continue
        if ...:
            break

    # boolop in sync function
    True and True
