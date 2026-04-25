# Regression test for https://github.com/python-trio/flake8-async/issues/132:
# rules fire against the canonical qualname regardless of import style.
# type: ignore
# ASYNCIO_NO_ERROR - ASYNC115 is trio/anyio-only
# ARG --enable=ASYNC115

import trio as t
import trio.lowlevel as ll
from trio import sleep
from trio import sleep as nap
from trio.lowlevel import checkpoint as cp


async def afoo():
    await t.sleep(0)  # error: 10, "trio"
    await sleep(0)  # error: 10, "trio"
    await nap(0)  # error: 10, "trio"

    # `import trio.lowlevel as ll` and `from trio.lowlevel import ... as ...`
    # are resolvable but aren't matched by ASYNC115 -- we're just asserting
    # that resolution doesn't misfire.
    ll.checkpoint()
    cp()

    # a local name that shadows nothing imported must not match
    sleep_2 = lambda x: None
    sleep_2(0)
