"""Tests for node helpers"""

import ast
import pytest

from rubberize.latexer.node_visitors import ExprVisitor
from rubberize.latexer.ranks import MULT_RANK
from rubberize.latexer.node_helpers import get_operand_type


def get_expr_node(source: str):
    """Helper function to parse an expression and return its AST node."""
    tree = ast.parse(source, mode="eval")
    return tree.body


# Define test cases in a dictionary
test_cases = {
    # Numeric values
    "0": "N",
    "1": "N",
    "1000": "N",
    "-5": "-N",
    "3.14": "N",
    "-2.718": "-N",
    # Sci notation not handled because its always bracketed
    # Letter variables (single-character base name)
    "x": "L",
    "y_foo": "L",
    "z_hat": "L",
    "S_star_ult": "L",
    "epsilon": "L",
    "DeltaT": "L",
    "psiQ": "L",
    "-a": "-L",
    "-b_foo": "-L",
    "-c_hat": "-L",
    "-phiR_n": "-L",
    # Word variables (multi-character base name)
    "foo": "W",
    "bar123": "W",
    "foo_alpha": "W",
    "gammaLoad": "W",
    "-baz_ly": "-W",
    "-tot_bar": "-W",
    "-xalpha": "-W",
    # Function calls
    "f(x)": "C",
    "sin(theta)": "C",
    "foo_baz(a + b)": "C",
    "-g(y, z)": "-C",
    "sqrt(x^2 + y^2)": "B",  # Sqrt treated as B
    "ceil(132.23)": "B",  # Also others that generate brackets
    "float(3)": "N",  # Should transform to number
    # # Bracketed expressions
    "(a + b)": "B",
    "(x - y)": "B",
    "-(m + n)": "-B",  # Signed bracketed expression
    "a / b": "B",  # Div treated as B
    "a // b": "B",  # Floor div treated as B
}


# Convert to (source, is_left, expected) tuples for pytest
expanded_cases = [
    (source, is_left, expected)
    for source, expected in test_cases.items()
    for is_left in [True, False]
]


@pytest.mark.parametrize("source, is_left, expected", expanded_cases)
def test_get_operand_type(source, is_left, expected):
    """Test get_operand_type()"""

    node = get_expr_node(source)
    visitor = ExprVisitor()
    latex = visitor.visit_opd(node, MULT_RANK).latex
    result = get_operand_type(node, latex, is_left=is_left)
    print(result)
    assert result == expected
