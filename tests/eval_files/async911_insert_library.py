# ensure that import gets added when adding checkpoints in loop body

# AUTOFIX
# ASYNCIO_NO_AUTOFIX


def condition() -> bool:
    return False


async def foo():
    await foo()
    while condition():
        yield  # ASYNC911: 8, "yield", Stmt("yield", lineno)
    await foo()
