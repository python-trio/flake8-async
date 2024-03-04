# type: ignore
# ARG --enable=ASYNC220
# NOASYNCIO
async def foo():
    subprocess.Popen()  # ASYNC220: 4, 'subprocess.Popen', "trio"
