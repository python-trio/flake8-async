# ensure that import gets added when adding checkpoints at end of function body

# AUTOFIX
# ASYNCIO_NO_AUTOFIX


def condition() -> bool:
    return False


async def foo():  # ASYNC910: 0, "exit", Stmt("function definition", line)
    print()
