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
except:
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
    except BaseException as e:
        try:
            raise e
        except trio.Cancelled as f:
            raise f  # ???

    try:
        pass
    except BaseException:
        return  # error
    except trio.Cancelled:
        while True:
            raise
        else:
            raise
    except trio.Cancelled:
        for i in var:
            raise
        else:
            raise
    except trio.Cancelled:  # error
        while True:
            raise
        else:
            pass
    except trio.Cancelled:  # error
        for i in var:
            pass
        else:
            raise

    if True:
        return

    try:
        pass
    except BaseException as e:
        try:
            raise e
        except:
            raise e

    try:
        pass
    except BaseException as e:  # TODO: nested try's
        try:
            raise e
        except:
            raise

    try:
        pass
    except BaseException as e:
        try:
            pass
        except:
            pass
        finally:
            raise e

    try:
        pass
    except BaseException as e:
        raise  # In theory safe? But godawful ugly so treat as error anyway


# TODO: how to handle raise from?
