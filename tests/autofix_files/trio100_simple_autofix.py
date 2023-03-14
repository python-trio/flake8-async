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
...;...;...
# fmt: on
# c
# d

# Doesn't autofix With's with multiple withitems
with (
    trio.move_on_after(10),  # error: 4, "trio", "move_on_after"
    open("") as f,
):
    ...


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
