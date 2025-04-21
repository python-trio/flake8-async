# type: ignore
# AUTOFIX
# ASYNCIO_NO_ERROR # timeout primitives are named differently in asyncio

import contextlib
import trio


def condition() -> bool:
    return False


# error: 5, "trio", "move_on_after"
...


async def function_name():
    # fmt: off
    ...; ...; ...  # error: 15, "trio", "fail_after"
    # fmt: on
    # error: 15, "trio", "fail_after"
    ...
    # error: 15, "trio", "fail_at"
    ...
    # error: 15, "trio", "move_on_after"
    ...
    # error: 15, "trio", "move_on_at"
    ...
    # error: 15, "trio", "CancelScope"
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

    # error: 9, "trio", "fail_after"
    ...

    send_channel, receive_channel = trio.open_memory_channel(0)
    async with trio.fail_after(10):
        async with send_channel:
            ...

    async with trio.fail_after(10):
        async for _ in receive_channel:
            ...

    # error: 15, "trio", "fail_after"
    for _ in receive_channel:
        ...

    # fix missed alarm when function is defined inside the with scope
    # error: 9, "trio", "move_on_after"

    async def foo():
        await trio.sleep(1)

    # error: 9, "trio", "move_on_after"
    if ...:

        async def foo():
            if ...:
                await trio.sleep(1)

    async with random_ignored_library.fail_after(10):
        ...


# The outer cancelscope can get triggered in more complex cases, so
# to avoid false positives we don't raise a warning.
async def does_contain_checkpoints():
    with trio.fail_after(1):
        with trio.CancelScope():
            await trio.sleep_forever()


async def more_nested_tests():
    with trio.fail_after(1):
        with trio.CancelScope():
            await trio.sleep_forever()
        # error: 13, "trio", "CancelScope"
        ...
        with trio.CancelScope():
            await trio.sleep_forever()
        # error: 13, "trio", "CancelScope"
        ...

    # error: 9, "trio", "fail_after"
    # error: 13, "trio", "CancelScope"
    ...
    # error: 13, "trio", "CancelScope"
    ...

    with trio.fail_after(1):
        with trio.CancelScope():
            with trio.CancelScope():
                with trio.CancelScope():
                    await trio.sleep_forever()

    # don't remove other scopes
    with contextlib.suppress(Exception):
        print("foo")
    # error: 9, "trio", "fail_after"
    with contextlib.suppress(Exception):
        print("foo")
    with contextlib.suppress(Exception):
        # error: 13, "trio", "fail_after"
        print("foo")

    with contextlib.suppress(Exception):
        with open("blah") as file:
            print("foo")


# Don't trigger for blocks with a yield statement
async def foo():
    with trio.fail_after(1):
        yield


# This previously caused an AssertionError, see issue #295
async def fn(timeout):
    with trio.fail_after(timeout):
        while True:
            if condition():
                return
            await trio.sleep(1)


async def dont_crash_on_non_name_or_attr_call():
    async with contextlib.asynccontextmanager(agen_fn)():
        ...


async def another_weird_with_call():
    async with a().b():
        ...


# ---open_nursery / create_task_group stuff---


async def nursery_no_cancel_point():
    # error: 9, "trio", "CancelScope"
    async with trio.open_nursery():
        ...


# but it is a cancel point if the nursery contains a call to start_soon()


async def nursery_start_soon():
    with trio.CancelScope():
        async with trio.open_nursery() as n:
            n.start_soon(trio.sleep, 0)


async def nursery_start_soon_misnested():
    async with trio.open_nursery() as n:
        # error: 13, "trio", "CancelScope"
        n.start_soon(trio.sleep, 0)


async def nested_scope():
    with trio.CancelScope():
        with trio.CancelScope():
            async with trio.open_nursery() as n:
                n.start_soon(trio.sleep, 0)


async def nested_nursery():
    with trio.CancelScope():
        async with trio.open_nursery() as n:
            async with trio.open_nursery() as n2:
                n2.start_soon(trio.sleep, 0)


async def nested_function_call():

    # error: 9, "trio", "CancelScope"
    async with trio.open_nursery() as n:

        def foo():
            n.start_soon(trio.sleep, 0)

        # a false alarm in case we call foo()... but we can't check if they do
        foo()


# insert cancel point on nursery exit, not at the start_soon call
async def cancel_point_on_nursery_exit():
    with trio.CancelScope():
        async with trio.open_nursery() as n:
            # error: 17, "trio", "CancelScope"
            n.start_soon(trio.sleep, 0)


# async100 does not consider *redundant* cancel scopes
async def redundant_cancel_scope():
    with trio.CancelScope():
        with trio.CancelScope():
            await trio.lowlevel.checkpoint()


# but if it did then none of these scopes should be marked redundant
# The inner checks task startup, the outer checks task exit
async def nursery_exit_blocks_with_start():
    with trio.CancelScope():
        async with trio.open_nursery() as n:
            with trio.CancelScope():
                await n.start(trio.sleep, 0)


async def autofix_multi_withitem():
    with open("foo"):  # error: 9, "trio", "CancelScope"
        ...

    # this one is completely removed
    # error: 8, "trio", "CancelScope"
    # error: 8, "trio", "CancelScope"
    ...

    # these keep the `open`
    with (
        open("aa") as _,  # error: 8, "trio", "fail_after"
    ):
        ...

    with (
        open("bb") as _,  # error: 8, "trio", "move_on_after"
    ):
        ...

    with (
        open("cc") as f,
    ):
        ...
