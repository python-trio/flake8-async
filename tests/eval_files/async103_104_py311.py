"""Test for ASYNC103/ASYNC104 with except* blocks.

ASYNC103: no-reraise-cancelled
ASYNC104: cancelled-not-raised
"""

# ARG --enable=ASYNC103,ASYNC104

try:
    ...
except* BaseException:  # ASYNC103_trio: 8, "BaseException"
    ...

try:
    ...
except* BaseException:
    raise

try:
    ...
except* ValueError:
    ...
except* BaseException:  # ASYNC103_trio: 8, "BaseException"
    ...

try:
    ...
except* BaseException:
    raise ValueError  # ASYNC104: 4


def foo():
    try:
        ...
    except* BaseException:  # ASYNC103_trio: 12, "BaseException"
        return  # ASYNC104: 8
    try:
        ...
    except* BaseException:
        raise ValueError  # ASYNC104: 8
