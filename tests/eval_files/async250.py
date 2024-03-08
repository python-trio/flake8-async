# NOASYNCIO # formatting sufficiently different that test infra needs separate file
async def foo():
    k = input()  # ASYNC250: 8, "trio.to_thread.run_sync"
    input("hello world")  # ASYNC250: 4, "trio.to_thread.run_sync"
