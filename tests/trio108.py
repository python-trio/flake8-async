import trio

_ = ""


async def foo():
    await foo()


# early return
async def foo_return_1():
    return  # error: 4, return


async def foo_return_2():  # safe
    if _:
        return  # error: 8, return
    await foo()


async def foo_return_3():  # TRIO103
    if _:
        await foo()
        return  # safe


async def foo_yield_1(delay, to):
    await foo()
    yield 5
    await foo()


async def foo_yield_2():
    yield  # error: 4, yield
    yield  # error: 4, yield
    await foo()


async def foo_yield_3():  # TRIO107: 0
    await foo()
    yield


async def foo_yield_4():
    yield  # error: 4, yield
    await (yield)  # error: 11, yield
    yield  # safe


async def foo_yield_return_1():
    yield  # error: 4, yield
    return  # error: 4, return


async def foo_yield_return_2():
    await foo()
    yield
    return  # error: 4, return


async def foo_yield_return_3():
    await foo()
    yield
    await foo()
    return


# async with
# async with guarantees checkpoint on at least one of entry or exit
async def foo_async_with():  # TRIO107: 0
    async with trio.fail_after(5):
        yield  # error: 8, yield


async def foo_async_with_2():  # TRIO107: 0
    # with'd expression evaluated before checkpoint
    async with (yield):  # error: 16, yield
        # not guaranteed that async with checkpoints on entry (or is that only for trio?)
        yield  # error: 8, yield


async def foo_async_with_3():  # TRIO107: 0
    async with trio.fail_after(5):
        ...
    yield  # safe


async def foo_async_with_4():  # TRIO107: 0
    async with trio.fail_after(5):
        yield  # error: 8, yield
        await foo()
    yield


async def foo_async_with_5():  # TRIO107: 0
    async with trio.fail_after(5):
        yield  # error: 8, yield
    yield  # error: 4, yield


# async for
async def foo_async_for():  # TRIO107: 0
    async for i in (yield):  # error: 20, yield
        yield  # safe
    else:
        yield  # safe


# await anext(iter) is not called on break
async def foo_async_for_2():  # TRIO107: 0
    async for i in trio.trick_pyright:
        yield
        if ...:
            break
    yield  # error: 4, yield


async def foo_async_for_3():  # safe
    async for i in trio.trick_pyright:
        yield


async def foo_async_for_4():  # safe
    async for i in trio.trick_pyright:
        yield
        continue


# for
async def foo_for():  # TRIO107: 0
    await foo()
    for i in "":
        yield  # error: 8, yield


# while
async def foo_while_0():  # TRIO107: 0
    while ...:
        await foo()
        if ...:
            break  # if it breaks, have checkpointed
    else:
        await foo()  # runs if 0-iter
    yield  # safe


async def foo_while_1():  # TRIO107: 0
    while ...:
        if ...:
            break
        await foo()  # might not run
    else:
        await foo()  # might not run
    yield  # error: 4, yield


async def foo_while_2():  # TRIO107: 0
    while ...:
        await foo()
    else:
        await foo()  # will always run
    yield  # safe


async def foo_while_3():  # TRIO107: 0
    await foo()
    while ...:
        yield  # error: 8, yield


# no checkpoint after yield if else is entered
async def foo_while_4():  # TRIO107: 0
    await foo()
    while ...:
        await foo()
        yield
    else:
        yield  # error: 8, yield


# no checkpoint after yield if else is entered
async def foo_while_5():  # TRIO107: 0
    while ...:
        yield  # error: 8, yield
        await foo()
    else:
        # might not enter loop body
        yield  # error: 8, yield


# Might not checkpoint after yield
async def foo_while_6():  # TRIO107: 0
    await foo()
    while ...:
        yield  # error: 8, yield
        if ...:
            continue
        await foo()


async def foo_while_7():  # TRIO107: 0
    await foo()
    while ...:
        yield  # safe
        if ...:
            break
        await foo()


# check nested TRIO107 is only printed once
async def foo_while_9():
    while ...:
        yield  # error: 8, yield

        async def foo_nested_error():  # TRIO107: 8
            yield  # error: 12, yield

    await foo()


async def foo_while_10():
    while ...:
        await foo()
        if ...:
            break
        yield
        break


# might execute loop body once, and continue the first time
# and therefore not checkpoint after yield
async def foo_while_11():  # TRIO107: 0
    await foo()
    while ...:
        yield  # error: 8, yield
        if ...:
            continue
        await foo()
        while ...:
            yield  # safe
            await foo()


async def foo_while_12():  # TRIO107: 0
    await foo()
    while ...:
        yield
        if ...:
            break
        await foo()
        while ...:
            yield  # safe
            await foo()
        yield  # safe
        await foo()
    yield  # error: 4, yield


# try
async def foo_try_1():  # TRIO107: 0
    try:
        yield  # error: 8, yield
    except:
        pass


# no checkpoint after yield in ValueError
async def foo_try_2():  # TRIO107: 0
    try:
        await foo()
    except ValueError:
        # try might not have checkpointed
        yield  # error: 8, yield
    except:
        await foo()
    else:
        pass


async def foo_try_3():  # TRIO107: 0
    try:
        ...
    except:
        await foo()
    else:
        yield  # error: 8, yield


async def foo_try_4():  # safe
    try:
        ...
    except:
        yield  # error: 8, yield
    finally:
        await foo()


async def foo_try_5():
    try:
        await foo()
    finally:
        # try might crash before checkpoint
        yield  # error: 8, yield
        await foo()


async def foo_try_6():
    try:
        await foo()
    except ValueError:
        pass
    yield 1  # error: 4, yield


# if
async def foo_if_1():
    if ...:
        yield  # error: 8, yield
        await foo()
    else:
        yield  # error: 8, yield
        await foo()


# normal function
def foo_normal_func_1():
    return


def foo_normal_func_2():
    ...


def foo_normal_func_3():
    yield
