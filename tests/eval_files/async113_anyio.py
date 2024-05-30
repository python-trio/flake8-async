# mypy: disable-error-code="arg-type"
# ARG --startable-in-context-manager=my_startable
from contextlib import asynccontextmanager

import anyio


async def my_startable(
    task_status: anyio.abc.TaskStatus[object] = anyio.TASK_STATUS_IGNORED,
):
    task_status.started()
    await anyio.lowlevel.checkpoint()


@asynccontextmanager
async def foo():
    # create_task_group only exists in anyio
    async with anyio.create_task_group() as bar_tg:
        bar_tg.start_soon(my_startable)  # ASYNC113: 8
        # false alarm - anyio.run_process is not startable
        bar_tg.start_soon(anyio.run_process)  # ASYNC113: 8
        yield
