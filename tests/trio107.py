import typing
from typing import Union, overload

_ = ""


async def foo():
    await foo()


async def foo2():  # error: 0
    ...


# If
async def foo_if_1():  # error: 0
    if _:
        await foo()


async def foo_if_2():
    if _:
        await foo()
    else:
        await foo()


async def foo_if_3():
    await foo()
    if _:
        ...


async def foo_if_4():  # error: 0
    if await foo():
        ...


# IfExp
async def foo_ifexp_1():  # safe
    print(await foo() if _ else await foo())


async def foo_ifexp_2():  # error: 0
    print(_ if await foo() else await foo())


# loops
async def foo_while_1():  # error: 0
    while _:
        await foo()


# due to not wanting to handle continue/break semantics
async def foo_while_2():  # error: 0
    while _:
        await foo()
    else:
        await foo()


async def foo_while_3():  # safe
    await foo()
    while _:
        ...


async def foo_for_1():  # error: 0
    for __ in _:
        await foo()


# due to not wanting to handle continue/break semantics
async def foo_for_2():  # error: 0
    for __ in _:
        await foo()
    else:
        await foo()


# try
# safe only if (try or else) and all except bodies either await or raise
# if foo() raises a ValueError it's not checkpointed
async def foo_try_1():  # error: 0
    try:
        await foo()
    except ValueError:
        ...
    except:
        raise
    else:
        await foo()


async def foo_try_2():  # safe
    try:
        ...
    except ValueError:
        ...
    except:
        raise
    finally:
        await foo()


async def foo_try_3():  # safe
    try:
        await foo()
    except ValueError:
        await foo()
    except:
        raise


# raise
async def foo_raise_1():  # safe
    raise ValueError()


async def foo_raise_2():  # safe
    if _:
        await foo()
    else:
        raise ValueError()


async def foo_try_4():  # safe
    try:
        ...
    except ValueError:
        raise
    except:
        raise
    else:
        await foo()


# early return
async def foo_return_1():  # silent to avoid duplicate errors
    return  # TRIO108


async def foo_return_2():  # safe
    if _:
        return  # TRIO108
    await foo()


async def foo_return_3():  # error: 0
    if _:
        await foo()
        return  # safe


# nested function definition
async def foo_func_1():
    await foo()

    async def foo_func_2():  # error: 4
        ...


async def foo_func_3():  # error: 0
    async def foo_func_4():
        await foo()


async def foo_func_5():  # error: 0
    def foo_func_6():  # safe
        async def foo_func_7():  # error: 8
            ...


async def foo_func_8():  # error: 0
    def foo_func_9():
        raise


# normal function
def foo_normal_func_1():
    return


def foo_normal_func_2():
    ...


# overload decorator
@overload
async def foo_overload_1(_: bytes):
    ...


@typing.overload
async def foo_overload_1(_: str):
    ...


async def foo_overload_1(_: Union[bytes, str]):
    await foo()
