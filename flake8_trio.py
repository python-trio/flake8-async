"""A highly opinionated flake8 plugin for Trio-related problems.

This can include anything from outright bugs, to pointless/dead code,
to likely performance issues, to minor points of idiom that might signal
a misunderstanding.

It may well be too noisy for anyone with different opinions, that's OK.

Pairs well with flake8-async and flake8-bugbear.
"""

from __future__ import annotations

import argparse
import ast
import keyword
import tokenize
from argparse import Namespace
from collections.abc import Iterable, Sequence
from fnmatch import fnmatch
from typing import Any, NamedTuple, Union, cast

from flake8.options.manager import OptionManager

# CalVer: YY.month.patch, e.g. first release of July 2022 == "22.7.1"
__version__ = "22.12.4"


class Statement(NamedTuple):
    name: str
    lineno: int
    col_offset: int = -1

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, Statement)
            and self[:2] == other[:2]  # type: ignore
            and (
                self.col_offset == other.col_offset
                or -1 in (self.col_offset, other.col_offset)
            )
        )


HasLineCol = Union[ast.expr, ast.stmt, ast.arg, ast.excepthandler, Statement]


# convenience function used in a lot of visitors
def get_matching_call(
    node: ast.AST, *names: str, base: str = "trio"
) -> tuple[ast.Call, str] | None:
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == base
        and node.func.attr in names
    ):
        return node, node.func.attr
    return None


class Error:
    def __init__(
        self, error_code: str, lineno: int, col: int, message: str, *args: object
    ):
        self.line = lineno
        self.col = col
        self.code = error_code
        self.message = message
        self.args = args

    # for yielding to flake8
    def __iter__(self):
        yield self.line
        yield self.col
        yield f"{self.code}: " + self.message.format(*self.args)
        yield type(Plugin)

    def cmp(self):
        return self.line, self.col, self.code, self.args

    # for sorting in tests
    def __lt__(self, other: Any) -> bool:
        assert isinstance(other, Error)
        return self.cmp() < other.cmp()

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Error) and self.cmp() == other.cmp()

    def __repr__(self) -> str:  # pragma: no cover
        trailer = "".join(f", {x!r}" for x in self.args)
        return f"<{self.code} error at {self.line}:{self.col}{trailer}>"


class Flake8TrioRunner(ast.NodeVisitor):
    def __init__(self, options: Namespace):
        super().__init__()
        self._problems: list[Error] = []
        self.visitors = {
            v(options, self._problems)
            for v in Flake8TrioVisitor.__subclasses__()
            # TODO: could here refrain from including subclasses for disabled checks
        }

    @classmethod
    def run(cls, tree: ast.AST, options: Namespace) -> Iterable[Error]:
        runner = cls(options)
        runner.visit(tree)
        yield from runner._problems

    def visit(self, node: ast.AST):
        """Visit a node."""
        # tracks the subclasses that, from this node on, iterated through it's subfields
        # we need to remember it so we can restore it at the end of the function.
        novisit: set[Flake8TrioVisitor] = set()

        method = "visit_" + node.__class__.__name__

        if m := getattr(self, method, None):
            m(node)

        for subclass in self.visitors:
            # check if subclass has defined a visitor for this type
            class_method = getattr(subclass, method, None)
            if class_method is None:
                continue

            # call it
            class_method(node)

            # it will set `.novisit` if it has itself handled iterating through subfields
            # so we add it to our novisit set
            if subclass.novisit:
                novisit.add(subclass)

        # Remove all subclasses that iterated through subfields from our list of
        # visitors, so we don't visit them twice.
        self.visitors.difference_update(novisit)

        # iterate through subfields using NodeVisitor
        self.generic_visit(node)

        # reset the novisit flag for the classes in novisit
        for subclass in novisit:
            subclass.novisit = False

        # and add them back to our visitors
        self.visitors.update(novisit)

        # restore any outer state that was saved in the visitor method
        for subclass in self.visitors:
            subclass.set_state(subclass.outer.pop(node, {}))

    def visit_Await(self, node: ast.Await):
        if isinstance(node.value, ast.Call):
            # add attribute to indicate it's awaited
            setattr(node.value, "awaited", True)  # noqa: B010


class Flake8TrioVisitor(ast.NodeVisitor):
    # abstract attribute by not providing a value
    error_codes: dict[str, str]

    def __init__(self, options: Namespace, _problems: list[Error]):
        super().__init__()
        assert self.error_codes, "subclass must define error_codes"
        self._problems = _problems
        self.suppress_errors = False
        self.options = options
        self.outer: dict[ast.AST, dict[str, Any]] = {}
        self.novisit = False

    def visit(self, node: ast.AST):
        """Visit a node."""
        # construct visitor for this node type
        visitor = getattr(self, "visit_" + node.__class__.__name__, None)

        # if we have a visitor for it, visit it
        # it will set self.novisit if it manually visits children
        self.novisit = False

        if visitor is not None:
            visitor(node)

        # if it doesn't set novisit, let the regular NodeVisitor iterate through
        # subfields
        if not self.novisit:
            super().generic_visit(node)

        # if an outer state was saved in this node restore it after visiting children
        self.set_state(self.outer.pop(node, {}))

        # set novisit so external runner doesn't visit this node with this class
        self.novisit = True

    def visit_nodes(self, *nodes: ast.AST | Iterable[ast.AST]):
        for arg in nodes:
            if isinstance(arg, ast.AST):
                self.visit(arg)
            else:
                for node in arg:
                    self.visit(node)

    def error(
        self,
        node: HasLineCol,
        *args: str | Statement | int,
        error_code: str | None = None,
    ):
        if error_code is None:
            assert len(self.error_codes) == 1
            error_code = next(iter(self.error_codes))

        if not self.suppress_errors:
            self._problems.append(
                Error(
                    error_code,
                    node.lineno,
                    node.col_offset,
                    self.error_codes[error_code],
                    *args,
                )
            )

    def get_state(self, *attrs: str, copy: bool = False) -> dict[str, Any]:
        if not attrs:
            attrs = cast(
                tuple[str, ...],
                set(self.__dict__.keys())
                - {"_problems", "options", "outer", "novisit", "error_codes"},
                # TODO: write something clean so don't need to hardcode
            )
        res: dict[str, Any] = {}
        for attr in attrs:
            value = getattr(self, attr)
            if copy and hasattr(value, "copy"):
                value = value.copy()
            res[attr] = value
        return res

    def set_state(self, attrs: dict[str, Any], copy: bool = False):
        for attr, value in attrs.items():
            if copy and hasattr(value, "copy"):
                value = value.copy()
            setattr(self, attr, value)

    def save_state(self, node: ast.AST, *attrs: str, copy: bool = False):
        self.outer[node] = self.get_state(*attrs, copy=copy)

    def walk(self, *body: ast.AST) -> Iterable[ast.AST]:
        for b in body:
            yield from ast.walk(b)


# ignores module and only checks the unqualified name of the decorator
# used in 101 and 107/108
def has_decorator(decorator_list: list[ast.expr], *names: str):
    for dec in decorator_list:
        if (isinstance(dec, ast.Name) and dec.id in names) or (
            isinstance(dec, ast.Attribute) and dec.attr in names
        ):
            return True
    return False


# matches the fully qualified name against fnmatch pattern
# used to match decorators and methods to user-supplied patterns
# used in 107/108 and 200
def fnmatch_qualified_name(name_list: list[ast.expr], *patterns: str) -> str | None:
    for name in name_list:
        if isinstance(name, ast.Call):
            name = name.func
        qualified_name = ast.unparse(name)

        for pattern in patterns:
            # strip leading "@"s for when we're working with decorators
            if fnmatch(qualified_name, pattern.lstrip("@")):
                return pattern
    return None


# used in 100
checkpoint_node_types = (ast.Await, ast.AsyncFor, ast.AsyncWith)
# used in 100, 101 and 102
cancel_scope_names = (
    "fail_after",
    "fail_at",
    "move_on_after",
    "move_on_at",
    "CancelScope",
)


class Visitor100(Flake8TrioVisitor):
    error_codes = {
        "TRIO100": (
            "{} context contains no checkpoints, add `await trio.lowlevel.checkpoint()`"
        ),
    }

    def visit_With(self, node: ast.With | ast.AsyncWith):
        for item in (i.context_expr for i in node.items):
            call = get_matching_call(item, *cancel_scope_names)
            if call and not any(
                isinstance(x, checkpoint_node_types) and x != node
                for x in ast.walk(node)
            ):
                self.error(item, f"trio.{call[1]}")

    visit_AsyncWith = visit_With


class Visitor101(Flake8TrioVisitor):
    error_codes = {
        "TRIO101": (
            "yield inside a nursery or cancel scope is only safe when implementing "
            "a context manager - otherwise, it breaks exception handling"
        ),
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._yield_is_error = False
        self._safe_decorator = False

    def visit_With(self, node: ast.With | ast.AsyncWith):
        self.save_state(node, "_yield_is_error", copy=True)
        for item in node.items:
            # if there's no safe decorator,
            # and it's not yet been determined that yield is error
            # and this withitem opens a cancelscope:
            # then yielding is unsafe
            if (
                not self._safe_decorator
                and not self._yield_is_error
                and get_matching_call(
                    item.context_expr, "open_nursery", *cancel_scope_names
                )
                is not None
            ):
                self._yield_is_error = True

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        self.save_state(node)
        self._yield_is_error = False
        self._safe_decorator = has_decorator(
            node.decorator_list, "contextmanager", "asynccontextmanager"
        )

    visit_AsyncWith = visit_With
    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Yield(self, node: ast.Yield):
        if self._yield_is_error:
            self.error(node)


# used in 102, 103 and 104
def critical_except(node: ast.ExceptHandler) -> Statement | None:
    def has_exception(node: ast.expr | None) -> str:
        if isinstance(node, ast.Name) and node.id == "BaseException":
            return "BaseException"
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "trio"
            and node.attr == "Cancelled"
        ):
            return "trio.Cancelled"
        return ""

    # bare except
    if node.type is None:
        return Statement("bare except", node.lineno, node.col_offset)
    # several exceptions
    if isinstance(node.type, ast.Tuple):
        for element in node.type.elts:
            name = has_exception(element)
            if name:
                return Statement(name, element.lineno, element.col_offset)
    # single exception, either a Name or an Attribute
    name = has_exception(node.type)
    if name:
        return Statement(name, node.type.lineno, node.type.col_offset)
    return None


class Visitor102(Flake8TrioVisitor):
    error_codes = {
        "TRIO102": (
            "await inside {0.name} on line {0.lineno} must have shielded cancel "
            "scope with a timeout"
        ),
    }

    class TrioScope:
        def __init__(self, node: ast.Call, funcname: str):
            self.node = node
            self.funcname = funcname
            self.variable_name: str | None = None
            self.shielded: bool = False
            self.has_timeout: bool = True

            # scope.shielded is assigned to in visit_Assign

            if self.funcname == "CancelScope":
                self.has_timeout = False
                for kw in node.keywords:
                    # Only accepts constant values
                    if kw.arg == "shield" and isinstance(kw.value, ast.Constant):
                        self.shielded = kw.value.value
                    # sets to True even if timeout is explicitly set to inf
                    if kw.arg == "deadline":
                        self.has_timeout = True

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._critical_scope: Statement | None = None
        self._trio_context_managers: list[Visitor102.TrioScope] = []

    # if we're inside a finally, and we're not inside a scope that doesn't have
    # both a timeout and shield
    def visit_Await(self, node: ast.Await | ast.AsyncFor | ast.AsyncWith):
        if self._critical_scope is not None and not any(
            cm.has_timeout and cm.shielded for cm in self._trio_context_managers
        ):
            self.error(node, self._critical_scope)

    visit_AsyncFor = visit_Await

    def visit_With(self, node: ast.With | ast.AsyncWith):
        self.save_state(node, "_trio_context_managers", copy=True)

        # Check for a `with trio.<scope_creater>`
        for item in node.items:
            call = get_matching_call(
                item.context_expr, "open_nursery", *cancel_scope_names
            )
            if call is None:
                continue

            trio_scope = self.TrioScope(*call)
            # check if it's saved in a variable
            if isinstance(item.optional_vars, ast.Name):
                trio_scope.variable_name = item.optional_vars.id

            self._trio_context_managers.append(trio_scope)
            break

    def visit_AsyncWith(self, node: ast.AsyncWith):
        self.visit_Await(node)
        self.visit_With(node)

    def visit_Try(self, node: ast.Try):
        self.save_state(node, "_critical_scope", "_trio_context_managers")
        # There's no visit_Finally, so we need to manually visit the Try fields.
        self.visit_nodes(node.body, node.handlers, node.orelse)

        self._trio_context_managers = []
        self._critical_scope = Statement("try/finally", node.lineno, node.col_offset)
        self.visit_nodes(node.finalbody)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        res = critical_except(node)
        if res is None:
            return

        self.save_state(node, "_critical_scope", "_trio_context_managers")
        self._trio_context_managers = []
        self._critical_scope = res

    def visit_Assign(self, node: ast.Assign):
        # checks for <scopename>.shield = [True/False]
        if self._trio_context_managers and len(node.targets) == 1:
            last_scope = self._trio_context_managers[-1]
            target = node.targets[0]
            if (
                last_scope.variable_name is not None
                and isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == last_scope.variable_name
                and target.attr == "shield"
                and isinstance(node.value, ast.Constant)
            ):
                last_scope.shielded = node.value.value


# Never have an except Cancelled or except BaseException block with a code path that
# doesn't re-raise the error
class Visitor103_104(Flake8TrioVisitor):
    error_codes = {
        "TRIO103": "{} block with a code path that doesn't re-raise the error",
        "TRIO104": "Cancelled (and therefore BaseException) must be re-raised",
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.except_name: str | None = ""
        self.unraised: bool = False
        self.unraised_break: bool = False
        self.unraised_continue: bool = False
        self.loop_depth = 0

    # If an `except` is bare, catches `BaseException`, or `trio.Cancelled`
    # set self.unraised, and if it's still set after visiting child nodes
    # then there might be a code path that doesn't re-raise.
    def visit_ExceptHandler(self, node: ast.ExceptHandler):

        self.save_state(node)
        marker = critical_except(node)

        # we need to *not* unset self.unraised if this is non-critical, to still
        # warn about `return`s

        if marker is not None:
            # save name from `as <except_name>`
            self.except_name = node.name

            self.loop_depth = 0
            self.unraised = True

        # visit child nodes. Will unset self.unraised if all code paths `raise`
        self.generic_visit(node)

        if self.unraised and marker is not None:
            self.error(
                marker,
                marker.name,
                error_code="TRIO103",
            )

    def visit_Raise(self, node: ast.Raise):
        # if there's an unraised critical exception, the raise isn't bare,
        # and the name doesn't match, signal a problem.
        if (
            self.unraised
            and node.exc is not None
            and not (isinstance(node.exc, ast.Name) and node.exc.id == self.except_name)
        ):
            self.error(node, error_code="TRIO104")

        # treat it as safe regardless, to avoid unnecessary error messages.
        self.unraised = False

    def visit_Return(self, node: ast.Return | ast.Yield):
        if self.unraised:
            # Error: must re-raise
            self.error(node, error_code="TRIO104")

    visit_Yield = visit_Return

    # Treat Try's as fully covering only if `finally` always raises.
    def visit_Try(self, node: ast.Try):
        if not self.unraised:
            return

        # in theory it's okay if the try and all excepts re-raise,
        # and there is a bare except
        # but is a pain to parse and would require a special case for bare raises in
        # nested excepts.
        for n in (*node.body, *node.handlers, *node.orelse):
            self.visit(n)
            # re-set unraised to warn about returns in each block
            self.unraised = True

        # but it's fine if we raise in finally
        self.visit_nodes(node.finalbody)

    # Treat if's as fully covering if both `if` and `else` raise.
    # `elif` is parsed by the ast as a new if statement inside the else.
    def visit_If(self, node: ast.If):
        if not self.unraised:
            return

        body_raised = False
        self.visit_nodes(node.body)

        # does body always raise correctly
        body_raised = not self.unraised

        self.unraised = True
        self.visit_nodes(node.orelse)

        # if body didn't raise, or it's unraised after else, set unraise
        self.unraised = not body_raised or self.unraised

    # A loop is guaranteed to raise if:
    # condition always raises, or
    #   else always raises, and
    #   always raise before break
    # or body always raises (before break) and is guaranteed to run at least once
    def visit_For(self, node: ast.For | ast.While):
        if not self.unraised:
            return

        infinite_loop = False
        if isinstance(node, ast.While):
            try:
                infinite_loop = body_guaranteed_once = bool(ast.literal_eval(node.test))
            except Exception:
                body_guaranteed_once = False
            self.visit_nodes(node.test)
        else:
            body_guaranteed_once = iter_guaranteed_once(node.iter)
            self.visit_nodes(node.target)
            self.visit_nodes(node.iter)

        self.save_state(node, "unraised_break", "unraised_continue")
        self.unraised_break = False
        self.unraised_continue = False

        self.loop_depth += 1
        self.visit_nodes(node.body)
        self.loop_depth -= 1

        # if body is not guaranteed to run, or can continue at unraised, reset
        if not (infinite_loop or (body_guaranteed_once and not self.unraised_continue)):
            self.unraised = True
        self.visit_nodes(node.orelse)

        # if we might break at an unraised point, set unraised
        self.unraised |= self.unraised_break

    visit_While = visit_For

    def visit_Break(self, node: ast.Break):
        if self.unraised and self.loop_depth == 0:
            self.error(node, error_code="TRIO104")
        self.unraised_break |= self.unraised

    def visit_Continue(self, node: ast.Continue):
        if self.unraised and self.loop_depth == 0:
            self.error(node, error_code="TRIO104")
        self.unraised_continue |= self.unraised


# used in 103/104 and 107/108
def iter_guaranteed_once(iterable: ast.expr) -> bool:
    # static container with an "elts" attribute
    if hasattr(iterable, "elts"):
        elts: Iterable[ast.expr] = iterable.elts  # type: ignore
        for elt in elts:
            assert isinstance(elt, ast.expr)
            # recurse starred expression
            if isinstance(elt, ast.Starred):
                if iter_guaranteed_once(elt.value):
                    return True
            else:
                return True
        return False
    if isinstance(iterable, ast.Constant):
        try:
            return len(iterable.value) > 0
        except Exception:
            return False
    if isinstance(iterable, ast.Dict):
        for key, val in zip(iterable.keys, iterable.values):
            # {**{...}, **{<...>}} is parsed as {None: {...}, None: {<...>}}
            if key is None and isinstance(val, ast.Dict):
                if iter_guaranteed_once(val):
                    return True
            else:
                return True
    # check for range() with literal parameters
    if (
        isinstance(iterable, ast.Call)
        and isinstance(iterable.func, ast.Name)
        and iterable.func.id == "range"
    ):
        try:
            return len(range(*[ast.literal_eval(a) for a in iterable.args])) > 0
        except Exception:
            return False
    return False


# used in 105
trio_async_funcs = (
    "aclose_forcefully",
    "open_file",
    "open_ssl_over_tcp_listeners",
    "open_ssl_over_tcp_stream",
    "open_tcp_listeners",
    "open_tcp_stream",
    "open_unix_socket",
    "run_process",
    "serve_listeners",
    "serve_ssl_over_tcp",
    "serve_tcp",
    "sleep",
    "sleep_forever",
    "sleep_until",
)


# used in 105 and 113
def is_nursery_call(node: ast.AST, name: str) -> bool:
    assert name in ("start", "start_soon")
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name):
            return node.attr == name and node.value.id.endswith("nursery")
        if isinstance(node.value, ast.Attribute):
            return node.attr == name and node.value.attr.endswith("nursery")
    return False


class Visitor105(Flake8TrioVisitor):
    error_codes = {
        "TRIO105": "trio async function {} must be immediately awaited",
    }

    def visit_Call(self, node: ast.Call):
        if (
            not getattr(node, "awaited", False)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and (
                (node.func.value.id == "trio" and node.func.attr in trio_async_funcs)
                or is_nursery_call(node.func, "start")
            )
        ):
            self.error(node, node.func.attr)


class Visitor106(Flake8TrioVisitor):
    error_codes = {
        "TRIO106": "trio must be imported with `import trio` for the linter to work",
    }

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "trio":
            self.error(node)

    def visit_Import(self, node: ast.Import):
        for name in node.names:
            if name.name == "trio" and name.asname is not None:
                self.error(node)


# used in 107/108
def empty_body(body: list[ast.stmt]) -> bool:
    # Does the function body consist solely of `pass`, `...`, and (doc)string literals?
    return all(
        isinstance(stmt, ast.Pass)
        or (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and (stmt.value.value is Ellipsis or isinstance(stmt.value.value, str))
        )
        for stmt in body
    )


class Visitor107_108(Flake8TrioVisitor):
    error_codes = {
        "TRIO107": (
            "{0} from async function with no guaranteed checkpoint or exception "
            "since function definition on line {1.lineno}"
        ),
        "TRIO108": (
            "{0} from async iterable with no guaranteed checkpoint since {1.name} "
            "on line {1.lineno}"
        ),
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.has_yield = False
        self.safe_decorator = False
        self.async_function = False

        self.uncheckpointed_statements: set[Statement] = set()
        self.uncheckpointed_before_continue: set[Statement] = set()
        self.uncheckpointed_before_break: set[Statement] = set()

        self.default = self.get_state()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # don't lint functions whose bodies solely consist of pass or ellipsis
        if has_decorator(node.decorator_list, "overload") or empty_body(node.body):
            return

        self.save_state(node)
        self.set_state(self.default, copy=True)

        # disable checks in asynccontextmanagers by saying the function isn't async
        self.async_function = not fnmatch_qualified_name(
            node.decorator_list, *self.options.no_checkpoint_warning_decorators
        )
        if not self.async_function:
            return

        self.uncheckpointed_statements = {
            Statement("function definition", node.lineno, node.col_offset)
        }

        self.generic_visit(node)

        self.check_function_exit(node)

    # error if function exits or returns with uncheckpointed statements
    def check_function_exit(self, node: ast.Return | ast.AsyncFunctionDef):
        for statement in self.uncheckpointed_statements:
            self.error(
                node,
                "return" if isinstance(node, ast.Return) else "exit",
                statement,
                error_code="TRIO108" if self.has_yield else "TRIO107",
            )

    def visit_Return(self, node: ast.Return):
        if not self.async_function:
            return
        self.generic_visit(node)
        self.check_function_exit(node)

        # avoid duplicate error messages
        self.uncheckpointed_statements = set()

    # disregard checkpoints in nested function definitions
    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.save_state(node)
        self.set_state(self.default, copy=True)

    # checkpoint functions
    def visit_Await(self, node: ast.Await | ast.Raise):
        # the expression being awaited is not checkpointed
        # so only set checkpoint after the await node
        self.generic_visit(node)

        # all nodes are now checkpointed
        self.uncheckpointed_statements = set()

    # raising exception means we don't need to checkpoint so we can treat it as one
    visit_Raise = visit_Await

    # Async context managers can reasonably checkpoint on either or both of entry and
    # exit.  Given that we can't tell which, we assume "both" to avoid raising a
    # missing-checkpoint warning when there might in fact be one (i.e. a false alarm).
    def visit_AsyncWith(self, node: ast.AsyncWith):
        self.visit_nodes(node.items)

        self.uncheckpointed_statements = set()
        self.visit_nodes(node.body)

        self.uncheckpointed_statements = set()

    # error if no checkpoint since earlier yield or function entry
    def visit_Yield(self, node: ast.Yield):
        if not self.async_function:
            return
        self.has_yield = True
        self.generic_visit(node)
        for statement in self.uncheckpointed_statements:
            self.error(
                node,
                "yield",
                statement,
                error_code="TRIO108",
            )

        # mark as requiring checkpoint after
        self.uncheckpointed_statements = {
            Statement("yield", node.lineno, node.col_offset)
        }

    # valid checkpoint if there's valid checkpoints (or raise) in:
    # (try or else) and all excepts, or in finally
    #
    # try can jump into any except or into the finally* at any point during it's
    # execution so we need to make sure except & finally can handle worst-case
    # * unless there's a bare except / except BaseException - not implemented.
    def visit_Try(self, node: ast.Try):
        if not self.async_function:
            return
        # except & finally guaranteed to enter with checkpoint if checkpointed
        # before try and no yield in try body.
        body_uncheckpointed_statements = self.uncheckpointed_statements.copy()
        for inner_node in self.walk(*node.body):
            if isinstance(inner_node, ast.Yield):
                body_uncheckpointed_statements.add(
                    Statement("yield", inner_node.lineno, inner_node.col_offset)
                )

        # check try body
        self.visit_nodes(node.body)

        # save state at end of try for entering else
        try_checkpoint = self.uncheckpointed_statements

        # check that all except handlers checkpoint (await or most likely raise)
        except_uncheckpointed_statements: set[Statement] = set()

        for handler in node.handlers:
            # enter with worst case of try
            self.uncheckpointed_statements = body_uncheckpointed_statements.copy()

            self.visit_nodes(handler)

            except_uncheckpointed_statements.update(self.uncheckpointed_statements)

        # check else
        # if else runs it's after all of try, so restore state to back then
        self.uncheckpointed_statements = try_checkpoint
        self.visit_nodes(node.orelse)

        # checkpoint if else checkpoints, and all excepts checkpoint
        self.uncheckpointed_statements.update(except_uncheckpointed_statements)

        if node.finalbody:
            added = body_uncheckpointed_statements.difference(
                self.uncheckpointed_statements
            )
            # if there's no bare except or except BaseException, we can jump into
            # finally from any point in try. But the exception will be reraised after
            # finally, so track what we add so it can be removed later.
            # (This is for catching return or yield in the finally, which is usually
            # very bad)
            if not any(
                h.type is None
                or (isinstance(h.type, ast.Name) and h.type.id == "BaseException")
                for h in node.handlers
            ):
                self.uncheckpointed_statements.update(added)

            self.visit_nodes(node.finalbody)
            self.uncheckpointed_statements.difference_update(added)

    # valid checkpoint if both body and orelse checkpoint
    def visit_If(self, node: ast.If | ast.IfExp):
        if not self.async_function:
            return
        # visit condition
        self.visit_nodes(node.test)
        outer = self.uncheckpointed_statements.copy()

        # visit body
        self.visit_nodes(node.body)
        body_outer = self.uncheckpointed_statements

        # reset to after condition and visit orelse
        self.uncheckpointed_statements = outer
        self.visit_nodes(node.orelse)

        # union of both branches is the new set of unhandled entries
        self.uncheckpointed_statements.update(body_outer)

    # inline if
    visit_IfExp = visit_If

    # Check for yields w/o checkpoint inbetween due to entering loop body the first time,
    # after completing all of loop body, and after any continues.
    # yield in else have same requirement
    # state after the loop same as above, and in addition the state at any break
    def visit_loop(self, node: ast.While | ast.For | ast.AsyncFor):
        if not self.async_function:
            return
        # visit condition
        infinite_loop = False
        if isinstance(node, ast.While):
            try:
                infinite_loop = body_guaranteed_once = bool(ast.literal_eval(node.test))
            except Exception:
                body_guaranteed_once = False
            self.visit_nodes(node.test)
        else:
            self.visit_nodes(node.target)
            self.visit_nodes(node.iter)
            body_guaranteed_once = iter_guaranteed_once(node.iter)

        # save state in case of nested loops
        outer = self.get_state(
            "uncheckpointed_before_continue",
            "uncheckpointed_before_break",
            "suppress_errors",
        )

        self.uncheckpointed_before_continue = set()

        # AsyncFor guaranteed checkpoint at every iteration
        if isinstance(node, ast.AsyncFor):
            self.uncheckpointed_statements = set()

        pre_body_uncheckpointed_statements = self.uncheckpointed_statements

        # check for all possible uncheckpointed statements before entering start of loop
        # due to `continue` or multiple iterations
        if not isinstance(node, ast.AsyncFor):
            # reset uncheckpointed_statements to not clear it if awaited
            self.uncheckpointed_statements = set()

            # avoid duplicate errors
            self.suppress_errors = True

            # set self.uncheckpointed_before_continue and uncheckpointed at end of loop
            self.visit_nodes(node.body)

            self.suppress_errors = outer["suppress_errors"]

            self.uncheckpointed_statements.update(self.uncheckpointed_before_continue)

        # add uncheckpointed on first iter
        self.uncheckpointed_statements.update(pre_body_uncheckpointed_statements)

        # visit body
        self.uncheckpointed_before_break = set()
        self.visit_nodes(node.body)

        # AsyncFor guarantees checkpoint on running out of iterable
        # so reset checkpoint state at end of loop. (but not state at break)
        if isinstance(node, ast.AsyncFor):
            self.uncheckpointed_statements = set()
        else:
            # enter orelse with worst case:
            # loop body might execute fully before entering orelse
            # (current state of self.uncheckpointed_statements)
            # or not at all
            if not body_guaranteed_once:
                self.uncheckpointed_statements.update(
                    pre_body_uncheckpointed_statements
                )
            # or at a continue, unless it's an infinite loop
            if not infinite_loop:
                self.uncheckpointed_statements.update(
                    self.uncheckpointed_before_continue
                )

        # visit orelse
        self.visit_nodes(node.orelse)

        # if this is an infinite loop, with no break in it, don't raise
        # alarms about the state after it.
        if infinite_loop and not any(
            isinstance(n, ast.Break) for n in self.walk(*node.body)
        ):
            self.uncheckpointed_statements = set()
        else:
            # We may exit from:
            # orelse (covering: no body, body until continue, and all body)
            # break
            self.uncheckpointed_statements.update(self.uncheckpointed_before_break)

        # reset break & continue in case of nested loops
        self.set_state(outer)

    visit_While = visit_loop
    visit_For = visit_loop
    visit_AsyncFor = visit_loop

    # save state in case of continue/break at a point not guaranteed to checkpoint
    def visit_Continue(self, node: ast.Continue):
        if not self.async_function:
            return
        self.uncheckpointed_before_continue.update(self.uncheckpointed_statements)

    def visit_Break(self, node: ast.Break):
        if not self.async_function:
            return
        self.uncheckpointed_before_break.update(self.uncheckpointed_statements)

    # first node in a condition is always evaluated, but may shortcut at any point
    # after that so we track worst-case checkpoint (i.e. after yield)
    def visit_BoolOp(self, node: ast.BoolOp):
        if not self.async_function:
            return
        self.visit(node.op)

        # first value always evaluated
        self.visit(node.values[0])

        worst_case_shortcut = self.uncheckpointed_statements.copy()

        for value in node.values[1:]:
            self.visit(value)
            worst_case_shortcut.update(self.uncheckpointed_statements)

        self.uncheckpointed_statements = worst_case_shortcut


class Visitor109(Flake8TrioVisitor):
    error_codes = {
        "TRIO109": (
            "Async function definition with a `timeout` parameter - use "
            "`trio.[fail/move_on]_[after/at]` instead"
        ),
    }

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # pending configuration or a more sophisticated check, ignore
        # all functions with a decorator
        if node.decorator_list:
            return

        args = node.args
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
            if arg.arg == "timeout":
                self.error(arg)


class Visitor110(Flake8TrioVisitor):
    error_codes = {
        "TRIO110": (
            "`while <condition>: await trio.sleep()` should be replaced by "
            "a `trio.Event`."
        ),
    }

    def visit_While(self, node: ast.While):
        if (
            len(node.body) == 1
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Await)
            and get_matching_call(node.body[0].value.value, "sleep", "sleep_until")
        ):
            self.error(node)


class Visitor111(Flake8TrioVisitor):
    error_codes = {
        "TRIO111": (
            "variable {2} is usable within the context manager on line {0}, but that "
            "will close before nursery opened on line {1} - this is usually a bug.  "
            "Nurseries should generally be the inner-most context manager."
        ),
    }

    class NurseryCall(NamedTuple):
        stack_index: int
        name: str

    class TrioContextManager(NamedTuple):
        lineno: int
        name: str
        is_nursery: bool

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._context_managers: list[Visitor111.TrioContextManager] = []
        self._nursery_call: Visitor111.NurseryCall | None = None

    def visit_With(self, node: ast.With | ast.AsyncWith):
        self.save_state(node, "_context_managers", copy=True)
        for item in node.items:
            # 111
            # if a withitem is saved in a variable,
            # push its line, variable, and whether it's a trio nursery
            # to the _context_managers stack,
            if isinstance(item.optional_vars, ast.Name):
                self._context_managers.append(
                    self.TrioContextManager(
                        item.context_expr.lineno,
                        item.optional_vars.id,
                        get_matching_call(item.context_expr, "open_nursery")
                        is not None,
                    )
                )

    visit_AsyncWith = visit_With

    def visit_FunctionDef(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda
    ):
        self.save_state(node)
        self._context_managers = []
        self._nursery_call = None

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef

    # if it's a <X>.start[_soon] call
    # and <X> is a nursery listed in self._context_managers:
    # Save <X>'s index in self._context_managers to guard against cm's higher in the
    # stack being passed as parameters to it. (and save <X> for the error message)
    def visit_Call(self, node: ast.Call):
        self.save_state(node, "_nursery_call")

        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.attr in ("start", "start_soon")
        ):
            self._nursery_call = None
            for i, cm in enumerate(self._context_managers):
                if node.func.value.id == cm.name:
                    # don't break upon finding a nursery in case there's multiple cm's
                    # on the stack with the same name
                    if cm.is_nursery:
                        self._nursery_call = self.NurseryCall(i, node.func.attr)
                    else:
                        self._nursery_call = None

    # If we're inside a <X>.start[_soon] call (where <X> is a nursery),
    # and we're accessing a variable cm that's on the self._context_managers stack,
    # with a higher index than <X>:
    #   Raise error since the scope of cm may close before the function passed to the
    # nursery finishes.
    def visit_Name(self, node: ast.Name):
        if self._nursery_call is None:
            return

        for i, cm in enumerate(self._context_managers):
            if cm.name == node.id and i > self._nursery_call.stack_index:
                self.error(
                    node,
                    cm.lineno,
                    self._context_managers[self._nursery_call.stack_index].lineno,
                    node.id,
                    self._nursery_call.name,
                )


class Visitor112(Flake8TrioVisitor):
    error_codes = {
        "TRIO112": (
            "Redundant nursery {}, consider replacing with directly awaiting "
            "the function call"
        ),
    }

    # if with has a withitem `trio.open_nursery() as <X>`,
    # and the body is only a single expression <X>.start[_soon](),
    # and does not pass <X> as a parameter to the expression
    def visit_With(self, node: ast.With | ast.AsyncWith):
        # body is single expression
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Expr):
            return
        for item in node.items:
            # get variable name <X>
            if not isinstance(item.optional_vars, ast.Name):
                continue
            var_name = item.optional_vars.id

            # check for trio.open_nursery
            nursery = get_matching_call(item.context_expr, "open_nursery")

            # `isinstance(..., ast.Call)` is done in get_matching_call
            body_call = cast(ast.Call, node.body[0].value)

            if (
                nursery is not None
                and get_matching_call(body_call, "start", "start_soon", base=var_name)
                # check for presence of <X> as parameter
                and not any(
                    (isinstance(n, ast.Name) and n.id == var_name)
                    for n in self.walk(*body_call.args, *body_call.keywords)
                )
            ):
                self.error(item.context_expr, var_name)

    visit_AsyncWith = visit_With


# used in 113
def _get_identifier(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


# used in 113 and 114
STARTABLE_CALLS = (
    "run_process",
    "serve_ssl_over_tcp",
    "serve_tcp",
    "serve_listeners",
    "serve",
)


class Visitor113(Flake8TrioVisitor):
    error_codes = {
        "TRIO113": (
            "Dangerous `.start_soon()`, process might not run before `__aenter__` "
            "exits. Consider replacing with `.start()`."
        ),
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.async_function = False
        self.asynccontextmanager = False
        self.aenter = False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.save_state(node, "aenter")

        self.aenter = node.name == "__aenter__" or any(
            _get_identifier(d) == "asynccontextmanager" for d in node.decorator_list
        )

    def visit_Yield(self, node: ast.Yield):
        self.aenter = False

    def visit_Call(self, node: ast.Call) -> None:
        def is_startable(n: ast.expr, *startable_list: str) -> bool:
            if isinstance(n, ast.Name):
                return n.id in startable_list
            if isinstance(n, ast.Attribute):
                return n.attr in startable_list
            if isinstance(n, ast.Call):
                return any(is_startable(nn, *startable_list) for nn in n.args)
            return False

        if (
            self.aenter
            and is_nursery_call(node.func, "start_soon")
            and len(node.args) > 0
            and is_startable(
                node.args[0],
                *STARTABLE_CALLS,
                *self.options.startable_in_context_manager,
            )
        ):
            self.error(node)


# Checks that all async functions with a "task_status" parameter have a match in
# --startable-in-context-manager. Will only match against the last part of the option
# name, so may miss cases where functions are named the same in different modules/classes
# and option names are specified including the module name.
class Visitor114(Flake8TrioVisitor):
    error_codes = {
        "TRIO114": (
            "Startable function {} not in --startable-in-context-manager parameter "
            "list, please add it so TRIO113 can catch errors using it."
        ),
    }

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if any(
            isinstance(n, ast.arg) and n.arg == "task_status"
            for n in self.walk(
                *node.args.args, *node.args.posonlyargs, *node.args.kwonlyargs
            )
        ) and not any(
            node.name == opt
            for opt in (*self.options.startable_in_context_manager, *STARTABLE_CALLS)
        ):
            self.error(node, node.name)


# Suggests replacing all `trio.sleep(0)` with the more suggestive
# `trio.lowlevel.checkpoint()`
class Visitor115(Flake8TrioVisitor):
    error_codes = {
        "TRIO115": "Use `trio.lowlevel.checkpoint()` instead of `trio.sleep(0)`.",
    }

    def visit_Call(self, node: ast.Call):
        if (
            get_matching_call(node, "sleep")
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == 0
        ):
            self.error(node)


class Visitor116(Flake8TrioVisitor):
    error_codes = {
        "TRIO116": (
            "trio.sleep() with >24 hour interval should usually be "
            "`trio.sleep_forever()`"
        ),
    }

    def visit_Call(self, node: ast.Call):
        if get_matching_call(node, "sleep") and len(node.args) == 1:
            arg = node.args[0]
            if (
                # `trio.sleep(math.inf)`
                (
                    isinstance(arg, ast.Attribute)
                    and isinstance(arg.value, ast.Name)
                    and arg.attr == "inf"
                    and arg.value.id == "math"
                )
                # `trio.sleep(inf)`
                or (isinstance(arg, ast.Name) and arg.id == "inf")
                # `trio.sleep(float("inf"))`
                or (
                    isinstance(arg, ast.Call)
                    and isinstance(arg.func, ast.Name)
                    and arg.func.id == "float"
                    and len(arg.args)
                    and isinstance(arg.args[0], ast.Constant)
                    and arg.args[0].value == "inf"
                )
                # `trio.sleep(1e999)` (constant value inf)
                # `trio.sleep(86401)`
                # `trio.sleep(86400.1)`
                or (
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, (int, float))
                    and arg.value > 86400
                )
            ):
                self.error(node)


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
            blocking_calls = self.options.trio200_blocking_calls
            if key := fnmatch_qualified_name([node.func], *blocking_calls):
                self.error(node, key, blocking_calls[key])


class ListOfIdentifiers(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Sequence[str] | None,
        option_string: str | None = None,
    ):
        assert values is not None
        assert option_string is not None
        for value in values:
            if keyword.iskeyword(value) or not value.isidentifier():
                raise argparse.ArgumentError(
                    self, f"{value!r} is not a valid method identifier"
                )
        setattr(namespace, self.dest, values)


class ParseDict(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Sequence[str] | None,
        option_string: str | None = None,
    ):
        res: dict[str, str] = {}
        splitter = "->"  # avoid ":" because it's part of .ini file syntax
        assert values is not None
        for value in values:
            split_values = list(map(str.strip, value.split(splitter)))
            if len(split_values) != 2:
                raise argparse.ArgumentError(
                    self,
                    f"Invalid number ({len(split_values)-1}) of splitter "
                    f"tokens {splitter!r} in {value!r}",
                )
            res[split_values[0]] = split_values[1]

        setattr(namespace, self.dest, res)


class Plugin:
    name = __name__
    version = __version__
    options: Namespace = Namespace()

    def __init__(self, tree: ast.AST):
        self._tree = tree

    @classmethod
    def from_filename(cls, filename: str) -> Plugin:
        with tokenize.open(filename) as f:
            source = f.read()
        return cls(ast.parse(source))

    def run(self) -> Iterable[Error]:
        # temporary workaround, since the Action does not seem to be called properly
        # by flake8 when parsing from config
        if isinstance(self.options.trio200_blocking_calls, list):
            ParseDict([""], dest="trio200_blocking_calls")(
                None,  # type: ignore
                self.options,
                self.options.trio200_blocking_calls,  # type: ignore
                None,
            )
        yield from Flake8TrioRunner.run(self._tree, self.options)

    @staticmethod
    def add_options(option_manager: OptionManager):
        option_manager.add_option(
            "--no-checkpoint-warning-decorators",
            default="asynccontextmanager",
            parse_from_config=True,
            required=False,
            comma_separated_list=True,
            help=(
                "Comma-separated list of decorators to disable TRIO107 & TRIO108 "
                "checkpoint warnings for. "
                "Decorators can be dotted or not, as well as support * as a wildcard. "
                "For example, ``--no-checkpoint-warning-decorators=app.route,"
                "mydecorator,mypackage.mydecorators.*``"
            ),
        )
        option_manager.add_option(
            "--startable-in-context-manager",
            default="",
            parse_from_config=True,
            required=False,
            comma_separated_list=True,
            action=ListOfIdentifiers,
            help=(
                "Comma-separated list of method calls to additionally enable TRIO113 "
                "warnings for. Will also check for the pattern inside function calls. "
                "Methods must be valid identifiers as per `str.isidientifier()` and "
                "not reserved keywords. "
                "For example, ``--startable-in-context-manager=worker_serve,"
                "myfunction``"
            ),
        )
        option_manager.add_option(
            "--trio200-blocking-calls",
            default={},
            parse_from_config=True,
            required=False,
            comma_separated_list=True,
            action=ParseDict,
            help=(
                "Comma-separated list of key:value pairs, where key is a [dotted] "
                "function that if found inside an async function will raise TRIO200, "
                "suggesting it be replaced with {value}"
            ),
        )

    @staticmethod
    def parse_options(options: Namespace):
        Plugin.options = options
