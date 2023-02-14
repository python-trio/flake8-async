# type: ignore
import functools
from functools import partial

import trio
import trio as noterror

# error
with trio.open_nursery() as n:  # error: 5, "n"
    n.start(...)

with trio.open_nursery(...) as nurse:  # error: 5, "nurse"
    nurse.start_soon(...)

with trio.open_nursery() as n:  # error: 5, "n"
    n.start_soon(n=7)


async def foo():
    async with trio.open_nursery() as n:  # error: 15, "n"
        n.start(...)


# weird ones with multiple `withitem`s
# but if split among several `with` they'd all be treated as error (or TRIO111), so
# treating as error for now.
with trio.open_nursery() as n, trio.open("") as n:  # error: 5, "n"
    n.start(...)

with open("") as o, trio.open_nursery() as n:  # error: 20, "n"
    n.start(o)

with trio.open_nursery() as n, trio.open_nursery() as nurse:  # error: 31, "nurse"
    nurse.start(n.start(...))

with trio.open_nursery() as n, trio.open_nursery() as n:  # error: 5, "n" # error: 31, "n"
    n.start(...)

# safe if passing variable as parameter
with trio.open_nursery() as n:
    n.start(..., n, ...)

with trio.open_nursery() as n:
    n.start(..., foo=n + 7, bar=...)

with trio.open_nursery() as n:
    n.start(foo=tuple(tuple(tuple(tuple(n)))))

# explicitly check for partial usage
with trio.open_nursery() as n:
    n.start(partial(tuple, n))

with trio.open_nursery() as n:
    n.start(partial(n, "foo"))

with trio.open_nursery() as n:
    n.start(functools.partial(tuple, n))

with trio.open_nursery() as n:
    n.start(functools.partial(n, "foo"))

# safe if multiple lines
with trio.open_nursery() as n:
    ...
    n.start_soon(...)

with trio.open_nursery() as n:
    n.start_soon(...)
    ...

# fmt: off
with trio.open_nursery() as n:
    n.start_soon(...) ; ...
# fmt: on

# n as a parameter to lambda is in fact not using it, but we don't parse
with trio.open_nursery() as n:
    n.start_soon(lambda n: n + 1)


# body isn't a call to n.start
async def foo_1():
    with trio.open_nursery(...) as n:
        await n.start(...)


# not *trio*.open_nursery
with noterror.open_nursery(...) as n:
    n.start(...)

# not trio.*open_nursery*
with trio.not_error(...) as n:
    n.start(...)

p = trio.not_error
# not *n*.start[_soon]
with trio.open_nursery() as n:
    p.start(...)

# not n.*start[_soon]*
with trio.open_nursery() as n:
    n.start_never(...)

# redundant nursery, not handled
with trio.open_nursery():
    pass

# code coverage: no variable name and body is an expression
with trio.open_nursery():
    print()
