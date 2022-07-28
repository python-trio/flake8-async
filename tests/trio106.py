import importlib

import trio
import trio as foo
from trio import *  # noqa
from trio import blah, open_file as foo  # noqa

# ways of sidestepping the check, that no sane person would do
k = importlib.import_module("trio")

import trio

l = trio
