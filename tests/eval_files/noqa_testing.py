# AUTOFIX
# NOANYIO # TODO
# ARG --enable=ASYNC911
import trio


async def foo_0():
    yield  # ASYNC911: 4, "yield", Statement("function definition", lineno-1)
    await trio.lowlevel.checkpoint()
