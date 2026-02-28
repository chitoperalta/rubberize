"""Converters for builtin functions and functions from the Standard
Library.
"""

import ast
from copy import copy
from typing import Optional, TYPE_CHECKING

from rubberize.config import config
from rubberize.latexer.calls.common import (
    get_result_and_convert,
    rename,
    unary,
    wrap,
)
from rubberize.latexer.calls.convert_call import register_call_converter
from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.expr_rules import COLLECTIONS_COL, COLLECTIONS_ROW
from rubberize.latexer.formatters import format_elts
from rubberize.latexer.node_helpers import get_id, get_object
from rubberize.latexer.ranks import (
    get_rank,
    BELOW_POW_RANK,
    BELOW_MULT_RANK,
    BELOW_ADD_RANK,
)

if TYPE_CHECKING:
    from rubberize.latexer.node_visitors import ExprVisitor


# pylint: disable-next=too-many-locals
def _range(visitor: "ExprVisitor", call: ast.Call) -> Optional[ExprLatex]:
    """Convert a `range` call."""

    assert get_id(call.func) == "range"

    start, stop, step = _get_range_args(call)

    start_value = get_object(start, None)  # None if not a Constant.
    stop_value = get_object(stop, None)
    step_value = get_object(step, None)
    dots = r"\vdots" if config.show_list_as_col else r"\cdots"

    if (
        start_value is not None
        and step_value is not None
        and stop_value is not None
    ):
        obj = range(start_value, stop_value, step_value)
        if len(obj) <= 3:
            elts_latex = [str(o) for o in obj]
        else:
            elts_latex = [str(obj[0]), str(obj[1]), dots, str(obj[-1])]

    else:
        start_latex = visitor.visit(start).latex
        stop_latex = visitor.visit(stop).latex
        step_latex = visitor.visit(step).latex

        elts_latex = [start_latex]

        if start_value is not None and step_value is not None:
            elts_latex.append(f"{start_value + step_value}")
        elif step_value and step_value < 0:
            elts_latex.append(start_latex + f" - {abs(step_value)}")
        else:
            elts_latex.append(start_latex + f" + {step_latex}")

        elts_latex.append(dots)

        if step_value and step_value < 0:
            elts_latex.append("> " + stop_latex)
        elif step_value and step_value > 0:
            elts_latex.append("< " + stop_latex)
        else:
            elts_latex.append(r"\sim " + stop_latex)

    if config.show_list_as_col:
        syntax = COLLECTIONS_COL[list]
    else:
        syntax = COLLECTIONS_ROW[list]
    latex = format_elts(elts_latex, *(syntax))

    return ExprLatex(latex)


def _get_range_args(call: ast.Call) -> tuple[ast.expr, ast.expr, ast.expr]:
    """Collect start, stop, and step expression nodes of a `range()`
    call node.
    """

    if len(call.args) == 1:
        return ast.Constant(value=0), call.args[0], ast.Constant(value=1)
    if len(call.args) == 2:
        return call.args[0], call.args[1], ast.Constant(value=1)
    return call.args[0], call.args[1], call.args[2]


def _exp(visitor: "ExprVisitor", call: ast.Call) -> Optional[ExprLatex]:
    """Convert an `exp` call."""

    rank = BELOW_POW_RANK
    assert get_id(call.func) == "exp"

    if isinstance(call.args[0], ast.BinOp) and isinstance(
        call.args[0].op, ast.Div
    ):
        return rename(visitor, call, r"\exp ")

    return wrap(visitor, call, "e^{", "}", rank=rank)


def _log(visitor: "ExprVisitor", call: ast.Call) -> ExprLatex:
    """Convert a `log` call."""

    assert get_id(call.func) == "log"

    if len(call.args) == 1:
        return unary(visitor, call, r"\ln ")
    if isinstance(call.args[1], ast.Constant) and call.args[1].value == 10:
        return unary(visitor, call, r"\log ")
    if get_id(call.args[1]) == "e":
        return unary(visitor, call, r"\ln ")

    base = visitor.visit(call.args[1])
    return unary(visitor, call, r"\log_{" + base.latex + "} ")


# pylint: disable-next=too-many-locals
def _sum_prod(visitor: "ExprVisitor", call: ast.Call) -> Optional[ExprLatex]:
    """Convert a `sum`, `fsum`, or `prod` call."""

    rank = BELOW_MULT_RANK
    with_initial_rank = BELOW_ADD_RANK

    name = get_id(call.func)
    assert name in ("sum", "fsum", "prod")

    if visitor.namespace is not None:
        # Prevent substitution
        visitor = copy(visitor)
        visitor.namespace = None

    if not isinstance(call.args[0], ast.GeneratorExp):
        opd = visitor.visit_opd(call.args[0], rank)
        op_latex = "\\" + name
    else:
        opd = visitor.visit_opd(call.args[0].elt, get_rank(call.args[0]))
        ops = []
        for comp in call.args[0].generators:
            if (
                isinstance(comp.iter, ast.Call)
                and get_id(comp.iter.func) == "range"
                and len(comp.iter.args) < 3
            ):
                # Iterated over range(b) or range(a, b)
                var = visitor.visit(comp.target)
                start, stop, _ = _get_range_args(comp.iter)

                sub = var.latex + " = " + visitor.visit(start).latex
                stop_value = get_object(stop, None)  # None if not a Constant
                if stop_value is not None:
                    sup = str(stop_value - 1)
                else:
                    sup = visitor.visit(stop).latex + "- 1"

                ops.append("\\" + name + "_{" + sub + "}^{" + sup + "}")
            else:
                # Element-wise operation on a list or a collection
                ops.append("\\" + name + "_{" + visitor.visit(comp).latex + "}")
        op_latex = r"\,".join(ops)

    if len(call.args) == 2:
        init = visitor.visit_opd(call.args[1], with_initial_rank)
        latex = init.latex + " + " + op_latex + " " + opd.latex
        return ExprLatex(latex, BELOW_ADD_RANK)

    latex = op_latex + " " + opd.latex
    return ExprLatex(latex, BELOW_MULT_RANK)


# fmt: off
# pylint: disable=line-too-long
register_call_converter("int", get_result_and_convert)
register_call_converter("float", get_result_and_convert)
register_call_converter("Decimal", get_result_and_convert)
register_call_converter("Fraction", get_result_and_convert)
register_call_converter("complex", get_result_and_convert)
register_call_converter("list", get_result_and_convert)
register_call_converter("tuple", get_result_and_convert)
register_call_converter("set", get_result_and_convert)
register_call_converter("dict", get_result_and_convert)
register_call_converter("range", _range)
register_call_converter("abs", lambda v, c: wrap(v, c, r"\left|", r"\right|"))
register_call_converter("fabs", lambda v, c: wrap(v, c, r"\left|", r"\right|"))
register_call_converter("ceil", lambda v, c: wrap(v, c, r"\left\lceil", r"\right\rceil"))
register_call_converter("comb", lambda v, c: rename(v, c, r"\operatorname{C}"))
register_call_converter("perm", lambda v, c: rename(v, c, r"\operatorname{P}"))
register_call_converter("exp", _exp)
register_call_converter("factorial", lambda v, c: unary(v, c, "", "!"))
register_call_converter("floor", lambda v, c: wrap(v, c, r"\left\lfloor", r"\right\rfloor"))
register_call_converter("gamma", lambda v, c: rename(v, c, r"\Gamma"))
register_call_converter("log", _log)
register_call_converter("log10", lambda v, c: unary(v, c, r"\log"))
register_call_converter("log1p", lambda v, c: wrap(v, c, r"\ln \left(1 +", r"\right)"))
register_call_converter("log2", lambda v, c: unary(v, c, r"\log_{2} "))
register_call_converter("sqrt", lambda v, c: wrap(v, c, r"\sqrt{", "}", rank=BELOW_POW_RANK))
register_call_converter("cbrt", lambda v, c: wrap(v, c, r"\sqrt[3]{", "}", rank=BELOW_POW_RANK))
register_call_converter("sum", _sum_prod)
register_call_converter("fsum", _sum_prod)
register_call_converter("prod", _sum_prod)
register_call_converter("sin", lambda v, c: unary(v, c, r"\sin "))
register_call_converter("cos", lambda v, c: unary(v, c, r"\cos "))
register_call_converter("tan", lambda v, c: unary(v, c, r"\tan "))
register_call_converter("csc", lambda v, c: unary(v, c, r"\csc "))
register_call_converter("sec", lambda v, c: unary(v, c, r"\sec "))
register_call_converter("cot", lambda v, c: unary(v, c, r"\cot "))
register_call_converter("sinh", lambda v, c: unary(v, c, r"\sinh "))
register_call_converter("cosh", lambda v, c: unary(v, c, r"\cosh "))
register_call_converter("tanh", lambda v, c: unary(v, c, r"\tanh "))
register_call_converter("csch", lambda v, c: unary(v, c, r"\operatorname{csch} "))
register_call_converter("sech", lambda v, c: unary(v, c, r"\operatorname{sech} "))
register_call_converter("coth", lambda v, c: unary(v, c, r"\coth "))
register_call_converter("asin", lambda v, c: unary(v, c, r"\arcsin "))
register_call_converter("arcsin", lambda v, c: unary(v, c, r"\arcsin "))
register_call_converter("acos", lambda v, c: unary(v, c, r"\arccos "))
register_call_converter("arccos", lambda v, c: unary(v, c, r"\arccos "))
register_call_converter("atan", lambda v, c: unary(v, c, r"\arctan "))
register_call_converter("atan2", lambda v, c: unary(v, c, r"\arctan "))
register_call_converter("arctan", lambda v, c: unary(v, c, r"\arctan "))
register_call_converter("arccsc", lambda v, c: unary(v, c, r"\arccsc "))
register_call_converter("arcsec", lambda v, c: unary(v, c, r"\arcsec "))
register_call_converter("arccot", lambda v, c: unary(v, c, r"\arccot "))
register_call_converter("arsinh", lambda v, c: unary(v, c, r"\operatorname{arsinh} "))
register_call_converter("arcosh", lambda v, c: unary(v, c, r"\operatorname{arcosh} "))
register_call_converter("artanh", lambda v, c: unary(v, c, r"\operatorname{artanh} "))
register_call_converter("arcsch", lambda v, c: unary(v, c, r"\operatorname{arcsch} "))
register_call_converter("arsech", lambda v, c: unary(v, c, r"\operatorname{arsech} "))
register_call_converter("arcoth", lambda v, c: unary(v, c, r"\operatorname{arcoth} "))
