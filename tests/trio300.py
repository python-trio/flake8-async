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
        ...
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


async def foo_try_3():  # safe
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
async def foo_return_1():  # error
    return


async def foo_return_2():  # safe
    await foo()
    return


async def foo_return_3():  # error
    if _:
        await foo()
    return


# raise
async def foo_raise_1():  # safe
    raise ValueError()


async def foo_raise_2():  # safe
    if _:
        await foo()
    else:
        raise ValueError()
