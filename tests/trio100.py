import trio

with trio.move_on_after(10):
    pass


async def function_name():
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

    with (
        open("veryverylongfilenamesoshedsplitsthisintotwolines") as _,
        trio.fail_after(10),
    ):
        pass
