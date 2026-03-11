"""Functions to convert ast.expr nodes to LaTeX, formatted to one of
these display modes using ExprVisitor:

definition: The base form of the expression, before any specific values
    are substituted in
substitution: Shows the expression after numerical values have been
    substituted for the variables.
result: The final calculated value of the expression after all
    operations have been performed

all_modes: Gather all three modes as a list, excluding repeated forms if
    they converged to the same LaTeX.
"""

import ast

from rubberize.config import config
from rubberize.latexer import helpers
from rubberize.latexer.objects import convert_object
from rubberize.latexer.visitors import ExprVisitor


def definition(node: ast.expr, ns: dict[str, object] | None = None) -> str:
    """Return the LaTeX for the ast.expr node, in definition form.

    ns can be supplied to apply special conversions to specific object
        types if defined in rubberize.latexer.objects.

    Args:
        node: The node to investigate.
        ns: Name and object mapping.
    """

    return ExprVisitor(ns).visit(node).latex


def substitution(node: ast.expr, ns: dict[str, object] | None = None) -> str:
    """Return the LaTex for the ast.expr node, in substituted form.

    Args:
        node: The node to investigate.
        ns: Name and object mapping.
    """

    return ExprVisitor(ns, is_subst=True).visit(node).latex


def result(node: ast.expr, ns: dict[str, object] | None = None) -> str:
    """Return the LaTeX for the ast.expr node result.

    The result is retrieved from its referenced object found in ns, or
    using eval(). The result is then converted to LaTeX using
    rubberize.latexer.objects.

    Args:
        node: The node to investigate.
        ns: Name and object mapping.
    """

    obj = helpers.get_object(node, ns)
    obj_latex = convert_object(obj) if obj is not None else None

    if obj_latex is not None:
        return obj_latex.latex

    return definition(node, ns)


def all_modes(
    node: ast.expr,
    ns: dict[str, object] | None = None,
    result_node: ast.expr | None = None,
) -> list[str]:
    """Collects all LaTeX display modes for the ast.expr node.

    Args:
        node: The node to investigate.
        ns: Name and object mapping.
        result_node: The node which will be used by result() to retrieve
            the object. If not supplied, it will use node.
    """

    latexes = []

    if config.show_definition:
        definition_latex = definition(node, ns)
        latexes.append(definition_latex)

    if ns and config.show_substitution:
        substitution_latex = substitution(node, ns)
        if substitution_latex not in latexes:
            latexes.append(substitution_latex)

    if ns and config.show_result:
        result_latex = result(result_node or node, ns)
        if result_latex not in latexes:
            latexes.append(result_latex)

    return latexes
