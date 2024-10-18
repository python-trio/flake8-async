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
except* Exception as e:
    raise e.exceptions[0]  # error: 4

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
