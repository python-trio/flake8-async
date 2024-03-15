# NOAUTOFIX

import time
from time import sleep


async def foo():
    time.sleep(5) if 5 else None  # ASYNC251: 8, "trio"
    time.sleep(5)  # ASYNC251: 4, "trio"

    # Not handled due to difficulty tracking imports and not wanting to trigger
    # false positives. But could definitely be handled by ruff et al.
    sleep(5)
