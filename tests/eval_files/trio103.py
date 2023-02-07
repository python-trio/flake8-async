# ARG --enable-visitor-codes-regex=(TRIO103)|(TRIO104)

from typing import Any


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
    BaseException,  # TRIO103_trio: 4, "BaseException"
) as p:
    ...

try:
    ...
except (SyntaxError, ValueError):
    raise

try:
    ...
except BaseException as e:
    raise e

try:
    ...
except BaseException as e:
    raise  # acceptable - see https://peps.python.org/pep-0678/#example-usage

try:
    ...
except BaseException:  # TRIO103_trio: 7, "BaseException"
    ...

# if
try:
    ...
except BaseException as e:  # TRIO103_trio: 7, "BaseException"
    if True:
        raise e
    elif True:
        ...
    else:
        raise e

try:
    ...
except BaseException:  # TRIO103_trio: 7, "BaseException"
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
except BaseException:  # TRIO103_trio: 7, "BaseException"
    while foo():
        raise

# raise inside else are guaranteed to run, unless there's a break
try:
    ...
except BaseException:
    while ...:
        ...
    else:
        raise

try:
    ...
except BaseException:
    for _ in "":
        ...
    else:
        raise

try:
    ...
except BaseException:  # TRIO103_trio: 7, "BaseException"
    while ...:
        if ...:
            break
        raise
    else:
        raise

try:
    ...
except BaseException:  # TRIO103_trio: 7, "BaseException"
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
except BaseException as e:  # TRIO103_trio: 7, "BaseException"
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
except BaseException as e:
    try:
        ...
    except BaseException as f:
        raise f
    raise e

# don't bypass raise by raising from nested except
try:
    ...
except BaseException as e:
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
except:  # TRIO103_trio: 0, "bare except"
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
    BaseException,  # TRIO103_trio: 4, "BaseException"
    ValueError,
    BaseException,  # no complaint on this line
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
except BaseException:  # TRIO103_trio: 7, "BaseException"
    for i in [1, 2, 3]:
        ...

try:
    ...
except BaseException:  # TRIO103_trio: 7, "BaseException"
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
except BaseException:  # TRIO103_trio: 7, "BaseException"
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
except BaseException:
    raise
except:  # now silent
    ...

# don't throw multiple 103's even if `Cancelled` wasn't properly handled.
try:
    ...
except BaseException:  # TRIO103_trio: 7, "BaseException"
    ...
except:  # now silent
    ...

# Check state management of whether cancelled has been handled across nested try's
try:
    try:
        ...
    except BaseException:
        raise
except BaseException:  # TRIO103_trio: 7, "BaseException"
    ...
except:
    try:
        ...
    except BaseException:  # TRIO103_trio: 11, "BaseException"
        ...
