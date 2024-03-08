# type: ignore
# NOTRIO # see async232.py
# NOANYIO # see async232.py
import io
from io import BufferedRandom, BufferedReader, BufferedWriter, TextIOWrapper
from typing import Any, Optional

blah: Any = None


async def file_text(f: io.TextIOWrapper):
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'
    f.readlines()  # ASYNC232_asyncio: 4, 'readlines', 'f'

    # there might be non-sync calls on TextIOWrappers? - but it will currently trigger
    # on all calls
    f.anything()  # ASYNC232_asyncio: 4, 'anything', 'f'
    f.aoeuaoeuaoeuaoeuaoeu()  # ASYNC232_asyncio: 4, 'aoeuaoeuaoeuaoeuaoeu', 'f'


# Test different file types for the type tracker
# We use f.read() in all of them for simplicity, but any method call would trigger the same error


async def file_binary_read(f: io.BufferedReader):
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


async def file_binary_write(f: io.BufferedWriter):
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


async def file_binary_readwrite(f: io.BufferedRandom):
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


async def file_text_(f: TextIOWrapper):
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


async def file_binary_read_(f: BufferedReader):
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


async def file_binary_write_(f: BufferedWriter):
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


async def file_binary_readwrite_(f: BufferedRandom):
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


async def file_text_3(f: TextIOWrapper = blah):
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


async def file_text_4(f: TextIOWrapper | None):
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'
    if f:
        f.read()  # ASYNC232_asyncio: 8, 'read', 'f'


async def file_text_4_left(f: None | TextIOWrapper):
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'
    if f:
        f.read()  # ASYNC232_asyncio: 8, 'read', 'f'


# not handled
async def file_text_4_both(f: None | TextIOWrapper | None):
    f.read()


# not handled
async def file_text_4_non_none(f: TextIOWrapper | int):
    f.read()


async def file_text_5(f: TextIOWrapper | None = None):
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'
    if f:
        f.read()  # ASYNC232_asyncio: 8, 'read', 'f'


async def file_text_6(f: Optional[TextIOWrapper] = None):
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'
    if f:
        f.read()  # ASYNC232_asyncio: 8, 'read', 'f'


# posonly
async def file_text_7(f: TextIOWrapper = blah, /):
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


# keyword-only
async def file_text_8(*, f: TextIOWrapper = blah):
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


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
        f.read()  # ASYNC232_asyncio: 8, 'read', 'f'


async def open_file_4():
    f = open("")


async def open_file_5():
    f = open("")
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


async def open_file_6():
    ff = open("")
    f = ff
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'
    ff.read()  # ASYNC232_asyncio: 4, 'read', 'ff'


async def noerror():
    with blah("") as f:
        f.read()


def sync_fun(f: TextIOWrapper):
    async def async_fun():
        f.read()  # ASYNC232_asyncio: 8, 'read', 'f'


def sync_fun_2():
    f = open("")

    async def async_fun():
        f.read()  # ASYNC232_asyncio: 8, 'read', 'f'


async def type_assign():
    f: TextIOWrapper = ...
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


# define global variables
f = open("")
g: TextIOWrapper = ...


# Test state handling on nested functions
async def async_wrapper(f: TextIOWrapper):
    def inside(f: int):
        f.read()

        async def inception():
            f.read()

        f.read()

    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'
    lambda f: f.read()
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


# and show that they're still marked as TextIOWrappers
async def global_vars():
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'
    g.read()  # ASYNC232_asyncio: 4, 'read', 'g'


# If the type is explicitly overridden, it will not error
async def overridden_type(f: TextIOWrapper):
    f: int = 7
    f.read()
    f: TextIOWrapper = ...
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'
    f: int = 7
    f.read()
    f: TextIOWrapper = ...
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


# ***** Known unhandled cases *****


# It will error on non-explicit assignments
async def implicit_overridden_type():
    f: TextIOWrapper = ...
    f = arbitrary_function()
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'
    f = 7
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


# Tuple assignments are completely ignored
async def multi_assign():
    x, y = open(""), open("")
    x.read()  # should error
    y.read()  # should error


# as are attribute assignments
async def attribute_assign():
    x.y = open("")
    x.y.read()  # should error


# or calling on subattributes of an object
async def attribute_access_on_object():
    f: TextIOWrapper = ...
    f.any.thing()  # should error


# The type checker is very naive, and will not do any parsing of logic pertaining
# to the type
async def type_restricting_1(f: Optional[TextIOWrapper] = None):
    if f is None:
        f.read()  # ASYNC232_asyncio: 8, 'read', 'f'


async def type_restricting_2(f: Optional[TextIOWrapper] = None):
    if isinstance(f, TextIOWrapper):
        return
    f.read()  # ASYNC232_asyncio: 4, 'read', 'f'


# Classes are not supported, partly due to not handling attributes at all,
# but would require additional logic
class myclass:
    x: TextIOWrapper

    async def foo(self):
        self.x.read()  # should error


class myclass_2:
    def __init__(self):
        self.x: TextIOWrapper = open("")

    async def foo(self):
        self.x.read()  # should error


# Return types are not parsed
async def call_function_with_return_type():
    def return_textiowrapper() -> TextIOWrapper:
        return open("")

    k = return_textiowrapper()
    k.read()  # should error
