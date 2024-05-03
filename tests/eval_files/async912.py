# ASYNCIO_NO_ERROR
import trio


async def foo():
    with trio.move_on_after(0.1):  # error: 4
        ...
    with trio.move_on_at(0.1):  # error: 4
        ...
    with trio.fail_after(0.1):  # error: 4
        ...
    with trio.fail_at(0.1):  # error: 4
        ...
    with trio.CancelScope(0.1):  # error: 4
        ...

    with open(""):
        ...

    with trio.move_on_after(0.1):
        await trio.lowlevel.checkpoint()

    with trio.move_on_after(0.1):  # error: 4
        with trio.move_on_after(0.1):  # error: 8
            ...

    with trio.move_on_after(0.1):  # TODO: should probably raise an error?
        with trio.move_on_after(0.1):
            await trio.lowlevel.checkpoint()

    with trio.move_on_after(0.1):
        await trio.lowlevel.checkpoint()
        with trio.move_on_after(0.1):
            await trio.lowlevel.checkpoint()

    with trio.move_on_after(0.1):
        with trio.move_on_after(0.1):
            await trio.lowlevel.checkpoint()
        await trio.lowlevel.checkpoint()

    # TODO: should probably raise the error at the call, rather than at the with statement
    # fmt: off
    with (  # error: 4
            # a
            # b
            trio.move_on_after(0.1)
            # c
            ):
        ...

    with (  # error: 4
            open(""),
            trio.move_on_at(5),
            open(""),
            ):
        ...
    # fmt: on

    # TODO: only raises one error currently, can make it raise 2(?)
    with (  # error: 4
        trio.move_on_after(0.1),
        trio.fail_at(5),
    ):
        ...


# TODO: issue #240
async def livelocks():
    with trio.move_on_after(0.1):  # should error
        while True:
            try:
                await trio.sleep("1")  # type: ignore
            except TypeError:
                pass


def condition() -> bool:
    return True


async def livelocks_2():
    with trio.move_on_after(0.1):  # error: 4
        while condition():
            try:
                await trio.sleep("1")  # type: ignore
            except TypeError:
                pass


# TODO: add --async912-context-managers=
async def livelocks_3():
    import contextlib

    with trio.move_on_after(0.1):  # should error
        while True:
            with contextlib.suppress(TypeError):
                await trio.sleep("1")  # type: ignore


# raises an error...?
with trio.move_on_after(10):  # error: 0
    ...


# completely sync function ... is this something we care about?
def sync_func():
    with trio.move_on_after(10):
        ...
