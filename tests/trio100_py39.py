import trio


async def function_name():
    with (
        open("veryverylongfilenamesoshedsplitsthisintotwolines") as _,
        trio.fail_after(10),  # error
    ):
        pass

    with (
        trio.fail_after(5),  # error
        open("veryverylongfilenamesoshedsplitsthisintotwolines") as _,
        trio.move_on_after(5),  # error
    ):
        pass
    await function_name()  # avoid TRIO107
