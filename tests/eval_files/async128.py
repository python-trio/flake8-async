"""Test file for ASYNC128 task-status-never-started."""

# ASYNC128 does not care about the imported library, so will raise errors regardless
# of trio/anyio/asyncio

from typing import Any

import trio
from trio import TaskStatus


async def never_started(  # error: 0, "never_started", "task_status"
    task_status=trio.TASK_STATUS_IGNORED,
):
    await trio.sleep(1)


async def started(task_status=trio.TASK_STATUS_IGNORED):
    task_status.started()


async def started_with_value(task_status=trio.TASK_STATUS_IGNORED):
    task_status.started(7)


async def no_task_status():
    await trio.sleep(1)


# a conditional call counts - no attempt is made to check all code paths
async def conditional_start(condition: bool, *, task_status):
    if condition:
        task_status.started()


# ... even if the call can never actually execute
async def unreachable_start(task_status):
    for _ in range(0):
        task_status.started()


# annotated parameters trigger regardless of their name
async def annotated(status: TaskStatus[int]):  # error: 0, "annotated", "status"
    await trio.sleep(1)


async def annotated_bare(status: TaskStatus):  # error: 0, "annotated_bare", "status"
    await trio.sleep(1)


async def annotated_qualified(  # error: 0, "annotated_qualified", "status"
    status: trio.TaskStatus[int],
):
    await trio.sleep(1)


async def annotated_ok(status: TaskStatus[int]):
    status.started(5)


# a `task_status` parameter that's positional-only can't be startable, but an
# explicit annotation still counts
async def posonly_ignored(task_status, /):
    await trio.sleep(1)


async def posonly_annotated(  # error: 0, "posonly_annotated", "status"
    status: TaskStatus[int], /
):
    await trio.sleep(1)


async def starargs_ignored(*task_status, **kwargs):
    await trio.sleep(1)


# passing `task_status` to a helper does not count, even if the helper calls
# `started()` for you. The check is intentionally strict, silence it with `noqa`
# if you're intentionally proxying it.
async def helper(fn: Any, task_status):  # error: 0, "helper", "task_status"
    await fn(task_status=task_status)


# aliasing does not count either
async def aliased(task_status):  # error: 0, "aliased", "task_status"
    ts = task_status
    ts.started()


# accessing `.started` without calling it does not count
async def not_called(task_status):  # error: 0, "not_called", "task_status"
    task_status.started


# the call must be on the parameter itself, not e.g. an attribute by the same name
class AttributeStatus:
    task_status: TaskStatus[None]

    async def relay(self, task_status):  # error: 4, "relay", "task_status"
        self.task_status.started()


# calls in nested functions closing over the parameter do count
async def closure(task_status=trio.TASK_STATUS_IGNORED):
    def inner():
        task_status.started()

    inner()


async def lambda_closure(task_status=trio.TASK_STATUS_IGNORED):
    fn = lambda: task_status.started()
    fn()


# ... but not if the nested function rebinds the name; it is instead
# checked on its own
async def shadowed(task_status):  # error: 0, "shadowed", "task_status"
    async def inner(task_status=trio.TASK_STATUS_IGNORED):
        task_status.started()

    await inner()


async def shadowed_by_lambda(  # error: 0, "shadowed_by_lambda", "task_status"
    task_status,
):
    fn = lambda task_status: task_status.started()
    fn(None)


async def shadowed_by_vararg(  # error: 0, "shadowed_by_vararg", "task_status"
    task_status,
):
    def inner(*task_status: Any):
        task_status[0].started()

    inner(None)


async def nested_never_started():
    async def inner(  # error: 4, "inner", "task_status"
        task_status=trio.TASK_STATUS_IGNORED,
    ):
        await trio.sleep(1)

    await inner()


# stub bodies don't error, e.g. overloads, protocols, and abstract methods
class StartableProtocol:
    async def ellipsis_body(self, *, task_status: TaskStatus[None]): ...

    async def pass_body(self, *, task_status: TaskStatus[None]):
        pass

    async def docstring_body(self, *, task_status: TaskStatus[None]):
        """It has a docstring."""

    async def raise_body(self, *, task_status: TaskStatus[None]):
        raise NotImplementedError

    async def method_never_started(  # error: 4, "method_never_started", "task_status"
        self, task_status=trio.TASK_STATUS_IGNORED
    ):
        await trio.sleep(1)


# sync functions are not checked - they cannot be passed to `.start()`
def sync_fn(task_status):
    return None
