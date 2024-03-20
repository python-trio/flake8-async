# type: ignore
# ASYNCIO_NO_ERROR - not yet supported # TODO
import trio
import trio as noerror


async def foo():
    # only trigger on while loop with body being exactly one sleep[_until] statement
    while ...:  # error: 4, "trio"
        await trio.sleep()

    while ...:  # error: 4, "trio"
        await trio.sleep_until()

    # nested

    while ...:  # safe
        while ...:  # error: 8, "trio"
            await trio.sleep()
        await trio.sleep()

    while ...:  # safe
        while ...:  # error: 8, "trio"
            await trio.sleep()

    ### the rest are all safe

    # don't trigger on bodies with more than one statement
    while ...:
        await trio.sleep()
        await trio.sleep()

    while ...:  # safe
        ...
        await trio.sleep()

    while ...:
        await trio.sleep()
        await trio.sleep_until()

    # check library name
    while ...:
        await noerror.sleep()

    async def sleep(): ...

    while ...:
        await sleep()

    # check function name
    while ...:
        await trio.sleepies()

    # don't trigger on [async] for
    for _ in "":
        await trio.sleep()

    async for _ in trio.blah:
        await trio.sleep()

    while ...:

        async def blah():
            await trio.sleep()

    while ...:
        if ...:
            await trio.sleep()

    while await trio.sleep():
        ...

    # also error when looping .lowlevel.checkpoint, which is equivalent to .sleep(0)
    # see https://github.com/python-trio/flake8-async/issues/201
    while ...:  # ASYNC110: 4, "trio"
        await trio.lowlevel.checkpoint()
