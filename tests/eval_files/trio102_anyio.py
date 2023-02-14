# type: ignore
import anyio
from anyio import get_cancelled_exc_class

# this one is fine to also run with TRIO


async def foo():
    ...


async def foo_anyio():
    try:
        ...
    except anyio.get_cancelled_exc_class():
        await foo()  # error: 8, Statement("anyio.get_cancelled_exc_class()", lineno-1)
    except:
        await foo()  # safe

    try:
        ...
    except anyio.get_cancelled_exc_class():
        await foo()  # error: 8, Statement("anyio.get_cancelled_exc_class()", lineno-1)
    except BaseException:
        await foo()  # safe

    try:
        ...
    except get_cancelled_exc_class():
        await foo()  # error: 8, Statement("get_cancelled_exc_class()", lineno-1)
    except:
        await foo()  # safe

    try:
        ...
    except anyio.get_cancelled_exc_class():
        await foo()  # error: 8, Statement("anyio.get_cancelled_exc_class()", lineno-1)
    except anyio.get_cancelled_exc_class():
        await foo()

    # these are all type errors, and will not be matched by critical_except
    try:
        ...
    except anyio.get_cancelled_exc_class:
        await foo()  # not handled
    except anyio.get_cancelled_exc_class(...):
        await foo()  # not handled
    except get_cancelled_exc_class:
        await foo()  # not handled
    except:
        await foo()  # error: 8, Statement("bare except", lineno-1)

    try:
        ...
    except anyio.foo():
        await foo()
    except ValueError:
        await foo()  # safe
    except anyio.Cancelled:
        await foo()  # not an error
    except:
        await foo()  # error: 8, Statement("bare except", lineno-1)


async def foo_anyio_shielded():
    try:
        ...
    except anyio.get_cancelled_exc_class():
        with anyio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
    except BaseException:
        await foo()  # safe
