# ARG --enable=ASYNC103,ASYNC104
# NOASYNCIO
# NOANYIO

from typing import Any

import trio


def foo() -> Any: ...


# fmt: off
# TODO: Black 23.1.0 moves the long comments around a bit.

try:
    ...
except (
    SyntaxError,
    ValueError,
    trio.Cancelled,  # ASYNC103: 4, "trio.Cancelled"
) as p:
    ...

try:
    ...
except (SyntaxError, ValueError):
    raise

try:
    ...
except trio.Cancelled as e:
    raise e

try:
    ...
except trio.Cancelled as e:
    raise  # acceptable - see https://peps.python.org/pep-0678/#example-usage

try:
    ...
except trio.Cancelled:  # ASYNC103: 7, "trio.Cancelled"
    ...

# Issue #106, false alarm on excepts after `Cancelled` has already been handled
try:
    ...
except trio.Cancelled:
    raise
except BaseException:  # now silent
    ...
except:  # now silent
    ...

try:
    ...
except trio.Cancelled:
    raise
except:  # now silent
    ...


try:
    ...
except BaseException:
    raise
except:  # now silent
    ...

# don't throw multiple 103's even if `Cancelled` wasn't properly handled.
try:
    ...
except trio.Cancelled:  # ASYNC103: 7, "trio.Cancelled"
    ...
except BaseException:  # now silent
    ...
except:  # now silent
    ...

# Check state management of whether cancelled has been handled across nested try's
try:
    try:
        ...
    except trio.Cancelled:
        raise
except trio.Cancelled:  # ASYNC103: 7, "trio.Cancelled"
    ...
except:
    try:
        ...
    except trio.Cancelled:  # ASYNC103: 11, "trio.Cancelled"
        ...
