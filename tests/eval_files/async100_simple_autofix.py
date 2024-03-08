# ASYNCIO_NO_ERROR - no asyncio.move_on_after
# AUTOFIX
import trio

# a
# b
with trio.move_on_after(10):  # error: 5, "trio", "move_on_after"
    # c
    # d
    print(1)  # e
    # f
    # g
    print(2)  # h
    # i
    # j
    print(3)  # k
    # l
    # m
# n

with trio.move_on_after(10):  # error: 5, "trio", "move_on_after"
    ...


# a
# b
# fmt: off
with trio.move_on_after(10): ...;...;... # error: 5, "trio", "move_on_after"
# fmt: on
# c
# d


# multiline with, despite only being one statement
with (  # a
    # b
    # c
    trio.move_on_after(  # error: 4, "trio", "move_on_after"
        # d
        9999999999999999999999999999999999999999999999999999999  # e
        # f
    )  # g
    # h
):  # this comment is kept
    ...

# fmt: off
with (  # a
    # b
    trio.move_on_after(10)  # error: 4, "trio", "move_on_after"
    # c
): ...; ...; ...
# fmt: on


# same-line with
# fmt: off
with trio.fail_after(5): print(1)  # ASYNC100: 5, 'trio', 'fail_after'
# fmt: on
