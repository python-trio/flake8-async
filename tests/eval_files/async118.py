# NOTRIO
# NOASYNCIO
# This raises the same errors on trio/asyncio, which is a bit silly, but inconsequential
# marked not to run the tests though as error messages will only refer to anyio
from typing import Any

import anyio
from anyio import get_cancelled_exc_class, get_cancelled_exc_class as foo  # ASYNC118: 0

bar1 = anyio.get_cancelled_exc_class  # ASYNC118: 7
bar2 = anyio.get_cancelled_exc_class()  # ASYNC118: 7
bar3 = get_cancelled_exc_class  # ASYNC118: 7
bar4 = get_cancelled_exc_class()  # ASYNC118: 7

bar5: Any = anyio.get_cancelled_exc_class  # ASYNC118: 12
bar6: Any = anyio.get_cancelled_exc_class()  # ASYNC118: 12
bar7: Any = get_cancelled_exc_class  # ASYNC118: 12
bar8: Any = get_cancelled_exc_class()  # ASYNC118: 12

# code coverage
bar9: Any
from anyio import sleep  # isort: skip
