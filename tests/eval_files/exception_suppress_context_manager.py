# ARG --exception-suppress-context-managers=mysuppress,*.dangerousname,dangerouslibrary.*
# ARG --enable=ASYNC910,ASYNC911

# AUTOFIX
# ASYNCIO_NO_AUTOFIX

# 912 is tested in eval_files/async912.py to avoid problems with autofix/asyncio

import contextlib
from typing import Any

import trio

mysuppress: Any
anything: Any
dangerouslibrary: Any


async def foo() -> Any:
    await foo()


async def foo_suppress():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with contextlib.suppress():
        await foo()


async def foo_suppress_1():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with mysuppress():
        await foo()


async def foo_suppress_2():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with anything.dangerousname():
        await foo()


async def foo_suppress_3():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with dangerouslibrary.anything():
        await foo()


async def foo_suppress_async911():  # ASYNC911: 0, "exit", Statement("function definition", lineno)
    with contextlib.suppress():
        await foo()
        yield
        await foo()


# the `async with` checkpoints, so there's no error
async def foo_suppress_async():
    async with mysuppress:
        await foo()


async def foo_multiple():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with anything, contextlib.suppress():
        await foo()


# we only match on *calls*
async def foo_no_call():
    with contextlib.suppress:  # type: ignore[attr-defined]
        await foo()


# doesn't work on namedexpr, but those should use `as` anyway
async def foo_namedexpr():
    with (ref := contextlib.suppress()):
        await foo()


async def foo_suppress_as():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with contextlib.suppress() as my_suppressor:
        await foo()


# ###############################
# from contextlib import suppress
# ###############################


# not enabled unless it's imported from contextlib
async def foo_suppress_directly_imported_1():
    with suppress():
        await foo()


from contextlib import suppress


# now it's enabled
async def foo_suppress_directly_imported_2():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with suppress():
        await foo()


# it also supports importing with an alias
from contextlib import suppress as adifferentname


async def foo_suppress_directly_imported_3():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with adifferentname():
        await foo()


# and will keep track of all identifiers it's been assigned as
async def foo_suppress_directly_imported_4():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with suppress():
        await foo()


# basic function scoping is supported
async def function_that_contains_the_import():
    from contextlib import suppress as bar

    with adifferentname():
        await foo()
    yield  # ASYNC911: 4, "yield", Stmt("function definition", lineno-5)
    with bar():
        await foo()
    yield  # ASYNC911: 4, "yield", Stmt("yield", lineno-3)
    await foo()


# bar is not suppressing
async def foo_suppress_directly_imported_scoped():
    with bar():  # type: ignore[name-defined]
        await foo()


# adifferentname is still suppressing
async def foo_suppress_directly_imported_restored_after_scope():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with adifferentname():
        await foo()


# We don't track the identifier being overridden though.
adifferentname = None  # type: ignore[assignment]


# shouldn't give an error
async def foo_suppress_directly_imported_5():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with adifferentname():
        await foo()


# or assignments to different identifiers
from contextlib import suppress

my_second_suppress = suppress


# should give an error
async def foo_suppress_directly_imported_assignment():
    with my_second_suppress():
        await foo()
