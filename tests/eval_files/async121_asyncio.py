# ANYIO_NO_ERROR
# TRIO_NO_ERROR # checked in async121.py
# BASE_LIBRARY asyncio
# TaskGroup was added in 3.11, we run type checking with 3.9
# mypy: disable-error-code=attr-defined

import asyncio


# To avoid mypy unreachable-statement we wrap control flow calls in if statements
# they should have zero effect on the visitor logic.
def condition() -> bool:
    return False


# only tests that asyncio.TaskGroup is detected, main tests in async121.py
async def foo_return():
    while True:
        async with asyncio.TaskGroup():
            if condition():
                continue  # ASYNC121: 16, "continue", "task group"
            if condition():
                break  # ASYNC121: 16, "break", "task group"
            return  # ASYNC121: 12, "return", "task group"
