# ASYNCIO_NO_ERROR
# ARG --no-checkpoint-warning-decorator=no_checkpoint_warning_decorator
# ARG --transform-async-generator-decorators=transform_async_gen_decorator


import contextlib
import contextlib as bla
from contextlib import asynccontextmanager, contextmanager, contextmanager as blahabla
import pytest
import pytest as blo
from pytest import fixture

import trio


# cancel scope aliases
async def foo_fail_after():
    with trio.fail_after(10):
        yield 1  # error: 8


async def foo_fail_at():
    with trio.fail_at(10):
        yield 1  # error: 8


async def foo_move_on_aft():
    with trio.move_on_after(10):
        yield 1  # error: 8


# `as` makes no difference
async def foo_move_on_at():
    with trio.move_on_at(10) as _:
        yield 1  # error: 8


async def foo_CancelScope():
    with trio.CancelScope() as _:
        yield 1  # error: 8


# the visitor does not care if the `with` is async
async def foo_async_with():
    async with trio.CancelScope() as _:  # type: ignore[attr-defined]
        yield 1  # error: 8


# raises error at each yield
async def foo_multiple_yield():
    with trio.CancelScope() as _:
        yield 1  # error: 8
        yield 1  # error: 8


# nested method is safe
async def foo5():
    with trio.CancelScope():
        yield 1  # error: 8

        def foo6():
            yield 1  # safe


# @[async]contextmanager suppresses the error
@contextmanager
def foo_contextmanager():
    with trio.CancelScope() as _:
        yield 1  # safe


@asynccontextmanager
async def foo4():
    with trio.CancelScope() as _:
        yield 1  # safe


@contextlib.asynccontextmanager
async def foo7():
    with trio.CancelScope() as _:
        yield 1  # safe


# pytest.fixture also silences async101, as they're morally context managers
@fixture
def foo_fixture():
    with trio.CancelScope() as _:
        yield 1  # safe


@pytest.fixture
def foo_pytest_fixture():
    with trio.CancelScope() as _:
        yield 1  # safe


# it does not care about what library that [async]contextmanager or fixture is in
@bla.contextmanager
def foo_bla_contextmanager():
    with trio.CancelScope() as _:
        yield 1  # safe


@blo.fixture
def foo_blo_fixture():
    with trio.CancelScope() as _:
        yield 1  # safe


# but any other decorator does nothing
@blahabla
def foo_blahabla():
    with trio.CancelScope() as _:
        yield 1  # error: 8


# parentheses and parameters are also fine
@fixture()
def foo_pytest_fixture_paren():
    with trio.CancelScope() as _:
        yield 1


@pytest.fixture(autouse=True)
def foo_pytest_fixture_params():
    with trio.CancelScope() as _:
        yield 1


def no_checkpoint_warning_decorator(_: object): ...


def transform_async_gen_decorator(_: object): ...


# --no-checkpoint-warning-decorator does not mark as safe
@no_checkpoint_warning_decorator
def no_checkpoint_warning_deco_fun():
    with trio.CancelScope():
        yield 1  # error: 8


# --transform-async-generator-decorators marks as safe
@transform_async_gen_decorator
def transfor_async_gen_deco_fun():
    with trio.CancelScope():
        yield 1  # safe


async def foo_open_nursery():
    async with trio.open_nursery() as _:
        yield 1  # error: 8


@asynccontextmanager
async def foo_open_nursery_contextmanager():
    async with trio.open_nursery() as _:
        yield 1  # safe
