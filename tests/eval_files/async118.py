# `get_cancelled_exc_class` will trigger errors even if anyio isn't imported, out of
# an abundance of caution. But `anyio.get_cancelled_exc_class` will not.
# NOTRIO # anyio-specific check, see above
# NOASYNCIO # anyio-specific check, see above
# BASE_LIBRARY anyio
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
