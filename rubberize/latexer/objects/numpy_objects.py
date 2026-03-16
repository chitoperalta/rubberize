"""Converters for NumPy objects."""

from __future__ import annotations

import numpy as np

from rubberize.latexer import formatters, ranks
from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.objects.convert_object import (
    register_object_converter,
    convert_object,
)


def _ndarray(obj: np.ndarray) -> ExprLatex | None:
    """Converter for np.ndarray."""

    def build(arr: np.ndarray):
        if arr.ndim == 1:
            parts: list = []

            for a in arr:
                elt = convert_object(a)
                if elt is None:
                    return None

                parts.append(elt.latex)

            return parts

        return [build(sub) for sub in arr]

    arr = build(obj)
    if arr is None:
        return None

    latex = formatters.format_array(arr)
    rank = ranks.COLLECTIONS_RANK

    return ExprLatex(latex, rank)


def _generic(obj: np.generic) -> ExprLatex | None:
    """Converter for np.generic, which is the base class for all NumPy
    scalars.
    """

    return convert_object(obj.item())


register_object_converter(np.ndarray, _ndarray)
register_object_converter(np.generic, _generic)
