"""Object conversion to LaTeX representations.

This module provides a registry for converting objects into LaTeX
representations using custom converter functions. The registry maps
object types to corresponding conversion functions that return an
`ExprLatex` instance, which represents the LaTeX expression of the
object.

Users can register custom converters for specific types using
`register_object_converter()`. When an object needs to be converted,
`convert_object()` looks up the appropriate converter and applies it.
"""

from typing import Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from rubberize.latexer.expr_latex import ExprLatex

_object_converters: dict[type, Callable[[Any], Optional["ExprLatex"]]] = {}


def register_object_converter(
    cls: type, func: Callable[[Any], Optional["ExprLatex"]]
) -> None:
    """Register a converter function for a specific object type.

    The provided function should take an instance of `cls` and return
    an `ExprLatex` instance representing its LaTeX expression. If the
    function returns `None`, the object is considered unconvertible.

    Args:
        cls: The type of objects the converter applies to.
        func: A function that takes an object of `cls` and returns an
            `ExprLatex` instance or `None`.
    """

    _object_converters[cls] = func


def convert_object(obj: Any) -> Optional["ExprLatex"]:
    """Convert an object to a LaTeX representation using a matching
    registered converter.

    If a converter is registered for the exact type of `obj`, it is
    used. Otherwise, the function checks if `obj` is an instance of any
    registered superclass and applies the corresponding converter.

    Args:
        obj: The object to be converted.

    Returns:
        An `ExprLatex` instance for `obj`, or `None` if no suitable
        converter is found.
    """

    converter = _object_converters.get(type(obj))
    if not converter:
        # If not the same type, maybe a subclass?
        for registered_type, func in _object_converters.items():
            if issubclass(type(obj), registered_type):
                converter = func

    if converter:
        return converter(obj)
    return None
