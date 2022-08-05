import trio
import trio as noerror


async def sleep():
    return


async def foo():
    await trio.sleep()  # ok
    await sleep()
    await noerror.sleep()
    await trio.Event()

    while ...:
        await trio.sleep()  # error: 8
        await trio.sleep()  # error: 8
        await sleep()
        await noerror.sleep()
        await trio.Event()

    for _ in "":
        await trio.sleep()  # error: 8
        await sleep()
        await noerror.sleep()
        await trio.Event()

    async for _ in trio.blah:
        await trio.sleep()  # error: 8
        await sleep()
        await noerror.sleep()
        await trio.Event()

    while ...:
        await trio.sleep()  # error: 8

        async def blah():
            await trio.sleep()

        await trio.sleep()  # error: 8

    while ...:
        while ...:
            await trio.sleep()  # error: 12
        await trio.sleep()  # error: 8

    while ...:
        if ...:
            await trio.sleep()  # error: 12

    while await trio.sleep():  # error: 10
        ...
