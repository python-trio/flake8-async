# type: ignore
# ARG --enable-visitor-codes-regex=(TRIO220|TRIO221|TRIO222)


async def foo():
    subprocess.Popen()  # TRIO220: 4, 'subprocess.Popen', "trio"
    os.system()  # TRIO221: 4, 'os.system', "trio"

    system()
    os.system.anything()
    os.anything()

    subprocess.run()  # TRIO221: 4, 'subprocess.run', "trio"
    subprocess.call()  # TRIO221: 4, 'subprocess.call', "trio"
    subprocess.check_call()  # TRIO221: 4, 'subprocess.check_call', "trio"
    subprocess.check_output()  # TRIO221: 4, 'subprocess.check_output', "trio"
    subprocess.getoutput()  # TRIO221: 4, 'subprocess.getoutput', "trio"
    subprocess.getstatusoutput()  # TRIO221: 4, 'subprocess.getstatusoutput', "trio"

    await async_fun(
        subprocess.getoutput()  # TRIO221: 8, 'subprocess.getoutput', "trio"
    )

    subprocess.anything()
    subprocess.foo()
    subprocess.bar.foo()
    subprocess()

    os.posix_spawn()  # TRIO221: 4, 'os.posix_spawn', "trio"
    os.posix_spawnp()  # TRIO221: 4, 'os.posix_spawnp', "trio"

    os.spawn()
    os.spawn
    os.spawnllll()

    os.spawnl()  # TRIO221: 4,   'os.spawnl', "trio"
    os.spawnle()  # TRIO221: 4,  'os.spawnle', "trio"
    os.spawnlp()  # TRIO221: 4,  'os.spawnlp', "trio"
    os.spawnlpe()  # TRIO221: 4, 'os.spawnlpe', "trio"
    os.spawnv()  # TRIO221: 4,   'os.spawnv', "trio"
    os.spawnve()  # TRIO221: 4,  'os.spawnve', "trio"
    os.spawnvp()  # TRIO221: 4,  'os.spawnvp', "trio"
    os.spawnvpe()  # TRIO221: 4, 'os.spawnvpe', "trio"

    # if mode is given, and is not os.P_WAIT: TRIO220
    os.spawnl(os.P_NOWAIT)  # TRIO220: 4,   'os.spawnl', "trio"
    os.spawnl(P_NOWAIT)  # TRIO220: 4,   'os.spawnl', "trio"
    os.spawnl(mode=os.P_NOWAIT)  # TRIO220: 4,   'os.spawnl', "trio"
    os.spawnl(mode=P_NOWAIT)  # TRIO220: 4,   'os.spawnl', "trio"

    # if it is P_WAIT, TRIO221
    os.spawnl(os.P_WAIT)  # TRIO221: 4,   'os.spawnl', "trio"
    os.spawnl(P_WAIT)  # TRIO221: 4,   'os.spawnl', "trio"
    os.spawnl(mode=os.P_WAIT)  # TRIO221: 4,   'os.spawnl', "trio"
    os.spawnl(mode=P_WAIT)  # TRIO221: 4,   'os.spawnl', "trio"
    # treating this as 221 to simplify code, and see no real reason not to
    os.spawnl(foo.P_WAIT)  # TRIO221: 4,   'os.spawnl', "trio"

    # other weird cases: TRIO220
    os.spawnl(0)  # TRIO220: 4,   'os.spawnl', "trio"
    os.spawnl(1)  # TRIO220: 4,   'os.spawnl', "trio"
    os.spawnl(foo())  # TRIO220: 4,   'os.spawnl', "trio"

    # TRIO222
    os.wait()  # TRIO222: 4, 'os.wait', "trio"
    os.wait3()  # TRIO222: 4, 'os.wait3', "trio"
    os.wait4()  # TRIO222: 4, 'os.wait4', "trio"
    os.waitid()  # TRIO222: 4, 'os.waitid', "trio"
    os.waitpid()  # TRIO222: 4, 'os.waitpid', "trio"

    os.waitpi()
    os.waiti()
