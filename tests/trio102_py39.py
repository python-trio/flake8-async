import trio


async def foo():
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
