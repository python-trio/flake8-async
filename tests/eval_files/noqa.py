# NOAUTOFIX - TODO TODO TODO
# NOANYIO
# ARG --enable=TRIO100,TRIO102,TRIO911
import trio
from typing import Any


# fmt: off
async def foo_no_noqa():
    with trio.fail_after(5): yield  # TRIO100: 9, 'trio', 'fail_after'  # TRIO911: 29, "yield", Statement("function definition", lineno-1)
    await trio.lowlevel.checkpoint()


async def foo_noqa_bare():
    with trio.fail_after(5): yield  # noqa
    await trio.lowlevel.checkpoint()


async def foo_noqa_100():
    with trio.fail_after(5): yield  # noqa: TRIO100  # TRIO911: 29, "yield", Statement("function definition", lineno-1)
    await trio.lowlevel.checkpoint()


async def foo_noqa_911():
    with trio.fail_after(5): yield  # noqa: TRIO911  # TRIO100: 9, 'trio', 'fail_after'
    await trio.lowlevel.checkpoint()


async def foo_noqa_100_911():
    with trio.fail_after(5): yield  # noqa: TRIO100, TRIO911
    await trio.lowlevel.checkpoint()


async def foo_noqa_100_911_500():
    with trio.fail_after(5): yield  # noqa: TRIO100, TRIO911 , TRIO500,,,
    await trio.lowlevel.checkpoint()
# fmt: on


# errors from AST visitors
async def foo() -> Any:
    ...


async def foo_no_noqa_102():
    try:
        pass
    finally:
        await foo()  # TRIO102: 8, Statement("try/finally", lineno-3)


async def foo_noqa_102():
    try:
        pass
    finally:
        await foo()  # noqa: TRIO102


async def foo_bare_noqa_102():
    try:
        pass
    finally:
        await foo()  # noqa
