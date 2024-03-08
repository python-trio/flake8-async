# ASYNCIO_NO_ERROR - no asyncio.move_on_after
import trio


# Doesn't autofix With's with multiple withitems
async def function_name2():
    with (
        open("") as _,
        trio.fail_after(10),  # error: 8, "trio", "fail_after"
    ):
        ...

    with (
        trio.fail_after(5),  # error: 8, "trio", "fail_after"
        open("") as _,
        trio.move_on_after(5),  # error: 8, "trio", "move_on_after"
    ):
        ...


with (
    trio.move_on_after(10),  # error: 4, "trio", "move_on_after"
    open("") as f,
):
    ...
