# ARG --enable=ASYNC103,ASYNC104
try:
    ...
# raise different exception
except BaseException:
    raise ValueError()  # error: 4

try:
    ...
except BaseException as e:
    raise ValueError() from e  # error: 4

try:
    ...
except BaseException as e:
    # see https://github.com/python-trio/flake8-async/pull/8#discussion_r932737341
    raise BaseException() from e  # error: 4


# fmt: off
# TODO: Black 23.1.0 moves the long comments around a bit.

# nested try
# in theory safe if the try, and all excepts raises - and there's a bare except.
# But is a very weird pattern that we don't handle.
try:
    ...
except BaseException as e:  # ASYNC103_trio: 7, "BaseException"
    try:
        raise e
    except ValueError:
        raise e
    except:
        raise e  # though sometimes okay, error: 8

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
        raise g  # error: 8
    except BaseException as h:
        raise h  # error? currently treated as safe
    raise e

# avoid re-raise by raising parent exception
try:
    ...
except ValueError as e:
    try:
        ...
    except BaseException:
        raise e  # error: 8

def foo():
    if True:  # for code coverage
        return

# check for avoiding re-raise by returning from function
def foo2():
    try:
        ...
    except BaseException:  # ASYNC103_trio: 11, "BaseException"
        return  # error: 8

    # check that we properly iterate over all nodes in try
    try:
        ...
    except BaseException:  # ASYNC103_trio: 11, "BaseException"
        try:
            return  # error: 12
        except ValueError:
            return  # error: 12
        else:
            return  # type: ignore[unreachable] # error: 12
        finally:
            return  # error: 12


# don't avoid re-raise with continue/break
def foo3():
    while True:
        try:
            ...
        except BaseException:
            if True:
                continue  # error: 16
            raise

def foo4():
    while True:
        try:
            ...
        except BaseException:
            if True:
                break  # error: 16
            raise

try:
    ...
except BaseException:  # safe
    while True:
        break
    raise

try:
    ...
except BaseException:  # safe
    while True:
        continue
    raise

# check for avoiding re-raise by yielding from function
def foo_yield():
    if True:  # for code coverage
        yield 1

    try:
        ...
    except BaseException:
        yield 1  # error: 8
        raise

    # check that we properly iterate over all nodes in try
    try:
        ...
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


# issue #106
# don't warn on bare / BaseException when cancelled have been handled in a previous except
def foo_cancelled_handled():
    try:
        ...
    except BaseException:
        raise
    except:
        return  # would otherwise error

def foo_cancelled_not_handled():
    try:
        ...
    except BaseException:  # ASYNC103_trio: 11, "BaseException"
        return  # ASYNC104: 8
    except:
        return  # would otherwise error
