"""Converters for NumPy calls."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import numpy as np

from rubberize.config import config
from rubberize.latexer import formatters, helpers, ranks, rules
from rubberize.latexer.calls import common
from rubberize.latexer.calls.convert_call import register_call_converter
from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.objects import convert_object

if TYPE_CHECKING:
    from rubberize.latexer.visitors import ExprVisitor


def _cross(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.cross call."""

    a_node = helpers.get_arg_node(node, 0, "a", required=True)
    b_node = helpers.get_arg_node(node, 1, "b", required=True)

    rank = ranks.BELOW_MULT_RANK
    a = visitor.visit_operand(a_node, rank, non_assoc=True).latex
    b = visitor.visit_operand(b_node, rank, non_assoc=True).latex

    latex = a + r" \times " + b

    return ExprLatex(latex, rank)


def _fmt_shape(visitor: ExprVisitor, node: ast.expr) -> str | None:
    """Format array shape LaTeX from a node representing the shape of
    the array.
    """

    if isinstance(node, (ast.Tuple, ast.List)):
        shape = [visitor.visit(e).latex for e in node.elts]
    else:
        shape = [visitor.visit(node).latex]

    if not shape:
        return None

    if len(shape) == 1:
        shape = ["1", shape[0]]

    return r" \times ".join(shape)


def _ones(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a numpy.ones call."""

    shape_node = helpers.get_arg_node(node, 0, "shape", required=True)

    shape = _fmt_shape(visitor, shape_node)
    if shape is None:
        return None

    return ExprLatex(r"\mathbf{1}_{" + shape + "}")


def _ones_like(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a numpy.ones_like call."""

    a_node = helpers.get_arg_node(node, 0, "a", required=True)
    shape_node = helpers.get_arg_node(node, 4, "shape")

    visitor = common.no_substitution(visitor)

    if shape_node is not None:
        shape = _fmt_shape(visitor, shape_node)
        if shape is None:
            return None
    else:
        shape = visitor.visit(a_node).latex

    return ExprLatex(r"\mathbf{1}_{" + shape + "}")


def _zeros(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a numpy.zeros call."""

    shape_node = helpers.get_arg_node(node, 0, "shape", required=True)

    shape = _fmt_shape(visitor, shape_node)
    if shape is None:
        return None

    return ExprLatex(r"\mathbf{0}_{" + shape + "}")


def _zeros_like(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a numpy.zeros_like call."""

    a_node = helpers.get_arg_node(node, 0, "a", required=True)
    shape_node = helpers.get_arg_node(node, 4, "shape")

    visitor = common.no_substitution(visitor)

    if shape_node is not None:
        shape = _fmt_shape(visitor, shape_node)
        if shape is None:
            return None
    else:
        shape = visitor.visit(a_node).latex

    return ExprLatex(r"\mathbf{0}_{" + shape + "}")


def _eye(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.eye function call."""

    n_node = helpers.get_arg_node(node, 0, "N", required=True)
    m_node = helpers.get_arg_node(node, 1, "M")
    k_node = helpers.get_arg_node(node, 2, "k")

    n = visitor.visit(n_node).latex
    m = visitor.visit(m_node).latex if m_node else None
    k = visitor.visit(k_node).latex if k_node else None

    latex = r"\mathbf{I}_{" + n

    if m is not None:
        latex += rf" \times {m}"
    if k is not None:
        latex += r"}^{\left( " + k + r" \right)"

    latex += "}"
    rank = ranks.BELOW_POW_RANK

    return ExprLatex(latex, rank)


def _identity(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.identity function call."""

    n_node = helpers.get_arg_node(node, 0, "n", required=True)

    n = visitor.visit(n_node).latex
    return ExprLatex(r"\mathbf{I}_{" + n + "}")


def _full(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a numpy.full call."""

    shape_node = helpers.get_arg_node(node, 0, "shape", required=True)
    fill_node = helpers.get_arg_node(node, 1, "fill_value", required=True)

    shape = _fmt_shape(visitor, shape_node)
    if shape is None:
        return None

    rank = ranks.BELOW_MULT_RANK
    fill = visitor.visit_operand(fill_node, rank).latex

    latex = fill + r" \cdot \mathbf{1}_{" + shape + "}"

    return ExprLatex(latex, rank)


def _full_like(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a numpy.full_like call."""

    a_node = helpers.get_arg_node(node, 0, "a", required=True)
    fill_node = helpers.get_arg_node(node, 1, "fill_value", required=True)
    shape_node = helpers.get_arg_node(node, 5, "shape")

    visitor = common.no_substitution(visitor)

    if shape_node is not None:
        shape = _fmt_shape(visitor, shape_node)
        if shape is None:
            return None
    else:
        shape = visitor.visit(a_node).latex

    rank = ranks.BELOW_MULT_RANK
    fill = visitor.visit_operand(fill_node, rank).latex

    latex = fill + r" \cdot \mathbf{1}_{" + shape + "}"

    return ExprLatex(latex, rank)


def _transpose(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a numpy.transpose call."""

    if helpers.get_arg_node(node, 1, "axes") is not None:
        return None

    a_node = helpers.get_arg_node(node, 0, "a", required=True)
    return _transpose_common(visitor, a_node)


def _ndarray_transpose(
    visitor: ExprVisitor, node: ast.Call
) -> ExprLatex | None:
    """Convert a numpy.ndarray.transpose call."""

    if not isinstance(node.func, ast.Attribute):
        return None

    if node.args:
        return None

    return _transpose_common(visitor, node.func.value)


def _transpose_common(visitor: ExprVisitor, a_node: ast.expr) -> ExprLatex:
    a = visitor.visit(a_node).latex

    latex = a + r"^{\intercal}"
    rank = ranks.BELOW_POW_RANK

    return ExprLatex(latex, rank)


def _dot(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.dot call."""

    a_node = helpers.get_arg_node(node, 0, "a", required=True)
    b_node = helpers.get_arg_node(node, 1, "b", required=True)
    return _dot_common(visitor, a_node, b_node)


def _ndarray_dot(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a numpy.ndarray.dot call."""

    if not isinstance(node.func, ast.Attribute):
        return None

    other = helpers.get_arg_node(node, 0, None, required=True)
    return _dot_common(visitor, node.func.value, other)


def _vdot(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.vdot call."""

    a_node = helpers.get_arg_node(node, 0, None, required=True)
    b_node = helpers.get_arg_node(node, 1, None, required=True)
    return _dot_common(visitor, a_node, b_node)


def _vecdot(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.vecdot call."""

    x1_node = helpers.get_arg_node(node, 0, None, required=True)
    x2_node = helpers.get_arg_node(node, 1, None, required=True)
    return _dot_common(visitor, x1_node, x2_node)


def _linalg_vecdot(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a numpy.linalg.vecdot call."""

    axis_node = helpers.get_arg_node(node, None, "axis") or ast.Constant(-1)
    if helpers.get_object(axis_node, visitor.ns) != -1:
        return None

    x1_node = helpers.get_arg_node(node, 0, None, required=True)
    x2_node = helpers.get_arg_node(node, 1, None, required=True)
    return _dot_common(visitor, x1_node, x2_node)


def _matmul(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.matmul call."""

    x1_node = helpers.get_arg_node(node, 0, None, required=True)
    x2_node = helpers.get_arg_node(node, 1, None, required=True)
    return _dot_common(visitor, x1_node, x2_node)


def _linalg_matmul(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.linalg.matmul call."""

    x1_node = helpers.get_arg_node(node, 0, None, required=True)
    x2_node = helpers.get_arg_node(node, 1, None, required=True)
    return _dot_common(visitor, x1_node, x2_node)


def _matvec(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.matvec call."""

    x1_node = helpers.get_arg_node(node, 0, None, required=True)
    x2_node = helpers.get_arg_node(node, 1, None, required=True)
    return _dot_common(visitor, x1_node, x2_node)


def _vecmat(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.vecmat call."""

    x1_node = helpers.get_arg_node(node, 0, None, required=True)
    x2_node = helpers.get_arg_node(node, 1, None, required=True)
    return _dot_common(visitor, x1_node, x2_node)


def _dot_common(
    visitor: ExprVisitor, a_node: ast.expr, b_node: ast.expr
) -> ExprLatex:
    op = rules.BIN_OPS[ast.MatMult]

    rank = ranks.BELOW_MULT_RANK
    a = visitor.visit_binop_operand(a_node, rank, op.left).latex
    b = visitor.visit_binop_operand(b_node, rank, op.right).latex

    latex = op.prefix + a + op.infix + b + op.suffix

    return ExprLatex(latex, rank)


def _linalg_multi_dot(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a numpy.linalg.multi_dot call."""

    arrays_node = helpers.get_arg_node(node, 0, "arrays", required=True)

    rank = ranks.MULT_RANK

    if isinstance(arrays_node, (ast.Tuple, ast.List)):
        arrs = [visitor.visit_operand(e, rank).latex for e in arrays_node.elts]
    else:
        arrs = [visitor.visit(node).latex]

    if not arrs:
        return None

    op = rules.BIN_OPS[ast.MatMult]
    latex = op.prefix + op.infix.join(arrs) + op.suffix

    return ExprLatex(latex, rank)


def _inner(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.inner call."""

    a_node = helpers.get_arg_node(node, 0, None, required=True)
    b_node = helpers.get_arg_node(node, 1, None, required=True)

    # syntax wraps the operands so visit rather than visit_operand
    a = visitor.visit(a_node).latex
    b = visitor.visit(b_node).latex

    latex = r"\left\langle " + a + r",\, " + b + r" \right\rangle"

    return ExprLatex(latex)


def _outer(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.outer call."""

    a_node = helpers.get_arg_node(node, 0, "a", required=True)
    b_node = helpers.get_arg_node(node, 1, "b", required=True)
    return _outer_common(visitor, a_node, b_node)


def _linalg_outer(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.linalg.outer call."""

    x1_node = helpers.get_arg_node(node, 0, None, required=True)
    x2_node = helpers.get_arg_node(node, 1, None, required=True)
    return _outer_common(visitor, x1_node, x2_node)


def _outer_common(visitor: ExprVisitor, a_node: ast.expr, b_node: ast.expr):
    rank = ranks.BELOW_MULT_RANK
    a = visitor.visit_operand(a_node, rank).latex
    b = visitor.visit_operand(b_node, rank).latex

    latex = a + r" \otimes " + b

    return ExprLatex(latex, rank)


def _linalg_matrix_power(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.linalg.matrix_power call."""

    a_node = helpers.get_arg_node(node, 0, "a", required=True)
    n_node = helpers.get_arg_node(node, 1, "n", required=True)

    rank = ranks.BELOW_POW_RANK
    a = visitor.visit_operand(a_node, rank, non_assoc=True).latex
    n = visitor.visit(n_node).latex

    latex = a + "^{" + n + "}"

    return ExprLatex(latex, rank)


def _linalg_norm(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a numpy.linalg.norm call."""

    axis_node = helpers.get_arg_node(node, 2, "axis") or ast.Constant(None)
    if helpers.get_object(axis_node, visitor.ns) is not None:
        return None

    x_node = helpers.get_arg_node(node, 0, "x", required=True)
    ord_node = helpers.get_arg_node(node, 1, "ord") or ast.Constant(None)

    array_obj: np.ndarray | None = helpers.get_object(x_node, visitor.ns)
    if array_obj is None:
        return None

    if visitor.ns and visitor.is_subst:
        latex = _array_in_env(visitor, x_node, "Vmatrix")
    else:
        x = visitor.visit(x_node).latex
        latex = formatters.format_delims(r"\left\|", x, r"\right\|")

    ord_obj = helpers.get_object(ord_node, visitor.ns)

    if array_obj.ndim == 1:
        if ord_obj == np.inf:
            latex += r"_{\infty}"
        elif ord_obj == -np.inf:
            latex += r"_{-\infty}"
        elif isinstance(ord_obj, (int, float)) and ord_obj != 2:
            latex += "_{" + str(ord_obj) + "}"
    elif array_obj.ndim == 2:
        if ord_obj is None or ord_obj == "fro":
            latex += "_{F}"
        elif ord_obj == "nuc":
            latex += "_{*}"
        if ord_obj == np.inf:
            latex += r"_{\infty}"
        elif ord_obj == -np.inf:
            latex += r"_{-\infty}"
        elif ord_obj in (1, -1, 2, -2):
            latex += "_{" + str(ord_obj) + "}"

    return ExprLatex(latex)


def _linalg_matrix_norm(
    visitor: ExprVisitor, node: ast.Call
) -> ExprLatex | None:
    """Convert a numpy.linalg.matrix_norm call."""

    x_node = helpers.get_arg_node(node, 0, None, required=True)
    ord_node = helpers.get_arg_node(node, None, "ord") or ast.Constant("fro")

    if visitor.ns and visitor.is_subst:
        latex = _array_in_env(visitor, x_node, "Vmatrix")
    else:
        x = visitor.visit(x_node).latex
        latex = formatters.format_delims(r"\left\|", x, r"\right\|")

    ord_obj = helpers.get_object(ord_node, visitor.ns)

    if ord_obj is None or ord_obj == "fro":
        latex += "_{F}"
    elif ord_obj == "nuc":
        latex += "_{*}"
    if ord_obj == np.inf:
        latex += r"_{\infty}"
    elif ord_obj == -np.inf:
        latex += r"_{-\infty}"
    elif ord_obj in (1, -1, 2, -2):
        latex += "_{" + str(ord_obj) + "}"

    return ExprLatex(latex)


def _linalg_vector_norm(
    visitor: ExprVisitor, node: ast.Call
) -> ExprLatex | None:
    """Convert a numpy.linalg.vector_norm call."""

    axis_node = helpers.get_arg_node(node, None, "axis") or ast.Constant(None)
    if helpers.get_object(axis_node, visitor.ns) is not None:
        return None

    x_node = helpers.get_arg_node(node, 0, None, required=True)
    ord_node = helpers.get_arg_node(node, None, "ord") or ast.Constant(2)

    if visitor.ns and visitor.is_subst:
        latex = _array_in_env(visitor, x_node, "Vmatrix")
    else:
        x = visitor.visit(x_node).latex
        latex = formatters.format_delims(r"\left\|", x, r"\right\|")

    ord_obj = helpers.get_object(ord_node, visitor.ns)

    if ord_obj == np.inf:
        latex += r"_{\infty}"
    elif ord_obj == -np.inf:
        latex += r"_{-\infty}"
    elif isinstance(ord_obj, (int, float)) and ord_obj != 2:
        latex += "_{" + str(ord_obj) + "}"

    return ExprLatex(latex)


def _array_in_env(visitor: ExprVisitor, node: ast.expr, env: str) -> str:
    """Visit and format an array object but the outermost delimiter
    changed to env.
    """

    if not visitor.ns or not visitor.is_subst:
        return visitor.visit(node).latex

    obj = helpers.get_object(node, visitor.ns)

    if obj is None:
        return visitor.visit(node).latex

    if not isinstance(obj, np.ndarray):
        return visitor.visit(node).latex

    # custom ndarray object converter for array in custom LaTeX env

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
        return visitor.visit(node).latex

    return formatters.format_array(arr, env=env)


def array_func(
    visitor: ExprVisitor,
    node: ast.Call,
    name: str,
    *,
    rank: int = ranks.CALL_RANK,
) -> ExprLatex:
    """Common converter for a function with an array argument. If more
    than one argument is supplied, uses common.rename().
    """

    if len(node.args) == 1:
        arg = _array_in_env(visitor, node.args[0], "pmatrix")

        if arg.startswith(r"\begin{pmatrix}"):
            latex = f"{name} {arg}"
            return ExprLatex(latex, rank)

    return common.rename(visitor, node, name, rank=rank)


def array_method(
    visitor: ExprVisitor,
    node: ast.Call,
    name: str,
    *,
    rank: int = ranks.CALL_RANK,
) -> ExprLatex | None:
    """Common converter for a method of an array that must be formatted
    like an array_func. If more than one argument is supplied, uses
    common.rename_method().
    """

    if not isinstance(node.func, ast.Attribute):
        return None

    if not node.args:
        arg = _array_in_env(visitor, node.func.value, "pmatrix")

        if arg.startswith(r"\begin{pmatrix}"):
            latex = f"{name} {arg}"
            return ExprLatex(latex, rank)

    return common.rename_method(visitor, node, name, rank=rank)


def _linalg_solve(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.linalg.solve call."""

    a_node = helpers.get_arg_node(node, 0, "a", required=True)
    b_node = helpers.get_arg_node(node, 1, "b", required=True)

    rank = ranks.BELOW_MULT_RANK
    a = visitor.visit_operand(a_node, rank, non_assoc=True).latex

    with config.override(show_1d_as_col=True):
        b = visitor.visit_operand(b_node, rank).latex

    latex = (
        r"\underbracket{"
        + (a + "^{-1}" + r" \cdot " + b)
        + r"}_{\text{via LAPACK}}"
    )

    return ExprLatex(latex, rank)


def _linalg_inv(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.linalg.inv call."""

    a_node = helpers.get_arg_node(node, 0, "a", required=True)

    rank = ranks.BELOW_POW_RANK
    a = visitor.visit_operand(a_node, rank, non_assoc=True).latex

    latex = a + "^{-1}"

    return ExprLatex(latex, rank)


def _linalg_pinv(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.linalg.pinv call."""

    a_node = helpers.get_arg_node(node, 0, "a", required=True)

    rank = ranks.BELOW_POW_RANK
    a = visitor.visit_operand(a_node, rank, non_assoc=True).latex

    latex = a + "^{+}"

    return ExprLatex(latex, rank)


def _sum(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a numpy.sum call."""

    if helpers.get_arg_node(node, 1, "axis") is not None:
        return None

    a_node = helpers.get_arg_node(node, 0, "a", required=True)
    op_symbol = r"\sum"

    return _sum_prod_common(visitor, op_symbol, a_node)


def _ndarray_sum(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a numpy.ndarray.sum call."""

    if not isinstance(node.func, ast.Attribute):
        return None

    if helpers.get_arg_node(node, 0, "axis") is not None:
        return None

    op_symbol = r"\sum"

    return _sum_prod_common(visitor, op_symbol, node.func.value)


def _prod(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a numpy.prod call."""

    if helpers.get_arg_node(node, 1, "axis") is not None:
        return None

    a_node = helpers.get_arg_node(node, 0, "a", required=True)
    op_symbol = r"\prod"

    return _sum_prod_common(visitor, op_symbol, a_node)


def _ndarray_prod(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a numpy.ndarray.prod call."""

    if not isinstance(node.func, ast.Attribute):
        return None

    if helpers.get_arg_node(node, 0, "axis") is not None:
        return None

    op_symbol = r"\prod"

    return _sum_prod_common(visitor, op_symbol, node.func.value)


def _sum_prod_common(
    visitor: ExprVisitor, op_symbol: str, a_node: ast.expr
) -> ExprLatex:

    visitor = common.no_substitution(visitor)

    rank = ranks.BELOW_MULT_RANK
    operand = visitor.visit_operand(a_node, rank).latex

    latex = f"{op_symbol} {operand}"

    return ExprLatex(latex, rank)


def _logical_and(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.logical_and call."""

    x1_node = helpers.get_arg_node(node, 0, None, required=True)
    x2_node = helpers.get_arg_node(node, 1, None, required=True)

    op_node = ast.BoolOp(op=ast.And(), values=[x1_node, x2_node])

    latex = visitor.visit(op_node).latex
    rank = ranks.get_rank(op_node) - 1

    return ExprLatex(latex, rank)


def _logical_or(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.logical_or call."""

    x1_node = helpers.get_arg_node(node, 0, None, required=True)
    x2_node = helpers.get_arg_node(node, 1, None, required=True)

    op_node = ast.BoolOp(op=ast.Or(), values=[x1_node, x2_node])

    latex = visitor.visit(op_node).latex
    rank = ranks.get_rank(op_node) - 1

    return ExprLatex(latex, rank)


def _logical_not(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.logical_not call."""

    x_node = helpers.get_arg_node(node, 0, None, required=True)

    op_node = ast.UnaryOp(op=ast.Not(), operand=x_node)

    latex = visitor.visit(op_node).latex
    rank = ranks.get_rank(op_node) - 1

    return ExprLatex(latex, rank)


def _logical_xor(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.logical_xor call."""

    x1_node = helpers.get_arg_node(node, 0, None, required=True)
    x2_node = helpers.get_arg_node(node, 1, None, required=True)

    rank = ranks.BELOW_COMPARE_RANK
    x1 = visitor.visit_operand(x1_node, rank).latex
    x2 = visitor.visit_operand(x2_node, rank).latex

    latex = rf"{x1} \veebar {x2}"

    return ExprLatex(latex, rank)


def _allclose_isclose(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.isclose and numpy.allclose call"""

    a_node = helpers.get_arg_node(node, 0, "a", required=True)
    b_node = helpers.get_arg_node(node, 1, "b", required=True)

    rank = ranks.BELOW_COMPARE_RANK
    a = visitor.visit_operand(a_node, rank).latex
    b = visitor.visit_operand(b_node, rank).latex

    latex = rf"{a} \approx {b}"

    return ExprLatex(latex, rank)


def _array_equal(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a numpy.array_equal call."""

    a1_node = helpers.get_arg_node(node, 0, "a1", required=True)
    a2_node = helpers.get_arg_node(node, 1, "a2", required=True)

    op_node = ast.Compare(left=a1_node, ops=[ast.Eq()], comparators=[a2_node])

    latex = visitor.visit(op_node).latex
    rank = ranks.get_rank(op_node) - 1

    return ExprLatex(latex, rank)


def _compare(visitor: ExprVisitor, node: ast.Call, op: ast.cmpop) -> ExprLatex:
    """Convert a numpy comparison call."""

    x1_node = helpers.get_arg_node(node, 0, None, required=True)
    x2_node = helpers.get_arg_node(node, 1, None, required=True)

    op_node = ast.Compare(left=x1_node, ops=[op], comparators=[x2_node])

    latex = visitor.visit(op_node).latex
    rank = ranks.get_rank(op_node) - 1

    return ExprLatex(latex, rank)


# fmt: off
# pylint: disable=line-too-long
register_call_converter(np.array, lambda v, n: v.visit_array(n.args[0]))
register_call_converter(np.cross, _cross)
register_call_converter(np.ones, _ones)
register_call_converter(np.ones_like, _ones_like)
register_call_converter(np.zeros, _zeros)
register_call_converter(np.zeros_like, _zeros_like)
register_call_converter(np.eye, _eye)
register_call_converter(np.identity, _identity)
register_call_converter(np.full, _full)
register_call_converter(np.full_like, _full_like)

register_call_converter(np.transpose, _transpose)
register_call_converter(np.ndarray.transpose, _ndarray_transpose, syntactic=False)
register_call_converter(np.linalg.matrix_transpose, _transpose)

register_call_converter(np.dot, _dot)
register_call_converter(np.ndarray.dot, _ndarray_dot, syntactic=False)
register_call_converter(np.vdot, _vdot)
register_call_converter(np.vecdot, _vecdot)
register_call_converter(np.linalg.vecdot, _linalg_vecdot, syntactic=False)
register_call_converter(np.matmul, _matmul)
register_call_converter(np.linalg.matmul, _linalg_matmul, syntactic=False)
register_call_converter(np.matvec, _matvec)
register_call_converter(np.vecmat, _vecmat)
register_call_converter(np.linalg.multi_dot, _linalg_multi_dot)
register_call_converter(np.inner, _inner)
register_call_converter(np.outer, _outer)
register_call_converter(np.linalg.outer, _linalg_outer, syntactic=False)
register_call_converter(np.linalg.matrix_power, _linalg_matrix_power)
register_call_converter(np.linalg.norm, _linalg_norm)
register_call_converter(np.linalg.matrix_norm, _linalg_matrix_norm)
register_call_converter(np.linalg.vector_norm, _linalg_vector_norm)
register_call_converter(np.linalg.det, lambda v, n: array_func(v, n, r"\det"))
register_call_converter(np.linalg.matrix_rank, lambda v, n: array_func(v, n, r"\operatorname{rank}"))
register_call_converter(np.trace, lambda v, n: array_func(v, n, r"\operatorname{Tr}"))
register_call_converter(np.linalg.trace, lambda v, n: array_func(v, n, r"\operatorname{Tr}"), syntactic=False)
register_call_converter(np.linalg.solve, _linalg_solve)
register_call_converter(np.diagonal, lambda v, n: array_func(v, n, r"\operatorname{diag}"))
register_call_converter(np.linalg.diagonal, lambda v, n: array_func(v, n, r"\operatorname{diag}"), syntactic=False)
register_call_converter(np.ndarray.diagonal, lambda v, n: array_method(v, n, r"\operatorname{diag}"), syntactic=False)
register_call_converter(np.linalg.inv, _linalg_inv)
register_call_converter(np.linalg.pinv, _linalg_pinv)

register_call_converter(np.amax, lambda v, n: array_func(v, n, r"\max"))
register_call_converter(np.ndarray.max, lambda v, n: array_method(v, n, r"\max"), syntactic=False)
register_call_converter(np.amin, lambda v, n: array_func(v, n, r"\min"))
register_call_converter(np.ndarray.min, lambda v, n: array_method(v, n, r"\min"), syntactic=False)
register_call_converter(np.ndarray.mean, lambda v, n: array_method(v, n, r"\operatorname{mean}"), syntactic=False)
register_call_converter(np.prod, _prod, syntactic=False)
register_call_converter(np.ndarray.prod, _ndarray_prod, syntactic=False)
register_call_converter(np.sum, _sum, syntactic=False)
register_call_converter(np.ndarray.sum, _ndarray_sum, syntactic=False)

register_call_converter(np.logical_and, _logical_and, syntactic=False)
register_call_converter(np.logical_or, _logical_or, syntactic=False)
register_call_converter(np.logical_not, _logical_not, syntactic=False)
register_call_converter(np.logical_xor, _logical_xor, syntactic=False)
register_call_converter(np.allclose, _allclose_isclose, syntactic=False)
register_call_converter(np.isclose, _allclose_isclose, syntactic=False)
register_call_converter(np.array_equal, _array_equal, syntactic=False)
register_call_converter(np.greater, lambda v, n: _compare(v, n, ast.Gt()), syntactic=False)
register_call_converter(np.greater_equal, lambda v, n: _compare(v, n, ast.GtE()), syntactic=False)
register_call_converter(np.less, lambda v, n: _compare(v, n, ast.Lt()), syntactic=False)
register_call_converter(np.less_equal, lambda v, n: _compare(v, n, ast.LtE()), syntactic=False)
register_call_converter(np.equal, lambda v, n: _compare(v, n, ast.Eq()), syntactic=False)
register_call_converter(np.not_equal, lambda v, n: _compare(v, n, ast.NotEq()), syntactic=False)
