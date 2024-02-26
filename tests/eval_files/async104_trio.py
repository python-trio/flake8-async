# NOANYIO
# NOASYNCIO
import trio

try:
    ...
except trio.Cancelled as e:
    raise ValueError() from e  # error: 4


def foo():
    try:
        ...
    except trio.Cancelled:
        raise
    except BaseException:
        return  # would otherwise error
    except:
        return  # would otherwise error

    try:
        ...
    except trio.Cancelled:
        raise
    except:
        return  # would otherwise error
