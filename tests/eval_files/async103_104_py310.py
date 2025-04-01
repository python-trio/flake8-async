"""Test for ASYNC103/ASYNC104 with structural pattern matching

ASYNC103: no-reraise-cancelled
ASYNC104: cancelled-not-raised
"""

# ARG --enable=ASYNC103,ASYNC104


def foo() -> Any: ...


try:
    ...
except BaseException as e:  # ASYNC103_trio: 7, "BaseException"
    match foo():
        case True:
            raise e
        case False:
            ...
        case _:
            raise e

try:
    ...
except BaseException:  # ASYNC103_trio: 7, "BaseException"
    match foo():
        case True:
            raise

try:
    ...
except BaseException:  # safe
    match foo():
        case True:
            raise
        case False:
            raise
        case _:
            raise
try:
    ...
except BaseException:  # ASYNC103_trio: 7, "BaseException"
    match foo():
        case _ if foo():
            raise
try:
    ...
except BaseException:  # ASYNC103_trio: 7, "BaseException"
    match foo():
        case 1:
            return  # ASYNC104: 12
        case 2:
            raise
        case 3:
            return  # ASYNC104: 12
        case blah:
            raise
