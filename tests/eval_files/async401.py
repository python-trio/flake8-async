import builtins
import sys

import pytest
from exceptiongroup import BaseExceptionGroup as BackportBaseExceptionGroup
from exceptiongroup import ExceptionGroup as BackportExceptionGroup
from pytest import RaisesExc as raises_exc
from pytest import RaisesGroup as raises_group
from pytest import mark as pytest_mark
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

pytest.raises(ExceptionGroup[Exception])  # error: 0, "ExceptionGroup[Exception]"
pytest.RaisesExc(ExceptionGroup)  # error: 0, "ExceptionGroup"
pytest.RaisesExc(  # error: 0, "BaseExceptionGroup"
    expected_exception=BaseExceptionGroup
)
pytest.RaisesGroup(ExceptionGroup)  # error: 0, "ExceptionGroup"
pytest.RaisesGroup(ValueError, BaseExceptionGroup)  # error: 0, "BaseExceptionGroup"
pytest.mark.xfail(raises=ExceptionGroup)  # error: 0, "ExceptionGroup"
pytest.mark.xfail(  # error: 0, "ExceptionGroup"
    reason="expected", raises=(ValueError, ExceptionGroup)
)

pytest.RaisesExc(ValueError)
pytest.RaisesGroup(pytest.RaisesGroup(ValueError))
pytest.mark.xfail(raises=ValueError)
pytest.mark.xfail(reason="expected")

raises_exc(BackportExceptionGroup)  # error: 0, "BackportExceptionGroup"
raises_group(  # error: 0, "ExceptionGroup[Exception]"
    ValueError, ExceptionGroup[Exception]
)
pytest_mark.xfail(  # error: 0, "BackportBaseExceptionGroup"
    raises=BackportBaseExceptionGroup
)
pytest.RaisesGroup(ExceptionGroup, BaseExceptionGroup)  # error: 0, "ExceptionGroup"
pytest.RaisesGroup(pytest.RaisesGroup(ExceptionGroup))  # error: 19, "ExceptionGroup"
pytest.RaisesExc(builtins.BaseExceptionGroup)  # type: ignore[attr-defined]  # error: 0, "builtins.BaseExceptionGroup"

pytest.raises((ValueError, TypeError))
pytest.raises(match="message")
pytest.RaisesExc(match="message")
pytest.RaisesGroup()
pytest.RaisesGroup(ValueError, TypeError, match="message")
pytest.mark.xfail(ExceptionGroup)
pytest.mark.xfail(raises=pytest.RaisesGroup(ValueError))
pytest.mark.xfail(**{"raises": ExceptionGroup})
not_pytest.raises(ExceptionGroup[Exception])
pytest.raises(list[ExceptionGroup])
