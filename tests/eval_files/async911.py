# AUTOFIX
# ASYNCIO_NO_AUTOFIX
from typing import Any

import pytest
import trio

_: Any = ""

# ARG --enable=ASYNC910,ASYNC911


async def foo() -> Any:
    await foo()


def bar(*args) -> Any: ...


# mypy now treats `if ...` as `if True`, so we have another arbitrary function instead
def condition() -> Any: ...


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
# checkpoint on both entry and exit
async def foo_async_with():
    async with trio.fail_after(5):
        yield


async def foo_async_with_3():
    async with trio.fail_after(5):
        yield
        yield  # error: 8, "yield", Statement("yield", lineno-1)


# async for
async def foo_async_for():  # error: 0, "exit", Statement("yield", lineno+4)
    async for i in bar():
        yield  # safe
    else:
        yield  # safe


# await anext(iter) is not called on break
async def foo_async_for_2():  # error: 0, "exit", Statement("yield", lineno+2)
    async for i in trio.trick_pyright:
        yield
        if condition():
            break


async def foo_async_for_3():  # safe
    async for i in trio.trick_pyright:
        yield


async def foo_async_for_4():  # safe
    async for i in trio.trick_pyright:
        yield
        continue


# for
async def foo_for():  # error: 0, "exit", Statement("yield", lineno+3)
    await foo()
    for i in "":
        yield  # error: 8, "yield", Statement("yield", lineno)


async def foo_for_1():  # error: 0, "exit", Statement("function definition", lineno) # error: 0, "exit", Statement("yield", lineno+3)
    for _ in "":
        await foo()
        yield


# while


# safe if checkpoint in else
async def foo_while_1():  # error: 0, "exit", Statement("yield", lineno+5)
    while foo():
        ...
    else:
        await foo()  # will always run
    yield  # safe


# simple yield-in-loop case
async def foo_while_2():  # error: 0, "exit", Statement("yield", lineno+3)
    await foo()
    while foo():
        yield  # error: 8, "yield", Statement("yield", lineno)


# no checkpoint after yield if else is entered
async def foo_while_3():  # error: 0, "exit", Statement("yield", lineno+5)
    while foo():
        await foo()
        yield
    else:
        yield  # error: 8, "yield", Statement("yield", lineno-2) # error: 8, "yield", Statement("function definition", lineno-5)


# check that errors are suppressed in visit_While
async def foo_while_4():  # error: 0, "exit", Statement("yield", lineno+3) # error: 0, "exit", Statement("yield", lineno+5) # error: 0, "exit", Statement("yield", lineno+7)
    await foo()
    while foo():
        yield  # error: 8, "yield", Statement("yield", lineno) # error: 8, "yield", Statement("yield", lineno+2) # error: 8, "yield", Statement("yield", lineno+4)
        while foo():
            yield  # error: 12, "yield", Statement("yield", lineno)# error: 12, "yield", Statement("yield", lineno-2)# error: 12, "yield", Statement("yield", lineno+2)
            while foo():
                yield  # error: 16, "yield", Statement("yield", lineno-2)# error: 16, "yield", Statement("yield", lineno)


# check that state management is handled in for loops as well
async def foo_while_4_for():  # error: 0, "exit", Statement("yield", lineno+3) # error: 0, "exit", Statement("yield", lineno+5) # error: 0, "exit", Statement("yield", lineno+7)
    await foo()
    for i in bar():
        yield  # error: 8, "yield", Statement("yield", lineno) # error: 8, "yield", Statement("yield", lineno+2) # error: 8, "yield", Statement("yield", lineno+4)
        for i in bar():
            yield  # error: 12, "yield", Statement("yield", lineno)# error: 12, "yield", Statement("yield", lineno-2)# error: 12, "yield", Statement("yield", lineno+2)
            for i in bar():
                yield  # error: 16, "yield", Statement("yield", lineno-2)# error: 16, "yield", Statement("yield", lineno)


# check error suppression is reset
async def foo_while_5():
    await foo()
    while foo():
        yield  # error: 8, "yield", Statement("yield", lineno)

        async def foo_nested_error():  # error: 8, "exit", Statement("yield", lineno+1)
            yield  # error: 12, "yield", Statement("function definition", lineno-1)

    await foo()


# --- while + continue ---
# no checkpoint on continue
async def foo_while_continue_1():  # error: 0, "exit", Statement("yield", lineno+3)
    await foo()
    while foo():
        yield  # error: 8, "yield", Statement("yield", lineno)
        if condition():
            continue
        await foo()


# multiple continues
async def foo_while_continue_2():  # error: 0, "exit", Statement("yield", lineno+3)
    await foo()
    while foo():
        yield  # error: 8, "yield", Statement("yield", lineno)
        if foo():
            continue
        await foo()
        if condition():
            continue
        while foo():
            yield  # safe
            await foo()


# --- while + break ---
# else might not run
async def foo_while_break_1():  # error: 0, "exit", Statement("yield", lineno+6)
    while foo():
        if condition():
            break
    else:
        await foo()
    yield  # error: 4, "yield", Statement("function definition", lineno-6)


# no checkpoint on break
async def foo_while_break_2():  # error: 0, "exit", Statement("yield", lineno+3)
    await foo()
    while foo():
        yield  # safe
        if condition():
            break
        await foo()


# guaranteed if else and break
async def foo_while_break_3():  # error: 0, "exit", Statement("yield", lineno+7)
    while foo():
        await foo()
        if condition():
            break  # if it breaks, have checkpointed
    else:
        await foo()  # runs if 0-iter
    yield  # safe


# break at non-guaranteed checkpoint
async def foo_while_break_4():  # error: 0, "exit", Statement("yield", lineno+7)
    while foo():
        if condition():
            break
        await foo()  # might not run
    else:
        await foo()  # might not run
    yield  # error: 4, "yield", Statement("function definition", lineno-7)


# check break is reset on nested
async def foo_while_break_5():  # error: 0, "exit", Statement("yield", lineno+12)
    await foo()
    while foo():
        yield
        if condition():
            break
        await foo()
        while foo():
            yield  # safe
            await foo()
        yield  # safe
        await foo()
    yield  # error: 4, "yield", Statement("yield", lineno-9)


# check multiple breaks
async def foo_while_break_6():  # error: 0, "exit", Statement("yield", lineno+11)
    await foo()
    while foo():
        yield
        if condition():
            break
        await foo()
        yield
        await foo()
        if condition():
            break
    yield  # error: 4, "yield", Statement("yield", lineno-8)


async def foo_while_break_7():  # error: 0, "exit", Statement("function definition", lineno)# error: 0, "exit", Statement("yield", lineno+5)
    while foo():
        await foo()
        if condition():
            break
        yield
        break


async def foo_while_endless_1():
    while True:
        await foo()
        yield


async def foo_while_endless_2():  # error: 0, "exit", Statement("function definition", lineno)# error: 0, "exit", Statement("yield", lineno+3)
    while foo():
        await foo()
        yield


async def foo_while_endless_3():
    while True:
        ...
    yield  # type: ignore[unreachable]
    await foo()


async def foo_while_endless_4():
    await foo()
    while True:
        yield
        while True:
            await foo()
            yield


# try
async def foo_try_1():  # error: 0, "exit", Statement("function definition", lineno) # error: 0, "exit", Statement("yield", lineno+2)
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


async def foo_try_7():  # error: 0, "exit", Statement("yield", lineno+17)
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
    # Then the error will be propagated upwards
    yield  # safe


## safe only if (try or else) and all except bodies either await or raise
## if foo() raises a ValueError it's not checkpointed, and may or may not yield
async def foo_try_8():  # error: 0, "exit", Statement("function definition", lineno) # error: 0, "exit", Statement("yield", lineno+3)
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


# no checkpoint after yield in else
async def foo_try_9():  # error: 0, "exit", Statement("yield", lineno+6)
    try:
        await foo()
    except:
        await foo()
    else:
        yield


# bare except means we'll jump to finally after full execution of either try or the except
async def foo_try_10():
    try:
        await foo()
    except:
        await foo()
    finally:
        yield
        await foo()


async def foo_try_10_BaseException():
    try:
        await foo()
    except BaseException:
        await foo()
    finally:
        yield
        await foo()


# not fully covering excepts
async def foo_try_10_exception():
    try:
        await foo()
    except ValueError:
        await foo()
    finally:
        yield  # error: 8, "yield", Statement("function definition", lineno-6)
        await foo()


async def foo_try_10_no_except():
    try:
        await foo()
    finally:
        # try might crash before checkpoint
        yield  # error: 8, "yield", Statement("function definition", lineno-5)
        await foo()


# if
async def foo_if_1():
    if condition():
        yield  # error: 8, "yield", Statement("function definition", lineno-2)
        await foo()
    else:
        yield  # error: 8, "yield", Statement("function definition", lineno-5)
        await foo()


async def foo_if_2():  # error: 0, "exit", Statement("yield", lineno+6)
    await foo()
    if condition():
        ...
    else:
        yield
    yield  # error: 4, "yield", Statement("yield", lineno-1)


async def foo_if_3():  # error: 0, "exit", Statement("yield", lineno+6)
    await foo()
    if condition():
        yield
    else:
        ...
    yield  # error: 4, "yield", Statement("yield", lineno-3)


async def foo_if_4():  # error: 0, "exit", Statement("yield", lineno+7)
    await foo()
    yield
    if condition():
        await foo()
    else:
        ...
    yield  # error: 4, "yield", Statement("yield", lineno-5)


async def foo_if_5():  # error: 0, "exit", Statement("yield", lineno+8)
    await foo()
    if condition():
        yield
        await foo()
    else:
        yield
        ...
    yield  # error: 4, "yield", Statement("yield", lineno-2)


async def foo_if_6():  # error: 0, "exit", Statement("yield", lineno+8)
    await foo()
    if condition():
        yield
    else:
        yield
        await foo()
        ...
    yield  # error: 4, "yield", Statement("yield", lineno-5)


async def foo_if_7():  # error: 0, "exit", Statement("function definition", lineno)
    if condition():
        await foo()
        yield
        await foo()


async def foo_if_8():  # error: 0, "exit", Statement("function definition", lineno)
    if condition():
        ...
    else:
        await foo()
        yield
        await foo()


# IfExp
async def foo_ifexp_1():  # error: 0, "exit", Statement("yield", lineno+1) # error: 0, "exit", Statement("yield", lineno+1)
    print((yield) if await foo() else (yield))


# Will either enter else, and it's a guaranteed checkpoint - or enter if, in which
# case the problem is the yield.
async def foo_ifexp_2():  # error: 0, "exit", Statement("yield", lineno+2)
    print(
        (yield)  # error: 9, "yield", Statement("function definition", lineno-2)
        if condition() and await foo()
        else await foo()
    )


# normal function
def foo_sync_1():
    return


def foo_sync_2(): ...


def foo_sync_3():
    yield


def foo_sync_4():
    if condition():
        return
    yield


def foo_sync_5():
    if condition():
        return
    yield


def foo_sync_6():
    while foo():
        yield


def foo_sync_7():
    while foo():
        if condition():
            return
        yield


# nested function definition
async def foo_func_1():
    await foo()

    async def foo_func_2():  # error: 4, "exit", Statement("yield", lineno+1)
        yield  # error: 8, "yield", Statement("function definition", lineno-1)


# autofix doesn't insert newline after nested function def and before checkpoint
# so we need to disable black
# fmt: off
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
# fmt: on


# No error from function definition, but may shortcut after yield
async def foo_boolops_1():  # error: 0, "exit", Stmt("yield", line+1)
    _ = await foo() and (yield) and await foo()


# loop over non-empty static collection
async def foo_loop_static():
    # break/else behaviour on guaranteed body execution
    for _ in [1, 2, 3]:
        await foo()
    else:
        yield
    await foo()
    yield

    for _ in [1, 2, 3]:
        await foo()
        if condition():
            break
    else:
        yield
        await foo()
    yield

    # continue
    for _ in [1, 2, 3]:
        if condition():
            continue
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-7)

    # continue/else
    for _ in [1, 2, 3]:
        if condition():
            continue
        await foo()
    else:
        yield  # error: 8, "yield", Stmt("yield", line-8)
    await foo()
    yield

    for _ in [1, 2, 3]:
        await foo()
        if condition():
            break
    else:
        yield
        await foo()
    yield

    # test different containers
    for _ in (1, 2, 3):
        await foo()
    yield

    for _ in (foo(), foo()):
        await foo()
    yield

    for _ in ((),):
        await foo()
    yield

    for _ in "hello":
        await foo()
    yield

    for _ in b"hello":
        await foo()
    yield

    for _ in r"hello":
        await foo()
    yield

    for _ in {1, 2, 3}:
        await foo()
    yield

    for _ in ():
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    for _ in {1: 2, 3: 4}:
        await foo()
    yield

    for _ in "   ".strip():
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    for _ in range(0):
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    for _ in (*range(0),):
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    for _ in (*(1, 2),):
        await foo()
    yield

    for _ in {**{}}:
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    for _ in {**{}, **{}}:
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    for _ in {**{1: 2}}:
        await foo()
    yield

    for _ in (*range(0), *[1, 2, 3]):
        await foo()
    yield

    for _ in {**{}, **{1: 2}}:  # type: ignore[arg-type]
        await foo()
    yield

    x: Any = ...
    for _ in (*x, *[1, 2, 3]):
        await foo()
    yield

    for _ in {**x, **{1: 2}}:
        await foo()
    yield

    for _ in {}:
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    for _ in "":
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    for _ in """""":
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    for _ in [[], []][0]:
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    for _ in [[], []].__getitem__(0):
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    # not handled
    for _ in list((1, 2)):
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-5)

    for _ in list():
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    # while
    while True:
        await foo()
        if condition():
            break
    yield

    while True:
        if condition():
            break
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-6)

    while True:
        if condition():
            continue
        await foo()
        if condition():
            break
    yield

    while False:
        await foo()  # type: ignore[unreachable]
    yield  # error: 4, "yield", Stmt("yield", line-4)

    while "hello":
        await foo()
    yield

    # false positive on containers
    while [1, 2]:
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-5)

    # will get caught by any number of linters, but trio911 will also complain
    for _ in 5:  # type: ignore
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-5)

    # range with constant arguments also handled, see more extensive tests in 910
    for i in range(5):
        await foo()
    yield

    for i in range(0x23):
        await foo()
    yield

    for i in range(0b01):
        await foo()
    yield

    for i in range(1 + 1):  # not handled
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    for i in range(None):  # type: ignore
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    for i in range(+3):
        await foo()
    yield

    for i in range(-3.5):  # type: ignore
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    # duplicated from 910 to have all range tests in one place
    for i in range(5, 10):
        await foo()
    yield

    for i in range(10, 5, -1):
        await foo()
    yield

    # ~0 == -1
    for i in range(10, 5, ~0):
        await foo()
    yield

    # length > sys.maxsize
    for i in range(27670116110564327421):
        await foo()
    yield

    for i in range(10, 5):
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    # binary operations are not handled
    for i in range(3 - 2):
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-5)

    for i in range(10**3):
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-4)

    # nor nested unary operations
    for i in range(--3):
        await foo()
    yield  # error: 4, "yield", Stmt("yield", line-5)

    await foo()


# don't warn on pytest.fixture
@pytest.fixture
async def foo_test():
    yield


@pytest.fixture()
async def foo_test2():
    yield


async def comprehensions():
    # guaranteed iteration with await in test
    [... for x in range(10) if await foo()]
    yield  # safe

    # guaranteed iteration and await in value, but test is not guaranteed
    [await foo() for x in range(10) if bar()]
    yield  # error: 4, "yield", Stmt("yield", line-4)

    # guaranteed iteration and await in value
    [await foo() for x in range(10)]
    yield  # safe

    # not guaranteed to iter
    [await foo() for x in bar()]
    yield  # error: 4, "yield", Stmt("yield", line-4)

    # await statement in loop expression
    [... for x in bar(await foo())]
    yield

    # set comprehensions use same logic as list
    {await foo() for x in range(10)}
    yield  # safe

    {await foo() for x in bar()}
    yield  # error: 4, "yield", Stmt("yield", line-3)

    # dict comprehensions use same logic as list
    {await foo(): 5 for x in bar()}
    yield  # error: 4, "yield", Stmt("yield", line-4)

    # other than `await` can be in both key&val
    {await foo(): 5 for x in range(10)}
    yield

    {5: await foo() for x in range(10)}
    yield

    # generator expressions are never treated as safe
    (await foo() for x in range(10))
    yield  # error: 4, "yield", Stmt("yield", line-4)

    (await foo() for x in bar() if await foo())
    yield  # error: 4, "yield", Stmt("yield", line-3)

    # async for always safe
    [... async for x in bar()]
    yield  # safe
    {... async for x in bar()}
    yield  # safe
    {...: ... async for x in bar()}
    yield  # safe

    # other than in generator expression
    (... async for x in bar())
    yield  # error: 4, "yield", Stmt("yield", line-4)

    # multiple loops
    [... for x in range(10) for y in range(10) if await foo()]
    yield
    [... for x in range(10) for y in bar() if await foo()]
    yield  # error: 4, "yield", Stmt("yield", line-2)
    [... for x in bar() for y in range(10) if await foo()]
    yield  # error: 4, "yield", Stmt("yield", line-2)

    [await foo() for x in range(10) for y in range(10)]
    yield
    [await foo() for x in range(10) for y in bar()]
    yield  # error: 4, "yield", Stmt("yield", line-2)
    [await foo() for x in bar() for y in range(10)]
    yield  # error: 4, "yield", Stmt("yield", line-2)

    # trip loops!
    [... for x in range(10) for y in range(10) async for z in bar()]
    yield
    [... for x in range(10) for y in range(10) for z in range(10)]
    yield  # error: 4, "yield", Stmt("yield", line-2)

    # multiple ifs
    [... for x in range(10) for y in range(10) if await foo() if await foo()]
    yield

    [... for x in range(10) for y in bar() if await foo() if await foo()]
    yield  # error: 4, "yield", Stmt("yield", line-3)

    # nested comprehensions
    [[await foo() for x in range(10)] for y in range(10)]
    yield

    # code coverage: inner comprehension with no checkpointed statements
    [... for x in [await foo()] for y in x]
