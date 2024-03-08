# ASYNCIO_NO_ERROR - no asyncio.move_on_after
# AUTOFIX
import trio

# a
# b
# error: 5, "trio", "move_on_after"
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
pass
# n

# error: 5, "trio", "move_on_after"
...


# a
# b
# fmt: off
...;...;... # error: 5, "trio", "move_on_after"
# fmt: on
# c
# d


# multiline with, despite only being one statement
# a
# b
# c
# error: 4, "trio", "move_on_after"
# d
# e
# f
# g
# h
# this comment is kept
...

# fmt: off
# a
# b
# error: 4, "trio", "move_on_after"
# c
...; ...; ...
# fmt: on


# same-line with
# fmt: off
print(1)  # ASYNC100: 5, 'trio', 'fail_after'
# fmt: on
