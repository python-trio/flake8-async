# type: ignore
import importlib

import trio
import trio as foo  # error: 0, "trio"
from foo import blah
from trio import *  # type: ignore # noqa # error: 0, "trio"
from trio import blah, open_file as foo  # noqa # error: 0, "trio"

# Note that our tests exercise the Visitor classes, without going through the noqa filter later in flake8 - so these suppressions are picked up by our project-wide linter stack but not the tests.

# ways of sidestepping the check, that no sane person would do
k = importlib.import_module("trio")

import trio

l = trio
