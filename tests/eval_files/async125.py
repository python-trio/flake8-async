import trio
from typing import Final

# ASYNCIO_NO_ERROR
# anyio.[fail/move_on]_at doesn't exist, but no harm in erroring if we encounter them

trio.fail_at(5)  # ASYNC125: 13, "trio.fail_at", "trio"
trio.fail_at(deadline=5)  # ASYNC125: 22, "trio.fail_at", "trio"
trio.move_on_at(10**3)  # ASYNC125: 16, "trio.move_on_at", "trio"
trio.fail_at(7 * 3 + 2 / 5 - (8**7))  # ASYNC125: 13, "trio.fail_at", "trio"

trio.CancelScope(deadline=7)  # ASYNC125: 26, "trio.CancelScope", "trio"
trio.CancelScope(shield=True, deadline=7)  # ASYNC125: 39, "trio.CancelScope", "trio"

# we *could* tell them to use math.inf here ...
trio.fail_at(10**1000)  # ASYNC125: 13, "trio.fail_at", "trio"

# _after is fine
trio.fail_after(5)
trio.move_on_after(2.3)

trio.fail_at(trio.current_time())
trio.fail_at(trio.current_time() + 7)

# relative_deadline is fine, though anyio doesn't have it
trio.CancelScope(relative_deadline=7)

# does not trigger on other "constants".. but we could opt to trigger on
# any all-caps variable, or on :Final
MY_CONST_VALUE = 7
trio.fail_at(MY_CONST_VALUE)
my_final_value: Final = 3
trio.fail_at(my_final_value)
