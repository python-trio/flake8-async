# type: ignore
# AUTOFIX

import trio

with trio.move_on_after(10):  # error: 5, "trio", "move_on_after"
    ...


async def function_name():
    # fmt: off
    async with trio.fail_after(10): ...; ...; ...  # error: 15, "trio", "fail_after"
    # fmt: on
    async with trio.fail_after(10):  # error: 15, "trio", "fail_after"
        ...
    async with trio.fail_at(10):  # error: 15, "trio", "fail_at"
        ...
    async with trio.move_on_after(10):  # error: 15, "trio", "move_on_after"
        ...
    async with trio.move_on_at(10):  # error: 15, "trio", "move_on_at"
        ...
    async with trio.CancelScope(...):  # error: 15, "trio", "CancelScope"
        ...

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
        ...

    with trio.fail_after(10):  # error: 9, "trio", "fail_after"
        ...

    send_channel, receive_channel = trio.open_memory_channel(0)
    async with trio.fail_after(10):
        async with send_channel:
            ...

    async with trio.fail_after(10):
        async for _ in receive_channel:
            ...

    async with trio.fail_after(10):  # error: 15, "trio", "fail_after"
        for _ in receive_channel:
            ...

    # fix missed alarm when function is defined inside the with scope
    with trio.move_on_after(10):  # error: 9, "trio", "move_on_after"

        async def foo():
            await trio.sleep(1)

    with trio.move_on_after(10):  # error: 9, "trio", "move_on_after"
        if ...:

            async def foo():
                if ...:
                    await trio.sleep(1)

    async with random_ignored_library.fail_after(10):
        ...


# Seems like the inner context manager 'hides' the checkpoint.
async def does_contain_checkpoints():
    with trio.fail_after(1):  # false-alarm TRIO100
        with trio.CancelScope():  # or any other context manager
            await trio.sleep_forever()


async def more_nested_tests():
    with trio.fail_after(1):
        with trio.CancelScope():
            await trio.sleep_forever()
        with trio.CancelScope():  # error: 13, "trio", "CancelScope"
            ...
        with trio.CancelScope():
            await trio.sleep_forever()
        with trio.CancelScope():  # error: 13, "trio", "CancelScope"
            ...

    with trio.fail_after(1):  # error: 9, "trio", "fail_after"
        with trio.CancelScope():  # error: 13, "trio", "CancelScope"
            ...
        with trio.CancelScope():  # error: 13, "trio", "CancelScope"
            ...

    with trio.fail_after(1):
        with trio.CancelScope():
            with trio.CancelScope():
                with trio.CancelScope():
                    await trio.sleep_forever()

    # don't remove other scopes
    with contextlib.suppress(Exception):
        print("foo")
    with trio.fail_after(1):  # error: 9, "trio", "fail_after"
        with contextlib.suppress(Exception):
            print("foo")
    with contextlib.suppress(Exception):
        with trio.fail_after(1):  # error: 13, "trio", "fail_after"
            print("foo")

    with contextlib.suppress(Exception):
        with open("blah") as file:
            print("foo")
