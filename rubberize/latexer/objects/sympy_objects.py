"""Converter for Sympy objects."""

import sympy as sp
from sympy import latex

from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.objects.convert_object import (
    register_object_converter,
)


# fmt: off
# pylint: disable=line-too-long
register_object_converter(sp.Expr, lambda o: ExprLatex(latex(o, mul_symbol=r"\,", imaginary_unit="ri", diff_operator="rd")))
