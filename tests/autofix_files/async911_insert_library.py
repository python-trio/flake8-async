# ensure that import gets added when adding checkpoints in loop body

# AUTOFIX
# ASYNCIO_NO_AUTOFIX


import trio
def condition() -> bool:
    return False


async def foo():
    await foo()
    while condition():
        await trio.lowlevel.checkpoint()
        yield  # ASYNC911: 8, "yield", Stmt("yield", lineno)
    await foo()
