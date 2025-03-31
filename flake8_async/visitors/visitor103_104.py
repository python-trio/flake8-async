"""Contains Visitor103_104.

Never have an except Cancelled or except BaseException block with a code path that
doesn't re-raise the error.
103 is given when an except block exits without any raises, while 104 is given when
an improper raise, or other flow control, is encountered.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any

from .flake8asyncvisitor import Flake8AsyncVisitor
from .helpers import critical_except, error_class, iter_guaranteed_once

if TYPE_CHECKING:
    from collections.abc import Mapping

_async103_common_msg = "{} block with a code path that doesn't re-raise the error."
_suggestion = " Consider adding an `except {}: raise` before this exception handler."
_suggestion_dict: dict[tuple[str, ...], str] = {
    ("anyio",): "anyio.get_cancelled_exc_class()",
    ("trio",): "trio.Cancelled",
    ("asyncio",): "asyncio.exceptions.CancelledError",
}
# TODO: ugly
for a, b in (("anyio", "trio"), ("anyio", "asyncio"), ("asyncio", "trio")):
    _suggestion_dict[(a, b)] = (
        "[" + "/".join((_suggestion_dict[(a,)], _suggestion_dict[(b,)])) + "]"
    )
_suggestion_dict[
    (
        "anyio",
        "asyncio",
        "trio",
    )
] = (
    "["
    + "|".join(
        (
            _suggestion_dict[("anyio",)],
            _suggestion_dict[("asyncio",)],
            _suggestion_dict[("trio",)],
        )
    )
    + "]"
)

_error_codes = {
    "ASYNC103": _async103_common_msg,
    "ASYNC104": "Cancelled (and therefore BaseException) must be re-raised.",
}
for poss_library, _lib_suggest in _suggestion_dict.items():
    _error_codes[f"ASYNC103_{'_'.join(poss_library)}"] = (
        _async103_common_msg + _suggestion.format(_lib_suggest)
    )


@error_class
class Visitor103_104(Flake8AsyncVisitor):
    error_codes: Mapping[str, str] = _error_codes

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.except_name: str | None = ""
        self.unraised: bool = False
        self.unraised_break: bool = False
        self.unraised_continue: bool = False
        self.loop_depth = 0

        self.cancelled_caught: set[str] = set()

    # If an `except` is bare, catches `BaseException`, or `trio.Cancelled`
    # set self.unraised, and if it's still set after visiting child nodes
    # then there might be a code path that doesn't re-raise.
    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        marker = critical_except(node)

        if marker is None:
            # not a critical exception handler
            return

        # If previous excepts have handled trio.Cancelled, don't do anything - namely
        # don't set self.unraised (so 104 isn't triggered) nor check for 103.
        if marker.name == "trio.Cancelled":
            error_code = "ASYNC103"
            self.cancelled_caught.add("trio")
        elif marker.name in (
            "anyio.get_cancelled_exc_class()",
            "get_cancelled_exc_class()",
        ):
            error_code = "ASYNC103"
            self.cancelled_caught.add("anyio")
        elif marker.name in (
            "asyncio.exceptions.CancelledError",
            "exceptions.CancelledError",
            "CancelledError",
        ):
            error_code = "ASYNC103"
            self.cancelled_caught.add("asyncio")
        else:
            if self.cancelled_caught:
                return
            if len(self.library) < 2:
                error_code = f"ASYNC103_{self.library_str}"
            else:
                error_code = f"ASYNC103_{'_'.join(sorted(self.library))}"
            self.cancelled_caught.update("trio", "anyio", "asyncio")

        # Don't save the state of cancelled_caught, that's handled in Try and would
        # reset it between each except
        # Don't need to reset the values of unraised_[break/continue] since that's handled
        # by visit_For, but need to save the state of them to not mess up loops we're
        # nested inside
        self.save_state(
            node,
            "except_name",
            "unraised",
            "unraised_break",
            "unraised_continue",
            "loop_depth",
        )

        # save name from `as <except_name>`
        self.except_name = node.name

        self.loop_depth = 0
        self.unraised = True

        # Visit child nodes manually since we want to do logic afterwards.
        # Will unset self.unraised if all code paths `raise`
        self.generic_visit(node)

        if self.unraised:
            self.error(
                marker,
                marker.name,
                error_code=error_code,
            )

    def visit_Raise(self, node: ast.Raise):
        # if there's an unraised critical exception, the raise isn't bare,
        # and the name doesn't match, signal a problem.
        if (
            self.unraised
            and node.exc is not None
            and not (isinstance(node.exc, ast.Name) and node.exc.id == self.except_name)
        ):
            self.error(node, error_code="ASYNC104")

        # treat it as safe regardless, to avoid unnecessary error messages.
        self.unraised = False

    def visit_Return(self, node: ast.Return | ast.Yield):
        if self.unraised:
            # Error: must re-raise
            self.error(node, error_code="ASYNC104")

    visit_Yield = visit_Return

    # Treat Try's as fully covering only if `finally` always raises.
    def visit_Try(self, node: ast.Try | ast.TryStar):  # type: ignore[name-defined]
        self.save_state(node, "cancelled_caught", copy=True)
        self.cancelled_caught = set()

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

    visit_TryStar = visit_Try

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

    def visit_Match(self, node: ast.Match):  # type: ignore[name-defined]
        if not self.unraised:
            return
        all_cases_raise = True
        has_fallback = False
        for case in node.cases:
            # check for "bare pattern", i.e `case varname:`
            has_fallback |= (
                case.guard is None
                and isinstance(case.pattern, ast.MatchAs)  # type: ignore[attr-defined]
                and case.pattern.pattern is None
            )
            self.visit_nodes(case.body)
            all_cases_raise &= not self.unraised
            self.unraised = True

        self.unraised = not (all_cases_raise and has_fallback)

    # A loop is guaranteed to raise if:
    # condition always raises, or
    #   else always raises, and
    #   always raise before break
    # or body always raises (before break) and is guaranteed to run at least once
    def visit_For(self, node: ast.For | ast.While):
        if not self.unraised:
            return

        # the following block is duplicated in Visitor91X
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
            self.error(node, error_code="ASYNC104")
        self.unraised_break |= self.unraised

    def visit_Continue(self, node: ast.Continue):
        if self.unraised and self.loop_depth == 0:
            self.error(node, error_code="ASYNC104")
        self.unraised_continue |= self.unraised
