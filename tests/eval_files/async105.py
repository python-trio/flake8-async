# ANYIO_NO_ERROR # not supported, and no plans to
# ASYNCIO_NO_ERROR # not supported, and no plans to
from typing import Any
from collections.abc import Coroutine

import trio

par: Any = ...
async_funpar: Coroutine[Any, Any, Any] = ...  # type: ignore


async def myasyncfun(task_status): ...


# calls that don't return
async def inf1() -> None:
    await trio.serve_listeners(par, par)


async def inf2() -> None:
    await trio.serve_ssl_over_tcp()


async def inf3() -> None:
    await trio.serve_tcp()


async def inf4() -> None:
    await trio.sleep_forever()


async def foo() -> None:
    # not async
    trio.run(par)

    # safely awaited
    await trio.aclose_forcefully(par)
    await trio.open_file(par)
    await trio.open_ssl_over_tcp_listeners(par, par)
    await trio.open_ssl_over_tcp_stream(par, par)
    await trio.open_tcp_listeners(par)
    await trio.open_tcp_stream(par, par)
    await trio.open_unix_socket(par)
    await trio.run_process(par)
    await trio.sleep(5)
    await trio.sleep_until(5)
    await trio.lowlevel.cancel_shielded_checkpoint()
    await trio.lowlevel.checkpoint()
    await trio.lowlevel.checkpoint_if_cancelled()
    await trio.lowlevel.open_process(par)
    await trio.lowlevel.permanently_detach_coroutine_object(par)
    await trio.lowlevel.reattach_detached_coroutine_object(par, par)
    await trio.lowlevel.temporarily_detach_coroutine_object(par)
    await trio.lowlevel.wait_readable(par)
    await trio.lowlevel.wait_task_rescheduled(par)
    await trio.lowlevel.wait_writable(par)

    # all async functions
    # fmt: off
    trio.aclose_forcefully(par)  # error: 4, "trio.aclose_forcefully", "function"
    trio.open_file(par)  # error: 4, "trio.open_file", "function"
    trio.open_ssl_over_tcp_listeners(par, par)  # error: 4, "trio.open_ssl_over_tcp_listeners", "function"
    trio.open_ssl_over_tcp_stream(par, par)  # error: 4, "trio.open_ssl_over_tcp_stream", "function"
    trio.open_tcp_listeners(par)  # error: 4, "trio.open_tcp_listeners", "function"
    trio.open_tcp_stream(par, par)  # error: 4, "trio.open_tcp_stream", "function"
    trio.open_unix_socket(par)  # error: 4, "trio.open_unix_socket", "function"
    trio.run_process(par)  # error: 4, "trio.run_process", "function"
    trio.serve_listeners(par, par)  # error: 4, "trio.serve_listeners", "function"
    trio.serve_ssl_over_tcp(par, par, par)  # error: 4, "trio.serve_ssl_over_tcp", "function"
    trio.serve_tcp(par, par)  # error: 4, "trio.serve_tcp", "function"
    trio.sleep(par)  # error: 4, "trio.sleep", "function"
    trio.sleep_forever()  # error: 4, "trio.sleep_forever", "function"
    trio.sleep_until(par)  # error: 4, "trio.sleep_until", "function"

    # long lines, wheee
    trio.lowlevel.cancel_shielded_checkpoint()  # error: 4, "trio.lowlevel.cancel_shielded_checkpoint", "function"
    trio.lowlevel.checkpoint()  # error: 4, "trio.lowlevel.checkpoint", "function"
    trio.lowlevel.checkpoint_if_cancelled()  # error: 4, "trio.lowlevel.checkpoint_if_cancelled", "function"
    trio.lowlevel.open_process()  # error: 4, "trio.lowlevel.open_process", "function"
    trio.lowlevel.permanently_detach_coroutine_object(par)  # error: 4, "trio.lowlevel.permanently_detach_coroutine_object", "function"
    trio.lowlevel.reattach_detached_coroutine_object(par, par)  # error: 4, "trio.lowlevel.reattach_detached_coroutine_object", "function"
    trio.lowlevel.temporarily_detach_coroutine_object(par)  # error: 4, "trio.lowlevel.temporarily_detach_coroutine_object", "function"
    trio.lowlevel.wait_readable(par)  # error: 4, "trio.lowlevel.wait_readable", "function"
    trio.lowlevel.wait_task_rescheduled(par)  # error: 4, "trio.lowlevel.wait_task_rescheduled", "function"
    trio.lowlevel.wait_writable(par)  # error: 4, "trio.lowlevel.wait_writable", "function"
    # fmt: on
    # safe
    async with await trio.open_file(par) as f:
        pass

    async with trio.open_file(par) as f:  # error: 15, "trio.open_file", "function"
        pass

    # safe in theory, but deemed sufficiently poor style that parsing
    # it isn't supported
    k = trio.open_file(par)  # error: 8, "trio.open_file", "function"
    await k

    # issue #56
    async with trio.open_nursery() as nursery:
        await nursery.start(myasyncfun)
        await nursery.start_foo()

        nursery.start(myasyncfun)  # error: 8, "trio.Nursery.start", "method"
        None.start()  # type: ignore
        nursery.start_soon(par)
        nursery.start_foo()

        async with trio.open_nursery() as booboo:
            booboo.start(myasyncfun)  # error: 12, "trio.Nursery.start", "method"

        barbar: trio.Nursery = ...
        barbar.start(myasyncfun)  # error: 8, "trio.Nursery.start", "method"
