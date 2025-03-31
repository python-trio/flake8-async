# ARG --enable=ASYNC910,ASYNC911,ASYNC913
# AUTOFIX
# ASYNCIO_NO_AUTOFIX
import trio


async def foo(): ...


async def match_subject() -> None:
    match await foo():
        case False:
            pass


async def match_not_all_cases() -> (  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    None
):
    match foo():
        case 1:
            ...
        case _:
            await foo()
    await trio.lowlevel.checkpoint()


async def match_no_fallback() -> (  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    None
):
    match foo():
        case 1:
            await foo()
        case 2:
            await foo()
        case _ if True:
            await foo()
    await trio.lowlevel.checkpoint()


async def match_fallback_is_guarded() -> (  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    None
):
    match foo():
        case 1:
            await foo()
        case 2:
            await foo()
        case _ if foo():
            await foo()
    await trio.lowlevel.checkpoint()


async def match_all_cases() -> None:
    match foo():
        case 1:
            await foo()
        case 2:
            await foo()
        case _:
            await foo()


async def match_fallback_await_in_guard() -> None:
    # The case guard is only executed if the pattern matches, so we can mostly treat
    # it as part of the body, except for a special case for fallback+checkpointing guard.
    match foo():
        case 1 if await foo():
            ...
        case _ if await foo():
            ...


async def match_checkpoint_guard() -> None:
    # The above pattern is quite cursed, but this seems fairly reasonable to do.
    match foo():
        case 1 if await foo():
            ...
        case _:
            await foo()


async def match_not_checkpoint_in_all_guards() -> (  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    None
):
    match foo():
        case 1:
            ...
        case _ if await foo():
            ...
    await trio.lowlevel.checkpoint()
