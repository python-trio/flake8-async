import io
from io import BufferedRandom, BufferedReader, BufferedWriter, TextIOWrapper
from typing import Any, Optional

blah: Any = None


async def file_text(f: io.TextIOWrapper):
    f.read()  # TRIO232: 4, 'read', 'f'


async def file_binary_read(f: io.BufferedReader):
    f.read()  # TRIO232: 4, 'read', 'f'


async def file_binary_write(f: io.BufferedWriter):
    f.read()  # TRIO232: 4, 'read', 'f'


async def file_binary_readwrite(f: io.BufferedRandom):
    f.read()  # TRIO232: 4, 'read', 'f'


async def file_text_(f: TextIOWrapper):
    f.read()  # TRIO232: 4, 'read', 'f'


async def file_binary_read_(f: BufferedReader):
    f.read()  # TRIO232: 4, 'read', 'f'


async def file_binary_write_(f: BufferedWriter):
    f.read()  # TRIO232: 4, 'read', 'f'


async def file_binary_readwrite_(f: BufferedRandom):
    f.read()  # TRIO232: 4, 'read', 'f'


async def file_text_3(f: TextIOWrapper = blah):
    f.read()  # TRIO232: 4, 'read', 'f'


async def file_text_4(f: TextIOWrapper | None):
    if f:
        f.read()  # TRIO232: 8, 'read', 'f'


async def file_text_5(f: TextIOWrapper | None = None):
    if f:
        f.read()  # TRIO232: 8, 'read', 'f'


async def file_text_6(f: Optional[TextIOWrapper] = None):
    if f:
        f.read()  # TRIO232: 8, 'read', 'f'


async def file_text_7(f: TextIOWrapper = blah, /):
    f.read()  # TRIO232: 4, 'read', 'f'


async def file_text_8(*, f: TextIOWrapper = blah):
    f.read()  # TRIO232: 4, 'read', 'f'


async def file_text_9(lf: list[TextIOWrapper]):
    for f in lf:
        f.read()  # not handled


async def open_file_1():
    with open(""):
        ...


async def open_file_2():
    with open("") as f:
        print(f)


async def open_file_3():
    with open("") as f:
        f.read()  # TRIO232: 8, 'read', 'f'


async def open_file_4():
    f = open("")


async def open_file_5():
    f = open("")
    f.read()  # TRIO232: 4, 'read', 'f'


async def open_file_6():
    ff = open("")
    f = ff
    f.read()  # TRIO232: 4, 'read', 'f'
    ff.read()  # TRIO232: 4, 'read', 'ff'


async def noerror():
    with blah("") as f:
        f.read()


def sync_fun(f: TextIOWrapper):
    async def async_fun():
        f.read()  # TRIO232: 8, 'read', 'f'


def sync_fun_2():
    f = open("")

    async def async_fun():
        f.read()  # TRIO232: 8, 'read', 'f'


async def async_wrapper(f: TextIOWrapper):
    def inside(f: int):
        f.read()

        async def inception():
            f.read()

        f.read()

    f.read()  # TRIO232: 4, 'read', 'f'
    lambda f: f.read()
    f.read()  # TRIO232: 4, 'read', 'f'

    # known false positive, but will be complained about by type checkers
    f = None
    f.read()  # TRIO232: 4, 'read', 'f'
