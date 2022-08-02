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
    trio.aclose_forcefully()  # error: 4, aclose_forcefully
    trio.open_file()  # error: 4, open_file
    trio.open_ssl_over_tcp_listeners()  # error: 4, open_ssl_over_tcp_listeners
    trio.open_ssl_over_tcp_stream()  # error: 4, open_ssl_over_tcp_stream
    trio.open_tcp_listeners()  # error: 4, open_tcp_listeners
    trio.open_tcp_stream()  # error: 4, open_tcp_stream
    trio.open_unix_socket()  # error: 4, open_unix_socket
    trio.run_process()  # error: 4, run_process
    trio.serve_listeners()  # error: 4, serve_listeners
    trio.serve_ssl_over_tcp()  # error: 4, serve_ssl_over_tcp
    trio.serve_tcp()  # error: 4, serve_tcp
    trio.sleep()  # error: 4, sleep
    trio.sleep_forever()  # error: 4, sleep_forever
    trio.sleep_until()  # error: 4, sleep_until

    # safe
    async with await trio.open_file() as f:
        pass

    async with trio.open_file() as f:  # error: 15, open_file
        pass

    # safe in theory, but deemed sufficiently poor style that parsing
    # it isn't supported
    k = trio.open_file()  # error: 8, open_file
    await k
