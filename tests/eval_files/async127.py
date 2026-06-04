# type: ignore
# isort: skip
import importlib

import httpx  # error: 0
import httpx as foo  # error: 0
import httpx.config  # error: 0
import httpx, httpx.config  # error: 0
from httpx import AsyncClient  # error: 0
from httpx import Client as bar  # error: 0
from httpx import *  # error: 0
from httpx._client import Client  # error: 0

# httpx2 is the maintained continuation of httpx, and is what we recommend
import httpx2
import httpx2 as foo2
from httpx2 import AsyncClient

# other modules that happen to share a prefix or name are fine
import httpx_auth
from httpx_auth import Whatever
import foo.httpx
from foo.httpx import bar

# relative imports refer to local modules, not the httpx package
from . import httpx
from .httpx import Client

# ways of sidestepping the check, that we don't attempt to detect
k = importlib.import_module("httpx")
