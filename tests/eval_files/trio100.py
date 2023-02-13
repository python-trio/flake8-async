# type: ignore
import trio

with trio.move_on_after(10):  # error: 5,"trio", "move_on_after"
    pass


async def function_name():
    async with trio.fail_after(10):  # error: 15,"trio", "fail_after"
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

    with trio.fail_after(10):  # error: 9,"trio", "fail_after"
        pass

    send_channel, receive_channel = trio.open_memory_channel(0)
    async with trio.fail_after(10):
        async with send_channel:
            pass
    async with trio.fail_after(10):
        async for _ in receive_channel:
            pass


async def function_name2():
    with (
        open("") as _,
        trio.fail_after(10),  # error: 8, "trio", "fail_after"
    ):
        pass

    with (
        trio.fail_after(5),  # error: 8, "trio", "fail_after"
        open("") as _,
        trio.move_on_after(5),  # error: 8, "trio", "move_on_after"
    ):
        pass
