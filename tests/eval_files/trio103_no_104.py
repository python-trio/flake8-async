# ARG --enable-visitor-codes-regex=TRIO103
# NOANYIO - TRIO103_alt not implemented for anyio
# check that partly disabling a visitor works
from typing import Any


def foo() -> Any:
    ...


# nested try
# in theory safe if the try, and all excepts raises - and there's a bare except.
# But is a very weird pattern that we don't handle.
try:
    ...
except BaseException as e:  # TRIO103_alt: 7, "BaseException"
    try:
        raise e
    except ValueError:
        raise e
    except:
        raise e  # disabled TRIO104 error
