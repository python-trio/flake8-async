# type: ignore
# ARG --enable-visitor-codes-regex=(TRIO220)
# NOANYIO
async def foo():
    subprocess.Popen()  # TRIO220: 4, 'subprocess.Popen', "trio"
