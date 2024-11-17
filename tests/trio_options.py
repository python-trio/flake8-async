"""Test file used in tests/test_decator.py to check decorator and command line."""

import asyncio

app = None


def condition() -> bool:
    return False


@app.route  # type: ignore
async def f():
    if condition():
        await asyncio.sleep(0)
