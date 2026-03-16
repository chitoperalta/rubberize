"""Object converter to LaTeX."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Callable
    from rubberize.latexer.expr_latex import ExprLatex

_object_converters: dict[type, Callable[[Any], ExprLatex | None]] = {}


def register_object_converter(
    cls: type, func: Callable[[Any], ExprLatex | None]
) -> None:
    """Register a converter function for a specific class.

    Args:
        cls: Object type the converter applies to.
        func: The converter function.
    """

    _object_converters[cls] = func


def convert_object(obj: object) -> ExprLatex | None:
    """Convert an object to LaTex using a matching converter function."""

    for cls in type(obj).__mro__:
        converter = _object_converters.get(cls)

        if converter:
            return converter(obj)

    return None
