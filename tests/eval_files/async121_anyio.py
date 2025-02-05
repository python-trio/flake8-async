# ASYNCIO_NO_ERROR # checked in async121_asyncio.py
# BASE_LIBRARY anyio

import anyio


# To avoid mypy unreachable-statement we wrap control flow calls in if statements
# they should have zero effect on the visitor logic.
def condition() -> bool:
    return False


# only tests that asyncio.TaskGroup is detected, main tests in async121.py
async def foo_return():
    while True:
        async with anyio.create_task_group():
            if condition():
                continue  # ASYNC121: 16, "continue", "task group"
            if condition():
                break  # ASYNC121: 16, "break", "task group"
            return  # ASYNC121: 12, "return", "task group"
