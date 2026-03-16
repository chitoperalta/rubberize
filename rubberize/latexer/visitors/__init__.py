"""Node visitors.

Python's AST follows a hierarchy:

    1.  ast.mod: The root of the AST, containing a single statement or a
        sequence of statements that make up a module.
    2.  ast.stmt: A complete Python instruction that carry out action.
        Statements can define structures (variable assignments, function
        definitions, etc.), control execution (if-elif-else blocks, for
        loops, etc.), or modify state (module imports, expression
        statements, etc.).
    3.  ast.expr: The building blocks of statements. Constructs that
        evaluate to a value and can be part of another expression or a
        statement.

For example, the Python code `x = a + 1` follows the following AST:

```
Module(                                         # ast.mod: ast.Module
    body=[
        Assign(                                 # ast.stmt: ast.Assign
            targets=[
                Name(id='x', ctx=Store())],     # ast.expr: ast.Name
            value=BinOp(                        # ast.expr: ast.BinOp
                left=Name(id='a', ctx=Load()),  # ast.expr: ast.Name
                op=Add(),
                right=Constant(value=1)))],     # ast.expr: asr.Constant
    type_ignores=[])
```

These node visitors provides a structured way to traverse the hierarchy
to generate LaTeX for each node.
"""

from rubberize.latexer.visitors.expr_visitor import ExprVisitor
from rubberize.latexer.visitors.stmt_visitor import StmtVisitor
from rubberize.latexer.visitors.mod_visitor import ModVisitor
