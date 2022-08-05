timeout = 10


async def foo():
    ...


# args
async def foo_1(timeout):  # error: 16
    ...


# arg in args wih default & annotation
async def foo_2(timeout: int = 3):  # error: 16
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
    timeout,  # error: 4
):
    ...


# posonlyargs
async def foo_6(
    timeout,  # error: 4
    /,
    bar,
):
    ...


# kwonlyargs
async def foo_7(
    *,
    timeout,  # error: 4
):
    ...


# kwonlyargs (and kw_defaults)
async def foo_8(
    *,
    timeout=5,  # error: 4
):
    ...


async def foo_9(k=timeout):
    ...


# normal functions are not checked
def foo_10(timeout):
    ...


def foo_11(timeout, /):
    ...


def foo_12(*, timeout):
    ...
