import copy
import sys
from typing import Any

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup


def condition() -> bool:
    return True


def any_fun(arg: Exception) -> Exception:
    return arg


try:
    ...
except ExceptionGroup as e:
    if condition():
        raise e.exceptions[0]  # error: 8
    elif condition():
        raise copy.copy(e.exceptions[0])  # safe
    elif condition():
        raise copy.deepcopy(e.exceptions[0])  # safe
    else:
        raise any_fun(e.exceptions[0])  # safe
try:
    ...
except BaseExceptionGroup as e:
    raise e.exceptions[0]  # error: 4
try:
    ...
except ExceptionGroup as e:
    my_e = e.exceptions[0]
    raise my_e  # error: 4
try:
    ...
except ExceptionGroup as e:
    excs = e.exceptions
    my_e = excs[0]
    raise my_e  # error: 4
try:
    ...
except ExceptionGroup as e:
    excs_2 = e.subgroup(bool)
    if excs_2:
        raise excs_2.exceptions[0]  # error: 8
try:
    ...
except ExceptionGroup as e:
    excs_1, excs_2 = e.split(bool)
    if excs_1:
        raise excs_1.exceptions[0]  # error: 8
    if excs_2:
        raise excs_2.exceptions[0]  # error: 8

try:
    ...
except ExceptionGroup as e:
    f = e
    raise f.exceptions[0]  # error: 4
try:
    ...
except ExceptionGroup as e:
    excs = e.exceptions
    excs2 = excs
    raise excs2[0]  # error: 4
try:
    ...
except ExceptionGroup as e:
    my_exc = e.exceptions[0]
    my_exc2 = my_exc
    raise my_exc2  # error: 4

try:
    ...
except ExceptionGroup as e:
    raise e.exceptions[0].exceptions[0]  # error: 4
try:
    ...
except ExceptionGroup as e:
    excs = e.exceptions
    for exc in excs:
        if ...:
            raise exc  # error: 12
    raise
try:
    ...
except ExceptionGroup as e:
    ff: ExceptionGroup[Exception] = e
    raise ff.exceptions[0]  # error: 4
try:
    ...
except ExceptionGroup as e:
    raise e.subgroup(bool).exceptions[0]  # type: ignore  # error: 4

# not implemented
try:
    ...
except ExceptionGroup as e:
    a, *b = e.exceptions
    raise a

# not implemented
try:
    ...
except ExceptionGroup as e:
    x: Any = object()
    x.y = e
    raise x.y.exceptions[0]

# coverage
try:
    ...
except ExceptionGroup:
    ...

# not implemented
try:
    ...
except ExceptionGroup as e:
    (a, *b), (c, *d) = e.split(bool)
    if condition():
        raise a
    if condition():
        raise b[0]
    if condition():
        raise c
    if condition():
        raise d[0]

# coverage (skip irrelevant assignments)
x = 0

# coverage (ignore multiple targets when assign target is child exception)
try:
    ...
except ExceptionGroup as e:
    exc = e.exceptions[0]
    b, c = exc
    if condition():
        raise b  # not handled, and probably shouldn't raise
    else:
        raise c  # same

# coverage (skip irrelevant loop)
for x in range(5):
    ...
