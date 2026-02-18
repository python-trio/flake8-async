# type: ignore
import pytest


async def test_pytest_raises_exceptiongroup():
    with pytest.raises(ExceptionGroup):  # ASYNC430: 9
        pass


async def test_pytest_raises_baseexceptiongroup():
    with pytest.raises(BaseExceptionGroup):  # ASYNC430: 9
        pass


async def test_pytest_raises_other():
    # Should not error
    with pytest.raises(ValueError):
        pass


async def test_pytest_raises_group():
    # Should not error - this is what we want users to use
    with pytest.RaisesGroup(ExceptionGroup):
        pass
