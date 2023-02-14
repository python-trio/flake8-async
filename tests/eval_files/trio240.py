# type: ignore
import os.path
from os.path import isfile, normpath, relpath


async def foo():
    normpath("")  # TRIO240: 4, 'normpath', "trio"
    relpath("")  # TRIO240: 4, 'relpath', "trio"
    isfile("")  # TRIO240: 4, 'isfile', "trio"

    os.path._path_normpath(...)  # TRIO240: 4, '_path_normpath', "trio"
    os.path.normpath("")  # TRIO240: 4, 'normpath', "trio"
    os.path._joinrealpath(...)  # TRIO240: 4, '_joinrealpath', "trio"
    os.path.islink("")  # TRIO240: 4, 'islink', "trio"
    os.path.lexists("")  # TRIO240: 4, 'lexists', "trio"
    os.path.ismount("")  # TRIO240: 4, 'ismount', "trio"
    os.path.realpath("")  # TRIO240: 4, 'realpath', "trio"
    os.path.exists("")  # TRIO240: 4, 'exists', "trio"
    os.path.isdir("")  # TRIO240: 4, 'isdir', "trio"
    os.path.isfile("")  # TRIO240: 4, 'isfile', "trio"
    os.path.getatime("")  # TRIO240: 4, 'getatime', "trio"
    os.path.getctime("")  # TRIO240: 4, 'getctime', "trio"
    os.path.getmtime("")  # TRIO240: 4, 'getmtime', "trio"
    os.path.getsize("")  # TRIO240: 4, 'getsize', "trio"
    os.path.samefile("", "")  # TRIO240: 4, 'samefile', "trio"
    os.path.sameopenfile(0, 1)  # TRIO240: 4, 'sameopenfile', "trio"
    os.path.relpath("")  # TRIO240: 4, 'relpath', "trio"

    await os.path.isfile("")  # TRIO240: 10, 'isfile', "trio"
    print(os.path.isfile(""))  # TRIO240: 10, 'isfile', "trio"
    os.path.abspath("")
    os.path.anything("")


def foo2():
    os.path.isfile("")
