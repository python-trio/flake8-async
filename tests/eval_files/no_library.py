# type: ignore
# ARG --enable=TRIO220
# NOANYIO
async def foo():
    subprocess.Popen()  # TRIO220: 4, 'subprocess.Popen', "trio"
