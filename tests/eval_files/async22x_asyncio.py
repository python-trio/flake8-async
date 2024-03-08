# type: ignore
# ARG --enable=ASYNC220,ASYNC221,ASYNC222
# NOANYIO
# NOTRIO
# BASE_LIBRARY asyncio

# same content as async22x.py, but different error message


async def foo():
    await async_fun(
        subprocess.getoutput()  # ASYNC221_asyncio: 8, 'subprocess.getoutput'
    )
    subprocess.Popen()  # ASYNC220_asyncio: 4, 'subprocess.Popen'
    os.system()  # ASYNC221_asyncio: 4, 'os.system'

    system()
    os.system.anything()
    os.anything()

    subprocess.run()  # ASYNC221_asyncio: 4, 'subprocess.run'
    subprocess.call()  # ASYNC221_asyncio: 4, 'subprocess.call'
    subprocess.check_call()  # ASYNC221_asyncio: 4, 'subprocess.check_call'
    subprocess.check_output()  # ASYNC221_asyncio: 4, 'subprocess.check_output'
    subprocess.getoutput()  # ASYNC221_asyncio: 4, 'subprocess.getoutput'
    subprocess.getstatusoutput()  # ASYNC221_asyncio: 4, 'subprocess.getstatusoutput'

    await async_fun(
        subprocess.getoutput()  # ASYNC221_asyncio: 8, 'subprocess.getoutput'
    )

    subprocess.anything()
    subprocess.foo()
    subprocess.bar.foo()
    subprocess()

    os.posix_spawn()  # ASYNC221_asyncio: 4, 'os.posix_spawn'
    os.posix_spawnp()  # ASYNC221_asyncio: 4, 'os.posix_spawnp'

    os.spawn()
    os.spawn
    os.spawnllll()

    os.spawnl()  # ASYNC221_asyncio: 4,   'os.spawnl'
    os.spawnle()  # ASYNC221_asyncio: 4,  'os.spawnle'
    os.spawnlp()  # ASYNC221_asyncio: 4,  'os.spawnlp'
    os.spawnlpe()  # ASYNC221_asyncio: 4, 'os.spawnlpe'
    os.spawnv()  # ASYNC221_asyncio: 4,   'os.spawnv'
    os.spawnve()  # ASYNC221_asyncio: 4,  'os.spawnve'
    os.spawnvp()  # ASYNC221_asyncio: 4,  'os.spawnvp'
    os.spawnvpe()  # ASYNC221_asyncio: 4, 'os.spawnvpe'

    # if mode is given, and is not os.P_WAIT: ASYNC220
    os.spawnl(os.P_NOWAIT)  # ASYNC220_asyncio: 4,   'os.spawnl'
    os.spawnl(P_NOWAIT)  # ASYNC220_asyncio: 4,   'os.spawnl'
    os.spawnl(mode=os.P_NOWAIT)  # ASYNC220_asyncio: 4,   'os.spawnl'
    os.spawnl(mode=P_NOWAIT)  # ASYNC220_asyncio: 4,   'os.spawnl'

    # if it is P_WAIT, ASYNC221
    os.spawnl(os.P_WAIT)  # ASYNC221_asyncio: 4,   'os.spawnl'
    os.spawnl(P_WAIT)  # ASYNC221_asyncio: 4,   'os.spawnl'
    os.spawnl(mode=os.P_WAIT)  # ASYNC221_asyncio: 4,   'os.spawnl'
    os.spawnl(mode=P_WAIT)  # ASYNC221_asyncio: 4,   'os.spawnl'
    # treating this as 221 to simplify code, and see no real reason not to
    os.spawnl(foo.P_WAIT)  # ASYNC221_asyncio: 4,   'os.spawnl'

    # other weird cases: ASYNC220
    os.spawnl(0)  # ASYNC220_asyncio: 4,   'os.spawnl'
    os.spawnl(1)  # ASYNC220_asyncio: 4,   'os.spawnl'
    os.spawnl(foo())  # ASYNC220_asyncio: 4,   'os.spawnl'

    # ASYNC222
    os.wait()  # ASYNC222_asyncio: 4, 'os.wait'
    os.wait3()  # ASYNC222_asyncio: 4, 'os.wait3'
    os.wait4()  # ASYNC222_asyncio: 4, 'os.wait4'
    os.waitid()  # ASYNC222_asyncio: 4, 'os.waitid'
    os.waitpid()  # ASYNC222_asyncio: 4, 'os.waitpid'

    os.waitpi()
    os.waiti()
