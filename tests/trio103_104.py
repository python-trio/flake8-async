import trio

try:
    pass
except (SyntaxError, ValueError, BaseException):
    raise
except (SyntaxError, ValueError, trio.Cancelled) as p:  # error
    pass
except (SyntaxError, ValueError):
    raise
except trio.Cancelled as e:
    raise e
except trio.Cancelled as e:
    raise  # acceptable - see https://peps.python.org/pep-0678/#example-usage
except trio.Cancelled:  # error
    pass

# raise different exception
except BaseException:
    raise ValueError()  # error TRIO104
except trio.Cancelled as e:
    raise ValueError() from e  # error TRIO104
except trio.Cancelled as e:
    # see https://github.com/Zac-HD/flake8-trio/pull/8#discussion_r932737341
    raise BaseException() from e  # error TRIO104

# if
except BaseException as e:  # error
    if True:
        raise e
    elif True:
        pass
    else:
        raise e
except BaseException:  # error
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
except trio.Cancelled:  # error
    while True:
        raise
    else:
        raise
except trio.Cancelled:  # error
    for _ in "":
        raise
    else:
        raise

# nested try
# in theory safe if the try, and all excepts raises - and there's a bare except.
# But is a very weird pattern that we don't handle.
except BaseException as e:  # error
    try:
        raise e
    except ValueError:
        raise e
    except:
        raise e  # error: though sometimes okay
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
        raise g  # error
    except BaseException as h:
        raise h  # error? currently treated as safe
    raise e
# bare except, equivalent to `except baseException`
except:  # error
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
    BaseException,  # error
    ValueError,
    trio.Cancelled,  # no complaint on this line
):
    pass

# avoid re-raise by raising parent exception
try:
    pass
except ValueError as e:
    try:
        pass
    except BaseException:
        raise e  # error TRIO104

# check for avoiding re-raise by returning from function
def foo():
    if True:  # for code coverage
        return

    try:
        pass
    except BaseException:  # error
        return  # error

    # check that we properly iterate over all nodes in try
    except BaseException:  # error
        try:
            return  # error
        except ValueError:
            return  # error
        else:
            return  # error
        finally:
            return  # error


# don't avoid re-raise with continue/break
while True:
    try:
        pass
    except BaseException:
        if True:
            continue  # error
        raise

while True:
    try:
        pass
    except BaseException:
        if True:
            break  # error
        raise

try:
    pass
except BaseException:  # safe
    while True:
        break
    raise
except BaseException:  # safe
    while True:
        continue
    raise

# check for avoiding re-raise by yielding from function
def foo_yield():
    if True:  # for code coverage
        yield 1

    try:
        pass
    except BaseException:
        yield 1  # error
        raise

    # check that we properly iterate over all nodes in try
    except BaseException:
        try:
            yield 1  # error
        except ValueError:
            yield 1  # error
        else:
            yield 1  # error
        finally:
            yield 1  # error
        raise
