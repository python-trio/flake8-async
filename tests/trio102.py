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

    try:
        pass
    finally:
        with trio.move_on_after(30) as s, trio.fail_after(5):
            s.shield = True
            await foo()  # error?

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
            await foo()
        with open("bar"):
            pass
        with trio.move_on_after():
            await foo()
        with trio.move_on_after(foo=bar):
            await foo()
