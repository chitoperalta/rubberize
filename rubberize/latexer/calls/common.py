"""Useful non-specific call converters."""

from __future__ import annotations

import ast
import copy
from typing import TYPE_CHECKING

from rubberize.latexer import formatters, helpers, ranks, rules
from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.objects import convert_object

if TYPE_CHECKING:
    from rubberize.latexer.visitors import ExprVisitor


def no_substitution(visitor: ExprVisitor) -> ExprVisitor:
    """Return a copy of the visitor without a namespace to suppress
    generating a substitution display mode.
    """

    if visitor.ns is not None:
        visitor = copy.copy(visitor)
        visitor.ns = None

    return visitor


def get_result_and_convert(
    visitor: ExprVisitor, node: ast.Call
) -> ExprLatex | None:
    """Get the resulting object of an ast.Call node, and then convert
    the object to latex."""

    obj = helpers.get_object(node, visitor.ns)

    if obj is None:
        return None

    return convert_object(obj)


# pylint: disable-next=too-many-arguments
def wrap(
    visitor: ExprVisitor,
    node: ast.Call,
    prefix: str,
    suffix: str,
    sep: str = r",\, ",
    *,
    rank: int = ranks.VALUE_RANK,
) -> ExprLatex:
    """Remove the name and wrap prefix, suffix, and separator to args."""

    args = [visitor.visit(a).latex for a in node.args]

    for kw in node.keywords:
        val = visitor.visit(kw.value).latex
        if kw.arg is None:
            args.append("{**}" + val)
        else:
            kwarg = formatters.format_name(kw.arg)
            args.append(f"{kwarg}{rules.KWARG_ASSIGN}{val}")

    latex = formatters.format_delims(prefix, sep.join(args), suffix)

    return ExprLatex(latex, rank)


# pylint: disable-next=too-many-arguments
def wrap_method(
    visitor: ExprVisitor,
    node: ast.Call,
    prefix: str,
    suffix: str,
    sep: str = rules.CALL_ARGS_SYNTAX[1],
    *,
    rank: int = ranks.VALUE_RANK,
) -> ExprLatex | None:
    """Remove the name, add the object of the method call as the first
    argument, and wrap prefix, suffix, and separator to args.

    foo.bar(a, b) -> (foo, a, b)
    """

    if not isinstance(node.func, ast.Attribute):
        return None

    args = [visitor.visit(node.func.value).latex]

    for a in node.args:
        args.append(visitor.visit(a).latex)

    for kw in node.keywords:
        val = visitor.visit(kw.value).latex
        if kw.arg is None:
            args.append("{**}" + val)
        else:
            kwarg = formatters.format_name(kw.arg)
            args.append(f"{kwarg}{rules.KWARG_ASSIGN}{val}")

    latex = formatters.format_delims(prefix, sep.join(args), suffix)

    return ExprLatex(latex, rank)


def rename(
    visitor: ExprVisitor,
    node: ast.Call,
    name: str,
    *,
    rank: int = ranks.CALL_RANK,
) -> ExprLatex:
    """Change the operator name and retain the default call syntax."""

    prefix, sep, suffix = rules.CALL_ARGS_SYNTAX
    prefix = f"{name} {prefix}"

    return wrap(visitor, node, prefix, suffix, sep, rank=rank)


def rename_method(
    visitor: ExprVisitor,
    node: ast.Call,
    name: str,
    *,
    rank: int = ranks.CALL_RANK,
) -> ExprLatex | None:
    """Change the operator name, add the object of the method call as
    the first argument, and retain the default call syntax.
    """

    prefix, sep, suffix = rules.CALL_ARGS_SYNTAX
    prefix = f"{name} {prefix}"

    return wrap_method(visitor, node, prefix, suffix, sep, rank=rank)


def unary(
    visitor: ExprVisitor,
    node: ast.Call,
    prefix: str,
    suffix: str = "",
    *,
    rank: int = ranks.BELOW_POW_RANK,
) -> ExprLatex:
    """Math function that notationally take only one argument."""

    iden = helpers.get_id(node.func)
    arg = node.args[0]

    # special cases: arg is factorial or exponentiation
    is_fac = isinstance(arg, ast.Call) and (
        iden == "factorial" or helpers.get_id(arg) == "factorial"
    )
    is_pow = isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Pow)

    arg = visitor.visit_operand(arg, rank, force=is_fac or is_pow).latex
    latex = formatters.format_delims(prefix, arg, suffix)

    return ExprLatex(latex, rank)


def first_arg(visitor: ExprVisitor, node: ast.Call) -> ExprLatex:
    """Visit and return LaTeX for the first argument only, effectively
    hiding the call on the argument.
    """

    return visitor.visit(node.args[0])


def hide_method(visitor: ExprVisitor, node: ast.Call) -> ExprLatex | None:
    """Visit and return LaTeX of the parent object of a method call,
    effectively hiding the call itself and its arguments.
    """

    if not isinstance(node.func, ast.Attribute):
        return None

    return visitor.visit(node.func.value)
