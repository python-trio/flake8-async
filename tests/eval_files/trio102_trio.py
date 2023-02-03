# NOANYIO


# New: except cancelled/baseexception are also critical
async def foo4():
    try:
        ...
    except ValueError:
        await foo()  # safe
    except trio.Cancelled:
        await foo()  # error: 8, Statement("trio.Cancelled", lineno-1)
    except BaseException:
        await foo()  # error: 8, Statement("BaseException", lineno-1)
    except:
        await foo()  # error: 8, Statement("bare except", lineno-1)


async def foo5():
    try:
        ...
    except trio.Cancelled:
        with trio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
    except BaseException:
        with trio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
    except:
        with trio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
