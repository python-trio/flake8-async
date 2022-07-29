import trio

with trio.move_on_after(10):  # error
    pass


async def function_name():
    async with trio.fail_after(10):  # error
        pass

    with trio.move_on_after(10):
        await trio.sleep(1)

    with trio.move_on_after(10):
        await trio.sleep(1)
        print("hello")

    with trio.move_on_after(10):
        while True:
            await trio.sleep(1)
        print("hello")

    with open("filename") as _:
        pass

    with trio.fail_after(10):  # error
        pass

    send_channel, receive_channel = trio.open_memory_channel(0)
    async with trio.fail_after(10):
        async with send_channel:
            pass
    async with trio.fail_after(10):
        async for _ in receive_channel:
            pass
