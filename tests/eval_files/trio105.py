# NOANYIO
from typing import Any

import trio

par: Any = ...


async def foo():
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
    await trio.serve_listeners(par, par)
    await trio.serve_ssl_over_tcp()
    await trio.serve_tcp()
    await trio.sleep()
    await trio.sleep_forever()
    await trio.sleep_until()
    await trio.lowlevel.cancel_shielded_checkpoint()
    await trio.lowlevel.checkpoint()
    await trio.lowlevel.checkpoint_if_cancelled()
    await trio.lowlevel.open_process()
    await trio.lowlevel.permanently_detach_coroutine_object()
    await trio.lowlevel.reattach_detached_coroutine_object()
    await trio.lowlevel.temporarily_detach_coroutine_object()
    await trio.lowlevel.wait_readable()
    await trio.lowlevel.wait_task_rescheduled()
    await trio.lowlevel.wait_writable()

    # all async functions
    trio.aclose_forcefully()  # error: 4, "trio.aclose_forcefully", "function"
    trio.open_file()  # error: 4, "trio.open_file", "function"
    trio.open_ssl_over_tcp_listeners()  # error: 4, "trio.open_ssl_over_tcp_listeners", "function"
    trio.open_ssl_over_tcp_stream()  # error: 4, "trio.open_ssl_over_tcp_stream", "function"
    trio.open_tcp_listeners()  # error: 4, "trio.open_tcp_listeners", "function"
    trio.open_tcp_stream()  # error: 4, "trio.open_tcp_stream", "function"
    trio.open_unix_socket()  # error: 4, "trio.open_unix_socket", "function"
    trio.run_process()  # error: 4, "trio.run_process", "function"
    trio.serve_listeners()  # error: 4, "trio.serve_listeners", "function"
    trio.serve_ssl_over_tcp()  # error: 4, "trio.serve_ssl_over_tcp", "function"
    trio.serve_tcp()  # error: 4, "trio.serve_tcp", "function"
    trio.sleep()  # error: 4, "trio.sleep", "function"
    trio.sleep_forever()  # error: 4, "trio.sleep_forever", "function"
    trio.sleep_until()  # error: 4, "trio.sleep_until", "function"

    # long lines, wheee
    trio.lowlevel.cancel_shielded_checkpoint()  # error: 4, "trio.lowlevel.cancel_shielded_checkpoint", "function"
    trio.lowlevel.checkpoint()  # error: 4, "trio.lowlevel.checkpoint", "function"
    trio.lowlevel.checkpoint_if_cancelled()  # error: 4, "trio.lowlevel.checkpoint_if_cancelled", "function"
    trio.lowlevel.open_process()  # error: 4, "trio.lowlevel.open_process", "function"
    trio.lowlevel.permanently_detach_coroutine_object()  # error: 4, "trio.lowlevel.permanently_detach_coroutine_object", "function"
    trio.lowlevel.reattach_detached_coroutine_object()  # error: 4, "trio.lowlevel.reattach_detached_coroutine_object", "function"
    trio.lowlevel.temporarily_detach_coroutine_object()  # error: 4, "trio.lowlevel.temporarily_detach_coroutine_object", "function"
    trio.lowlevel.wait_readable()  # error: 4, "trio.lowlevel.wait_readable", "function"
    trio.lowlevel.wait_task_rescheduled()  # error: 4, "trio.lowlevel.wait_task_rescheduled", "function"
    trio.lowlevel.wait_writable()  # error: 4, "trio.lowlevel.wait_writable", "function"

    # safe
    async with await trio.open_file() as f:
        pass

    async with trio.open_file() as f:  # error: 15, "trio.open_file", "function"
        pass

    # safe in theory, but deemed sufficiently poor style that parsing
    # it isn't supported
    k = trio.open_file()  # error: 8, "trio.open_file", "function"
    await k

    # issue #56
    nursery = trio.open_nursery()
    await nursery.start()
    await nursery.start_foo()

    nursery.start()  # error: 4, "trio.Nursery.start", "method"
    None.start()  # type: ignore
    nursery.start_soon()
    nursery.start_foo()

    with trio.open_nursery() as booboo:
        booboo.start()  # error: 8, "trio.Nursery.start", "method"

    barbar: trio.Nursery = ...
    barbar.start()  # error: 4, "trio.Nursery.start", "method"
