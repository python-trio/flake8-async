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

    # all async functions
    trio.aclose_forcefully()  # error
    trio.open_file()  # error
    trio.open_ssl_over_tcp_listeners()  # error
    trio.open_ssl_over_tcp_stream()  # error
    trio.open_tcp_listeners()  # error
    trio.open_tcp_stream()  # error
    trio.open_unix_socket()  # error
    trio.run_process()  # error
    trio.serve_listeners()  # error
    trio.serve_ssl_over_tcp()  # error
    trio.serve_tcp()  # error
    trio.sleep()  # error
    trio.sleep_forever()  # error
    trio.sleep_until()  # error

    # safe
    async with await trio.open_file() as f:
        pass

    async with trio.open_file() as f:  # error
        pass

    # safe in theory, but deemed sufficiently poor style that parsing
    # it isn't supported
    k = trio.open_file()  # error
    await k
