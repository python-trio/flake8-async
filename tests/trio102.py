from contextlib import asynccontextmanager

import trio


async def foo():
    try:
        pass
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
        await foo()  # error

    try:
        pass
    finally:
        with trio.move_on_after(30) as s:
            await foo()  # error

    try:
        pass
    finally:
        with trio.move_on_after(30):
            await foo()  # error

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
            await foo()  # error
            s.shield = True
            await foo()

    try:
        pass
    finally:
        with open("bar"):
            await foo()  # safe
        with open("bar"):
            pass
        with trio.move_on_after():
            await foo()  # error
        with trio.move_on_after(foo=bar):
            await foo()  # error
        with trio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
        with trio.CancelScope(shield=True):
            await foo()  # error
        with trio.CancelScope(deadline=30):
            await foo()  # error
        with trio.CancelScope(deadline=30, shield=(1 == 1)):
            await foo()  # safe in theory, but deemed error
        myvar = True
        with trio.open_nursery(10) as s:
            s.shield = myvar
            await foo()  # safe in theory, but deemed error
        with trio.CancelScope(deadline=30, shield=True):
            with trio.move_on_after(30):
                await foo()  # safe
        async for i in trio.bypasslinters:  # error
            pass
        async with trio.CancelScope(deadline=30, shield=True):  # error
            await foo()  # safe

    with trio.CancelScope(deadline=30, shield=True):
        try:
            pass
        finally:
            await foo()  # error


@asynccontextmanager
async def foo2():
    try:
        yield 1
    finally:
        await foo()  # safe


async def foo3():
    try:
        pass
    finally:
        with trio.move_on_after(30) as s, trio.fail_after(5):
            s.shield = True
            await foo()  # safe
        with open(""), trio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
        with trio.fail_after(5), trio.move_on_after(30) as s:
            s.shield = True
            await foo()  # safe in theory, but we don't bother parsing
