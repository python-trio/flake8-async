# type: ignore
# ARG --enable=ASYNC220,ASYNC221,ASYNC222
# NOASYNCIO - specifies error message differently


async def foo():
    await async_fun(
        subprocess.getoutput()  # ASYNC221: 8, 'subprocess.getoutput', "trio"
    )
    subprocess.Popen()  # ASYNC220: 4, 'subprocess.Popen', "trio"
    os.system()  # ASYNC221: 4, 'os.system', "trio"

    system()
    os.system.anything()
    os.anything()

    subprocess.run()  # ASYNC221: 4, 'subprocess.run', "trio"
    subprocess.call()  # ASYNC221: 4, 'subprocess.call', "trio"
    subprocess.check_call()  # ASYNC221: 4, 'subprocess.check_call', "trio"
    subprocess.check_output()  # ASYNC221: 4, 'subprocess.check_output', "trio"
    subprocess.getoutput()  # ASYNC221: 4, 'subprocess.getoutput', "trio"
    subprocess.getstatusoutput()  # ASYNC221: 4, 'subprocess.getstatusoutput', "trio"

    await async_fun(
        subprocess.getoutput()  # ASYNC221: 8, 'subprocess.getoutput', "trio"
    )

    subprocess.anything()
    subprocess.foo()
    subprocess.bar.foo()
    subprocess()

    os.posix_spawn()  # ASYNC221: 4, 'os.posix_spawn', "trio"
    os.posix_spawnp()  # ASYNC221: 4, 'os.posix_spawnp', "trio"

    os.spawn()
    os.spawn
    os.spawnllll()

    os.spawnl()  # ASYNC221: 4,   'os.spawnl', "trio"
    os.spawnle()  # ASYNC221: 4,  'os.spawnle', "trio"
    os.spawnlp()  # ASYNC221: 4,  'os.spawnlp', "trio"
    os.spawnlpe()  # ASYNC221: 4, 'os.spawnlpe', "trio"
    os.spawnv()  # ASYNC221: 4,   'os.spawnv', "trio"
    os.spawnve()  # ASYNC221: 4,  'os.spawnve', "trio"
    os.spawnvp()  # ASYNC221: 4,  'os.spawnvp', "trio"
    os.spawnvpe()  # ASYNC221: 4, 'os.spawnvpe', "trio"

    # if mode is given, and is not os.P_WAIT: ASYNC220
    os.spawnl(os.P_NOWAIT)  # ASYNC220: 4,   'os.spawnl', "trio"
    os.spawnl(P_NOWAIT)  # ASYNC220: 4,   'os.spawnl', "trio"
    os.spawnl(mode=os.P_NOWAIT)  # ASYNC220: 4,   'os.spawnl', "trio"
    os.spawnl(mode=P_NOWAIT)  # ASYNC220: 4,   'os.spawnl', "trio"

    # if it is P_WAIT, ASYNC221
    os.spawnl(os.P_WAIT)  # ASYNC221: 4,   'os.spawnl', "trio"
    os.spawnl(P_WAIT)  # ASYNC221: 4,   'os.spawnl', "trio"
    os.spawnl(mode=os.P_WAIT)  # ASYNC221: 4,   'os.spawnl', "trio"
    os.spawnl(mode=P_WAIT)  # ASYNC221: 4,   'os.spawnl', "trio"
    # treating this as 221 to simplify code, and see no real reason not to
    os.spawnl(foo.P_WAIT)  # ASYNC221: 4,   'os.spawnl', "trio"

    # other weird cases: ASYNC220
    os.spawnl(0)  # ASYNC220: 4,   'os.spawnl', "trio"
    os.spawnl(1)  # ASYNC220: 4,   'os.spawnl', "trio"
    os.spawnl(foo())  # ASYNC220: 4,   'os.spawnl', "trio"

    # ASYNC222
    os.wait()  # ASYNC222: 4, 'os.wait', "trio"
    os.wait3()  # ASYNC222: 4, 'os.wait3', "trio"
    os.wait4()  # ASYNC222: 4, 'os.wait4', "trio"
    os.waitid()  # ASYNC222: 4, 'os.waitid', "trio"
    os.waitpid()  # ASYNC222: 4, 'os.waitpid', "trio"

    os.waitpi()
    os.waiti()
