# ARG --enable-visitor-codes-regex=(TRIO103)|(TRIO104)

from typing import Any

import trio


def foo() -> Any:
    ...


# fmt: off
# TODO: Black 23.1.0 moves the long comments around a bit.

try:
    ...
except (SyntaxError, ValueError, BaseException):
    raise

try:
    ...
except (
    SyntaxError,
    ValueError,
    trio.Cancelled,  # error: 4, "trio.Cancelled", ""
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
except trio.Cancelled:  # error: 7, "trio.Cancelled", ""
    ...

# if
try:
    ...
except BaseException as e:  # error: 7, "BaseException", " Consider adding an `except trio.Cancelled: raise` before this exception handler."
    if True:
        raise e
    elif True:
        ...
    else:
        raise e

try:
    ...
except BaseException:  # error: 7, "BaseException", " Consider adding an `except trio.Cancelled: raise` before this exception handler."
    if True:
        raise

try:
    ...
except BaseException:  # safe
    if True:
        raise
    elif True:
        raise
    else:
        raise

# loops
# raises inside the body are never guaranteed to run and are ignored
try:
    ...
except trio.Cancelled:  # error: 7, "trio.Cancelled", ""
    while foo():
        raise

# raise inside else are guaranteed to run, unless there's a break
try:
    ...
except trio.Cancelled:
    while ...:
        ...
    else:
        raise

try:
    ...
except trio.Cancelled:
    for _ in "":
        ...
    else:
        raise

try:
    ...
except BaseException:  # error: 7, "BaseException", " Consider adding an `except trio.Cancelled: raise` before this exception handler."
    while ...:
        if ...:
            break
        raise
    else:
        raise

try:
    ...
except BaseException:  # error: 7, "BaseException", " Consider adding an `except trio.Cancelled: raise` before this exception handler."
    for _ in "":
        if ...:
            break
        raise
    else:
        raise

# ensure we don't ignore previous guaranteed raise (although that's unreachable code)
try:
    ...
except BaseException:
    raise
    for _ in "":
        if ...:
            break
        raise
    else:
        raise

# nested try
# in theory safe if the try, and all excepts raises - and there's a bare except.
# But is a very weird pattern that we don't handle.
try:
    ...
except BaseException as e:  # error: 7, "BaseException", " Consider adding an `except trio.Cancelled: raise` before this exception handler."
    try:
        raise e
    except ValueError:
        raise e
    except:
        raise e  # TRIO104: 8

try:
    ...
except BaseException:  # safe
    try:
        ...
    finally:
        raise

# check that nested non-critical exceptions are ignored
try:
    ...
except BaseException:
    try:
        ...
    except ValueError:
        ...  # safe
    raise

# check that name isn't lost
try:
    ...
except trio.Cancelled as e:
    try:
        ...
    except BaseException as f:
        raise f
    raise e

# don't bypass raise by raising from nested except
try:
    ...
except trio.Cancelled as e:
    try:
        ...
    except ValueError as g:
        raise g  # TRIO104: 8
    except BaseException as h:
        raise h  # error? currently treated as safe
    raise e

# bare except, equivalent to `except baseException`
try:
    ...
except:  # error: 0, "bare except", " Consider adding an `except trio.Cancelled: raise` before this exception handler."
    ...

try:
    ...
except:
    raise

# point to correct exception in multi-line handlers
my_super_mega_long_exception_so_it_gets_split = SyntaxError
try:
    ...
except (
    my_super_mega_long_exception_so_it_gets_split,
    SyntaxError,
    BaseException,  # error: 4, "BaseException", " Consider adding an `except trio.Cancelled: raise` before this exception handler."
    ValueError,
    trio.Cancelled,  # no complaint on this line
):
    ...

# loop over non-empty static collection
try:
    ...
except BaseException as e:
    for i in [1, 2, 3]:
        raise

try:
    ...
except BaseException:  # error: 7, "BaseException", " Consider adding an `except trio.Cancelled: raise` before this exception handler."
    for i in [1, 2, 3]:
        ...

try:
    ...
except BaseException:  # error: 7, "BaseException", " Consider adding an `except trio.Cancelled: raise` before this exception handler."
    for i in [1, 2, 3]:
        if ...:
            continue
        raise

try:
    ...
except BaseException:
    while True:
        raise

try:
    ...
except BaseException:  # error: 7, "BaseException", " Consider adding an `except trio.Cancelled: raise` before this exception handler."
    while True:
        if ...:
            break
        raise

try:
    ...
except BaseException:
    while True:
        if ...:
            continue
        raise


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
except trio.Cancelled:  # error: 7, "trio.Cancelled", ""
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
except trio.Cancelled:  # error: 7, "trio.Cancelled", ""
    ...
except:
    try:
        ...
    except trio.Cancelled:  # error: 11, "trio.Cancelled", ""
        ...
