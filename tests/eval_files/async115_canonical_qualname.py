# Regression test for https://github.com/python-trio/flake8-async/issues/132:
# rules should fire against the canonical qualname regardless of how a symbol
# is imported -- plain `import trio`, `import ... as ...`,
# `from ... import ...`, or `from ... import ... as ...`.
# type: ignore
# ASYNCIO_NO_ERROR - ASYNC115 is trio/anyio-only
# ARG --enable=ASYNC115

import trio as t
import trio.lowlevel as ll
from trio import sleep
from trio import sleep as nap
from trio.lowlevel import checkpoint as cp


async def afoo():
    # `import trio as t`
    await t.sleep(0)  # error: 10, "trio"

    # `from trio import sleep`
    await sleep(0)  # error: 10, "trio"

    # `from trio import sleep as nap`
    await nap(0)  # error: 10, "trio"

    # `import trio.lowlevel as ll` still resolves the canonical qualname
    # (we only track this for its side-effect on ASYNC110 elsewhere, but it
    # must not crash).
    ll.checkpoint()

    # `from trio.lowlevel import checkpoint as cp` -- ASYNC115 doesn't match this
    # particular qualname, but we just want to show resolution doesn't crash.
    cp()

    # non-aliased local name that shadows an import should not falsely match:
    # no import binds `sleep_2`, so `sleep_2(0)` is not flagged.
    sleep_2 = lambda x: None
    sleep_2(0)
