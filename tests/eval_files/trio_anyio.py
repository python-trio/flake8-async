# type: ignore
# ARG --enable=ASYNC220
# NOANYIO
# NOASYNCIO  # TODO
import trio  # isort: skip
import anyio  # isort: skip


async def foo():
    subprocess.Popen()  # ASYNC220: 4, 'subprocess.Popen', "[trio/anyio]"
