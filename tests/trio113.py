import contextlib
import contextlib as arbitrary_import_alias_for_contextlib
import os
from contextlib import asynccontextmanager

import trio


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


nursery = anything = custom_startable_function = trio  # type: ignore


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

        # We have a test that sets `startable-in-context-manager` to error here
        nursery.start_soon(custom_startable_function)


class foo3:
    async def __aenter__(_a_parameter_not_named_self):
        nursery.start_soon(trio.run_process)  # error: 8


# might be monkeypatched onto an instance, count this as an error too
async def __aenter__():
    nursery.start_soon(trio.run_process)  # error: 4
    nursery.start_soon()  # broken code, but our analysis shouldn't crash
    nursery.cancel_scope.cancel()


# this only takes a single parameter ... right? :P
class foo4:
    async def __aenter__(self, *, args="foo"):
        nursery.start_soon(trio.run_process)  # error: 8


@contextlib.asynccontextmanager
async def contextlib_acm():
    nursery.start_soon(trio.run_process)  # error: 4
    yield


@arbitrary_import_alias_for_contextlib.asynccontextmanager
async def contextlib_import_alias_acm():
    nursery.start_soon(trio.run_process)  # error: 4
    yield
