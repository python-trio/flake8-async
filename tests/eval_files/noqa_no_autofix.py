# ARG --enable=ASYNC102
# ASYNCIO_NO_ERROR  # ASYNC102 not applicable to asyncio

import trio
from typing import Any


# errors from AST visitors
async def foo() -> Any: ...


async def foo_no_noqa_102():
    try:
        pass
    finally:
        await foo()  # ASYNC102: 8, Statement("try/finally", lineno-3)


async def foo_noqa_102():
    try:
        pass
    finally:
        await foo()  # noqa: ASYNC102


async def foo_bare_noqa_102():
    try:
        pass
    finally:
        await foo()  # noqa
