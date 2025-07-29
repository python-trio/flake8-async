# ARG --enable=ASYNC109

import trio
from typing import Any


# errors from AST visitors
async def foo() -> Any: ...


async def foo_no_noqa_109(timeout):  # ASYNC109: 26, "trio"
    ...


async def foo_noqa_102(timeout):  # noqa: ASYNC109
    ...


async def foo_bare_noqa_109(timeout):  # noqa
    ...
