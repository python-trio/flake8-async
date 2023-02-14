# mypy: disable-error-code="arg-type,call-overload,misc"
import contextlib
import contextlib as arbitrary_import_alias_for_contextlib
import functools
import os
from contextlib import asynccontextmanager
from functools import partial
from typing import Any

import trio

# ARG --startable-in-context-manager=custom_startable_function
# NOANYIO


@asynccontextmanager
async def custom_startable_externally_tested():
    nursery.start_soon(custom_startable_function)  # error: 4
    yield


@asynccontextmanager
async def run_sampling_profiler():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(  # error: 8
            trio.run_process, ["start-sampling-profiler", str(os.getpid())]
        )
        yield

        nursery.start_soon(  # safe, it's after the first yield
            trio.run_process, ["start-sampling-profiler", str(os.getpid())]
        )


async def not_cm():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(
            trio.run_process, ["start-sampling-profiler", str(os.getpid())]
        )
        yield


class foo:
    async def __aenter__(self):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(  # error: 12
                trio.run_process, ["start-sampling-profiler", str(os.getpid())]
            )
            yield


nursery: trio.Nursery = ...  # type: ignore
anything_nursery = nursery
anything: Any = ...
custom_startable_function: Any = ...


class foo2:
    _nursery = nursery

    async def __aenter__(self):
        nursery.start_soon(trio.run_process)  # error: 8
        nursery.start_soon(trio.serve_ssl_over_tcp)  # error: 8
        nursery.start_soon(trio.serve_tcp)  # error: 8
        nursery.start_soon(trio.serve_listeners)  # error: 8

        # Where does `nursery` come from in __aenter__?  Probably an attribute:
        self._nursery.start_soon(trio.run_process)  # error: 8
        self._nursery.start_soon(trio.serve_ssl_over_tcp)  # error: 8
        self._nursery.start_soon(trio.serve_tcp)  # error: 8
        self._nursery.start_soon(trio.serve_listeners)  # error: 8

        # triggers on anything whose name ends with nursery
        anything_nursery.start_soon(trio.run_process)  # error: 8
        anything.start_soon(trio.run_process)
        None.start_soon(trio.run_process)  # type: ignore

        # explicitly check partial support
        nursery.start_soon(partial(trio.run_process))  # error: 8
        nursery.start_soon(functools.partial(trio.run_process))  # error: 8
        nursery.start_soon(anything.partial(trio.run_process))  # error: 8

        # trigger when the sensitive methods are inside a call
        nursery.start_soon(tuple(tuple(tuple(tuple(trio.run_process)))))  # error: 8
        nursery.start_soon(None, tuple(tuple(tuple(tuple(trio.run_process)))))
        nursery.start_soon(partial(print, 5))
        nursery.start_soon(partial(print, trio.run_process))  # error: 8

        serve = run_process = myfun = anything
        # error if name shared with trio
        nursery.start_soon(serve)  # error: 8
        nursery.start_soon(run_process)  # error: 8
        # don't error if a startable name is a parameter or module
        nursery.start_soon(myfun(serve=None))
        nursery.start_soon(serve.myfun)

        # doesn't support more esoteric ways of baking in the name
        nursery.start_soon(lambda x: serve(x))
        nursery.start_soon([serve])


class foo3:
    async def __aenter__(_a_parameter_not_named_self):
        nursery.start_soon(trio.run_process)  # error: 8


# might be monkeypatched onto an instance, count this as an error too
async def __aenter__():
    nursery.start_soon(trio.run_process)  # error: 4
    nursery.start_soon()  # broken code, but our analysis shouldn't crash
    nursery.cancel_scope.cancel()


@contextlib.asynccontextmanager
async def contextlib_acm():
    nursery.start_soon(trio.run_process)  # error: 4
    yield


@arbitrary_import_alias_for_contextlib.asynccontextmanager
async def contextlib_import_alias_acm():
    nursery.start_soon(trio.run_process)  # error: 4
    yield


# code coverage for non-name, non-attribute decorator
@None  # type: ignore
async def foo4():
    ...
