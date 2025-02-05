# ARG --enable=ASYNC124,ASYNC910,ASYNC911
from pytest import fixture


# @fixture with no params can be converted to sync
# 910/911 skips funcs with `@fixture` decorator, so this doesn't get auto"fixed"
@fixture
async def foo_fix_no_subfix():  # ASYNC124: 0
    print("blah")
