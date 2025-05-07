# ARG --enable=ASYNC102,ASYNC120
# NOASYNCIO # TODO: support asyncio shields (?)

import trio


def condition() -> bool:
    return False


async def foo():
    try:
        ...
    except ValueError:
        await foo()  # ASYNC120: 8, Stmt("except", lineno-1)
        if condition():
            raise
        await foo()

    try:
        ...
    except ValueError:
        await foo()  # ASYNC120: 8, Stmt("except", lineno-1)
        raise

    # don't error if the raise is in a separate excepthandler
    try:
        ...
    except ValueError:
        await foo()
    except TypeError:
        raise

    # does not support conditional branches
    try:
        ...
    except ValueError:
        if ...:
            await foo()  # ASYNC120: 12, Stmt("except", lineno-2)
        else:
            raise

    # don't trigger on cases of ASYNC102 (?)
    try:
        ...
    except:
        await foo()  # ASYNC102: 8, Stmt("bare except", lineno-1)
        raise

    # shielded awaits with timeouts don't trigger 120
    try:
        ...
    except:
        with trio.fail_after(10) as cs:
            cs.shield = True
            await foo()
        raise

    try:
        ...
    except:
        with trio.fail_after(10) as cs:
            cs.shield = True
            await foo()
            raise

    # ************************
    # Weird nesting edge cases
    # ************************

    # nested excepthandlers should not trigger 120 on awaits in
    # their parent scope
    try:
        ...
    except ValueError:
        await foo()
        try:
            ...
        except TypeError:
            raise

    # but the other way around probably should(?)
    try:
        ...
    except ValueError:
        try:
            ...
        except TypeError:
            await foo()
        raise

    # but only when they're properly nested, this should not give 120
    try:
        ...
    except TypeError:
        await foo()
    if condition():
        raise

    try:
        ...
    except ValueError:
        await foo()  # ASYNC120: 8, Statement("except", lineno-1)
        try:
            await foo()  # ASYNC120: 12, Statement("except", lineno-3)
        except BaseException:
            await foo()  # ASYNC102: 12, Statement("BaseException", lineno-1)
        except:
            await foo()
        await foo()  # ASYNC120: 8, Statement("except", lineno-8)
        raise


# nested funcdef
async def foo_nested_funcdef():
    try:
        ...
    except ValueError:

        async def foobar():
            await foo()

        raise


# shielded but no timeout no longer triggers async120
# https://github.com/python-trio/flake8-async/issues/272
async def foo_shield_no_timeout():
    try:
        ...
    finally:
        with trio.CancelScope(shield=True):
            await foo()
