# AUTOFIX
# ARG --enable=ASYNC910,ASYNC911,ASYNC914
import trio
import trio.lowlevel
from typing import Any


def condition() -> bool:
    return False


async def foo() -> Any:
    await trio.lowlevel.checkpoint()


# branching logic
async def foo_none_none():
    if condition():
        ...
    await trio.lowlevel.checkpoint()


async def foo_none_false():
    if condition():
        await trio.lowlevel.checkpoint()
    await trio.lowlevel.checkpoint()


async def foo_none_true():
    if condition():
        await trio.lowlevel.checkpoint()
    await trio.lowlevel.checkpoint()


async def foo_none_obj():
    if condition():
        await foo()
    await trio.lowlevel.checkpoint()


async def foo_false_false():
    await trio.lowlevel.checkpoint()
    if condition():
        ...


# foo_false_true(): # not possible, state can't change false<->true


async def foo_false_obj():
    await trio.lowlevel.checkpoint()
    if condition():
        await foo()


async def foo_true_true():
    await trio.lowlevel.checkpoint()
    if condition():
        ...


async def foo_true_obj():
    await trio.lowlevel.checkpoint()  # false -> obj
    if condition():
        await foo()


async def sequence_00():
    await trio.lowlevel.checkpoint()


async def sequence_01():
    await foo()


async def sequence_10():
    await foo()


async def sequence_11():
    await foo()
    await foo()


# all permutations of 3
async def sequencing_000():
    await trio.lowlevel.checkpoint()


async def sequencing_001():
    await foo()


async def sequencing_010():
    await foo()


async def sequencing_011():
    await foo()
    await foo()


async def sequencing_100():
    await foo()


async def sequencing_101():
    await foo()
    await foo()


async def sequencing_110():
    await foo()
    await foo()


async def sequencing_111():
    await foo()
    await foo()
    await foo()


async def foo_raise():
    raise


# when entering an if statement, there's 3 possible states:
# there's uncheckpointed statements
# checkpointed by lowlevel
# checkpointed by non-lowlevel


# we need to determine whether to treat the if statement as a lowlevel checkpoint,
# a non-lowlevel checkpoint, or not checkpointing. Both w/r/t statements before it, and
# separately w/r/t statements after it.
# and we also need to handle redundant checkpoints within bodies of it.

# the if statement can:

# 1. not checkpoint at all, easy
# 2. checkpoint in all branches with lowlevel, in which case they can all be removed
#        TODO: this is not handled
# 3. checkpoint in at least some branches with non-lowlevel.


async def foo_if():
    if condition():
        await trio.lowlevel.checkpoint()
    else:
        await foo()


async def foo_if_2():
    if condition():
        await trio.lowlevel.checkpoint()
    else:
        await trio.lowlevel.checkpoint()


async def foo_if_3():
    await trio.lowlevel.checkpoint()
    if condition():
        pass
    else:
        pass


async def foo_if_4():
    if condition():
        await trio.lowlevel.checkpoint()
    else:
        await trio.lowlevel.checkpoint()


async def foo_if_5():
    if condition():
        pass
    else:
        pass
    await foo()


async def foo_if_6():
    # lowlevel checkpoints made redundant within the same block will warn
    if condition():
        await foo()
    else:
        await foo()


async def foo_if_7():
    await trio.lowlevel.checkpoint()
    if condition():
        await foo()


async def foo_if_0000():
    await trio.lowlevel.checkpoint()
    if condition():
        pass
    else:
        pass


async def foo_if_0001():
    if condition():
        pass
    else:
        pass
    await foo()


async def foo_if_0010():  # not ideal
    await trio.lowlevel.checkpoint()
    if condition():
        pass
    else:
        await foo()


async def foo_if_0010_2():  # not ideal
    await trio.lowlevel.checkpoint()
    if condition():
        pass
    else:
        await foo()


async def foo_if_0100():
    await trio.lowlevel.checkpoint()
    if condition():
        await foo()
    else:
        pass


async def foo_if_1000():
    await foo()
    if condition():
        pass
    else:
        pass


async def foo_if_1000_1():
    await foo()
    yield
    if condition():
        await trio.lowlevel.checkpoint()
    else:
        await trio.lowlevel.checkpoint()


async def foo_if_1000_2():
    await foo()
    if condition():
        yield
        await trio.lowlevel.checkpoint()
    else:
        pass


async def foo_if_1000_3():
    await foo()
    if condition():
        yield
    else:
        pass
    await trio.lowlevel.checkpoint()


async def foo_if_1000_4():
    await foo()
    if condition():
        pass
    else:
        yield
        await trio.lowlevel.checkpoint()


async def foo_if_1000_5():
    await foo()
    if condition():
        pass
    else:
        yield
    await trio.lowlevel.checkpoint()


async def foo_if_1000_6():
    await foo()
    if condition():
        pass
    else:
        pass
    yield
    await trio.lowlevel.checkpoint()


# Current logic is very conservative, treating the artificial statement injected
# at the start of the loop as something that needs checkpointing.
# This probably isn't a bad thing, as it's not unusual to want to checkpoint in loops
# to let the scheduler run (even if it's not detected as infinite by us).
async def foo_while_1():
    await trio.lowlevel.checkpoint()
    while condition():
        await trio.lowlevel.checkpoint()  # ignored


async def foo_while_2():
    await trio.lowlevel.checkpoint()  # but this should probably error
    while True:
        await foo()


async def foo_while_3():
    await trio.lowlevel.checkpoint()
    while condition():
        await foo()


async def foo_for_1():
    for i in range(3):
        await trio.lowlevel.checkpoint()
    else:
        await foo()


async def foo_try_1():
    await trio.lowlevel.checkpoint()
    try:
        pass
    except:
        pass


async def foo_try_2():
    await trio.lowlevel.checkpoint()
    try:
        pass
    except:
        await foo()


async def foo_try_3():
    await trio.lowlevel.checkpoint()
    try:
        await foo()
    except:
        pass


async def foo_try_4():
    await trio.lowlevel.checkpoint()
    try:
        await foo()
    except:
        await foo()


async def foo_try_5():
    await foo()
    try:
        pass
    except:
        pass


async def foo_try_6():
    await foo()
    try:
        pass
    except:
        await foo()


async def foo_try_7():
    await foo()
    try:
        await foo()
    except:
        pass


async def foo_try_8():
    await foo()
    try:
        await foo()
    except:
        await foo()


async def foo_try_9():
    try:
        pass
    except:
        await foo()
    else:
        await foo()


async def foo_try_10():
    try:
        await trio.lowlevel.checkpoint()
    finally:
        await foo()


async def foo_try_11():
    try:
        await trio.lowlevel.checkpoint()
    except:
        await foo()


async def foo_try_12():
    try:
        pass
    except:
        ...
    else:
        await foo()
    await trio.lowlevel.checkpoint()


async def foo_try_13():
    try:
        ...
    except ValueError:
        ...
    except:
        raise
    finally:
        await trio.lowlevel.checkpoint()
