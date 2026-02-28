"""These functions convert expression nodes to LaTeX string, formatted
to one of these display modes:

- **Definition mode**: The base form of the expression, before any
    specific values are substituted in. Use `definition()`.
- **Substitution mode**: Shows the expression after numerical values
    have been substituted for the variables. Use `substitution()`.
- **Result mode**: The final calculated value of the expression after
    all operations have been performed. Use `result()`.

A function to gather all three modes as a list, with redundant forms
removed, is provided: `all_modes()`.
"""

import ast
from typing import Any, Optional

from rubberize.config import config
from rubberize.latexer.node_helpers import get_object
from rubberize.latexer.node_visitors import ExprVisitor
from rubberize.latexer.objects import convert_object


def definition(
    node: ast.expr, namespace: Optional[dict[str, Any]] = None
) -> str:
    """Get the LaTeX string for the expression node. Namespace can be
    supplied to apply special conversions to certain nodes that refer to
    a specific object types.

    Args:
        node: The node to generate LaTeX from.
        namespace: A dictionary of identifier and object pairs.

    Returns:
        The LaTeX representation for the node.
    """

    return ExprVisitor(namespace).visit(node).latex


def substitution(node: ast.expr, namespace: Optional[dict[str, Any]]) -> str:
    """Get the LaTeX string for the expression node with values in the
    namespace substituted.

    Accepts `namespace = None`, in which case it works like the function
    `definition()`.

    Args:
        node: The node to generate LaTeX from.
        namespace: A dictionary of identifier and object pairs.

    Returns:
        The LaTeX representation for the expression node.
    """

    return ExprVisitor(namespace, is_subst=True).visit(node).latex


def result(node: ast.expr, namespace: dict[str, Any]) -> str:
    """Get the value of an expression node by retrieving its referenced
    object from the namespace or using `eval()` with the namespace as
    globals, and then converting it to LaTeX.

    If no object is retrieved, `definition()` is called on the node.

    Args:
        node: The node to generate LaTeX from.
        namespace: A dictionary of identifier and object pairs.

    Returns:
        The LaTeX representation for the expression node.
    """

    obj = get_object(node, namespace)
    converted_obj = convert_object(obj) if obj is not None else None
    if converted_obj is not None:
        return converted_obj.latex
    return definition(node, namespace)


def all_modes(
    node: ast.expr,
    namespace: Optional[dict[str, Any]] = None,
    result_node: Optional[ast.expr] = None,
) -> list[str]:
    """Collects all expression display modes of an expression node.

    Args:
        node: The expression node to generate LaTeX from.
        namespace: A dictionary of identifier and object pairs.
        result_node: The node which will be used to retrieve the object
            for `result()`. If not supplied, it will use the specified
            node.

    Returns:
        The LaTeX representation for the expression node.
    """

    modes = []

    if config.show_definition:
        modes.append(definition(node, namespace))

    if namespace and config.show_substitution:
        substituted_expr = substitution(node, namespace)
        if substituted_expr not in modes:
            modes.append(substituted_expr)

    if namespace and config.show_result:
        result_node = result_node or node
        result_expr = result(result_node, namespace)
        if result_expr not in modes:
            modes.append(result_expr)

    return modes
