import trio

try:
    ...
# raise different exception
except BaseException:
    raise ValueError()  # error: 4
except trio.Cancelled as e:
    raise ValueError() from e  # error: 4
except trio.Cancelled as e:
    # see https://github.com/Zac-HD/flake8-trio/pull/8#discussion_r932737341
    raise BaseException() from e  # error: 4


# nested try
# in theory safe if the try, and all excepts raises - and there's a bare except.
# But is a very weird pattern that we don't handle.
except BaseException as e:  # TRIO103
    try:
        raise e
    except ValueError:
        raise e
    except:
        raise e  # though sometimes okay, error: 8
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
        raise g  # error: 8
    except BaseException as h:
        raise h  # error? currently treated as safe
    raise e

# avoid re-raise by raising parent exception
try:
    pass
except ValueError as e:
    try:
        pass
    except BaseException:
        raise e  # error: 8

# check for avoiding re-raise by returning from function
def foo():
    if True:  # for code coverage
        return

    try:
        pass
    except BaseException:  # TRIO103
        return  # error: 8

    # check that we properly iterate over all nodes in try
    except BaseException:  # TRIO103
        try:
            return  # error: 12
        except ValueError:
            return  # error: 12
        else:
            return  # error: 12
        finally:
            return  # error: 12


# don't avoid re-raise with continue/break
while True:
    try:
        pass
    except BaseException:
        if True:
            continue  # error: 12
        raise

while True:
    try:
        pass
    except BaseException:
        if True:
            break  # error: 12
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
        yield 1  # error: 8
        raise

    # check that we properly iterate over all nodes in try
    except BaseException:
        try:
            yield 1  # error: 12
        except ValueError:
            yield 1  # error: 12
        else:
            yield 1  # error: 12
        finally:
            yield 1  # error: 12
        raise
