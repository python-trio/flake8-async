# type: ignore
# ARG --enable=ASYNC220
# NOTRIO
# set base library so trio doesn't get replaced when running with anyio
# BASE_LIBRARY anyio

# anyio eval will automatically prepend this test with `--anyio`
import trio  # isort: skip


async def foo():
    subprocess.Popen()  # ASYNC220: 4, 'subprocess.Popen', "[anyio/trio]"
