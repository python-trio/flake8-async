"""Test for ASYNC91x rules with except* blocks.

ASYNC910: async-function-no-checkpoint
ASYNC911: async-generator-no-checkpoint
ASYNC913: indefinite-loop-no-guaranteed-checkpoint

async912 handled in separate file
"""

# ARG --enable=ASYNC910,ASYNC911,ASYNC913
# AUTOFIX
# ASYNCIO_NO_AUTOFIX
import trio


async def foo(): ...


async def foo_try_except_star_1():  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    try:
        await foo()
    except* ValueError:
        ...
    except* RuntimeError:
        raise
    else:
        await foo()


async def foo_try_except_star_2():  # safe
    try:
        ...
    except* ValueError:
        ...
    finally:
        await foo()


async def foo_try_except_star_3():  # safe
    try:
        await foo()
    except* ValueError:
        raise


# Multiple except* handlers - should all guarantee checkpoint/raise
async def foo_try_except_star_4():
    try:
        await foo()
    except* ValueError:
        await foo()
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
        await foo()


async def try_else_raise_in_except():
    try:
        ...
    except* ValueError:
        raise
    else:
        await foo()


async def check_async911():  # ASYNC911: 0, "exit", Statement("yield", lineno+7)
    try:
        await foo()
    except* ValueError:
        ...
    except* RuntimeError:
        raise
    yield  # ASYNC911: 4, "yield", Statement("function definition", lineno-7)


async def check_async913():
    while True:  # ASYNC913: 4
        try:
            await foo()
        except* ValueError:
            # Missing checkpoint
            ...
