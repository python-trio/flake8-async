import trio


async def function_name():
    with (
        open("") as _,
        trio.fail_after(10),  # error: 8, trio.fail_after
    ):
        pass

    with (
        trio.fail_after(5),  # error: 8, trio.fail_after
        open("") as _,
        trio.move_on_after(5),  # error: 8, trio.move_on_after
    ):
        pass
