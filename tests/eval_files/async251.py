import time
from time import sleep


async def foo():
    time.sleep(5)  # ASYNC251: 4, "trio"
    time.sleep(5) if 5 else time.sleep(5)  # ASYNC251: 4, "trio"  # ASYNC251: 28, "trio"

    # `from time import sleep` -- resolves to canonical `time.sleep`
    sleep(5)  # ASYNC251: 4, "trio"
