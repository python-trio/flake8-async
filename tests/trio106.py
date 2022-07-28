import importlib

import trio
import trio as foo
from trio import *  # noqa
from trio import blah, open_file as foo  # noqa

# Note that our tests exercise the Visitor classes, without going through the noqa filter later in flake8 - so these suppressions are picked up by our project-wide linter stack but not the tests.

# ways of sidestepping the check, that no sane person would do
k = importlib.import_module("trio")

import trio

l = trio
