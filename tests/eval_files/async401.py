import builtins
import sys

import pytest
from exceptiongroup import BaseExceptionGroup as BackportBaseExceptionGroup
from exceptiongroup import ExceptionGroup as BackportExceptionGroup
from pytest import raises
from pytest import raises as pytest_raises

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup


class _NotPytest:
    def raises(self, expected_exception):
        pass


not_pytest = _NotPytest()

pytest.raises(ExceptionGroup)  # error: 0, "ExceptionGroup"
pytest.raises(BaseExceptionGroup)  # error: 0, "BaseExceptionGroup"
pytest.raises(expected_exception=ExceptionGroup)  # error: 0, "ExceptionGroup"
pytest.raises((ValueError, ExceptionGroup))  # error: 0, "ExceptionGroup"
pytest.raises(builtins.ExceptionGroup)  # type: ignore[attr-defined]  # error: 0, "builtins.ExceptionGroup"
pytest.raises(BackportExceptionGroup)  # error: 0, "BackportExceptionGroup"
pytest.raises(BackportBaseExceptionGroup)  # error: 0, "BackportBaseExceptionGroup"
raises(ExceptionGroup)  # error: 0, "ExceptionGroup"
pytest_raises(ExceptionGroup)  # error: 0, "ExceptionGroup"

pytest.raises(ValueError)
pytest.RaisesGroup(ValueError)
raises(ValueError)
not_pytest.raises(ExceptionGroup)
