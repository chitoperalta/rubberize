"""Converters for Numpy calls"""

import ast
from typing import TYPE_CHECKING

import numpy as np  # pylint: disable=unused-import

from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.formatters import format_array
from rubberize.latexer.calls.builtin_calls import unary
from rubberize.latexer.calls.convert_call import register_call_converter
from rubberize.latexer.node_helpers import get_id, is_method
from rubberize.latexer.ranks import BELOW_MULT_RANK, BELOW_POW_RANK

if TYPE_CHECKING:
    from rubberize.latexer.node_visitors import ExprVisitor


def _array(visitor: "ExprVisitor", call: ast.Call) -> ExprLatex:
    """Convert a `array()` function call."""

    assert get_id(call.func) == "array"

    def _visit(elt: ast.expr) -> str | list:
        if isinstance(elt, (ast.List, ast.Tuple)):
            visited_list = []
            for e in elt.elts:
                visited_list.append(_visit(e))
            return visited_list
        return visitor.visit(elt).latex

    visited_arg = _visit(call.args[0])
    latex = format_array(visited_arg)

    return ExprLatex(latex)


def _cross(visitor: "ExprVisitor", call: ast.Call) -> ExprLatex:
    """Convert a `cross()` function call."""

    assert get_id(call.func) == "cross"
    rank = BELOW_MULT_RANK

    left_opd = visitor.visit_opd(call.args[0], rank, non_assoc=True)
    right_opd = visitor.visit_opd(call.args[1], rank, non_assoc=True)
    latex = left_opd.latex + r" \times " + right_opd.latex

    return ExprLatex(latex, rank)


def _zeros(visitor: "ExprVisitor", call: ast.Call) -> ExprLatex:
    """Convert a `zeros()` function call."""

    assert get_id(call.func) == "zeros"

    if isinstance(call.args[0], ast.Tuple):
        dims_latex = [visitor.visit(e).latex for e in call.args[0].elts]
        if not dims_latex:
            return ExprLatex("0")
        if len(dims_latex) == 1:
            dims_latex = ["1", dims_latex[0]]

        return ExprLatex(r"\mathbf{0}_{" + r" \times ".join(dims_latex) + "}")

    return ExprLatex(
        r"\mathbf{0}_{1 \times " + visitor.visit(call.args[0]).latex + "}"
    )


def _identity(visitor: "ExprVisitor", call: ast.Call) -> ExprLatex:
    """Convert an `identity()` or `eye()` function call."""

    assert get_id(call.func) in ("identity", "eye")
    return ExprLatex(r"\mathbf{I}_{" + visitor.visit(call.args[0]).latex + "}")


def _transpose(visitor: "ExprVisitor", call: ast.Call) -> ExprLatex:
    """Convert a `transpose()` function call."""

    name = get_id(call.func)
    assert name == "transpose"
    rank = BELOW_POW_RANK

    if is_method(call, np.ndarray, name, visitor.namespace):
        assert isinstance(call.func, ast.Attribute)
        array = call.func.value
    else:
        array = call.args[0]

    return ExprLatex(visitor.visit(array).latex + r"^\intercal", rank)


def _matrix_power(visitor: "ExprVisitor", call: ast.Call) -> ExprLatex:
    """Convert a `matrix_power()` function."""

    assert get_id(call.func) == "matrix_power"
    rank = BELOW_POW_RANK

    matrix = visitor.visit_opd(call.args[0], rank, non_assoc=True)
    latex = matrix.latex + "^{" + visitor.visit(call.args[1]).latex + "}"

    return ExprLatex(latex, rank)


def _inv(visitor: "ExprVisitor", call: ast.Call) -> ExprLatex:
    """Convert a `inv()` function."""

    assert get_id(call.func) == "inv"
    rank = BELOW_POW_RANK

    matrix = visitor.visit_opd(call.args[0], rank, non_assoc=True)
    latex = matrix.latex + "^{-1}"

    return ExprLatex(latex, rank)


def _pinv(visitor: "ExprVisitor", call: ast.Call) -> ExprLatex:
    """Convert a `pinv()` function."""

    assert get_id(call.func) == "pinv"
    rank = BELOW_POW_RANK

    matrix = visitor.visit_opd(call.args[0], rank, non_assoc=True)
    latex = matrix.latex + "^{+}"

    return ExprLatex(latex, rank)


def _solve(visitor: "ExprVisitor", call: ast.Call) -> ExprLatex:
    """Convert a `solve()` function."""

    assert get_id(call.func) == "solve"
    rank = BELOW_MULT_RANK

    a_mat = visitor.visit_opd(call.args[0], rank, non_assoc=True)
    b_mat = visitor.visit_opd(call.args[1], rank)
    latex = (
        r"\underbracket{"
        + (a_mat.latex + "^{-1}" + r" \cdot " + b_mat.latex)
        + r"}_{\text{via LAPACK}}"
    )

    return ExprLatex(latex, rank)


# fmt: off
register_call_converter("array", _array)
register_call_converter("cross", _cross)
register_call_converter("zeros", _zeros)
register_call_converter("identity", _identity)
register_call_converter("eye", _identity)
register_call_converter("transpose", _transpose)
register_call_converter("det", lambda v, c: unary(v, c, r"\det "))
register_call_converter("matrix_rank", lambda v, c: unary(v, c, r"\operatorname{rank} "))
register_call_converter("matrix_power", _matrix_power)
register_call_converter("inv", _inv)
register_call_converter("pinv", _pinv)
register_call_converter("solve", _solve)
