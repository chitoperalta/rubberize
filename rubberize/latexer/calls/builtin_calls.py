"""Converters for calls to builtin functions."""

from __future__ import annotations

import ast
import decimal
import fractions
import math
from typing import TYPE_CHECKING

from rubberize.config import config
from rubberize.latexer import formatters, helpers, ranks, rules
from rubberize.latexer.calls import common, register_call_converter
from rubberize.latexer.expr_latex import ExprLatex

if TYPE_CHECKING:
    from rubberize.latexer.visitors import ExprVisitor


# pylint: disable-next=too-many-locals
def _range(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a range call"""

    visitor = common.no_substitution(visitor)
    start, stop, step = _get_range_args(node)

    start_val = helpers.get_object(start, None)  # None if not a constant
    stop_val = helpers.get_object(stop, None)
    step_val = helpers.get_object(step, None)

    if start_val is not None and step_val is not None and stop_val is not None:
        obj = range(start_val, stop_val, step_val)
        if len(obj) <= 4:
            elts = [str(o) for o in obj]
        else:
            elts = [str(obj[0]), str(obj[1]), "\ue000", str(obj[-1])]

    else:
        start_latex = visitor.visit(start).latex
        stop_latex = visitor.visit(stop).latex
        step_latex = visitor.visit(step).latex

        elts = [start_latex]

        if start_val is not None and step_val is not None:
            elts.append(f"{start_val + step_val}")
        elif step_val and step_val < 0:
            elts.append(start_latex + f" - {abs(step_val)}")
        else:
            elts.append(start_latex + f" + {step_latex}")

        elts.append("\ue000")

        if step_val and step_val < 0:
            elts.append(r"\ge " + stop_latex + " + 1")
        elif step_val and step_val > 0:
            elts.append(r"\le " + stop_latex + " - 1")
        else:
            elts.append(r"\sim " + stop_latex)

    if len(elts) > config.max_inline_elts:
        prefix, sep, suffix = rules.TUPLE_COL_SYNTAX
        dots = r"\vdots"
    else:
        prefix, sep, suffix = rules.TUPLE_ROW_SYNTAX
        dots = r"\cdots"

    latex = formatters.format_delims(
        prefix, sep.join(elts).replace("\ue000", dots), suffix
    )
    rank = ranks.COLLECTIONS_RANK

    return ExprLatex(latex, rank)


def _get_range_args(node: ast.Call) -> tuple[ast.expr, ast.expr, ast.expr]:
    """Collect the range arguments"""

    if len(node.args) == 1:
        return ast.Constant(0), node.args[0], ast.Constant(1)
    if len(node.args) == 2:
        return node.args[0], node.args[1], ast.Constant(1)
    return node.args[0], node.args[1], node.args[2]


def _sum(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a sum or math.fsum call."""

    iterable_node = helpers.get_arg_node(node, 0, None, required=True)
    start_node = helpers.get_arg_node(node, 1, "start") or ast.Constant(0)

    op_symbol = r"\sum"

    return _sum_prod_common(visitor, op_symbol, iterable_node, start_node)


def _prod(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Convert a math.prod call."""

    iterable_node = helpers.get_arg_node(node, 0, None, required=True)
    start_node = helpers.get_arg_node(node, 1, "start") or ast.Constant(1)

    op_symbol = r"\prod"

    return _sum_prod_common(visitor, op_symbol, iterable_node, start_node)


# pylint: disable-next=too-many-locals
def _sum_prod_common(
    visitor: ExprVisitor,
    op_symbol: str,
    iterable_node: ast.expr,
    start_node: ast.expr,
) -> ExprLatex | None:
    gen_visitor = common.no_substitution(visitor)

    if not isinstance(iterable_node, ast.GeneratorExp):
        op_rank = ranks.BELOW_MULT_RANK
        operand_node = iterable_node
        op = op_symbol
    else:
        op_rank = ranks.get_rank(iterable_node)
        operand_node = iterable_node.elt

        ops: list[str] = []

        for g in iterable_node.generators:
            # iterated over range(stop) or range(start, stop)
            if (
                isinstance(g.iter, ast.Call)
                and helpers.get_func_id(g.iter, visitor.ns) == "range"
                and len(g.iter.args) < 3
            ):
                var = gen_visitor.visit(g.target).latex
                sta, sto, _ = _get_range_args(g.iter)

                sub = f"{var} = {gen_visitor.visit(sta).latex}"

                if isinstance(sto, ast.Constant) and isinstance(sto.value, int):
                    sup = str(sto.value - 1)
                else:
                    sup_node = ast.BinOp(sto, ast.Sub(), ast.Constant(1))
                    sup = visitor.visit(sup_node).latex

                ops.append(op_symbol + "_{" + sub + "}^{" + sup + "}")

            # element-wise operation
            else:
                comp = gen_visitor.visit(g).latex
                ops.append(op_symbol + "_{" + comp + "}")

        op = r"\,".join(ops)

    operand = gen_visitor.visit_operand(operand_node, op_rank).latex

    start_default, start_op, start_rank = {
        r"\sum": (0, " + ", ranks.BELOW_ADD_RANK),
        r"\prod": (1, r" \cdot ", ranks.BELOW_MULT_RANK),
    }[op_symbol]

    if helpers.get_object(start_node, visitor.ns) != start_default:
        start = visitor.visit_operand(start_node, ranks.BELOW_ADD_RANK).latex
        latex = f"{start}{start_op}{op} {operand}"
        rank = start_rank
    else:
        latex = f"{op} {operand}"
        rank = ranks.BELOW_MULT_RANK

    return ExprLatex(latex, rank)


def _exp(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert an math.exp call."""

    x_node = helpers.get_arg_node(node, 0, None, required=True)

    if any(isinstance(n, ast.Div) for n in ast.walk(x_node)):
        return common.rename(visitor, node, r"\exp")

    return common.wrap(visitor, node, "e^{", "}", rank=ranks.BELOW_POW_RANK)


def _log(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a math.log call."""

    base_node = helpers.get_arg_node(node, 1, "base")

    if base_node is None:
        return common.unary(visitor, node, r"\ln ")
    if isinstance(base_node, ast.Constant) and base_node.value == 10:
        return common.unary(visitor, node, r"\log ")
    if helpers.get_id(base_node) == "e":
        return common.unary(visitor, node, r"\ln ")

    base = visitor.visit(base_node).latex

    return common.unary(visitor, node, r"\log_{" + base + "} ")


def _isclose(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Convert a math.isclose call"""

    a_node = helpers.get_arg_node(node, 0, "a", required=True)
    b_node = helpers.get_arg_node(node, 1, "b", required=True)

    rank = ranks.BELOW_COMPARE_RANK
    a = visitor.visit_operand(a_node, rank).latex
    b = visitor.visit_operand(b_node, rank).latex

    latex = rf"{a} \approx {b}"

    return ExprLatex(latex, rank)


register_call_converter(int, common.get_result_and_convert)
register_call_converter(float, common.get_result_and_convert)
register_call_converter(complex, common.get_result_and_convert)
register_call_converter(list, common.get_result_and_convert)
register_call_converter(tuple, common.get_result_and_convert)
register_call_converter(set, common.get_result_and_convert)
register_call_converter(dict, common.get_result_and_convert)
register_call_converter(range, _range)
register_call_converter(decimal.Decimal, common.get_result_and_convert)
register_call_converter(fractions.Fraction, common.get_result_and_convert)

# fmt: off
# pylint: disable=line-too-long
register_call_converter(max, lambda v, n: common.rename(v, n, r"\max"))
register_call_converter(min, lambda v, n: common.rename(v, n, r"\min"))
register_call_converter(abs, lambda v, n: common.wrap(v, n, r"\left|", r"\right|"))
register_call_converter(sum, _sum)

register_call_converter(math.fabs, lambda v, n: common.wrap(v, n, r"\left|", r"\right|"))
register_call_converter(math.fsum, _sum)
register_call_converter(math.prod, _prod)
register_call_converter(math.ceil, lambda v, n: common.wrap(v, n, r"\left\lceil", r"\right\rceil"))
register_call_converter(math.floor, lambda v, n: common.wrap(v, n, r"\left\lfloor", r"\right\rfloor"))
register_call_converter(math.comb, lambda v, n: common.rename(v, n, r"\operatorname{C}"))
register_call_converter(math.perm, lambda v, n: common.rename(v, n, r"\operatorname{P}"))
register_call_converter(math.factorial, lambda v, n: common.unary(v, n, "", "!"))
register_call_converter(math.gamma, lambda v, n: common.rename(v, n, r"\Gamma"))

register_call_converter(math.exp, _exp)
register_call_converter(math.log, _log)
register_call_converter(math.log10, lambda v, n: common.unary(v, n, r"\log "))
register_call_converter(math.log1p, lambda v, n: common.wrap(v, n, r"\ln \left(1 +", r"\right)"))
register_call_converter(math.log2, lambda v, n: common.unary(v, n, r"\log_{2} "))
register_call_converter(math.sqrt, lambda v, n: common.wrap(v, n, r"\sqrt{", "}", rank=ranks.BELOW_POW_RANK))
register_call_converter(math.cbrt, lambda v, n: common.wrap(v, n, r"\sqrt[3]{", "}", rank=ranks.BELOW_POW_RANK))
register_call_converter(math.isclose, _isclose)

register_call_converter(math.sin, lambda v, n: common.unary(v, n, r"\sin "))
register_call_converter(math.cos, lambda v, n: common.unary(v, n, r"\cos "))
register_call_converter(math.tan, lambda v, n: common.unary(v, n, r"\tan "))
register_call_converter("csc", lambda v, n: common.unary(v, n, r"\csc "))
register_call_converter("sec", lambda v, n: common.unary(v, n, r"\sec "))
register_call_converter("cot", lambda v, n: common.unary(v, n, r"\cot "))
register_call_converter(math.sinh, lambda v, n: common.unary(v, n, r"\sinh "))
register_call_converter(math.cosh, lambda v, n: common.unary(v, n, r"\cosh "))
register_call_converter(math.tanh, lambda v, n: common.unary(v, n, r"\tanh "))
register_call_converter("csch", lambda v, n: common.unary(v, n, r"\operatorname{csch} "))
register_call_converter("sech", lambda v, n: common.unary(v, n, r"\operatorname{sech} "))
register_call_converter("coth", lambda v, n: common.unary(v, n, r"\coth "))
register_call_converter(math.asin, lambda v, n: common.unary(v, n, r"\arcsin "))
register_call_converter("arcsin", lambda v, n: common.unary(v, n, r"\arcsin "))
register_call_converter(math.acos, lambda v, n: common.unary(v, n, r"\arccos "))
register_call_converter("arccos", lambda v, n: common.unary(v, n, r"\arccos "))
register_call_converter(math.atan, lambda v, n: common.unary(v, n, r"\arctan "))
register_call_converter(math.atan2, lambda v, n: common.unary(v, n, r"\arctan "))
register_call_converter("arctan", lambda v, n: common.unary(v, n, r"\arctan "))
register_call_converter("arccsc", lambda v, n: common.unary(v, n, r"\arccsc "))
register_call_converter("arcsec", lambda v, n: common.unary(v, n, r"\arcsec "))
register_call_converter("arccot", lambda v, n: common.unary(v, n, r"\arccot "))
register_call_converter(math.asinh, lambda v, n: common.unary(v, n, r"\operatorname{arsinh} "))
register_call_converter("arsinh", lambda v, n: common.unary(v, n, r"\operatorname{arsinh} "))
register_call_converter(math.acosh, lambda v, n: common.unary(v, n, r"\operatorname{arcosh} "))
register_call_converter("arcosh", lambda v, n: common.unary(v, n, r"\operatorname{arcosh} "))
register_call_converter(math.atanh, lambda v, n: common.unary(v, n, r"\operatorname{artanh} "))
register_call_converter("artanh", lambda v, n: common.unary(v, n, r"\operatorname{artanh} "))
register_call_converter("arcsch", lambda v, n: common.unary(v, n, r"\operatorname{arcsch} "))
register_call_converter("arsech", lambda v, n: common.unary(v, n, r"\operatorname{arsech} "))
register_call_converter("arcoth", lambda v, n: common.unary(v, n, r"\operatorname{arcoth} "))
