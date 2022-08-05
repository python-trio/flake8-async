from contextlib import asynccontextmanager

import trio


async def foo():
    try:
        ...
    finally:
        with trio.move_on_after(deadline=30) as s:
            s.shield = True
            await foo()

    try:
        pass
    finally:
        with trio.move_on_after(30) as s:
            s.shield = True
            await foo()

    try:
        pass
    finally:
        await foo()  # error: 8, 21, 4, try/finally

    try:
        pass
    finally:
        with trio.move_on_after(30) as s:
            await foo()  # error: 12, 26, 4, try/finally

    try:
        pass
    finally:
        with trio.move_on_after(30):
            await foo()  # error: 12, 32, 4, try/finally

    bar = 10

    try:
        pass
    finally:
        with trio.move_on_after(bar) as s:
            s.shield = True
            await foo()

    try:
        pass
    finally:
        with trio.move_on_after(bar) as s:
            s.shield = False
            s.shield = True
            await foo()

    try:
        pass
    finally:
        with trio.move_on_after(bar) as s:
            s.shield = True
            await foo()
            s.shield = False
            await foo()  # error: 12, 55, 4, try/finally
            s.shield = True
            await foo()

    try:
        pass
    finally:
        with open("bar"):
            await foo()  # error: 12, 66, 4, try/finally
        with open("bar"):
            pass
        with trio.move_on_after():
            await foo()  # error: 12, 66, 4, try/finally
        with trio.move_on_after(foo=bar):
            await foo()  # error: 12, 66, 4, try/finally
        with trio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
        with trio.CancelScope(shield=True):
            await foo()  # error: 12, 66, 4, try/finally
        with trio.CancelScope(deadline=30):
            await foo()  # error: 12, 66, 4, try/finally
        with trio.CancelScope(deadline=30, shield=(1 == 1)):
            await foo()  # safe in theory, error: 12, 66, 4, try/finally
        myvar = True
        with trio.open_nursery(10) as s:
            s.shield = myvar
            await foo()  # safe in theory, error: 12, 66, 4, try/finally
        with trio.CancelScope(deadline=30, shield=True):
            with trio.move_on_after(30):
                await foo()  # safe
        async for i in trio.bypasslinters:  # error: 8, 66, 4, try/finally
            pass
        async with trio.CancelScope(  # error: 8, 66, 4, try/finally
            deadline=30, shield=True
        ):
            await foo()  # safe

    with trio.CancelScope(deadline=30, shield=True):
        try:
            pass
        finally:
            await foo()  # error: 12, 100, 8, try/finally


@asynccontextmanager
async def foo2():
    try:
        yield 1
    finally:
        await foo()  # safe


async def foo3():
    try:
        ...
    finally:
        with trio.move_on_after(30) as s, trio.fail_after(5):
            s.shield = True
            await foo()  # safe
        with open(""), trio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
        with trio.fail_after(5), trio.move_on_after(30) as s:
            s.shield = True
            await foo()  # safe in theory, error: 12, $lineno-10, 4, try/finally


# New: except cancelled/baseexception are also critical
async def foo4():
    try:
        ...
    except ValueError:
        await foo()  # safe
    except trio.Cancelled:
        await foo()  # error: 8, $lineno-1, 11, trio.Cancelled
    except BaseException:
        await foo()  # error: 8, $lineno-1, 11, BaseException
    except:
        await foo()  # error: 8, $lineno-1, 4, bare except


async def foo5():
    try:
        ...
    except trio.Cancelled:
        with trio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
    except BaseException:
        with trio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
    except:
        with trio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
