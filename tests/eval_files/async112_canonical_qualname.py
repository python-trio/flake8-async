# Regression test for https://github.com/python-trio/flake8-async/issues/132:
# detection works regardless of how trio is imported.
# type: ignore
# ASYNCIO_NO_ERROR
# ARG --enable=ASYNC112

import trio
import trio as t
from trio import open_nursery
from trio import open_nursery as on


# `import trio as t`
with t.open_nursery() as n:  # error: 5, "n", "nursery"
    n.start(...)


# `from trio import open_nursery`
with open_nursery() as n:  # error: 5, "n", "nursery"
    n.start(...)


# `from trio import open_nursery as on`
with on() as n:  # error: 5, "n", "nursery"
    n.start_soon(...)


# canonical name still matches when chained through an ordinary `import trio`
with trio.open_nursery() as n:  # error: 5, "n", "nursery"
    n.start(...)
