import trio

try:
    pass
except (SyntaxError, ValueError, BaseException):
    raise
except (SyntaxError, ValueError, trio.Cancelled) as p:  # error: 33, trio.Cancelled
    pass
except (SyntaxError, ValueError):
    raise
except trio.Cancelled as e:
    raise e
except trio.Cancelled as e:
    raise  # acceptable - see https://peps.python.org/pep-0678/#example-usage
except trio.Cancelled:  # error: 7, trio.Cancelled
    pass

# raise different exception
except BaseException:
    raise ValueError()  # TRIO104
except trio.Cancelled as e:
    raise ValueError() from e  # TRIO104
except trio.Cancelled as e:
    # see https://github.com/Zac-HD/flake8-trio/pull/8#discussion_r932737341
    raise BaseException() from e  # TRIO104

# if
except BaseException as e:  # error: 7, BaseException
    if True:
        raise e
    elif True:
        pass
    else:
        raise e
except BaseException:  # error: 7, BaseException
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
except trio.Cancelled:  # error: 7, trio.Cancelled
    while True:
        raise
    else:
        raise
except trio.Cancelled:  # error: 7, trio.Cancelled
    for _ in "":
        raise
    else:
        raise

# nested try
# in theory safe if the try, and all excepts raises - and there's a bare except.
# But is a very weird pattern that we don't handle.
except BaseException as e:  # error: 7, BaseException
    try:
        raise e
    except ValueError:
        raise e
    except:
        raise e  # though sometimes okay, TRIO104
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
        raise g  # TRIO104
    except BaseException as h:
        raise h  # error? currently treated as safe
    raise e
# bare except, equivalent to `except baseException`
except:  # error: 0, bare except
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
    BaseException,  # error: 4, BaseException
    ValueError,
    trio.Cancelled,  # no complaint on this line
):
    pass
