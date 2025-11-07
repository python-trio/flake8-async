"""Test for ASYNC91x rules with except* blocks.

ASYNC910: async-function-no-checkpoint
ASYNC911: async-generator-no-checkpoint
ASYNC913: indefinite-loop-no-guaranteed-checkpoint

async912 handled in separate file
"""

# ARG --enable=ASYNC910,ASYNC911,ASYNC913,ASYNC914
# AUTOFIX
import trio


async def foo_try_except_star_1():  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    try:
        await trio.lowlevel.checkpoint()
    except* ValueError:
        ...
    except* RuntimeError:
        raise
    else:
        await trio.lowlevel.checkpoint()  # ASYNC914: 8


async def foo_try_except_star_2():  # safe
    try:
        ...
    except* ValueError:
        ...
    finally:
        await trio.lowlevel.checkpoint()


async def foo_try_except_star_3():  # safe
    try:
        await trio.lowlevel.checkpoint()
    except* ValueError:
        raise


# Multiple except* handlers - should all guarantee checkpoint/raise
async def foo_try_except_star_4():
    try:
        await trio.lowlevel.checkpoint()
    except* ValueError:
        await trio.lowlevel.checkpoint()
    except* TypeError:
        raise
    except* Exception:
        raise


async def try_else_no_raise_in_except():  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    try:
        ...
    except* ValueError:
        ...
    else:
        await trio.lowlevel.checkpoint()


async def try_else_raise_in_except():
    try:
        ...
    except* ValueError:
        raise
    else:
        await trio.lowlevel.checkpoint()


async def check_async911():  # ASYNC911: 0, "exit", Statement("yield", lineno+7)
    try:
        await trio.lowlevel.checkpoint()
    except* ValueError:
        ...
    except* RuntimeError:
        raise
    yield  # ASYNC911: 4, "yield", Statement("function definition", lineno-7)


async def check_async913():
    while True:  # ASYNC913: 4
        try:
            # If this was lowlevel it'd be marked as ASYNC914 after we insert a checkpoint
            # before the try. TODO: Ideally it'd be fixed in the same pass.
            await foo()
        except* ValueError:
            # Missing checkpoint
            ...


# ASYNC914
async def foo_try_1():
    await trio.lowlevel.checkpoint()
    try:
        await trio.lowlevel.checkpoint()  # ASYNC914: 8
    except* BaseException:
        await trio.lowlevel.checkpoint()  # ASYNC914: 8


async def foo_try_2():
    await trio.lowlevel.checkpoint()
    try:
        await trio.lowlevel.checkpoint()  # ASYNC914: 8
    except* BaseException:
        await foo()


async def foo_try_3():
    await trio.lowlevel.checkpoint()
    try:
        await foo()
    except* BaseException:
        await trio.lowlevel.checkpoint()  # ASYNC914: 8


async def foo_try_4():
    await trio.lowlevel.checkpoint()
    try:
        await foo()
    except* BaseException:
        await foo()


async def foo_try_5():
    await foo()
    try:
        await trio.lowlevel.checkpoint()  # ASYNC914: 8
    except* BaseException:
        await trio.lowlevel.checkpoint()  # ASYNC914: 8


async def foo_try_6():
    await foo()
    try:
        await trio.lowlevel.checkpoint()  # ASYNC914: 8
    except* BaseException:
        await foo()


async def foo_try_7():
    await foo()
    try:
        await foo()
    except* BaseException:
        await trio.lowlevel.checkpoint()  # ASYNC914: 8


async def foo_try_8():
    await foo()
    try:
        await foo()
    except* BaseException:
        await foo()


async def foo_try_9():
    try:
        await trio.lowlevel.checkpoint()  # ASYNC914: 8
    except* BaseException:
        await foo()
    else:
        await foo()


async def foo_try_10():
    try:
        await trio.lowlevel.checkpoint()
    finally:
        await foo()


async def foo_try_11():
    try:
        await trio.lowlevel.checkpoint()
    except* BaseException:
        await foo()


async def foo_try_12():
    try:
        await trio.lowlevel.checkpoint()  # ASYNC914: 8
    except* BaseException:
        ...
    else:
        await foo()
    await trio.lowlevel.checkpoint()


async def foo_try_13():
    try:
        ...
    except* ValueError:
        ...
    except* BaseException:
        raise
    finally:
        await trio.lowlevel.checkpoint()
