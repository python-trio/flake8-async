import trio

_ = ""


async def foo():
    await foo()


async def foo2():  # error
    ...


# If
async def foo_if_1():  # error
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


async def foo_if_4():  # error
    if await foo():
        ...


# IfExp
async def foo_ifexp_1():  # safe
    print(await foo() if _ else await foo())


async def foo_ifexp_2():  # error
    print(_ if await foo() else await foo())


# loops
async def foo_while_1():  # error
    while _:
        await foo()


async def foo_while_2():  # error: due to not wanting to handle continue/break semantics
    while _:
        await foo()
    else:
        await foo()


async def foo_while_3():  # safe
    await foo()
    while _:
        ...


async def foo_for_1():  # error
    for __ in _:
        await foo()


async def foo_for_2():  # error: due to not wanting to handle continue/break semantics
    for __ in _:
        await foo()
    else:
        await foo()


# try
async def foo_try_1():  # error
    try:
        await foo()
    except ValueError:
        await foo()
    except:
        await foo()


async def foo_try_2():  # safe
    try:
        await foo()
    except ValueError:
        await foo()
    except:
        await foo()
    finally:
        with trio.CancelScope(deadline=30, shield=True):  # avoid TRIO102
            await foo()


# early return
async def foo_return_1():  # silent to avoid duplicate errors
    return  # error


async def foo_return_2():  # safe
    if _:
        return  # error
    await foo()


async def foo_return_3():  # error
    if _:
        await foo()
        return  # safe


# raise
async def foo_raise_1():  # safe
    raise ValueError()


async def foo_raise_2():  # safe
    if _:
        await foo()
    else:
        raise ValueError()


# nested function definition
async def foo_func_1():
    await foo()

    async def foo_func_2():  # error
        ...


async def foo_func_3():  # error
    async def foo_func_4():
        await foo()


async def foo_func_5():  # error
    def foo_func_6():  # safe
        async def foo_func_7():  # error
            ...


async def foo_func_8():  # error
    def foo_func_9():
        raise


# normal function
def foo_normal_func_1():
    return


def foo_normal_func_2():
    ...
