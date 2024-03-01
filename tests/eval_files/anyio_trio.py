# type: ignore
# ARG --enable=ASYNC220
# NOTRIO
# BASE_LIBRARY anyio
# TODO: why does this pass with --asyncio

# anyio eval will automatically prepend this test with `--anyio`
import trio  # isort: skip


async def foo():
    subprocess.Popen()  # ASYNC220: 4, 'subprocess.Popen', "[anyio|trio]"
