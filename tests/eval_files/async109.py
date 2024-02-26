# type: ignore
import trio
import trio as anything

timeout = 10


async def foo(): ...


# args
async def foo_1(timeout):  # error: 16, "trio"
    ...


# arg in args with default & annotation
async def foo_2(timeout: int = 3):  # error: 16, "trio"
    ...


# vararg
async def foo_3(*timeout):  # ignored
    ...


# kwarg
async def foo_4(**timeout):  # ignored
    ...


# correct line/col
async def foo_5(
    bar,
    timeouts,
    my_timeout,
    timeout_,
    timeout,  # error: 4, "trio"
): ...


# posonlyargs
async def foo_6(
    timeout,  # error: 4, "trio"
    /,
    bar,
): ...


# kwonlyargs
async def foo_7(
    *,
    timeout,  # error: 4, "trio"
): ...


# kwonlyargs (and kw_defaults)
async def foo_8(
    *,
    timeout=5,  # error: 4, "trio"
): ...


async def foo_9(k=timeout): ...


# normal functions are not checked
def foo_10(timeout): ...


def foo_11(timeout, /): ...


def foo_12(*, timeout): ...


# ignore all functions with a decorator
@anything.anything
async def foo_decorator_1(timeout): ...


@anything.anything
async def foo_decorator_2(*, timeout): ...


@anything
async def foo_decorator_3(timeout, /): ...
