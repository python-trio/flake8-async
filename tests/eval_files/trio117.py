# type: ignore
# ANYIO_NO_ERROR
# Conventional usage
from trio import MultiError

try:
    raise MultiError  # TRIO117: 10, "MultiError"
    raise NonBaseMultiError  # TRIO117: 10, "NonBaseMultiError"
    raise trio.MultiError  # TRIO117: 10, "trio.MultiError"
    raise trio.NonBaseMultiError  # TRIO117: 10, "trio.NonBaseMultiError"
except MultiError:  # TRIO117: 7, "MultiError"
    ...
except NonBaseMultiError:  # TRIO117: 7, "NonBaseMultiError"
    ...
except trio.MultiError:  # TRIO117: 7, "trio.MultiError"
    ...
except trio.NonBaseMultiError:  # TRIO117: 7, "trio.NonBaseMultiError"
    ...

# Any other mention of it
MultiError  # TRIO117: 0, "MultiError"
NonBaseMultiError  # TRIO117: 0, "NonBaseMultiError"
trio.MultiError  # TRIO117: 0, "trio.MultiError"
trio.NonBaseMultiError  # TRIO117: 0, "trio.NonBaseMultiError"

MultiError.foo  # TRIO117: 0, "MultiError"
trio.MultiError.foo  # TRIO117: 0, "trio.MultiError"

MultiError()  # TRIO117: 0, "MultiError"


def bar(x: MultiError):  # TRIO117: 11, "MultiError"
    ...


# Known false alarm
MultiError: int  # TRIO117: 0, "MultiError"


# args are not ast.Name's, so this one (surprisingly!) isn't a false positive
# (though any use of the variable will be)
def foo(MultiError: int):
    ...


# only triggers on *trio*.MultiError
anything.MultiError
blah.MultiError.bee
