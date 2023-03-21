# type: ignore
# ARG --enable=TRIO220
# NOANYIO
import trio  # isort: skip
import anyio  # isort: skip


async def foo():
    subprocess.Popen()  # TRIO220: 4, 'subprocess.Popen', "[trio|anyio]"
