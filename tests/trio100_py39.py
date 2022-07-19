import trio


async def function_name():
    with (
        open("veryverylongfilenamesoshedsplitsthisintotwolines") as _,
        trio.fail_after(10),
    ):
        pass

    with (
        trio.fail_after(5),
        open("veryverylongfilenamesoshedsplitsthisintotwolines") as _,
        trio.move_on_after(5),
    ):
        pass
