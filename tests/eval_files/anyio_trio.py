# type: ignore
# ARG --enable=TRIO220
# NOTRIO

# anyio eval will automatically prepend this test with `--anyio`
import trio  # isort: skip


async def foo():
    subprocess.Popen()  # TRIO220: 4, 'subprocess.Popen', "[anyio|trio]"
