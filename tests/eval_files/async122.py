# ASYNCIO_NO_ERROR

import trio


def safe():
    with trio.move_on_after(5):
        ...
    with open("hello"), trio.move_on_after(5):
        ...


def separated():
    k = trio.move_on_after(5)  # ASYNC122: 8, "trio.move_on_after"

    with k:
        ...

    l = trio.fail_after(5)  # ASYNC122: 8, "trio.fail_after"
    with l:
        ...


def fancy_thing_we_dont_cover():
    # it's hard to distinguish this bad case
    kk = trio.fail_after

    ll = kk(5)

    with ll:
        ...
    # from this good case
    with kk(5):
        ...
    # so we don't bother
