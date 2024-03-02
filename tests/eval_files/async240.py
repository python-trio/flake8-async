# type: ignore
# NOASYNCIO
import os.path
from os.path import isfile, normpath, relpath


async def foo():
    normpath("")  # ASYNC240: 4, 'normpath', "trio"
    relpath("")  # ASYNC240: 4, 'relpath', "trio"
    isfile("")  # ASYNC240: 4, 'isfile', "trio"

    os.path._path_normpath(...)  # ASYNC240: 4, '_path_normpath', "trio"
    os.path.normpath("")  # ASYNC240: 4, 'normpath', "trio"
    os.path._joinrealpath(...)  # ASYNC240: 4, '_joinrealpath', "trio"
    os.path.islink("")  # ASYNC240: 4, 'islink', "trio"
    os.path.lexists("")  # ASYNC240: 4, 'lexists', "trio"
    os.path.ismount("")  # ASYNC240: 4, 'ismount', "trio"
    os.path.realpath("")  # ASYNC240: 4, 'realpath', "trio"
    os.path.exists("")  # ASYNC240: 4, 'exists', "trio"
    os.path.isdir("")  # ASYNC240: 4, 'isdir', "trio"
    os.path.isfile("")  # ASYNC240: 4, 'isfile', "trio"
    os.path.getatime("")  # ASYNC240: 4, 'getatime', "trio"
    os.path.getctime("")  # ASYNC240: 4, 'getctime', "trio"
    os.path.getmtime("")  # ASYNC240: 4, 'getmtime', "trio"
    os.path.getsize("")  # ASYNC240: 4, 'getsize', "trio"
    os.path.samefile("", "")  # ASYNC240: 4, 'samefile', "trio"
    os.path.sameopenfile(0, 1)  # ASYNC240: 4, 'sameopenfile', "trio"
    os.path.relpath("")  # ASYNC240: 4, 'relpath', "trio"

    await os.path.isfile("")  # ASYNC240: 10, 'isfile', "trio"
    print(os.path.isfile(""))  # ASYNC240: 10, 'isfile', "trio"
    os.path.abspath("")
    os.path.anything("")


def foo2():
    os.path.isfile("")
