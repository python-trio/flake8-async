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
except:  # error: bare except is equivalent to `except baseException`
    pass

try:
    pass
except BaseException:
    raise ValueError()  # error


def foo(var):
    try:
        pass
    except trio.Cancelled:  # error
        pass
    except BaseException as e:  # error
        if True:
            raise e
        if True:
            pass
        else:
            raise e

    try:
        pass
    except BaseException as e:  # error - not guaranteed that try block will raise
        try:
            raise e
        except trio.Cancelled as f:
            raise f  # safe

    try:
        pass
    except BaseException:  # error
        return  # error

    if True:  # for code coverage
        return

    try:
        pass
    except BaseException as e:
        raise  # acceptable - see https://peps.python.org/pep-0678/#example-usage
    except trio.Cancelled:  # error
        while var:
            raise

        for i in var:
            if i:
                return  # error
    except trio.Cancelled as e:
        raise ValueError() from e  # error
    except trio.Cancelled as e:
        # error - see https://github.com/Zac-HD/flake8-trio/pull/8#discussion_r932737341
        raise BaseException() from e

    try:
        pass
    # in theory safe if the try, and all excepts raises - and there's a bare except.
    # But is a very weird pattern that we don't handle.
    except BaseException as e:  # error
        try:
            raise e
        except ValueError:
            raise e
        except:
            raise e

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

    try:
        pass
    # check that `raise` in loops are ignored
    except BaseException:  # error
        while False:
            raise
    except BaseException:  # error
        for _ in False:
            raise
    # check that nested non-critical exceptions are ignored
    except BaseException:
        try:
            pass
        except ValueError:
            pass  # safe
        raise

    # check that name isn't lost
    try:
        pass
    except trio.Cancelled as e:
        try:
            pass
        except BaseException as f:
            raise f
        raise e
