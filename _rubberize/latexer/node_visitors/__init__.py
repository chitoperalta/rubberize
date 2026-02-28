"""Node visitors.

Python's AST follows a hierarchy:

    1.  `mod` nodes: The root of the AST, containing a single
        statement or a sequence of statements that make up a module.
    2.  `stmt` nodes: A complete Python instruction that carry out an
        action. Statements can define structures (variable assignments,
        function definitions, etc.), control execution (`if` blocks,
        `for` loops, etc.), or modify state (module imports, expression
        statements, etc.).
    3.  `expr`: The building blocks of statements. These are constructs
        that evaluate to a value and can be part of another expression or a statement.

For example, the Python code `x = a + 1` follows the following AST:

```
Module(  # `mod` node
    body=[
        Assign(  # `stmt` node
            targets=[
                Name(id='x', ctx=Store())],  # `expr` node
            value=BinOp(  # `expr` node
                left=Name(id='a', ctx=Load()),  # `expr` node
                op=Add(),
                right=Constant(value=1)))],  # `expr` node
    type_ignores=[])
```

The `stmt` node `Assign` represents the variable assignment, and the
expression `expr` node `BinOp` represents the operation `a + 1`, which
is the `Assign`'s `value`.

These node visitors provides a structured way to traverse the hierarchy
to generate LaTeX representation for each node.
"""

from rubberize.latexer.node_visitors.expr_visitor import ExprVisitor
from rubberize.latexer.node_visitors.stmt_visitor import StmtVisitor
from rubberize.latexer.node_visitors.mod_visitor import ModVistor
