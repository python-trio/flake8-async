_ = ""


async def foo():
    await foo()


# early return
async def foo_return_1():  # silent to avoid duplicate errors
    return  # error: 4


async def foo_return_2():  # safe
    if _:
        return  # error: 8
    await foo()


async def foo_return_3():  # TRIO103
    if _:
        await foo()
        return  # safe
