import trio

with trio.open_nursery() as n:  # error: 0
    n.start(...)

with trio.open_nursery() as n:  # error: 0
    n.start_soon(...)

with trio.open_nursery() as n:  # error: 0
    n.start_soon(n=7)

with trio.open_nursery() as n:  # error in theory
    n.start_soon(lambda n: n + 1)

# safe?
with trio.open_nursery() as n, open("") as o:
    n.start(...)

# safe
with trio.open_nursery() as n:
    n.start(..., n, ...)

with trio.open_nursery() as n:
    n.start(..., foo=n, bar=...)

with trio.open_nursery() as n:
    n.start(foo=tuple(tuple(tuple(tuple(n)))))

with trio.open_nursery() as n:
    ...
    n.start_soon(...)

with trio.open_nursery() as n:
    n.start_soon(...)
    ...
