# type: ignore
# ANYIO_NO_ERROR
# Conventional usage
from trio import MultiError

try:
    raise MultiError  # ASYNC117: 10, "MultiError"
    raise NonBaseMultiError  # ASYNC117: 10, "NonBaseMultiError"
    raise trio.MultiError  # ASYNC117: 10, "trio.MultiError"
    raise trio.NonBaseMultiError  # ASYNC117: 10, "trio.NonBaseMultiError"
except MultiError:  # ASYNC117: 7, "MultiError"
    ...
except NonBaseMultiError:  # ASYNC117: 7, "NonBaseMultiError"
    ...
except trio.MultiError:  # ASYNC117: 7, "trio.MultiError"
    ...
except trio.NonBaseMultiError:  # ASYNC117: 7, "trio.NonBaseMultiError"
    ...

# Any other mention of it
MultiError  # ASYNC117: 0, "MultiError"
NonBaseMultiError  # ASYNC117: 0, "NonBaseMultiError"
trio.MultiError  # ASYNC117: 0, "trio.MultiError"
trio.NonBaseMultiError  # ASYNC117: 0, "trio.NonBaseMultiError"

MultiError.foo  # ASYNC117: 0, "MultiError"
trio.MultiError.foo  # ASYNC117: 0, "trio.MultiError"

MultiError()  # ASYNC117: 0, "MultiError"


def bar(x: MultiError):  # ASYNC117: 11, "MultiError"
    ...


# Known false alarm
MultiError: int  # ASYNC117: 0, "MultiError"


# args are not ast.Name's, so this one (surprisingly!) isn't a false positive
# (though any use of the variable will be)
def foo(MultiError: int): ...


# only triggers on *trio*.MultiError
anything.MultiError
blah.MultiError.bee
