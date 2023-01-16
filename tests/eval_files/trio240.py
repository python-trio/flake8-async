import os.path
from os.path import isfile, normpath, relpath  # ....


async def foo():
    normpath("")  # TRIO240: 4, 'normpath'
    relpath("")  # TRIO240: 4, 'relpath'
    isfile("")  # TRIO240: 4, 'isfile'

    os.path._path_normpath(...)  # TRIO240: 4, '_path_normpath'
    os.path.normpath("")  # TRIO240: 4, 'normpath'
    os.path._joinrealpath(...)  # TRIO240: 4, '_joinrealpath'
    os.path.islink("")  # TRIO240: 4, 'islink'
    os.path.lexists("")  # TRIO240: 4, 'lexists'
    os.path.ismount("")  # TRIO240: 4, 'ismount'
    os.path.realpath("")  # TRIO240: 4, 'realpath'
    os.path.exists("")  # TRIO240: 4, 'exists'
    os.path.isdir("")  # TRIO240: 4, 'isdir'
    os.path.isfile("")  # TRIO240: 4, 'isfile'
    os.path.getatime("")  # TRIO240: 4, 'getatime'
    os.path.getctime("")  # TRIO240: 4, 'getctime'
    os.path.getmtime("")  # TRIO240: 4, 'getmtime'
    os.path.getsize("")  # TRIO240: 4, 'getsize'
    os.path.samefile("", "")  # TRIO240: 4, 'samefile'
    os.path.sameopenfile(0, 1)  # TRIO240: 4, 'sameopenfile'
    os.path.relpath("")  # TRIO240: 4, 'relpath'

    await os.path.isfile("")  # TRIO240: 10, 'isfile'
    print(os.path.isfile(""))  # TRIO240: 10, 'isfile'
    os.path.abspath("")
    os.path.anything("")


def foo2():
    os.path.isfile("")
