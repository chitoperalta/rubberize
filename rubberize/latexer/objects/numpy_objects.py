"""Converters for Numpy objects."""

from typing import Any, Optional

import numpy as np

from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.formatters import format_array
from rubberize.latexer.objects.convert_object import (
    register_object_converter,
    convert_object,
)


def _ndarray(obj: np.ndarray) -> Optional[ExprLatex]:
    """Converter for `numpy.ndarray` type object."""

    data = obj.tolist()

    def _process(elt: Any) -> str | list | None:
        if isinstance(elt, list):
            converted_list = []
            for e in elt:
                converted = _process(e)
                if converted is None:
                    return None
                converted_list.append(converted)
            return converted_list
        converted_obj = convert_object(elt)
        return converted_obj.latex if converted_obj else None

    processed_data = _process(data)
    if processed_data is None:
        return None

    return ExprLatex(format_array(processed_data))


def _generic(obj: np.generic) -> Optional[ExprLatex]:
    """Converter for `numpy.generic` type object, which is the base
    class for all numpy scalars.
    """

    return convert_object(obj.item())


register_object_converter(np.ndarray, _ndarray)
register_object_converter(np.generic, _generic)
