# check that partly disabling a visitor works
from typing import Any

import trio


def foo() -> Any:
    ...


try:
    pass
except (SyntaxError, ValueError, BaseException):
    raise
except (SyntaxError, ValueError, trio.Cancelled) as p:  # error: 33, "trio.Cancelled"
    pass
except (SyntaxError, ValueError):
    raise
except trio.Cancelled as e:
    raise e
except trio.Cancelled as e:
    raise  # acceptable - see https://peps.python.org/pep-0678/#example-usage
except trio.Cancelled:  # error: 7, "trio.Cancelled"
    pass

# if
except BaseException as e:  # error: 7, "BaseException"
    if True:
        raise e
    elif True:
        pass
    else:
        raise e
except BaseException:  # error: 7, "BaseException"
    if True:
        raise
except BaseException:  # safe
    if True:
        raise
    elif True:
        raise
    else:
        raise

# loops
# raises inside the body are never guaranteed to run and are ignored
except trio.Cancelled:  # error: 7, "trio.Cancelled"
    while foo():
        raise

# raise inside else are guaranteed to run, unless there's a break
except trio.Cancelled:
    while ...:
        ...
    else:
        raise
except trio.Cancelled:
    for _ in "":
        ...
    else:
        raise
except BaseException:  # error: 7, "BaseException"
    while ...:
        if ...:
            break
        raise
    else:
        raise
except BaseException:  # error: 7, "BaseException"
    for _ in "":
        if ...:
            break
        raise
    else:
        raise
# ensure we don't ignore previous guaranteed raise (although that's unreachable code)
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
except BaseException as e:  # error: 7, "BaseException"
    try:
        raise e
    except ValueError:
        raise e
    except:
        raise e  # disabled TRIO104 error
except BaseException:  # safe
    try:
        pass
    finally:
        raise
# check that nested non-critical exceptions are ignored
except BaseException:
    try:
        pass
    except ValueError:
        pass  # safe
    raise
# check that name isn't lost
except trio.Cancelled as e:
    try:
        pass
    except BaseException as f:
        raise f
    raise e
# don't bypass raise by raising from nested except
except trio.Cancelled as e:
    try:
        pass
    except ValueError as g:
        raise g  # disabled TRIO104 error
    except BaseException as h:
        raise h  # error? currently treated as safe
    raise e
# bare except, equivalent to `except baseException`
except:  # error: 0, "bare except"
    pass
try:
    pass
except:
    raise

# point to correct exception in multi-line handlers
my_super_mega_long_exception_so_it_gets_split = SyntaxError
try:
    pass
except (
    my_super_mega_long_exception_so_it_gets_split,
    SyntaxError,
    BaseException,  # error: 4, "BaseException"
    ValueError,
    trio.Cancelled,  # no complaint on this line
):
    pass

# loop over non-empty static collection
except BaseException as e:
    for i in [1, 2, 3]:
        raise
except BaseException:  # error: 7, "BaseException"
    for i in [1, 2, 3]:
        ...
except BaseException:  # error: 7, "BaseException"
    for i in [1, 2, 3]:
        if ...:
            continue
        raise
except BaseException:
    while True:
        raise
except BaseException:  # error: 7, "BaseException"
    while True:
        if ...:
            break
        raise
except BaseException:
    while True:
        if ...:
            continue
        raise
