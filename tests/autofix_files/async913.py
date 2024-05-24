# ARG --enable=ASYNC910,ASYNC911,ASYNC913
# AUTOFIX
# ASYNCIO_NO_AUTOFIX


import trio
def condition() -> bool:
    return False


async def foo():
    while True:  # ASYNC913: 4
        await trio.lowlevel.checkpoint()
        ...


async def foo2():
    while True:
        await foo()


async def foo3():
    while True:  # ASYNC913: 4
        await trio.lowlevel.checkpoint()
        if condition():
            await foo()


# ASYNC913 does not trigger on loops with break, but those will generally be handled
# by 910/911/912 if necessary
async def foo_break():  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    while True:
        if condition():
            break
    await trio.lowlevel.checkpoint()


# the inner loop will suppress the error in the outer loop
async def foo_nested():
    while True:
        while True:  # ASYNC913: 8
            await trio.lowlevel.checkpoint()
            ...


async def foo_conditional_nested():
    while True:  # ASYNC913: 4
        await trio.lowlevel.checkpoint()
        if condition():
            while True:  # ASYNC913: 12
                await trio.lowlevel.checkpoint()
                ...


# various checks I added for my own sanity to ensure autofixes worked when multiple
# codes simultaneously want to autofix.


async def foo_indef_and_910():
    while True:  # ASYNC913: 4
        await trio.lowlevel.checkpoint()
        if ...:
            await foo()
            return


async def foo_indef_and_910_2():
    while True:  # ASYNC913: 4
        await trio.lowlevel.checkpoint()
        if ...:
            return  # ASYNC910: 12, "return", Stmt("function definition", line-3)


async def foo_indef_and_911():
    await foo()
    while True:  # ASYNC913: 4
        await trio.lowlevel.checkpoint()
        if condition():
            yield  # ASYNC911: 12, "yield", Stmt("yield", line)  # ASYNC911: 12, "yield", Stmt("yield", line+2)
        if condition():
            await trio.lowlevel.checkpoint()
            yield  # ASYNC911: 12, "yield", Stmt("yield", line)  # ASYNC911: 12, "yield", Stmt("yield", line-2)  # ASYNC911: 12, "yield", Stmt("yield", line-2)


async def foo_indef_and_911_2():
    await foo()
    while True:  # ASYNC913: 4
        await trio.lowlevel.checkpoint()
        while condition():
            await trio.lowlevel.checkpoint()
            yield  # ASYNC911: 12, "yield", Stmt("yield", line)
