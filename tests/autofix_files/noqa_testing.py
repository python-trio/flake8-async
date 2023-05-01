# AUTOFIX
# NOANYIO # TODO
# ARG --enable=TRIO911
import trio


async def foo_0():
    await trio.lowlevel.checkpoint()
    yield  # TRIO911: 4, "yield", Statement("function definition", lineno-1)
    await trio.lowlevel.checkpoint()
