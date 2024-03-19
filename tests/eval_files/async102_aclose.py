# type: ignore
# exclude finally: await x.aclose() from async102


async def foo():
    # no type tracking in this check, we allow any call that looks like
    # `await [...].aclose()`
    x = None

    try:
        ...
    except BaseException:
        # still not allowed in BaseException
        await x.aclose()  # ASYNC102: 8, Statement("BaseException", lineno-2)
    finally:
        # but these will no longer raise any errors
        await x.aclose()
        await x.y.aclose()
