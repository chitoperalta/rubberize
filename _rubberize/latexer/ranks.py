"""Ranking of AST nodes in the order of operator precedence.

This module associates numerical precedence values to AST node types
based on Python's [operator precedence rules][1]. The values determine
whether a LaTeX representation of an operand node in an operation
requires to be wrapped in parentheses to visually indicate the intended
order of operations.

A higher rank indicates tighter binding, meaning the operation has a
higher precedence and is evaluated first.

For example, an expression written as `2 * 3 ** 4` is equivalent to
`2 * (3 ** 4)`. Since `**` (exponentiation, `ast.Pow`) has a rank of
`150` and `*` (multiplication, `ast.Mult`) has a rank of `130`, `**` is
evaluated first `(3 ** 4)` before multiplying by `2`.

To enforce a different evaluation order--such as computing `2 * 3` first
before exponentiation--parentheses are needed: `(2 * 3) ** 4`. The
ranking system ensures that when generating the LaTeX representation,
operands of an expression are correctly wrapped in parentheses as needed
to maintain the intended order of operations.

Each `ast.expr` node is assigned a rank by one of the visitor methods in
`ExprVisitor` via `get_rank()`, or in some cases, explicitly using
predefined helper constants (e.g. `VALUE_RANK`). The ranking information
for an expression is stored in the corresponding `ExprLatex` instance
created by `ExprVisitor`. If the expression is an operand, the
`visit_operand()` method in `ExprVisitor` is invoked by the operation's
visitor (e.g. `visit_BinOp()`) and uses this information to determine
whether parentheses are needed for the operand.

[1]: https://docs.python.org/3/reference/expressions.html#operator-precedence
"""

import ast

VALUE_RANK = 9_001
COLLECTIONS_RANK = 180
POW_RANK = 150
SIGNED_RANK = 140
MULT_RANK = DIV_RANK = 130
ADD_RANK = SUB_RANK = 120

BELOW_POW_RANK = POW_RANK - 1
BELOW_MULT_RANK = MULT_RANK - 1
BELOW_ADD_RANK = ADD_RANK - 1


# Rank of operators
_OPERATOR_RANKS: dict[type[ast.AST], int] = {
    ast.List: 180,
    ast.ListComp: 180,
    ast.Tuple: 180,
    ast.Dict: 180,
    ast.DictComp: 180,
    ast.Set: 180,
    ast.SetComp: 180,
    ast.GeneratorExp: 180,
    ast.Subscript: 170,
    ast.Slice: 170,
    ast.Call: 170,
    ast.Attribute: 170,
    ast.Await: 160,
    ast.Pow: 150,
    ast.UAdd: 140,
    ast.USub: 140,
    ast.Invert: 140,
    ast.Mult: 130,
    ast.MatMult: 130,
    ast.Div: 130,
    ast.FloorDiv: 130,
    ast.Mod: 130,
    ast.Add: 120,
    ast.Sub: 120,
    ast.LShift: 110,
    ast.RShift: 110,
    ast.BitAnd: 100,
    ast.BitXor: 90,
    ast.BitOr: 80,
    ast.Compare: 70,
    ast.Not: 60,
    ast.And: 50,
    ast.Or: 40,
    ast.IfExp: 30,
    ast.Lambda: 20,
    ast.NamedExpr: 10,
}


def get_rank(node: ast.expr) -> int:
    """Get the precedence rank of the given AST expression node.

    Assigns a numerical rank to an expression node based on precedence
    rules. Higher ranks indicate tighter binding. If the node represents
    a binary, unary, or boolean operation, the function looks up the
    rank of the operator (`node.op`). If no ranking is found, it is
    assumed that the node represents a single value, and `VALUE_RANK` is
    assigned.

    Args:
        node (ast.expr): The expression node to investigate.

    Returns:
        int: The precedence rank of the node. If the node type is not
            explicitly ranked, `VALUE_RANK` is returned.
    """

    if isinstance(node, (ast.BoolOp, ast.BinOp, ast.UnaryOp)):
        return _OPERATOR_RANKS[type(node.op)]
    return _OPERATOR_RANKS.get(type(node), VALUE_RANK)
