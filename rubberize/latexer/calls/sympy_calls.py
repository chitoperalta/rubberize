"""Converters for Sympy calls."""

import ast
from typing import Optional, TYPE_CHECKING

import sympy as sp

from rubberize import exceptions
from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.calls.common import hide_method
from rubberize.latexer.calls.convert_call import register_call_converter
from rubberize.latexer.node_helpers import get_id, is_method, is_class
from rubberize.latexer.ranks import BELOW_MULT_RANK

if TYPE_CHECKING:
    from rubberize.latexer.node_visitors import ExprVisitor


def _subs(visitor: "ExprVisitor", call: ast.Call) -> Optional[ExprLatex]:
    """Convert a `subs()` method call."""

    method = get_id(call.func)
    assert method == "subs"
    rank = BELOW_MULT_RANK

    if not is_method(call, sp.Expr, method, visitor.namespace):
        return None

    assert isinstance(call.func, ast.Attribute)
    expr = visitor.visit(call.func.value)

    if len(call.args) == 2:
        old = visitor.visit(call.args[0])
        new = visitor.visit(call.args[1])
        sub_latex = old.latex + " = " + new.latex
    elif len(call.args) == 1 and isinstance(call.args[0], ast.Dict):
        olds = [visitor.visit(o) for o in call.args[0].keys if o]
        news = [visitor.visit(n) for n in call.args[0].values if n]
        subs = [o.latex + " = " + n.latex for o, n in zip(olds, news)]
        sub_latex = r" \\ ".join(subs)
        if len(subs) > 1:
            sub_latex = r"\substack{" + sub_latex + "}"
    else:
        raise exceptions.RubberizeSyntaxError(
            f"Syntax not supported: f{ast.unparse(call)}"
        )

    latex = r"\left. " + expr.latex + r" \right|_{" + sub_latex + "}"

    return ExprLatex(latex, rank)


def _get_sympy_expr_and_args(
    visitor: "ExprVisitor", call: ast.Call
) -> tuple[ast.expr | None, list[ast.expr] | None]:
    """Collect appropriate operand and args for the function or method
    call.

    Since Sympy operations can either be called as a method of the
    expression or as a func with the expression as the first argument,
    we need this func to handle both cases.
    """

    name = get_id(call.func)
    assert name is not None

    if is_method(call, sp.Expr, name, visitor.namespace):
        assert isinstance(call.func, ast.Attribute)
        return call.func.value, call.args
    if is_class(call.args[0], sp.Expr, visitor.namespace):
        return call.args[0], call.args[1:]
    return None, None


def _underlabel(
    visitor: "ExprVisitor", call: ast.Call, label: Optional[str] = None
) -> Optional[ExprLatex]:
    """Convert a Sympy function or method call for an `Expr` instance.
    Renders the expression with a labeled underbracket indicating the
    operation to be performed on the expression.
    """

    if label is None:
        label = get_id(call.func) or "Sympy operation"

    func_value, args = _get_sympy_expr_and_args(visitor, call)
    if func_value is None or args is None:
        return None

    rank = BELOW_MULT_RANK

    opd = visitor.visit(func_value)
    elts_latex = [visitor.visit(a).latex for a in args]
    arglist = r",\, ".join(elts_latex)
    latex = (
        r"\underbracket{"
        + (opd.latex + r"}_{\text{" + label + r"} \," + arglist)
        + "}"
    )
    return ExprLatex(latex, rank)


def _diff(visitor: "ExprVisitor", call: ast.Call) -> Optional[ExprLatex]:
    """Convert a `diff()` function or method call."""

    assert get_id(call.func) == "diff"
    rank = BELOW_MULT_RANK

    func_value, args = _get_sympy_expr_and_args(visitor, call)
    if func_value is None or args is None:
        return None

    opd = visitor.visit_opd(func_value, rank)
    diffs_latex = [
        r"\frac{\mathrm{d}}{\mathrm{d}" + visitor.visit(a).latex + "}"
        for a in args
    ]
    diffs_latex.reverse()
    differential_latex = " ".join(diffs_latex) + " "
    latex = differential_latex + opd.latex

    return ExprLatex(latex, rank)


def _integration(visitor: "ExprVisitor", call: ast.Call) -> Optional[ExprLatex]:
    """Convert an `Integral()` instantiation, or an `integrate()`
    function or method call.
    """

    name = get_id(call.func)
    assert name in ("integrate", "Integral")
    rank = BELOW_MULT_RANK

    if name == "integrate":
        func_value, args = _get_sympy_expr_and_args(visitor, call)
        if func_value is None or args is None:
            return None
    elif name == "Integral":
        func_value, args = call.args[0], call.args[1:]
    else:
        return None

    opd = visitor.visit_opd(func_value, rank)

    ints_latex = []
    diffs_latex = []
    for var in args:
        if isinstance(var, ast.Name):
            ints_latex.append(r"\int")
            diffs_latex.append(r"\, \mathrm{d}" + visitor.visit(var).latex)
        elif isinstance(var, ast.Tuple) and len(var.elts) == 2:
            ints_latex.append(
                r"\int\limits^{" + visitor.visit(var.elts[1]).latex + "}"
            )
            diffs_latex.append(
                r"\, \mathrm{d}" + visitor.visit(var.elts[0]).latex
            )
        elif isinstance(var, ast.Tuple) and len(var.elts) == 3:
            ints_latex.append(
                r"\int\limits_{"
                + visitor.visit(var.elts[1]).latex
                + "}^{"
                + visitor.visit(var.elts[2]).latex
                + "}"
            )
            diffs_latex.append(
                r"\, \mathrm{d}" + visitor.visit(var.elts[0]).latex
            )
        else:
            raise exceptions.RubberizeSyntaxError(
                f"Syntax not supported: f{ast.unparse(call)}"
            )

    ints_latex.reverse()
    integral_latex = "".join(ints_latex) + " "
    differential_latex = "".join(diffs_latex)
    latex = integral_latex + opd.latex + differential_latex

    return ExprLatex(latex, rank)


def _limit(visitor: "ExprVisitor", call: ast.Call) -> Optional[ExprLatex]:
    """Convert a `limit()` function or method call."""

    assert get_id(call.func) == "limit"
    rank = BELOW_MULT_RANK

    func_value, args = _get_sympy_expr_and_args(visitor, call)
    if func_value is None or args is None:
        return None

    opd = visitor.visit_opd(
        func_value,
        BELOW_MULT_RANK,
    )
    var_latex, point_latex = [visitor.visit(a).latex for a in args]
    limit_latex = r"\lim_{" + var_latex + r" \to " + point_latex + "} "
    return ExprLatex(limit_latex + opd.latex, rank)


# fmt: off
register_call_converter("subs", _subs)
register_call_converter("evalf", lambda v, c: hide_method(v, c, sp.Expr))

register_call_converter("simplify", _underlabel)
register_call_converter("expand", _underlabel)
register_call_converter("factor", _underlabel)
register_call_converter("collect", _underlabel)
register_call_converter("cancel", _underlabel)
register_call_converter("apart", _underlabel)
register_call_converter("trigsimp", lambda v, c: _underlabel(v, c, "simplify trig"))
register_call_converter("expand_trig", lambda v, c: _underlabel(v, c, "expand trig"))
register_call_converter("powsimp", lambda v, c: _underlabel(v, c, "simplify power"))
register_call_converter("expand_power_exp", lambda v, c: _underlabel(v, c, "expand exponents"))
register_call_converter("expand_power_base", lambda v, c: _underlabel(v, c, "expand base"))
register_call_converter("powdenest", lambda v, c: _underlabel(v, c, "denest power"))
register_call_converter("expand_log", lambda v, c: _underlabel(v, c, "expand log"))
register_call_converter("logcombine", lambda v, c: _underlabel(v, c, "simplify log"))

register_call_converter("diff", _diff)
register_call_converter("integrate", _integration)
register_call_converter("Integral", _integration)
register_call_converter("limit", _limit)
