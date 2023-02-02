import anyio


async def foo4():
    try:
        ...
    except ValueError:
        await foo()  # safe
    except anyio.Cancelled:
        await foo()  # not an error
    except BaseException:
        await foo()  # error: 8, Statement("BaseException", lineno-1)
    except:
        await foo()  # error: 8, Statement("bare except", lineno-1)


async def foo5():
    try:
        ...
    except anyio.Cancelled:
        with anyio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
    except BaseException:
        with anyio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
    except:
        with anyio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
