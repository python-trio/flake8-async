# ARG --enable=TRIO910,TRIO911
from typing import Any


async def foo() -> Any:
    await foo()


# not handled, but at least doesn't insert an unnecessary checkpoint
async def foo_singleline():
    await foo()
    # fmt: off
    yield; yield  # TRIO911: 11, "yield", Statement("yield", lineno, 4)
    # fmt: on
    await foo()


# not autofixed
async def foo_singleline2():
    # fmt: off
    yield; await foo()  # TRIO911: 4, "yield", Statement("function definition", lineno-2)
    # fmt: on


# not autofixed
async def foo_singleline3():
    # fmt: off
    if ...: yield  # TRIO911: 12, "yield", Statement("function definition", lineno-2)
    # fmt: on
    await foo()


# fmt: off
async def foo_async_with_2():
    # with'd expression evaluated before checkpoint
    async with (yield):  # TRIO911: 16, "yield", Statement("function definition", lineno-2)
        yield
# fmt: on

# fmt: off
async def foo_boolops_3():
    _ = (await foo() or (yield) or await foo()) or (
        ...
        or (
            (yield)  # TRIO911: 13, "yield", Stmt("yield", line-3)
            and (yield))  # TRIO911: 17, "yield", Stmt("yield", line-1)
    )
    await foo()
# fmt: on


async def foo_async_for():
    async for i in (
        yield  # TRIO911: 8, "yield", Statement("function definition", lineno-2)
    ):
        yield  # safe
    else:
        yield  # safe
    await foo()


# may shortcut after any of the yields
async def foo_boolops_2():
    # known false positive - but chained yields in bool should be rare
    _ = (
        await foo()
        and (yield)
        and await foo()
        and (yield)  # TRIO911: 13, "yield", Stmt("yield", line-2, 13)
    )
    await foo()
