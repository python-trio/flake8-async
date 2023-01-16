"""2XX error classes, which checks for blocking sync calls in async functions.

200 is user-configured, doing nothing by default.
210 looks for usage of HTTP requests from common http libraries.
211 additionally matches on object methods whose signature looks like an http request.
220&221 looks for subprocess and os calls that should be wrapped.
230&231 looks for os.open and os.fdopen that should be wrapped.
240 looks for os.path functions that interact with the disk in various ways.
"""

from __future__ import annotations

import ast
import re
from typing import Any

from .flake8triovisitor import Flake8TrioVisitor
from .helpers import error_class, fnmatch_qualified_name, get_matching_call


@error_class
class Visitor200(Flake8TrioVisitor):
    error_codes = {
        "TRIO200": "User-configured blocking sync call {0} in async function, consider "
        "replacing with {1}.",
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.async_function = False

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef | ast.FunctionDef | ast.Lambda
    ):
        self.save_state(node, "async_function")
        self.async_function = isinstance(node, ast.AsyncFunctionDef)

    visit_FunctionDef = visit_AsyncFunctionDef
    visit_Lambda = visit_AsyncFunctionDef

    def visit_Call(self, node: ast.Call):
        if self.async_function and not getattr(node, "awaited", False):
            self.visit_blocking_call(node)

    def visit_blocking_call(self, node: ast.Call):
        blocking_calls = self.options.trio200_blocking_calls
        if key := fnmatch_qualified_name([node.func], *blocking_calls):
            self.error(node, key, blocking_calls[key])


@error_class
class Visitor21X(Visitor200):
    error_codes = {
        "TRIO210": "Sync HTTP call {} in async function, use httpx.AsyncClient",
        "TRIO211": (
            "Likely sync HTTP call {} in async function, use httpx.AsyncClient"
        ),
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.imports: set[str] = set()

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "urllib3":
            self.imports.add(node.module)

    def visit_Import(self, node: ast.Import):
        for name in node.names:
            if name.name == "urllib3":
                # Could also save the name.asname for matching
                self.imports.add(name.name)

    def visit_blocking_call(self, node: ast.Call):
        http_methods = {
            "get",
            "options",
            "head",
            "post",
            "put",
            "patch",
            "delete",
        }
        func_name = ast.unparse(node.func)
        for http_package in "requests", "httpx":
            if get_matching_call(node, *http_methods | {"request"}, base=http_package):
                self.error(node, func_name, error_code="TRIO210")
                return

        if func_name in (
            "urllib3.request",
            "urllib.request.urlopen",
            "request.urlopen",
            "urlopen",
        ):
            self.error(node, func_name, error_code="TRIO210")

        elif (
            "urllib3" in self.imports
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "request"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and node.args[0].value.lower() in http_methods | {"trace", "connect"}
        ):
            self.error(node, func_name, error_code="TRIO211")


# Process invocations 202
@error_class
class Visitor22X(Visitor200):
    error_codes = {
        "TRIO220": (
            "Sync call {} in async function, use "
            "`await nursery.start(trio.run_process, ...)`"
        ),
        "TRIO221": "Sync call {} in async function, use `await trio.run_process(...)`",
    }

    def visit_blocking_call(self, node: ast.Call):
        def is_p_wait(arg: ast.expr) -> bool:
            return (isinstance(arg, ast.Attribute) and arg.attr == "P_WAIT") or (
                isinstance(arg, ast.Name) and arg.id == "P_WAIT"
            )

        subprocess_calls = {
            "run",
            "call",
            "check_call",
            "check_output",
            "getoutput",
            "getstatusoutput",
        }

        func_name = ast.unparse(node.func)
        if func_name in ("subprocess.Popen", "os.popen"):
            self.error(node, func_name, error_code="TRIO220")
            return

        if func_name == "os.system" or get_matching_call(
            node, *subprocess_calls, base="subprocess"
        ):
            self.error(node, func_name, error_code="TRIO221")
            return

        if re.match("os.spawn[vl]p?e?", func_name):
            # if mode= is given and not [os.]P_WAIT: TRIO220
            # 1. as a positional parameter
            if node.args:
                arg = node.args[0]
                if not is_p_wait(arg):
                    self.error(node, func_name, error_code="TRIO220")
                    return
            # 2. as a keyword parameter
            for kw in node.keywords:
                if kw.arg == "mode" and not is_p_wait(kw.value):
                    self.error(node, func_name, error_code="TRIO220")
                    return

            # otherwise, TRIO221
            self.error(node, func_name, error_code="TRIO221")
            return


@error_class
class Visitor23X(Visitor200):
    error_codes = {
        "TRIO230": ("Sync call {} in async function, use " "`trio.open_file(...)`."),
        "TRIO231": ("Sync call {0} in async function, use " "`trio.wrap_file({0})`."),
    }

    def visit_Call(self, node: ast.Call):
        func_name = ast.unparse(node.func)
        if func_name == "trio.wrap_file" and len(node.args) == 1:
            setattr(node.args[0], "wrapped", True)  # noqa: B010
        super().visit_Call(node)

    def visit_blocking_call(self, node: ast.Call):
        if getattr(node, "wrapped", False):
            return
        func_name = ast.unparse(node.func)
        if func_name in ("open", "io.open", "io.open_code"):
            self.error(node, func_name, error_code="TRIO230")
        elif func_name == "os.fdopen":
            self.error(node, func_name, error_code="TRIO231")


@error_class
class Visitor24X(Visitor200):
    error_codes = {
        "TRIO240": ("Avoid using os.path, prefer using trio.Path objects"),
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.imports_from_ospath: set[str] = set()

    os_funcs = (
        "_path_normpath",
        "normpath",
        "_joinrealpath",
        "islink",
        "lexists",
        "ismount",  # safe on windows, unsafe on posix
        "realpath",
        "exists",
        "isdir",
        "isfile",
        "getatime",
        "getctime",
        "getmtime",
        "getsize",
        "samefile",
        "sameopenfile",
        "relpath",
    )

    # doesn't protect against `from os import path` or `import os.path as <x>`
    # but those should be very rare
    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "os.path":
            for alias in node.names:
                self.imports_from_ospath.add(
                    alias.asname if alias.asname is not None else alias.name
                )

    def visit_Call(self, node: ast.Call):
        if not self.async_function:
            return
        func_name = ast.unparse(node.func)
        if func_name in self.imports_from_ospath:
            self.error(node, func_name)
        elif (m := re.fullmatch(r"os\.path\.(?P<func>.*)", func_name)) and m.group(
            "func"
        ) in self.os_funcs:
            self.error(node, m.group("func"))
