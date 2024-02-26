# type: ignore
# ARG --enable=ASYNC220
# NOTRIO

# anyio eval will automatically prepend this test with `--anyio`
import trio  # isort: skip


async def foo():
    subprocess.Popen()  # ASYNC220: 4, 'subprocess.Popen', "[anyio|trio]"
