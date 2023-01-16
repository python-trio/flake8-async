# ARG --enable-visitor-codes-regex=(TRIO220|TRIO221)


async def foo():
    subprocess.Popen()  # TRIO220: 4, 'subprocess.Popen'
    os.system()  # TRIO221: 4, 'os.system'

    system()
    os.system.anything()
    os.anything()

    subprocess.run()  # TRIO221: 4, 'subprocess.run'
    subprocess.call()  # TRIO221: 4, 'subprocess.call'
    subprocess.check_call()  # TRIO221: 4, 'subprocess.check_call'
    subprocess.check_output()  # TRIO221: 4, 'subprocess.check_output'
    subprocess.getoutput()  # TRIO221: 4, 'subprocess.getoutput'
    subprocess.getstatusoutput()  # TRIO221: 4, 'subprocess.getstatusoutput'

    await async_fun(subprocess.getoutput())  # TRIO221: 20, 'subprocess.getoutput'

    subprocess.anything()
    subprocess.foo()
    subprocess.bar.foo()
    subprocess()

    os.spawn()
    os.spawn

    os.spawnl()  # TRIO221: 4,   'os.spawnl'
    os.spawnle()  # TRIO221: 4,  'os.spawnle'
    os.spawnlp()  # TRIO221: 4,  'os.spawnlp'
    os.spawnlpe()  # TRIO221: 4, 'os.spawnlpe'
    os.spawnv()  # TRIO221: 4,   'os.spawnv'
    os.spawnve()  # TRIO221: 4,  'os.spawnve'
    os.spawnvp()  # TRIO221: 4,  'os.spawnvp'
    os.spawnvpe()  # TRIO221: 4, 'os.spawnvpe'

    # if mode is given, and is not os.P_WAIT: TRIO220
    os.spawnl(os.P_NOWAIT)  # TRIO220: 4,   'os.spawnl'
    os.spawnl(P_NOWAIT)  # TRIO220: 4,   'os.spawnl'
    os.spawnl(mode=os.P_NOWAIT)  # TRIO220: 4,   'os.spawnl'
    os.spawnl(mode=P_NOWAIT)  # TRIO220: 4,   'os.spawnl'

    # if it is P_WAIT, TRIO221
    os.spawnl(os.P_WAIT)  # TRIO221: 4,   'os.spawnl'
    os.spawnl(P_WAIT)  # TRIO221: 4,   'os.spawnl'
    os.spawnl(mode=os.P_WAIT)  # TRIO221: 4,   'os.spawnl'
    os.spawnl(mode=P_WAIT)  # TRIO221: 4,   'os.spawnl'
    # treating this as 221 to simplify code, and see no real reason not to
    os.spawnl(foo.P_WAIT)  # TRIO221: 4,   'os.spawnl'

    # other weird cases: TRIO220
    os.spawnl(0)  # TRIO220: 4,   'os.spawnl'
    os.spawnl(1)  # TRIO220: 4,   'os.spawnl'
    os.spawnl(foo())  # TRIO220: 4,   'os.spawnl'
