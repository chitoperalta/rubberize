"""Useful converters."""

import ast
from typing import Optional, TYPE_CHECKING

from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.formatters import format_delims, format_elts
from rubberize.latexer.node_helpers import get_id, get_object, is_method
from rubberize.latexer.objects import convert_object
from rubberize.latexer.ranks import BELOW_POW_RANK, VALUE_RANK

if TYPE_CHECKING:
    from rubberize.latexer.node_visitors import ExprVisitor


def get_result_and_convert(
    visitor: "ExprVisitor", call: ast.Call
) -> Optional[ExprLatex]:
    """Common converter that gets the resulting object of a call node's
    call, and then converts the resulting object to latex."""

    obj = get_object(call, visitor.namespace)
    if obj is None:
        return None
    return convert_object(obj)


# pylint: disable-next=too-many-arguments
def wrap(
    visitor: "ExprVisitor",
    call: ast.Call,
    prefix: str,
    suffix: str,
    sep: str = r",\, ",
    *,
    rank: int = VALUE_RANK,
) -> ExprLatex:
    """Common converter that adds prefix, suffix, and separator to args."""

    args_latex = [visitor.visit(a).latex for a in call.args]
    latex = format_elts(args_latex, sep, (prefix, suffix))

    return ExprLatex(latex, rank)


# pylint: disable-next=too-many-arguments
def wrap_method(
    visitor: "ExprVisitor",
    call: ast.Call,
    prefix: str,
    suffix: str,
    sep: str = r",\, ",
    *,
    rank: int = VALUE_RANK,
) -> ExprLatex:
    """Common converter that adds prefix, suffix, and separator to
    attribute value and args."""

    assert isinstance(call.func, ast.Attribute)

    args_latex = [visitor.visit(call.func.value).latex]
    for arg in call.args:
        args_latex.append(visitor.visit(arg).latex)
    latex = format_elts(args_latex, sep, (prefix, suffix))

    return ExprLatex(latex, rank)


def rename(
    visitor: "ExprVisitor", call: ast.Call, name: str, *, rank: int = VALUE_RANK
) -> ExprLatex:
    """Common converter that only changes the operator name."""

    args_latex = [visitor.visit(a).latex for a in call.args]
    latex = name + format_elts(args_latex, r",\, ", (r"\left(", r"\right)"))

    return ExprLatex(latex, rank)


def unary(
    visitor: "ExprVisitor", call: ast.Call, prefix: str, suffix: str = ""
) -> ExprLatex:
    """Common converter for math functions that notationally take only
    one argument.
    """

    rank = BELOW_POW_RANK

    name = get_id(call.func)
    call_arg = call.args[0]

    is_fac_arg = isinstance(call_arg, ast.Call) and (
        name == "factorial" or get_id(call_arg) == "factorial"
    )
    is_pow_arg = isinstance(call_arg, ast.BinOp) and isinstance(
        call_arg.op, ast.Pow
    )

    arg = visitor.visit_opd(call_arg, rank, force=is_fac_arg or is_pow_arg)
    latex = format_delims(arg.latex, (prefix, suffix))

    return ExprLatex(latex, rank)


def first_arg(visitor: "ExprVisitor", call: ast.Call) -> ExprLatex:
    """Common converter that only returns the converted first argument
    of the call, effectively hiding the call on the first arg.
    """

    return visitor.visit(call.args[0])


def hide_method(
    visitor: "ExprVisitor", call: ast.Call, cls: type
) -> Optional[ExprLatex]:
    """Common converter that visits the parent object of a method
    call and hides the method call and its arguments.
    """

    method = get_id(call.func)
    assert method is not None

    if not is_method(call, cls, method, visitor.namespace):
        return None

    assert isinstance(call.func, ast.Attribute)
    return visitor.visit(call.func.value)
