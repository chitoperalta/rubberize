"""Call conversion to LaTeX representations.

This module provides a registry for converting calls into LaTeX
representations using custom converter functions. The registry maps
identifier names to corresponding conversion functions that return an
`ExprLatex` instance, which represents the LaTeX expression of the call.

Users can register custom converters for specific identifiers using
`register_call_converter()`. When a call node needs to be converted,
`convert_call()` looks up the appropriate converter and applies it.

Note:
    Call conversion is a heuristic process rather than an exact object
    resolution. It relies on identifier names, meaning it may not
    account for reassigned functions or module imports with aliases.
    While heuristics improve accuracy, the calls are converted on a
    best-effort basis rather than a guaranteed mapping.
"""

import ast
from typing import Callable, Optional, TYPE_CHECKING

from rubberize.config import config
from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.formatters import format_name, format_elts
from rubberize.latexer.node_helpers import get_id

if TYPE_CHECKING:
    from rubberize.latexer.node_visitors import ExprVisitor


_call_converters: dict[
    str, Callable[["ExprVisitor", ast.Call], Optional[ExprLatex]]
] = {}


def register_call_converter(
    name: str,
    func: Callable[["ExprVisitor", ast.Call], Optional[ExprLatex]],
) -> None:
    """Register a converter function for a call.

    The provided function should take an `ExprVisitor` object and a call
    node, and return an `ExprLatex` instance representing its LaTeX
    expression. If the function returns `None`, the matched conversion
    function is deemed not appropriate (either by control gates or by
    `assert` statements) and the call node is converted using the
    fallback representation in `convert_call()`.

    Args:
        name: The call identifier.
        func: A function that takes an `ExprVisitor` instance and the
            call node and returns an `ExprLatex` or `None`.
    """

    _call_converters[name] = func


def convert_call(visitor: "ExprVisitor", call: ast.Call) -> ExprLatex:
    """Convert a call node to a LaTeX representation using a matching
    registered converter.

    This function applies a heuristic approach to call conversion,
    relying on identifier names rather than exact object resolution.
    If the converter function fails conversion (returns `None`), the
    default LaTeX representation for a call is returned.

    Args:
        visitor: The `ExprVisitor` instance that will convert the child
            nodes of the call node.
        call: The call node to be converted.

    Returns:
        An `ExprLatex` instance for the call node.
    """

    name = get_id(call.func)
    if not name:
        name_latex = visitor.visit(call.func).latex
    else:
        if config.convert_special_funcs:
            converter = _call_converters.get(name)
            if converter:
                special_latex = converter(visitor, call)
                if special_latex:
                    return special_latex

        if isinstance(call.func, ast.Attribute):
            name_latex = visitor.visit_Attribute(call.func, call=True).latex
        else:
            name_latex = format_name(name, call=True)

    elts_latex = [visitor.visit(a).latex for a in call.args]
    args_latex = format_elts(elts_latex, r",\, ", (r"\left(", r"\right)"))

    return ExprLatex(name_latex + " " + args_latex)
