"""Call converter to LaTeX."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from rubberize._exceptions import RubberizeValueError
from rubberize.latexer import helpers
from rubberize.latexer.expr_latex import ExprLatex

if TYPE_CHECKING:
    from typing import Callable
    from rubberize.latexer.visitors import ExprVisitor


_call_converters: dict[
    Callable, Callable[[ExprVisitor, ast.Call], ExprLatex | None]
] = {}

_call_converters_by_name: dict[
    str, Callable[[ExprVisitor, ast.Call], ExprLatex | None]
] = {}


def register_call_converter(
    call: Callable | str,
    func: Callable[[ExprVisitor, ast.Call], ExprLatex | None],
    *,
    syntactic: bool = True,
) -> None:
    """Register a converter function for a call.

    Args:
        call: The callable object the converter applies to, or a string
            representing an undefined callable.
        func: The converter function.
    """

    if isinstance(call, str):
        _call_converters_by_name[call] = func
        return

    _call_converters[call] = func

    if syntactic:
        name = call.__name__

        existing = _call_converters_by_name.get(name)
        if existing is not None and existing is not func:
            raise RubberizeValueError(
                f"Syntactic converter already registered for '{name}'. "
                "Disable syntactic fallback or resolve the conflict."
            )

        _call_converters_by_name.setdefault(name, func)


def convert_call(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a call node to LaTex using a matching converter function.

    Args:
        visitor: The node visitor that will help with the conversion.
        node: The ast.Call node to be converted.
    """

    if visitor.ns is not None:
        key = helpers.get_func_object(node, visitor.ns)

        if key is not None:
            converter = _call_converters.get(key)
            if converter:
                return converter(visitor, node)

    # syntactic fallback -- search by name string
    name = helpers.get_id(node.func)

    if name is not None:
        converter = _call_converters_by_name.get(name)
        if converter:
            return converter(visitor, node)

    return None
