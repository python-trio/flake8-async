import trio


async def foo():
    # not async
    trio.run()

    # safely awaited
    await trio.aclose_forcefully()
    await trio.open_file()
    await trio.open_ssl_over_tcp_listeners()
    await trio.open_ssl_over_tcp_stream()
    await trio.open_tcp_listeners()
    await trio.open_tcp_stream()
    await trio.open_unix_socket()
    await trio.run_process()
    await trio.serve_listeners()
    await trio.serve_ssl_over_tcp()
    await trio.serve_tcp()
    await trio.sleep()
    await trio.sleep_forever()
    await trio.sleep_until()

    # errors
    trio.aclose_forcefully()
    trio.open_file()
    trio.open_ssl_over_tcp_listeners()
    trio.open_ssl_over_tcp_stream()
    trio.open_tcp_listeners()
    trio.open_tcp_stream()
    trio.open_unix_socket()
    trio.run_process()
    trio.serve_listeners()
    trio.serve_ssl_over_tcp()
    trio.serve_tcp()
    trio.sleep()
    trio.sleep_forever()
    trio.sleep_until()

    # safe
    async with await trio.open_file() as f:
        pass

    # error
    async with trio.open_file() as f:
        pass

    # safe in theory, but deemed sufficiently poor style that parsing
    # it isn't supported
    k = trio.open_file()
    await k
