# Regression test for https://github.com/python-trio/flake8-async/issues/132:
# rules fire against the canonical qualname regardless of import style.
# type: ignore
# ASYNCIO_NO_ERROR
# ARG --enable=ASYNC112

import trio
import trio as t
from trio import open_nursery
from trio import open_nursery as on

with t.open_nursery() as n:  # error: 5, "n", "nursery"
    n.start(...)


with open_nursery() as n:  # error: 5, "n", "nursery"
    n.start(...)


with on() as n:  # error: 5, "n", "nursery"
    n.start_soon(...)


with trio.open_nursery() as n:  # error: 5, "n", "nursery"
    n.start(...)
