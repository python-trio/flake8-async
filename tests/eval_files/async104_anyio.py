# type: ignore
# BASE_LIBRARY ANYIO
import anyio

try:
    ...
except anyio.get_cancelled_exc_class() as e:
    raise ValueError() from e  # error: 4

# anyio.Cancelled does not exist
try:
    ...
except anyio.Cancelled as e:
    raise ValueError() from e


def foo():
    try:
        ...
    except anyio.get_cancelled_exc_class():
        raise
    except BaseException:
        return  # would otherwise error
    except:
        return  # would otherwise error

    try:
        ...
    except anyio.get_cancelled_exc_class():
        raise
    except:
        return  # would otherwise error
